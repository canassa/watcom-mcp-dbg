"""
Test setting a breakpoint at specific address 0x0045240f
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger


def test_breakpoint_at_address():
    """Test breakpoint at 0x0045240f."""
    exe_path = "c:/entomorph/plague.exe"

    if not Path(exe_path).exists():
        print(f"Error: {exe_path} not found")
        return False

    print("=" * 60)
    print("Testing breakpoint at 0x0045240f")
    print("=" * 60)

    try:
        # Create debugger
        debugger = Debugger(exe_path)

        # Start process
        print("\n1. Starting process...")
        debugger.start()
        print("   Process started")

        # Run until first event (system breakpoint)
        print("\n2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at 0x{debugger.context.current_address:08x}")

        # Set breakpoint at the specified address
        print("\n3. Setting breakpoint at 0x0045240f...")
        success = debugger.set_breakpoint("0x0045240f")
        if not success:
            print("   Failed to set breakpoint")

        # List breakpoints to confirm
        debugger.list_breakpoints()

        # Continue execution to hit the breakpoint
        print("\n4. Continuing execution (will wait up to 10 seconds for breakpoint)...")
        import time
        start_time = time.time()

        # Continue and wait for breakpoint
        debugger.continue_execution()

        # Check if we hit the breakpoint
        if debugger.context.is_stopped():
            print(f"\n5. STOPPED at 0x{debugger.context.current_address:08x}")
            print(f"   Stop reason: {debugger.context.get_stop_reason()}")

            # Get current location info
            result = debugger.module_manager.resolve_address_to_line(
                debugger.context.current_address
            )

            if result:
                module_name, loc, module = result
                print(f"   Module: {module_name}")
                print(f"   Source: {Path(loc.file).name}:{loc.line}:{loc.column}")
                print(f"   File path: {loc.file}")
            else:
                print(f"   No source info available for this address")

            # Show registers
            if debugger.context.current_thread_id:
                print("\n6. Register state:")
                try:
                    regs = debugger.process_controller.get_all_registers(
                        debugger.context.current_thread_id
                    )
                    print(f"   EIP = 0x{regs['eip']:08x}")
                    print(f"   EAX = 0x{regs['eax']:08x}")
                    print(f"   EBX = 0x{regs['ebx']:08x}")
                    print(f"   ECX = 0x{regs['ecx']:08x}")
                    print(f"   EDX = 0x{regs['edx']:08x}")
                    print(f"   ESI = 0x{regs['esi']:08x}")
                    print(f"   EDI = 0x{regs['edi']:08x}")
                    print(f"   EBP = 0x{regs['ebp']:08x}")
                    print(f"   ESP = 0x{regs['esp']:08x}")
                    print(f"   EFLAGS = 0x{regs['eflags']:08x}")
                except Exception as e:
                    print(f"   Error reading registers: {e}")

            # Try to read some memory at this location
            print("\n7. Memory at breakpoint location:")
            try:
                mem = debugger.process_controller.read_memory(debugger.context.current_address, 16)
                hex_bytes = ' '.join(f'{b:02x}' for b in mem)
                print(f"   {hex_bytes}")
            except Exception as e:
                print(f"   Error reading memory: {e}")
        else:
            print("\n   Did not hit breakpoint (process may have exited or not reached that code)")
            print(f"   Current state: {debugger.context.state.value}")

        # Stop debugger
        print("\n8. Stopping debugger...")
        debugger.stop()

        print("\n" + "=" * 60)
        print("Test complete")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_breakpoint_at_address()
    sys.exit(0 if success else 1)
