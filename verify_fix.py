"""
Verification script for DWARF lazy-loading fix.

Tests that the pyelftools lazy-loading bug is resolved and all source
file paths are correctly resolved (no "unknown" entries).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo


def verify_dwarf_parsing(dll_path: str, test_address: int):
    """Verify DWARF parsing produces correct file paths."""

    print("=" * 70)
    print("DWARF Lazy-Loading Fix Verification")
    print("=" * 70)
    print()
    print(f"Testing DLL: {dll_path}")
    print(f"Test address: 0x{test_address:04x}")
    print()

    # Parse DWARF info
    parser = WatcomDwarfParser(dll_path)
    dwarf_info = parser.extract_dwarf_info()

    if not dwarf_info:
        print("ERROR: No DWARF info found!")
        return False

    # Build line info
    line_info = LineInfo(dwarf_info)

    # Test 1: Check specific address
    print("-" * 70)
    print("Test 1: Address-to-Line Mapping")
    print("-" * 70)

    loc = line_info.address_to_line(test_address)
    if not loc:
        print(f"ERROR: No location found for address 0x{test_address:04x}")
        return False

    print(f"Address 0x{test_address:04x} maps to:")
    print(f"  File: {loc.file}")
    print(f"  Line: {loc.line}")
    print(f"  Column: {loc.column}")
    print()

    if loc.file == "unknown":
        print("FAILURE: File is still 'unknown'!")
        return False

    print("PASS: File path correctly resolved")
    print()

    # Test 2: Check all files
    print("-" * 70)
    print("Test 2: All Source Files")
    print("-" * 70)

    files = sorted(line_info.get_files())
    print(f"Found {len(files)} unique source files:")

    has_unknown = False
    for f in files:
        if f == "unknown":
            print(f"  [ERROR] {f}")
            has_unknown = True
        else:
            print(f"  [OK] {Path(f).name}")

    print()

    if has_unknown:
        print("FAILURE: Found 'unknown' file paths!")
        return False

    print("PASS: All file paths correctly resolved")
    print()

    # Test 3: Sample addresses from each file
    print("-" * 70)
    print("Test 3: Multi-File Address Resolution")
    print("-" * 70)

    files_tested = {}
    for loc in line_info.get_all_locations():
        file_name = Path(loc.file).name
        if file_name not in files_tested:
            files_tested[file_name] = loc

    print(f"Testing {len(files_tested)} different source files:")

    all_passed = True
    for file_name, loc in sorted(files_tested.items()):
        if loc.file == "unknown":
            print(f"  [ERROR] 0x{loc.address:04x} -> unknown")
            all_passed = False
        else:
            print(f"  [OK] 0x{loc.address:04x} -> {file_name}:{loc.line}")

    print()

    if not all_passed:
        print("FAILURE: Some addresses still map to 'unknown'")
        return False

    print("PASS: All addresses correctly map to source files")
    print()

    # Test 4: Cache statistics
    print("-" * 70)
    print("Test 4: Cache Statistics")
    print("-" * 70)

    total_locations = len(line_info._address_to_line_cache)
    print(f"Total locations cached: {total_locations}")
    print(f"Unique source files: {len(files)}")
    print()

    if total_locations == 0:
        print("FAILURE: No locations in cache!")
        return False

    print("PASS: Cache populated successfully")
    print()

    # Final summary
    print("=" * 70)
    print("VERIFICATION RESULT: ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("The pyelftools lazy-loading bug has been successfully fixed!")
    print("All source file paths are correctly resolved.")
    print()

    return True


if __name__ == '__main__':
    dll_path = r'c:\entomorph\smackw32.dll'
    test_address = 0x3966

    success = verify_dwarf_parsing(dll_path, test_address)
    sys.exit(0 if success else 1)
