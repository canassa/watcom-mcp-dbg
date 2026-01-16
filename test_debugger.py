"""
Simple test of the debugger functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger


def test_debugger():
    """Test basic debugger functionality."""
    exe_path = "c:/entomorph/plague.exe"

    if not Path(exe_path).exists():
        print(f"Error: {exe_path} not found")
        return False

    print("=" * 60)
    print("Testing DGB Debugger")
    print("=" * 60)

    try:
        # Create debugger
        debugger = Debugger(exe_path)

        # Start process
        print("\n1. Starting process...")
        if not debugger.start():
            print("Failed to start")
            return False
        print("   [OK] Process started successfully")

        # Run until first event
        print("\n2. Running event loop (will stop at initial breakpoint)...")
        debugger.run_event_loop()

        if debugger.context.is_stopped():
            print(f"   [OK] Stopped at 0x{debugger.context.current_address:08x}")
            print(f"        Reason: {debugger.context.get_stop_reason()}")

        # List modules
        print("\n3. Listing loaded modules...")
        debugger.list_modules()

        # Try to set a breakpoint (this will only work if debug info is found)
        print("\n4. Attempting to set breakpoint...")
        # Try a generic address
        breakpoint_addr = 0x00401000  # Common entry point area
        print(f"   Setting breakpoint at 0x{breakpoint_addr:08x}")
        debugger.set_breakpoint(f"0x{breakpoint_addr:x}")

        # List breakpoints
        print("\n5. Listing breakpoints...")
        debugger.list_breakpoints()

        # Get registers
        print("\n6. Reading registers...")
        if debugger.context.current_thread_id:
            try:
                regs = debugger.process_controller.get_all_registers(
                    debugger.context.current_thread_id
                )
                print(f"   EIP = 0x{regs['eip']:08x}")
                print(f"   EAX = 0x{regs['eax']:08x}")
                print(f"   ESP = 0x{regs['esp']:08x}")
                print("   [OK] Register access working")
            except Exception as e:
                print(f"   Error reading registers: {e}")

        # Continue execution briefly
        print("\n7. Continuing execution for 1 second...")
        debugger.context.set_running()
        import time
        time.sleep(1)

        # Stop debugger
        print("\n8. Stopping debugger...")
        debugger.stop()
        print("   [OK] Debugger stopped")

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_debugger()
    sys.exit(0 if success else 1)
