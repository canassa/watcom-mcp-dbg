#!/usr/bin/env python3
"""Test setting breakpoint at 0x00123966 in plague.exe"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 60)
    print("Testing breakpoint at 0x00123966")
    print("=" * 60)

    # Create debugger
    debugger = Debugger("c:/entomorph/plague.exe")

    try:
        # Start process
        print("\n1. Starting process...")
        debugger.start()

        # Run to initial breakpoint
        print("\n2. Running to initial breakpoint...")
        debugger.run_event_loop()

        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")
        print(f"   Reason: {debugger.context.stop_info.reason}")

        # List modules at initial breakpoint
        print("\n3. Modules loaded at initial breakpoint:")
        debugger.list_modules()

        # Set breakpoint at 0x00123966
        print("\n4. Setting breakpoint at 0x00123966...")
        success = debugger.set_breakpoint("0x00123966")
        if success:
            print("   [OK] Breakpoint set")
        else:
            print("   [FAILED] Could not set breakpoint")

        # Continue execution
        print("\n5. Continuing execution...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        # Check if we stopped
        if debugger.context.is_stopped():
            print(f"\n6. Stopped at: 0x{debugger.context.current_address:08x}")
            print(f"   Reason: {debugger.context.stop_info.reason}")

            # List all modules
            print("\n7. All loaded modules:")
            debugger.list_modules()

            # List breakpoints
            print("\n8. Breakpoints:")
            debugger.list_breakpoints()

            # Get registers
            print("\n9. Registers:")
            eip = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EIP'
            )
            eax = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EAX'
            )
            esp = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'ESP'
            )
            print(f"   EIP = 0x{eip:08x}")
            print(f"   EAX = 0x{eax:08x}")
            print(f"   ESP = 0x{esp:08x}")
        elif debugger.context.is_exited():
            print("\n6. Process exited")
            print(f"   Exit code: {debugger.context.exit_code}")

            # List all modules that were loaded
            print("\n7. All modules that were loaded:")
            debugger.list_modules()
        else:
            print("\n6. Process still running")

    finally:
        print("\n8. Stopping debugger...")
        debugger.stop()

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
