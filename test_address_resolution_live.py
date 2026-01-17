#!/usr/bin/env python3
"""
Test: Verify address resolution with live debugging
Sets breakpoints and verifies they resolve to correct source locations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    print("=" * 70)
    print("Test: Address Resolution with Live Debugging")
    print("=" * 70)

    debugger = Debugger("c:/entomorph/plague.exe")

    try:
        print("\n1. Starting plague.exe...")
        debugger.start()

        print("\n2. Running to initial breakpoint...")
        debugger.run_event_loop()
        print(f"   Stopped at: 0x{debugger.context.current_address:08x}")

        # Set up deferred breakpoint for when SMACKW32.DLL loads
        original_on_load_dll = debugger._on_load_dll
        smackw32_loaded = [False]
        test_results = []

        def on_load_dll_with_test(event):
            original_on_load_dll(event)

            if not smackw32_loaded[0]:
                smackw32 = debugger.module_manager.get_module_by_name("SMACKW32.DLL")
                if smackw32:
                    smackw32_loaded[0] = True

                    print(f"\n{'='*70}")
                    print("SMACKW32.DLL LOADED - Testing Address Resolution")
                    print(f"{'='*70}")
                    print(f"\nBase address: 0x{smackw32.base_address:08x}")
                    print(f"Code section offset: 0x{smackw32.code_section_offset:x}")

                    # Test 1: Verify offset 0x3966 resolves to line 10
                    print(f"\n{'-'*70}")
                    print("Test 1: Offset 0x3966 should resolve to copy_string_01 (line 10)")
                    print(f"{'-'*70}")

                    test_addr_1 = smackw32.base_address + 0x3966
                    print(f"Testing address: 0x{test_addr_1:08x}")

                    result = debugger.module_manager.resolve_address_to_line(test_addr_1)
                    if result:
                        module_name, loc, mod = result
                        print(f"  Resolved to: {Path(loc.file).name}:{loc.line}")

                        if 'trampolines.cpp' in loc.file and loc.line == 10:
                            print("  [PASS] Correct! This is copy_string_01")
                            test_results.append(True)
                        else:
                            print(f"  [FAIL] Expected trampolines.cpp:10, got {Path(loc.file).name}:{loc.line}")
                            test_results.append(False)
                    else:
                        print("  [FAIL] Could not resolve address")
                        test_results.append(False)

                    # Test 2: Verify offset 0x3ac6 resolves to line 258
                    print(f"\n{'-'*70}")
                    print("Test 2: Offset 0x3ac6 should resolve to _SmackWait (line 258)")
                    print(f"{'-'*70}")

                    test_addr_2 = smackw32.base_address + 0x3ac6
                    print(f"Testing address: 0x{test_addr_2:08x}")

                    result = debugger.module_manager.resolve_address_to_line(test_addr_2)
                    if result:
                        module_name, loc, mod = result
                        print(f"  Resolved to: {Path(loc.file).name}:{loc.line}")

                        if 'trampolines.cpp' in loc.file and loc.line == 258:
                            print("  [PASS] Correct! This is _SmackWait")
                            test_results.append(True)
                        else:
                            print(f"  [FAIL] Expected trampolines.cpp:258, got {Path(loc.file).name}:{loc.line}")
                            test_results.append(False)
                    else:
                        print("  [FAIL] Could not resolve address")
                        test_results.append(False)

                    # Test 3: Reverse lookup - line 10 should give offset 0x3966
                    print(f"\n{'-'*70}")
                    print("Test 3: Line 10 should resolve to offset 0x3966")
                    print(f"{'-'*70}")

                    result = debugger.module_manager.resolve_line_to_address('trampolines.cpp', 10)
                    if result:
                        abs_addr, module = result
                        offset = abs_addr - smackw32.base_address
                        print(f"  Resolved to: 0x{abs_addr:08x} (offset 0x{offset:x})")

                        if offset == 0x3966:
                            print("  [PASS] Correct offset!")
                            test_results.append(True)
                        else:
                            print(f"  [FAIL] Expected offset 0x3966, got 0x{offset:x}")
                            test_results.append(False)
                    else:
                        print("  [FAIL] Could not resolve line")
                        test_results.append(False)

                    # Test 4: Reverse lookup - line 258 should give offset 0x3ac6
                    print(f"\n{'-'*70}")
                    print("Test 4: Line 258 should resolve to offset 0x3ac6")
                    print(f"{'-'*70}")

                    result = debugger.module_manager.resolve_line_to_address('trampolines.cpp', 258)
                    if result:
                        abs_addr, module = result
                        offset = abs_addr - smackw32.base_address
                        print(f"  Resolved to: 0x{abs_addr:08x} (offset 0x{offset:x})")

                        if offset == 0x3ac6:
                            print("  [PASS] Correct offset!")
                            test_results.append(True)
                        else:
                            print(f"  [FAIL] Expected offset 0x3ac6, got 0x{offset:x}")
                            test_results.append(False)
                    else:
                        print("  [FAIL] Could not resolve line")
                        test_results.append(False)

                    # Set breakpoint at offset 0x3966 to verify it
                    print(f"\n{'-'*70}")
                    print("Test 5: Setting breakpoint at offset 0x3966")
                    print(f"{'-'*70}")

                    absolute_addr = smackw32.base_address + 0x3966
                    print(f"  Absolute address: 0x{absolute_addr:08x}")

                    bp = debugger.breakpoint_manager.set_breakpoint_at_address(absolute_addr)
                    if bp:
                        print(f"  Breakpoint {bp.id} set successfully!")

                        # Check what source location the breakpoint resolves to
                        result = debugger.module_manager.resolve_address_to_line(bp.address)
                        if result:
                            module_name, loc, mod = result
                            print(f"  Breakpoint location: {Path(loc.file).name}:{loc.line}")

                            if 'trampolines.cpp' in loc.file and loc.line == 10:
                                print("  [PASS] Breakpoint correctly placed at copy_string_01")
                                test_results.append(True)
                            else:
                                print(f"  [FAIL] Expected trampolines.cpp:10")
                                test_results.append(False)
                        else:
                            print("  [WARNING] Could not resolve breakpoint location")
                            test_results.append(False)
                    else:
                        print("  [FAIL] Could not set breakpoint")
                        test_results.append(False)

                    # Print summary
                    print(f"\n{'='*70}")
                    print("TEST SUMMARY")
                    print(f"{'='*70}")
                    passed = sum(test_results)
                    total = len(test_results)
                    print(f"Passed: {passed}/{total}")

                    if all(test_results):
                        print("\n[PASS] All tests PASSED! Address resolution is working correctly.")
                    else:
                        print("\n[FAIL] Some tests failed.")
                    print(f"{'='*70}")

                    # Exit the debugger since we're done testing
                    debugger.context.should_quit = True

        debugger._on_load_dll = on_load_dll_with_test

        print("\n3. Continuing execution (waiting for SMACKW32.DLL to load)...")
        debugger.context.set_running()
        debugger.waiting_for_event = True
        debugger.run_event_loop()

        if not smackw32_loaded[0]:
            print("\n[FAIL] SMACKW32.DLL never loaded")
            return False

        return all(test_results) if test_results else False

    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\nCleaning up...")
        try:
            debugger.stop()
        except:
            pass

if __name__ == "__main__":
    success = main()
    print(f"\nFinal result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
