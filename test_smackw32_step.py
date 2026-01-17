#!/usr/bin/env python3
"""
Test: Set breakpoint at SMACKW32.DLL + 0x3966, hit it, and single-step
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Breakpoint at SMACKW32.DLL + 0x3966 with single-step")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        # Set up deferred breakpoint
        original_on_load_dll = debugger._on_load_dll
        breakpoint_set = [False]

        def on_load_dll_with_breakpoint(event):
            original_on_load_dll(event)

            if not breakpoint_set[0]:
                smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
                if smackw32:
                    absolute_addr = smackw32.base_address + target_offset
                    print(f"\n   [DLL Load] SMACKW32.DLL at 0x{smackw32.base_address:08x}")
                    print(f"   [DLL Load] Setting breakpoint at 0x{absolute_addr:08x}")

                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(absolute_addr)
                    if bp:
                        print(f"   [DLL Load] Breakpoint {bp.id} set successfully!")
                        breakpoint_set[0] = True

        debugger._on_load_dll = on_load_dll_with_breakpoint

        print("3. Continuing execution (waiting for breakpoint to hit)...")
        print("   NOTE: Breakpoint may require game interaction to trigger")

        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        if debugger.context.is_stopped() and debugger.context.stop_info.reason == "breakpoint":
            print(f"\n{'='*70}")
            print("BREAKPOINT HIT AT SMACKW32.DLL + 0x3966!")
            print(f"{'='*70}")

            # Get current state
            eip = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EIP'
            )
            print(f"\nStopped at: 0x{eip:08x}")

            # Show registers before step
            print(f"\nRegisters BEFORE step:")
            regs_before = {}
            for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                regs_before[reg] = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, reg
                )
                print(f"  {reg:6s} = 0x{regs_before[reg]:08x}")

            # Get source location
            result = debugger.module_manager.resolve_address_to_line(eip)
            if result:
                module_name, loc, mod = result
                print(f"\nSource: {loc.file}:{loc.line}")

            # SINGLE STEP
            print(f"\n{'='*70}")
            print("Performing SINGLE STEP...")
            print(f"{'='*70}")

            debugger.context.set_stopped(debugger.context.stop_info)  # Reset to stopped
            debugger.step_over()

            if debugger.context.is_stopped():
                eip_after = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, 'EIP'
                )
                print(f"\nAfter step, at: 0x{eip_after:08x}")

                # Show what changed
                print(f"\nRegisters AFTER step:")
                for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                    val_after = debugger.process_controller.get_register(
                        debugger.context.current_thread_id, reg
                    )
                    val_before = regs_before[reg]
                    changed = " <--" if val_after != val_before else ""
                    print(f"  {reg:6s} = 0x{val_after:08x}{changed}")

                # Check what module/function we're in now
                module = debugger.module_manager.address_to_module(eip_after)
                if module:
                    offset = eip_after - module.base_address
                    print(f"\nNow in: {module.name} + 0x{offset:04x}")

                    # Try to get source
                    result = debugger.module_manager.resolve_address_to_line(eip_after)
                    if result:
                        module_name, loc, mod = result
                        print(f"Source: {loc.file}:{loc.line}")

                print(f"\n{'='*70}")
                print("STEP COMPLETE")
                print(f"{'='*70}")

        elif debugger.context.is_stopped():
            print(f"\n{'='*70}")
            print(f"Stopped for different reason: {debugger.context.stop_info.reason}")
            print(f"Address: 0x{debugger.context.current_address:08x}")
            print(f"{'='*70}")

        elif debugger.context.is_exited():
            print(f"\n{'='*70}")
            print("Process exited without hitting breakpoint")
            print(f"{'='*70}")
            if breakpoint_set[0]:
                print("\n  Breakpoint was set but never hit")
                print("  The code at SMACKW32.DLL + 0x3966 was not executed")
                print("  You may need to interact with the game to trigger it")
            else:
                print("\n  SMACKW32.DLL never loaded")

    finally:
        print("\nCleaning up...")
        debugger.stop()

    print(f"\n{'='*70}")
    print("Test complete")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
