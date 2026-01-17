#!/usr/bin/env python3
"""
Test: Persistent breakpoint at SMACKW32.DLL + 0x3966
Handles module reload by updating the breakpoint address
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Persistent breakpoint at SMACKW32.DLL + 0x3966")
    print("Handles module reloading")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966

    # Track current breakpoint
    current_bp_info = {"bp_id": None, "address": None, "base_addr": None}

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        # Hook into module load to track SMACKW32.DLL and update breakpoint
        original_on_load_dll = debugger._on_load_dll

        def on_load_dll_track_smackw32(event):
            original_on_load_dll(event)

            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                new_base = smackw32.base_address
                new_addr = new_base + target_offset

                # Check if SMACKW32 moved to a different address
                if current_bp_info["base_addr"] != new_base:
                    if current_bp_info["bp_id"]:
                        print(f"\n   [DLL Reload] SMACKW32.DLL moved: 0x{current_bp_info['base_addr']:08x} -> 0x{new_base:08x}")
                        print(f"   [DLL Reload] Removing old breakpoint at 0x{current_bp_info['address']:08x}")
                        # Remove old breakpoint (it's at the wrong address now)
                        debugger.breakpoint_manager.breakpoints.pop(current_bp_info["address"], None)

                    print(f"   [DLL Load] SMACKW32.DLL at 0x{new_base:08x}")
                    print(f"   [DLL Load] Setting breakpoint at 0x{new_addr:08x} (offset +0x{target_offset:04x})")

                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(new_addr)
                    if bp:
                        print(f"   [DLL Load] Breakpoint {bp.id} set!")
                        current_bp_info["bp_id"] = bp.id
                        current_bp_info["address"] = new_addr
                        current_bp_info["base_addr"] = new_base
                    else:
                        print(f"   [DLL Load] Failed to set breakpoint")

        debugger._on_load_dll = on_load_dll_track_smackw32

        print("3. Continuing execution (waiting for breakpoint)...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        if debugger.context.is_stopped() and debugger.context.stop_info.reason == "breakpoint":
            print(f"\n{'='*70}")
            print("BREAKPOINT HIT AT SMACKW32.DLL + 0x3966!")
            print(f"{'='*70}")

            eip = debugger.process_controller.get_register(
                debugger.context.current_thread_id, 'EIP'
            )
            print(f"\nStopped at: 0x{eip:08x}")

            # Verify we're at the right place
            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                offset = eip - smackw32.base_address
                print(f"Module: SMACKW32.DLL @ 0x{smackw32.base_address:08x} + 0x{offset:04x}")

            # Show registers
            print(f"\nRegisters:")
            regs = {}
            for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                regs[reg] = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, reg
                )
                print(f"  {reg:6s} = 0x{regs[reg]:08x}")

            # Source location
            result = debugger.module_manager.resolve_address_to_line(eip)
            if result:
                module_name, loc, mod = result
                print(f"\nSource: {loc.file}:{loc.line}")

            # SINGLE STEP
            print(f"\n{'='*70}")
            print("Performing SINGLE STEP...")
            print(f"{'='*70}")

            debugger.step_over()

            if debugger.context.is_stopped():
                eip_after = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, 'EIP'
                )
                print(f"\nAfter step: 0x{eip_after:08x}")

                # Show register changes
                print(f"\nRegisters after step:")
                for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                    val_after = debugger.process_controller.get_register(
                        debugger.context.current_thread_id, reg
                    )
                    val_before = regs[reg]
                    changed = " <-- CHANGED" if val_after != val_before else ""
                    print(f"  {reg:6s} = 0x{val_after:08x}{changed}")

                # Where did we step to?
                module = debugger.module_manager.address_to_module(eip_after)
                if module:
                    offset = eip_after - module.base_address
                    print(f"\nStepped into: {module.name} + 0x{offset:04x}")

                    result = debugger.module_manager.resolve_address_to_line(eip_after)
                    if result:
                        module_name, loc, mod = result
                        print(f"Source: {loc.file}:{loc.line}")
                else:
                    print(f"\nStepped to unmapped memory or unknown module")

                print(f"\n{'='*70}")
                print("SUCCESS: Breakpoint hit and stepped!")
                print(f"{'='*70}")

        elif debugger.context.is_stopped():
            print(f"\nStopped (reason: {debugger.context.stop_info.reason}) at 0x{debugger.context.current_address:08x}")

        elif debugger.context.is_exited():
            print(f"\n{'='*70}")
            print("Process exited without hitting breakpoint")
            print(f"{'='*70}")
            if current_bp_info["bp_id"]:
                print(f"\n  Breakpoint was set at 0x{current_bp_info['address']:08x}")
                print(f"  but was never hit during execution")
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
