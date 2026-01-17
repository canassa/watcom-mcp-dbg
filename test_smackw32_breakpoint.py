#!/usr/bin/env python3
"""Test setting breakpoint in SMACKW32.DLL"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 60)
    print("Testing breakpoint in SMACKW32.DLL at offset 0x3966")
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

        # Continue and wait for SMACKW32.DLL to load
        print("\n3. Continuing to load modules...")
        debugger.context.set_running()
        debugger.waiting_for_event = True

        # Run for a bit to let modules load
        import threading
        import time

        # Run event loop in background briefly
        event_thread = threading.Thread(target=debugger.run_event_loop, daemon=True)
        event_thread.start()
        time.sleep(2)  # Give it time to load modules

        # Stop the event loop
        debugger.waiting_for_event = False
        event_thread.join(timeout=1)

        # Check if SMACKW32.DLL is loaded
        print("\n4. Checking for SMACKW32.DLL...")
        smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")

        if smackw32:
            print(f"   [OK] SMACKW32.DLL loaded at 0x{smackw32.base_address:08x}")
            print(f"        Has debug info: {smackw32.has_debug_info}")

            # Calculate absolute address for offset 0x3966
            offset = 0x3966
            absolute_addr = smackw32.base_address + offset
            print(f"\n5. Setting breakpoint at 0x{absolute_addr:08x} (base + 0x{offset:04x})...")

            success = debugger.set_breakpoint(f"0x{absolute_addr:x}")
            if success:
                print("   [OK] Breakpoint set")
            else:
                print("   [FAILED] Could not set breakpoint")

            # Continue execution
            print("\n6. Continuing execution...")
            debugger.context.set_running()
            debugger.waiting_for_event = True
            debugger.run_event_loop()

            # Check if we stopped
            if debugger.context.is_stopped():
                print(f"\n7. Stopped at: 0x{debugger.context.current_address:08x}")
                print(f"   Reason: {debugger.context.stop_info.reason}")

                # Get registers
                print("\n8. Registers:")
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

                # Try to get source
                print("\n9. Attempting to get source...")
                result = debugger.module_manager.resolve_address_to_line(eip)
                if result:
                    module_name, loc, module = result
                    print(f"   Location: {Path(loc.file).name}:{loc.line}")
                    print(f"   Module: {module_name}")
                else:
                    print("   No source information available at this address")

            elif debugger.context.is_exited():
                print("\n7. Process exited")
        else:
            print("   [FAILED] SMACKW32.DLL not loaded yet")
            print("\n   Loaded modules:")
            debugger.list_modules()

    finally:
        print("\n10. Stopping debugger...")
        debugger.stop()

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
