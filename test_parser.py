"""
Quick test script to verify DWARF parser works with smackw32.dll
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo


def test_parser(dll_path):
    """Test parsing a DLL with Watcom DWARF 2 info."""
    print(f"Testing parser on: {dll_path}")
    print("=" * 60)

    # Create parser
    parser = WatcomDwarfParser(dll_path)

    # Try to extract DWARF info
    print("Extracting DWARF info...")
    dwarf_info = parser.extract_dwarf_info()

    if not dwarf_info:
        print("[X] No DWARF information found")
        return False

    print(f"[OK] DWARF info found! Format: {parser.get_format_type()}")
    print()

    # Show compilation units
    print("Compilation Units:")
    print("-" * 60)
    for i, CU in enumerate(parser.get_compilation_units(), 1):
        try:
            top_die = CU.get_top_DIE()
            cu_name = top_die.attributes.get('DW_AT_name')
            cu_comp_dir = top_die.attributes.get('DW_AT_comp_dir')

            if cu_name:
                cu_name_str = cu_name.value.decode('utf-8', errors='ignore')
            else:
                cu_name_str = "unknown"

            if cu_comp_dir:
                cu_comp_dir_str = cu_comp_dir.value.decode('utf-8', errors='ignore')
            else:
                cu_comp_dir_str = "unknown"

            print(f"CU {i}: {cu_name_str}")
            print(f"  Compilation dir: {cu_comp_dir_str}")
            print(f"  Offset: 0x{CU.cu_offset:x}")
            print()
        except Exception as e:
            print(f"CU {i}: Error parsing CU - {e}")
            print()

    # Build line info
    print("Building line number information...")
    try:
        line_info = LineInfo(dwarf_info)

        # Show source files
        files = line_info.get_files()
        print(f"\nSource files ({len(files)}):")
        print("-" * 60)
        for file in sorted(files):
            print(f"  {file}")

        # Show some line mappings
        print("\nSample line mappings (first 10):")
        print("-" * 60)
        for i, loc in enumerate(line_info.get_all_locations()):
            if i >= 10:
                break
            print(f"  0x{loc.address:08x} -> {Path(loc.file).name}:{loc.line}:{loc.column}")

        print("\n[OK] Parser test successful!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to build line info: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <path_to_dll>")
        print("Example: python test_parser.py c:\\entomorph\\smackw32.dll")
        sys.exit(1)

    dll_path = sys.argv[1]
    if not Path(dll_path).exists():
        print(f"Error: File not found: {dll_path}")
        sys.exit(1)

    success = test_parser(dll_path)
    sys.exit(0 if success else 1)
