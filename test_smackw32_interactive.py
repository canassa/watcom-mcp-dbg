#!/usr/bin/env python3
"""
Test: Keep game running and wait for breakpoint at SMACKW32.DLL + 0x3966
This allows user interaction with the game to trigger the breakpoint
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Interactive breakpoint at SMACKW32.DLL + 0x3966")
    print("Game will stay running - interact with it to trigger breakpoint")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966
    current_bp_info = {"address": None, "base_addr": None}

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()

        # Set up persistent breakpoint
        original_on_load_dll = debugger._on_load_dll

        def on_load_dll_track_smackw32(event):
            original_on_load_dll(event)

            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                new_base = smackw32.base_address
                new_addr = new_base + target_offset

                if current_bp_info["base_addr"] != new_base:
                    if current_bp_info["address"]:
                        print(f"\n   [Reload] SMACKW32.DLL: 0x{current_bp_info['base_addr']:08x} -> 0x{new_base:08x}")
                        debugger.breakpoint_manager.breakpoints.pop(current_bp_info["address"], None)

                    print(f"   [BP] Setting at SMACKW32.DLL+0x{target_offset:04x} = 0x{new_addr:08x}")

                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(new_addr)
                    if bp:
                        print(f"   [BP] Breakpoint {bp.id} ready!")
                        current_bp_info["address"] = new_addr
                        current_bp_info["base_addr"] = new_base

        debugger._on_load_dll = on_load_dll_track_smackw32

        print("3. Continuing execution...")
        print("\n" + "=" * 70)
        print("GAME IS RUNNING")
        print("Waiting for breakpoint at SMACKW32.DLL + 0x3966...")
        print("Interact with the game window if needed")
        print("Press Ctrl+C to stop")
        print("=" * 70 + "\n")

        debugger.context.set_running()
        debugger.waiting_for_event = True

        # Run the event loop - it will stop when breakpoint hits
        debugger.run_event_loop()

        if debugger.context.is_stopped() and debugger.context.stop_info.reason == "breakpoint":
            print(f"\n{'='*70}")
            print("!!! BREAKPOINT HIT AT SMACKW32.DLL + 0x3966 !!!")
            print(f"{'='*70}")

            eip = debugger.process_controller.get_register(debugger.context.current_thread_id, 'EIP')
            print(f"\nHit at: 0x{eip:08x}")

            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                offset = eip - smackw32.base_address
                print(f"Module: SMACKW32.DLL @ 0x{smackw32.base_address:08x} + 0x{offset:04x}")

            # Registers
            print(f"\n{'='*70}")
            print("REGISTERS:")
            print(f"{'='*70}")
            regs = {}
            for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP', 'EFlags']:
                regs[reg] = debugger.process_controller.get_register(debugger.context.current_thread_id, reg)
                print(f"  {reg:6s} = 0x{regs[reg]:08x}")

            # Source
            result = debugger.module_manager.resolve_address_to_line(eip)
            if result:
                module_name, loc, mod = result
                print(f"\nSource: {loc.file}:{loc.line}")

            # SINGLE STEP
            print(f"\n{'='*70}")
            print("PERFORMING SINGLE STEP...")
            print(f"{'='*70}")

            debugger.step_over()

            if debugger.context.is_stopped():
                eip_after = debugger.process_controller.get_register(debugger.context.current_thread_id, 'EIP')

                print(f"\n{'='*70}")
                print(f"AFTER STEP: 0x{eip_after:08x}")
                print(f"{'='*70}")

                # Register changes
                print(f"\nRegister changes:")
                for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                    val_after = debugger.process_controller.get_register(debugger.context.current_thread_id, reg)
                    val_before = regs[reg]
                    if val_after != val_before:
                        print(f"  {reg:6s}: 0x{val_before:08x} -> 0x{val_after:08x}")

                # Where are we now?
                module = debugger.module_manager.address_to_module(eip_after)
                if module:
                    offset_after = eip_after - module.base_address
                    print(f"\nLocation: {module.name} + 0x{offset_after:04x}")

                    result = debugger.module_manager.resolve_address_to_line(eip_after)
                    if result:
                        module_name, loc, mod = result
                        print(f"Source: {loc.file}:{loc.line}")

                print(f"\n{'='*70}")
                print("SUCCESS!")
                print(f"{'='*70}")

        elif debugger.context.is_exited():
            print(f"\nGame exited before breakpoint was hit")
            if current_bp_info["address"]:
                print(f"Breakpoint was set at 0x{current_bp_info['address']:08x}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C)")
        if current_bp_info["address"]:
            print(f"Breakpoint was set at 0x{current_bp_info['address']:08x} but not hit yet")

    finally:
        print("\nCleaning up...")
        debugger.stop()

    print(f"\n{'='*70}")
    print("Test complete")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
