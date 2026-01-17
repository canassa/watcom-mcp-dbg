#!/usr/bin/env python3
"""
Test: Verify VirtualProtect fix allows writing breakpoints to DLL code sections
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: VirtualProtect Fix - DLL Breakpoint Writing")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        print("\n3. Continuing until SMACKW32.DLL loads...")
        debugger.context.set_running()

        # Run for a bit to load DLLs
        import time
        start_time = time.time()
        timeout = 10  # 10 seconds

        while time.time() - start_time < timeout:
            # Check if SMACKW32.DLL is loaded
            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                print(f"   SMACKW32.DLL loaded at 0x{smackw32.base_address:08x}")
                break

            # Run event loop briefly
            debugger.waiting_for_event = True
            debugger.run_event_loop()

            if debugger.context.is_exited():
                print("   Process exited before SMACKW32.DLL loaded")
                return

            time.sleep(0.1)
        else:
            print("   Timeout waiting for SMACKW32.DLL to load")
            return

        print("\n4. Attempting to set breakpoint at SMACKW32.DLL + 0x3966...")
        target_address = smackw32.base_address + target_offset
        print(f"   Target address: 0x{target_address:08x}")

        # Read original byte
        original_byte = debugger.process_controller.read_memory(target_address, 1)
        print(f"   Original byte: {original_byte.hex()}")

        # Set breakpoint (this will use VirtualProtect internally)
        try:
            bp = debugger.breakpoint_manager.set_breakpoint_at_address(target_address)
            print(f"   ✓ Breakpoint set successfully (ID: {bp.id})")
        except Exception as e:
            print(f"   ✗ FAILED to set breakpoint: {e}")
            raise

        # Verify INT 3 was written
        current_byte = debugger.process_controller.read_memory(target_address, 1)
        print(f"   Current byte: {current_byte.hex()}")

        if current_byte == b'\xcc':
            print(f"\n{'='*70}")
            print("SUCCESS: VirtualProtect fix works!")
            print("INT 3 (0xCC) was successfully written to DLL code section")
            print(f"{'='*70}")
            print("\nDetails:")
            print(f"  - DLL base address: 0x{smackw32.base_address:08x}")
            print(f"  - Breakpoint address: 0x{target_address:08x}")
            print(f"  - Original byte: {original_byte.hex()}")
            print(f"  - Written byte: 0xCC (INT 3)")
            print(f"  - Verified byte: {current_byte.hex()}")
        else:
            print(f"\n{'='*70}")
            print("FAILED: INT 3 was not written!")
            print(f"{'='*70}")
            print(f"  Expected: 0xcc")
            print(f"  Got: {current_byte.hex()}")

    finally:
        print("\nCleaning up...")
        debugger.stop()

if __name__ == "__main__":
    main()
