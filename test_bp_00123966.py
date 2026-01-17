#!/usr/bin/env python3
"""
Test: Start plague.exe and set breakpoint at 0x00123966

This script will:
1. Start plague.exe
2. Wait for modules to load
3. Determine which module contains 0x00123966
4. Set the breakpoint
5. Continue and wait for it to be hit
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Set breakpoint at 0x00123966 in plague.exe")
    print("=" * 70)

    # Create debugger
    debugger = Debugger("c:/entomorph/plague.exe")
    target_address = 0x00123966

    try:
        # Start process
        print("\n1. Starting plague.exe...")
        debugger.start()

        # Run to initial breakpoint
        print("2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        # Set up deferred breakpoint
        print(f"\n3. Setting up deferred breakpoint for address 0x{target_address:08x}...")

        original_on_load_dll = debugger._on_load_dll
        breakpoint_set = [False]

        def on_load_dll_check_breakpoint(event):
            original_on_load_dll(event)

            if not breakpoint_set[0]:
                # Check if target address is now in a loaded module
                module = debugger.module_manager.address_to_module(target_address)
                if module:
                    offset = target_address - module.base_address
                    print(f"\n   [DLL Event] Address 0x{target_address:08x} is in {module.name}")
                    print(f"   [DLL Event] Module base: 0x{module.base_address:08x}, offset: 0x{offset:04x}")

                    # Set the breakpoint
                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(target_address)
                    if bp:
                        print(f"   [DLL Event] ✓ Breakpoint {bp.id} set at 0x{target_address:08x}")
                        breakpoint_set[0] = True
                    else:
                        print(f"   [DLL Event] ✗ Failed to set breakpoint")

        debugger._on_load_dll = on_load_dll_check_breakpoint

        # Continue execution
        print("4. Continuing execution...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        # Check result
        if debugger.context.is_stopped():
            print(f"\n{'='*70}")
            print("BREAKPOINT HIT!")
            print(f"{'='*70}")
            print(f"\nStopped at: 0x{debugger.context.current_address:08x}")
            print(f"Reason: {debugger.context.stop_info.reason}")

            # Determine which module we're in
            module = debugger.module_manager.address_to_module(debugger.context.current_address)
            if module:
                offset = debugger.context.current_address - module.base_address
                print(f"Module: {module.name} (base 0x{module.base_address:08x}, offset 0x{offset:04x})")
                if module.has_debug_info:
                    print(f"Debug info: Available (DWARF 2)")
                else:
                    print(f"Debug info: Not available")

            # Get registers
            print(f"\nRegisters:")
            regs = {}
            for reg_name in ['EIP', 'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'ESP', 'EBP', 'EFlags']:
                regs[reg_name] = debugger.process_controller.get_register(
                    debugger.context.current_thread_id, reg_name
                )

            print(f"  EIP    = 0x{regs['EIP']:08x}")
            print(f"  EAX    = 0x{regs['EAX']:08x}")
            print(f"  EBX    = 0x{regs['EBX']:08x}")
            print(f"  ECX    = 0x{regs['ECX']:08x}")
            print(f"  EDX    = 0x{regs['EDX']:08x}")
            print(f"  ESI    = 0x{regs['ESI']:08x}")
            print(f"  EDI    = 0x{regs['EDI']:08x}")
            print(f"  ESP    = 0x{regs['ESP']:08x}")
            print(f"  EBP    = 0x{regs['EBP']:08x}")
            print(f"  EFlags = 0x{regs['EFlags']:08x}")

            # Try to get source location
            print(f"\nSource location:")
            result = debugger.module_manager.resolve_address_to_line(regs['EIP'])
            if result:
                module_name, loc, mod = result
                print(f"  File: {loc.file}")
                print(f"  Line: {loc.line}")
                print(f"  Column: {loc.column}")
            else:
                print(f"  No source information available at this address")

            print(f"\n{'='*70}")

        elif debugger.context.is_exited():
            print(f"\n{'='*70}")
            print("Process exited without hitting the breakpoint")
            print(f"{'='*70}")
            if breakpoint_set[0]:
                print("  → Breakpoint was set but never hit")
                print("  → The code at that address may not be executed during startup")
            else:
                print("  → Breakpoint was never set")
                print("  → The address may not be in any loaded module")

    finally:
        print("\nCleaning up...")
        debugger.stop()

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)

if __name__ == "__main__":
    main()
