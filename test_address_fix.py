"""Test script to verify DWARF address resolution fix.

This test verifies that section-relative DWARF addresses are correctly
converted to absolute addresses when accounting for the code section offset.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.module_manager import ModuleManager


def test_address_mapping():
    """Test that DWARF addresses map correctly with section offset."""
    print("=" * 70)
    print("Testing DWARF Address Resolution Fix")
    print("=" * 70)

    # Create module manager
    mgr = ModuleManager()

    # Load SMACKW32.DLL at base address 0x001d0000 (typical runtime address)
    dll_path = r'c:\entomorph\smackw32.dll'
    base_address = 0x001d0000

    print(f"\nLoading module: {dll_path}")
    print(f"Base address: 0x{base_address:08x}")
    print()

    mgr.on_module_loaded('SMACKW32.DLL', base_address, dll_path)

    # Get the module to check code section offset
    module = mgr.get_module_by_name('SMACKW32.DLL')
    if module:
        print(f"\nModule loaded successfully")
        print(f"  Code section offset: 0x{module.code_section_offset:x}")
        print(f"  Has debug info: {module.has_debug_info}")

    print("\n" + "-" * 70)
    print("Test 1: Line to Address (Forward Mapping)")
    print("-" * 70)

    # Test 1: copy_string_01 at line 10 should resolve to offset 0x3966
    print("\n1. Testing copy_string_01 (line 10)")
    print(f"   Expected absolute address: 0x{base_address + 0x3966:08x}")

    result = mgr.resolve_line_to_address('trampolines.cpp', 10)
    if result is not None:
        abs_addr, module = result
        offset = abs_addr - base_address
        print(f"   Actual absolute address:   0x{abs_addr:08x}")
        print(f"   Offset from base:          0x{offset:x}")

        if offset == 0x3966:
            print("   [PASS] PASS: Correct offset (0x3966)")
        else:
            print(f"   [FAIL] FAIL: Expected offset 0x3966, got 0x{offset:x}")
            return False
    else:
        print("   [FAIL] FAIL: Could not resolve line 10")
        return False

    # Test 2: _SmackWait at line 258 should resolve to offset 0x3ac6
    print("\n2. Testing _SmackWait (line 258)")
    print(f"   Expected absolute address: 0x{base_address + 0x3ac6:08x}")

    result = mgr.resolve_line_to_address('trampolines.cpp', 258)
    if result is not None:
        abs_addr, module = result
        offset = abs_addr - base_address
        print(f"   Actual absolute address:   0x{abs_addr:08x}")
        print(f"   Offset from base:          0x{offset:x}")

        if offset == 0x3ac6:
            print("   [PASS] PASS: Correct offset (0x3ac6)")
        else:
            print(f"   [FAIL] FAIL: Expected offset 0x3ac6, got 0x{offset:x}")
            return False
    else:
        print("   [FAIL] FAIL: Could not resolve line 258")
        return False

    print("\n" + "-" * 70)
    print("Test 2: Address to Line (Reverse Lookup)")
    print("-" * 70)

    # Test 3: Reverse lookup of 0x3966 should return line 10
    print("\n3. Testing reverse lookup of offset 0x3966")
    print(f"   Expected: trampolines.cpp:10 (copy_string_01)")

    test_addr = base_address + 0x3966
    result = mgr.resolve_address_to_line(test_addr)
    if result is not None:
        name, loc, module = result
        print(f"   Actual:   {Path(loc.file).name}:{loc.line}")

        if 'trampolines.cpp' in loc.file and loc.line == 10:
            print("   [PASS] PASS: Correct line (10)")
        else:
            print(f"   [FAIL] FAIL: Expected line 10, got line {loc.line}")
            return False
    else:
        print("   [FAIL] FAIL: Could not resolve address")
        return False

    # Test 4: Reverse lookup of 0x3ac6 should return line 258
    print("\n4. Testing reverse lookup of offset 0x3ac6")
    print(f"   Expected: trampolines.cpp:258 (_SmackWait)")

    test_addr = base_address + 0x3ac6
    result = mgr.resolve_address_to_line(test_addr)
    if result is not None:
        name, loc, module = result
        print(f"   Actual:   {Path(loc.file).name}:{loc.line}")

        if 'trampolines.cpp' in loc.file and loc.line == 258:
            print("   [PASS] PASS: Correct line (258)")
        else:
            print(f"   [FAIL] FAIL: Expected line 258, got line {loc.line}")
            return False
    else:
        print("   [FAIL] FAIL: Could not resolve address")
        return False

    print("\n" + "=" * 70)
    print("[PASS] All tests PASSED!")
    print("=" * 70)
    return True


if __name__ == '__main__':
    try:
        success = test_address_mapping()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
