#!/usr/bin/env python3
"""
Test: Set breakpoint via direct debugger API and wait for it to be hit
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger
import time

def main():
    print("=" * 70)
    print("Setting breakpoint at SMACKW32.DLL + 0x3966")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")
    target_offset = 0x3966
    breakpoint_set = False

    # Hook into DLL load to set breakpoint
    original_on_load_dll = debugger._on_load_dll

    def on_load_dll_set_bp(event):
        nonlocal breakpoint_set
        original_on_load_dll(event)

        if not breakpoint_set:
            smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
            if smackw32:
                target_address = smackw32.base_address + target_offset
                print(f"\n[*] SMACKW32.DLL loaded at 0x{smackw32.base_address:08x}")
                print(f"[*] Setting breakpoint at 0x{target_address:08x} (offset +0x{target_offset:04x})")

                bp = debugger.breakpoint_manager.set_breakpoint_at_address(target_address)
                if bp:
                    print(f"[+] Breakpoint {bp.id} set successfully!")
                    breakpoint_set = True
                else:
                    print(f"[-] Failed to set breakpoint!")

    debugger._on_load_dll = on_load_dll_set_bp

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()

        print("3. Continuing execution (waiting for breakpoint to be hit)...")
        debugger.context.set_running()
        debugger.waiting_for_event = True

        # Run and wait for breakpoint
        start_time = time.time()
        timeout = 30  # 30 seconds

        while time.time() - start_time < timeout:
            debugger.run_event_loop()

            if debugger.context.is_stopped():
                if debugger.context.stop_info.reason == "breakpoint":
                    print(f"\n{'='*70}")
                    print("BREAKPOINT HIT!")
                    print(f"{'='*70}")

                    eip = debugger.process_controller.get_register(
                        debugger.context.current_thread_id, 'EIP'
                    )
                    print(f"\nStopped at: 0x{eip:08x}")

                    # Verify location
                    smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
                    if smackw32:
                        offset = eip - smackw32.base_address
                        print(f"Module: SMACKW32.DLL + 0x{offset:04x}")

                    # Show registers
                    print(f"\nRegisters:")
                    for reg in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP']:
                        val = debugger.process_controller.get_register(
                            debugger.context.current_thread_id, reg
                        )
                        print(f"  {reg:6s} = 0x{val:08x}")

                    # Source location
                    result = debugger.module_manager.resolve_address_to_line(eip)
                    if result:
                        module_name, loc, mod = result
                        print(f"\nSource: {loc.file}:{loc.line}")

                    break
                else:
                    print(f"\nStopped (reason: {debugger.context.stop_info.reason})")
                    debugger.context.set_running()
                    debugger.waiting_for_event = True

            elif debugger.context.is_exited():
                print(f"\n{'='*70}")
                print("Process exited without hitting breakpoint")
                print(f"{'='*70}")
                break

            time.sleep(0.1)
        else:
            print(f"\n{'='*70}")
            print("Timeout waiting for breakpoint")
            print(f"{'='*70}")

    finally:
        print("\nCleaning up...")
        debugger.stop()

if __name__ == "__main__":
    main()
