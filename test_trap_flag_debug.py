"""
Diagnostic test to check Trap Flag state
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import time
from dgb.debugger.core import Debugger

def cleanup_plague():
    """Kill any plague.exe processes"""
    import psutil
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if 'plague' in proc.info['name'].lower():
                print(f"Killing existing plague.exe process (PID {proc.info['pid']})")
                proc.kill()
                proc.wait(timeout=3)
        except:
            pass

def test_trap_flag():
    """Test if Trap Flag is being set incorrectly"""

    print("=" * 80)
    print("Diagnostic: Trap Flag State")
    print("=" * 80)

    cleanup_plague()
    time.sleep(0.5)

    exe_path = r"c:\entomorph\plague.exe"
    debugger = None

    try:
        # 1. Create and start debugger
        print("\n[1] Creating debugger...")
        debugger = Debugger(exe_path)
        debugger.start()

        # 2. Run to initial breakpoint
        print("[2] Running to entry point...")
        debugger.run_event_loop()

        assert debugger.context.is_stopped(), "Should stop at entry"
        print(f"    [OK] Stopped at entry point: 0x{debugger.context.current_address:08x}")

        # 3. Check EFlags at entry point
        print("\n[3] Checking EFlags at entry point...")
        thread_id = debugger.context.current_thread_id
        eflags = debugger.process_controller.get_register(thread_id, 'EFlags')
        tf_set = (eflags & 0x100) != 0
        print(f"    EFlags = 0x{eflags:08x}")
        print(f"    Trap Flag (TF) = {'SET' if tf_set else 'CLEAR'}")

        if tf_set:
            print("    [WARN] Trap Flag is SET at entry point! This should not happen.")
            print("    [FIX] Clearing Trap Flag...")
            eflags &= ~0x100
            debugger.process_controller.set_register(thread_id, 'EFlags', eflags)
            eflags_after = debugger.process_controller.get_register(thread_id, 'EFlags')
            print(f"    EFlags after clear = 0x{eflags_after:08x}")
            tf_set_after = (eflags_after & 0x100) != 0
            print(f"    Trap Flag after clear = {'SET' if tf_set_after else 'CLEAR'}")
        else:
            print("    [OK] Trap Flag is correctly CLEAR")

        # 4. Set breakpoint
        print("\n[4] Setting breakpoint at 0x0045240f...")
        success = debugger.set_breakpoint("0x0045240f")
        assert success, "Failed to set breakpoint"
        print("    [OK] Breakpoint set")

        # 5. Check EFlags again before continuing
        print("\n[5] Checking EFlags before continue...")
        eflags = debugger.process_controller.get_register(thread_id, 'EFlags')
        tf_set = (eflags & 0x100) != 0
        print(f"    EFlags = 0x{eflags:08x}")
        print(f"    Trap Flag (TF) = {'SET' if tf_set else 'CLEAR'}")

        if tf_set:
            print("    [ERROR] Trap Flag is SET before continue! This will cause single-step!")
        else:
            print("    [OK] Trap Flag is CLEAR")

        # 6. Continue
        print("\n[6] Continuing...")
        debugger.continue_execution()

        # 7. Check where we stopped
        timeout = 5
        start = time.time()
        while not debugger.context.is_stopped() and time.time() - start < timeout:
            time.sleep(0.1)

        if debugger.context.is_stopped():
            addr = debugger.context.current_address
            reason = debugger.context.get_stop_reason()
            thread_id = debugger.context.current_thread_id

            print(f"\n[7] Stopped at:")
            print(f"    Address: 0x{addr:08x}")
            print(f"    Reason: {reason}")

            # Check EFlags at stop
            eflags = debugger.process_controller.get_register(thread_id, 'EFlags')
            tf_set = (eflags & 0x100) != 0
            print(f"    EFlags = 0x{eflags:08x}")
            print(f"    Trap Flag (TF) = {'SET' if tf_set else 'CLEAR'}")

            if reason == "step":
                print(f"    [ERROR] Got unexpected single-step exception!")
                print(f"    This means Trap Flag was set when it shouldn't be")
            elif reason == "breakpoint" and addr == 0x0045240f:
                print(f"    [SUCCESS] Hit our breakpoint!")
            else:
                print(f"    [INFO] Stopped for reason: {reason}")

        print("\n" + "=" * 80)
        print("[DONE]")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        if debugger:
            try:
                debugger.stop()
            except:
                pass
        cleanup_plague()
        time.sleep(1)

if __name__ == '__main__':
    test_trap_flag()
