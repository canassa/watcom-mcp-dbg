#!/usr/bin/env python3
"""Test breakpoint at SMACKW32.DLL + 0x3966"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Breakpoint at SMACKW32.DLL + 0x3966")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        # Set up deferred breakpoint for SMACKW32.DLL
        print(f"\n3. Setting up deferred breakpoint for SMACKW32.DLL + 0x{target_offset:04x}...")

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
                        print(f"   [DLL Load] Breakpoint {bp.id} set!")
                        breakpoint_set[0] = True
                    else:
                        print(f"   [DLL Load] Failed to set breakpoint")

        debugger._on_load_dll = on_load_dll_with_breakpoint

        print("4. Continuing execution...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        if debugger.context.is_stopped():
            print(f"\n{'='*70}")
            print("BREAKPOINT HIT!")
            print(f"{'='*70}")
            print(f"\nAddress: 0x{debugger.context.current_address:08x}")
            print(f"Reason: {debugger.context.stop_info.reason}")

            # Module info
            module = debugger.module_manager.address_to_module(debugger.context.current_address)
            if module:
                offset = debugger.context.current_address - module.base_address
                print(f"Module: {module.name} @ 0x{module.base_address:08x} + 0x{offset:04x}")

            # Registers
            print(f"\nRegisters:")
            for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                val = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, reg
                )
                print(f"  {reg:6s} = 0x{val:08x}")

            # Source location
            print(f"\nSource:")
            result = debugger.module_manager.resolve_address_to_line(
                debugger.context.current_address
            )
            if result:
                module_name, loc, mod = result
                print(f"  {loc.file}:{loc.line}")
            else:
                print(f"  No source available")

        elif debugger.context.is_exited():
            print(f"\n{'='*70}")
            print("Process exited")
            print(f"{'='*70}")
            if breakpoint_set[0]:
                print("  Breakpoint was set but never hit")
                print("  (Code at offset 0x3966 not executed during startup)")
            else:
                print("  SMACKW32.DLL never loaded")

    finally:
        print("\nCleaning up...")
        debugger.stop()

    print(f"\n{'='*70}")
    print("Test complete")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
