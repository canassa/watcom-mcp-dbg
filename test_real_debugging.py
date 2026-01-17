"""Test real debugging session to verify address resolution fix.

This script:
1. Starts plague.exe in the debugger
2. Sets breakpoint at 0x0045240f and runs to it
3. Gets smackw32.dll base address
4. Sets breakpoint at smackw32.dll+0x3966 (should be copy_string_01 line 10)
5. Verifies the breakpoint resolves correctly
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger
from dgb.debugger.win32api import ProcessInformation


def main():
    print("=" * 70)
    print("Real Debugging Session Test")
    print("=" * 70)

    # Create debugger
    debugger = Debugger()

    # Start plague.exe
    exe_path = r"c:\entomorph\plague.exe"
    print(f"\nStarting: {exe_path}")

    try:
        pi = debugger.create_process(exe_path, args="")
        print(f"Process created: PID {pi.dwProcessId}")
    except Exception as e:
        print(f"Failed to create process: {e}")
        return False

    # Set breakpoint at 0x0045240f
    bp_addr = 0x0045240f
    print(f"\nSetting breakpoint at 0x{bp_addr:08x}")

    try:
        debugger.set_breakpoint(bp_addr)
        print("Breakpoint set successfully")
    except Exception as e:
        print(f"Failed to set breakpoint: {e}")
        return False

    # Run to breakpoint
    print("\nRunning to breakpoint...")
    try:
        # Start the event loop until we hit the breakpoint
        while debugger.is_running():
            debugger.continue_execution()

            # Check if we hit the breakpoint
            if debugger.current_address == bp_addr:
                print(f"Hit breakpoint at 0x{bp_addr:08x}")
                break

    except Exception as e:
        print(f"Error during execution: {e}")
        return False

    # Get all loaded modules
    print("\n" + "-" * 70)
    print("Loaded Modules:")
    print("-" * 70)

    module_manager = debugger.module_manager
    smackw32_module = None

    for module in module_manager.get_all_modules():
        print(f"{module.name:20} Base: 0x{module.base_address:08x}  Debug: {module.has_debug_info}")
        if module.name.lower() == 'smackw32.dll':
            smackw32_module = module

    if not smackw32_module:
        print("\nERROR: smackw32.dll not loaded!")
        return False

    # Calculate breakpoint address in smackw32.dll
    print("\n" + "-" * 70)
    print("Setting breakpoint in smackw32.dll")
    print("-" * 70)

    dll_base = smackw32_module.base_address
    bp_offset = 0x3966
    bp_addr_dll = dll_base + bp_offset

    print(f"\nsmackw32.dll base address: 0x{dll_base:08x}")
    print(f"Target offset:             0x{bp_offset:x}")
    print(f"Absolute breakpoint addr:  0x{bp_addr_dll:08x}")

    # Check what this address should resolve to
    result = module_manager.resolve_address_to_line(bp_addr_dll)
    if result:
        name, loc, module = result
        print(f"\nAddress resolution:")
        print(f"  File: {Path(loc.file).name}")
        print(f"  Line: {loc.line}")
        print(f"  Column: {loc.column}")

        if 'trampolines.cpp' in loc.file and loc.line == 10:
            print("\n[PASS] Breakpoint correctly resolves to copy_string_01 (line 10)")
        else:
            print(f"\n[FAIL] Expected trampolines.cpp:10, got {Path(loc.file).name}:{loc.line}")
            return False
    else:
        print("\n[FAIL] Could not resolve address to source location")
        return False

    # Set the breakpoint
    print(f"\nSetting breakpoint at 0x{bp_addr_dll:08x}")
    try:
        debugger.set_breakpoint(bp_addr_dll)
        print("Breakpoint set successfully")
    except Exception as e:
        print(f"Failed to set breakpoint: {e}")
        return False

    # List all breakpoints
    print("\n" + "-" * 70)
    print("Active Breakpoints:")
    print("-" * 70)

    for bp in debugger.breakpoint_manager.list_breakpoints():
        addr = bp['address']

        # Try to resolve to source
        result = module_manager.resolve_address_to_line(addr)
        if result:
            name, loc, module = result
            print(f"  0x{addr:08x} -> {Path(loc.file).name}:{loc.line}")
        else:
            print(f"  0x{addr:08x} -> (no source info)")

    # Continue to the new breakpoint
    print("\nContinuing to smackw32.dll breakpoint...")
    try:
        debugger.continue_execution()

        # Wait for breakpoint
        while debugger.is_running():
            debugger.continue_execution()

            if debugger.current_address == bp_addr_dll:
                print(f"\nHit breakpoint at 0x{bp_addr_dll:08x}")
                break

        # Verify we're at the right location
        result = module_manager.resolve_address_to_line(debugger.current_address)
        if result:
            name, loc, module = result
            print(f"\nCurrent location:")
            print(f"  Address: 0x{debugger.current_address:08x}")
            print(f"  File: {Path(loc.file).name}")
            print(f"  Line: {loc.line}")

            if 'trampolines.cpp' in loc.file and loc.line == 10:
                print("\n[PASS] Stopped at copy_string_01 (line 10)")
                print("\n" + "=" * 70)
                print("[PASS] All tests PASSED! Address resolution is working correctly.")
                print("=" * 70)
                return True
            else:
                print(f"\n[FAIL] Expected trampolines.cpp:10")
                return False

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        try:
            debugger.terminate()
        except:
            pass

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
