#!/usr/bin/env python3
"""Test deferred breakpoint in SMACKW32.DLL at offset 0x3966"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 60)
    print("Testing deferred breakpoint in SMACKW32.DLL")
    print("Target: offset 0x3966")
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

        # Add a module load callback to set breakpoint when SMACKW32 loads
        original_on_load_dll = debugger._on_load_dll
        breakpoint_set = [False]  # Use list to modify in closure

        def on_load_dll_with_breakpoint(event):
            # Call original handler
            original_on_load_dll(event)

            # Check if SMACKW32.DLL just loaded and we haven't set breakpoint yet
            if not breakpoint_set[0]:
                smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
                if smackw32:
                    offset = 0x3966
                    absolute_addr = smackw32.base_address + offset
                    print(f"\n   [DLL Load Event] SMACKW32.DLL detected at 0x{smackw32.base_address:08x}")
                    print(f"   [DLL Load Event] Setting breakpoint at 0x{absolute_addr:08x} (base + 0x{offset:04x})")

                    # Set breakpoint using absolute address
                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(absolute_addr)
                    if bp:
                        print(f"   [DLL Load Event] Breakpoint {bp.id} set successfully!")
                        breakpoint_set[0] = True
                    else:
                        print(f"   [DLL Load Event] Failed to set breakpoint")

        # Replace the handler
        debugger._on_load_dll = on_load_dll_with_breakpoint

        # Continue execution - this will trigger DLL loads and our breakpoint will be set
        print("\n3. Continuing execution (will set breakpoint when SMACKW32 loads)...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        # Check result
        if debugger.context.is_stopped():
            print(f"\n4. Process stopped!")
            print(f"   Address: 0x{debugger.context.current_address:08x}")
            print(f"   Reason: {debugger.context.stop_info.reason}")

            # Get registers
            print("\n5. Registers:")
            eip = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EIP'
            )
            eax = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EAX'
            )
            ebx = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EBX'
            )
            ecx = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'ECX'
            )
            edx = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EDX'
            )
            esp = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'ESP'
            )
            ebp = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EBP'
            )
            print(f"   EIP = 0x{eip:08x}")
            print(f"   EAX = 0x{eax:08x}")
            print(f"   EBX = 0x{ebx:08x}")
            print(f"   ECX = 0x{ecx:08x}")
            print(f"   EDX = 0x{edx:08x}")
            print(f"   ESP = 0x{esp:08x}")
            print(f"   EBP = 0x{ebp:08x}")

            # Try to get source location
            print("\n6. Source location:")
            result = debugger.module_manager.resolve_address_to_line(eip)
            if result:
                module_name, loc, module = result
                print(f"   File: {loc.file}")
                print(f"   Line: {loc.line}")
                print(f"   Module: {module_name}")
            else:
                print(f"   No source information available")

            # List breakpoints
            print("\n7. Breakpoints:")
            debugger.list_breakpoints()

        elif debugger.context.is_exited():
            print("\n4. Process exited")
            if breakpoint_set[0]:
                print("   Breakpoint was set but never hit")
            else:
                print("   Breakpoint was never set (SMACKW32 may not have loaded)")

    finally:
        print("\n8. Stopping debugger...")
        debugger.stop()

    print("\n" + "=" * 60)
    print("[SUCCESS] Test complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
