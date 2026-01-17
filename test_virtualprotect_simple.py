#!/usr/bin/env python3
"""
Test: Verify VirtualProtect fix allows writing breakpoints to DLL code sections
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger
import time

def main():
    print("=" * 70)
    print("Test: VirtualProtect Fix - DLL Breakpoint Writing")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966

    # Hook DLL load to set breakpoint as soon as SMACKW32.DLL loads
    original_on_load_dll = debugger._on_load_dll
    test_passed = False

    def on_load_dll_test(event):
        nonlocal test_passed
        original_on_load_dll(event)

        smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
        if smackw32 and not test_passed:
            print(f"\n4. SMACKW32.DLL loaded at 0x{smackw32.base_address:08x}")
            print(f"   Attempting to set breakpoint at offset +0x{target_offset:04x}...")

            target_address = smackw32.base_address + target_offset
            print(f"   Target address: 0x{target_address:08x}")

            # Read original byte
            try:
                original_byte = debugger.process_controller.read_memory(target_address, 1)
                print(f"   Original byte: {original_byte.hex()}")
            except Exception as e:
                print(f"   Failed to read original byte: {e}")
                return

            # Set breakpoint (this will use VirtualProtect internally)
            try:
                bp = debugger.breakpoint_manager.set_breakpoint_at_address(target_address)
                print(f"   [OK] Breakpoint set successfully (ID: {bp.id})")
            except Exception as e:
                print(f"\n{'='*70}")
                print("FAILED: Could not set breakpoint")
                print(f"{'='*70}")
                print(f"   Error: {e}")
                debugger.stop()
                sys.exit(1)

            # Verify INT 3 was written
            try:
                current_byte = debugger.process_controller.read_memory(target_address, 1)
                print(f"   Current byte: {current_byte.hex()}")

                if current_byte == b'\xcc':
                    print(f"\n{'='*70}")
                    print("[OK] SUCCESS: VirtualProtect fix works!")
                    print("INT 3 (0xCC) was successfully written to DLL code section")
                    print(f"{'='*70}")
                    print("\nDetails:")
                    print(f"  - DLL base address: 0x{smackw32.base_address:08x}")
                    print(f"  - Breakpoint address: 0x{target_address:08x}")
                    print(f"  - Original byte: {original_byte.hex()}")
                    print(f"  - Written byte: 0xCC (INT 3)")
                    print(f"  - Verified byte: {current_byte.hex()}")
                    test_passed = True
                else:
                    print(f"\n{'='*70}")
                    print("[FAIL] FAILED: INT 3 was not written!")
                    print(f"{'='*70}")
                    print(f"  Expected: 0xcc")
                    print(f"  Got: {current_byte.hex()}")
                    debugger.stop()
                    sys.exit(1)
            except Exception as e:
                print(f"   Failed to verify: {e}")
                debugger.stop()
                sys.exit(1)

    debugger._on_load_dll = on_load_dll_test

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        print("\n3. Continuing to load DLLs...")
        debugger.context.set_running()
        debugger.waiting_for_event = True

        # Run briefly to load DLLs
        debugger.run_event_loop()

        if not test_passed:
            print("\n   SMACKW32.DLL did not load in time")

    finally:
        print("\nCleaning up...")
        debugger.stop()

    if test_passed:
        print(f"\n{'='*70}")
        print("Test complete: SUCCESS")
        print(f"{'='*70}")
        sys.exit(0)
    else:
        print(f"\n{'='*70}")
        print("Test complete: FAILED")
        print(f"{'='*70}")
        sys.exit(1)

if __name__ == "__main__":
    main()
