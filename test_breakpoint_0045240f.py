"""
Test breakpoint at 0x0045240f in plague.exe
This test verifies that the debugger doesn't corrupt plague.exe when hitting
a breakpoint at address 0x0045240f.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import time
import psutil
from dgb.debugger.core import Debugger

def cleanup_processes():
    """Kill any plague.exe processes"""
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if 'plague' in proc.info['name'].lower():
                print(f"Killing existing plague.exe process (PID {proc.info['pid']})")
                proc.kill()
                proc.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass

def test_breakpoint_0045240f():
    """Test breakpoint at 0x0045240f doesn't corrupt plague.exe"""

    print("=" * 80)
    print("Testing breakpoint at 0x0045240f in plague.exe")
    print("=" * 80)

    cleanup_processes()  # Clean slate
    time.sleep(0.5)

    exe_path = r"c:\entomorph\plague.exe"
    breakpoint_addr = 0x0045240f

    debugger = None

    try:
        # 1. Create and start debugger
        print("\n[1] Creating debugger...")
        debugger = Debugger(exe_path)

        print("[2] Starting debugger...")
        debugger.start()

        # 2. Run to initial breakpoint
        print("[3] Running to initial breakpoint (entry point)...")
        debugger.run_event_loop()

        assert debugger.context.is_stopped(), "Should stop at entry"
        print(f"    [OK] Stopped at entry point: 0x{debugger.context.current_address:08x}")

        # 3. Set breakpoint at target address
        print(f"\n[4] Setting breakpoint at 0x{breakpoint_addr:08x}...")
        success = debugger.set_breakpoint(f"0x{breakpoint_addr:x}")
        assert success, f"Failed to set breakpoint at 0x{breakpoint_addr:08x}"
        print(f"    [OK] Breakpoint set successfully")

        # 4. Continue to breakpoint
        print("\n[5] Continuing to breakpoint...")
        debugger.continue_execution()

        # Give it time to hit breakpoint (or crash)
        timeout = 10
        start = time.time()
        while not debugger.context.is_stopped() and time.time() - start < timeout:
            time.sleep(0.1)

        elapsed = time.time() - start
        print(f"    Stopped after {elapsed:.2f} seconds")

        # 5. Verify we hit the breakpoint
        print("\n[6] Verifying breakpoint hit...")
        assert debugger.context.is_stopped(), "Process should be stopped at breakpoint"

        current_addr = debugger.context.current_address
        stop_reason = debugger.context.get_stop_reason()

        print(f"    Current address: 0x{current_addr:08x}")
        print(f"    Stop reason: {stop_reason}")

        assert current_addr == breakpoint_addr, \
            f"Expected address 0x{breakpoint_addr:08x}, got 0x{current_addr:08x}"
        assert stop_reason == "breakpoint", \
            f"Expected stop reason 'breakpoint', got '{stop_reason}'"

        print(f"    [OK] Breakpoint hit correctly at 0x{breakpoint_addr:08x}")

        # 6. Read registers
        print("\n[7] Reading registers at breakpoint...")
        thread_id = debugger.context.current_thread_id
        regs = debugger.process_controller.get_all_registers(thread_id)
        print(f"    EIP    = 0x{regs['eip']:08x}")
        print(f"    EAX    = 0x{regs['eax']:08x}")
        print(f"    EBX    = 0x{regs['ebx']:08x}")
        print(f"    ECX    = 0x{regs['ecx']:08x}")
        print(f"    EDX    = 0x{regs['edx']:08x}")
        print(f"    ESP    = 0x{regs['esp']:08x}")
        print(f"    EBP    = 0x{regs['ebp']:08x}")
        print(f"    ESI    = 0x{regs['esi']:08x}")
        print(f"    EDI    = 0x{regs['edi']:08x}")
        print(f"    EFLAGS = 0x{regs['eflags']:08x}")

        # 7. Read memory at breakpoint
        print(f"\n[8] Reading memory at 0x{breakpoint_addr:08x}...")
        mem = debugger.process_controller.read_memory(breakpoint_addr, 16)
        hex_bytes = ' '.join(f'{b:02x}' for b in mem)
        print(f"    {hex_bytes}")

        # Check if we see 0xCC (breakpoint instruction)
        if mem[0] == 0xCC:
            print(f"    Note: First byte is 0xCC (breakpoint instruction)")
        else:
            print(f"    Note: First byte is 0x{mem[0]:02x} (original instruction)")

        # 8. Continue from breakpoint
        print(f"\n[9] Continuing from breakpoint...")
        debugger.continue_execution()

        # 9. Verify no corruption - give it a few seconds
        print("[10] Monitoring for corruption...")
        time.sleep(3)

        # Check if process crashed or has unexpected exceptions
        if debugger.context.is_exited():
            exit_code = debugger.context.stop_info.exception_code if debugger.context.stop_info else -1
            print(f"    Process exited with code {exit_code}")
            if exit_code == 0:
                print(f"    [OK] Clean exit")
            else:
                print(f"    [WARN] Non-zero exit code")
        elif debugger.context.is_stopped():
            reason = debugger.context.get_stop_reason()
            addr = debugger.context.current_address
            print(f"    Process stopped: reason={reason}, address=0x{addr:08x}")

            if reason == "exception":
                exc_code = debugger.context.stop_info.exception_code
                exc_addr = debugger.context.stop_info.exception_address
                print(f"    Exception code: 0x{exc_code:08x}")
                print(f"    Exception address: 0x{exc_addr:08x}")

                # Check for corruption-indicating exceptions
                if exc_code == 0x4000001f:
                    raise AssertionError(f"WOW64 single-step exception at 0x{exc_addr:08x} - possible Trap Flag not cleared!")
                elif exc_code == 0xc0000005:
                    raise AssertionError(f"Access violation at 0x{exc_addr:08x} - debugger corrupted execution!")
                elif exc_code in [0x80000003, 0x80000004]:
                    # Breakpoint or single-step - could be normal if we hit breakpoint again
                    print(f"    Note: Breakpoint/single-step exception (possibly hit breakpoint again)")
                else:
                    raise AssertionError(f"Unexpected exception 0x{exc_code:08x} at 0x{exc_addr:08x}")
            elif reason == "breakpoint":
                # Hit breakpoint again - this is OK if it's in a loop
                print(f"    [OK] Hit breakpoint again (likely in loop)")
            else:
                print(f"    [OK] Stopped normally: {reason}")
        else:
            print(f"    [OK] Process running normally")

        print("\n" + "=" * 80)
        print("[SUCCESS] Breakpoint test passed!")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"[FAILURE] {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 10. Cleanup
        print("\n[Cleanup] Stopping debugger and cleaning up processes...")
        if debugger:
            try:
                debugger.stop()
            except Exception as e:
                print(f"    Warning: Error stopping debugger: {e}")

        cleanup_processes()
        time.sleep(1)
        print("    [OK] Cleanup complete")

if __name__ == '__main__':
    success = test_breakpoint_0045240f()
    sys.exit(0 if success else 1)
