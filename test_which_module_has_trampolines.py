"""
Find which module actually contains trampolines.cpp

The issue: We assume trampolines.cpp is in smackw32.dll, but maybe it's elsewhere?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo

def check_module_for_trampolines(dll_path):
    """Check if a DLL contains trampolines.cpp in its debug info."""
    print(f"\nChecking: {dll_path}")

    try:
        parser = WatcomDwarfParser(dll_path)
        dwarf_info = parser.extract_dwarf_info()

        if not dwarf_info:
            print("  No DWARF info found")
            return False

        line_info = LineInfo(dwarf_info)

        # Try to resolve trampolines.cpp:10
        address = line_info.line_to_address("trampolines.cpp", 10)

        if address:
            print(f"  *** FOUND trampolines.cpp:10 ***")
            print(f"      Address: 0x{address:08x}")
            # Also get the source location to confirm
            loc = line_info.address_to_line(address)
            if loc:
                print(f"      File: {loc.file}")
                print(f"      Line: {loc.line}")
            return True
        else:
            # Try just searching for any file with "trampolines" in the name
            print(f"  Searching for files...")
            found_files = set()
            for cu in dwarf_info.iter_CUs():
                for entry in cu.iter_DIEs():
                    if entry.tag == 'DW_TAG_compile_unit':
                        file_name = entry.attributes.get('DW_AT_name')
                        if file_name:
                            file_str = file_name.value
                            if isinstance(file_str, bytes):
                                file_str = file_str.decode('utf-8', errors='ignore')
                            if 'trampolines' in file_str.lower():
                                found_files.add(file_str)

            if found_files:
                print(f"  Found trampolines-related files:")
                for f in found_files:
                    print(f"    - {f}")
                return True
            else:
                print(f"  No trampolines.cpp found")
                return False

    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Searching for trampolines.cpp in modules")
    print("=" * 60)

    # Check smackw32.dll
    check_module_for_trampolines(r"c:\entomorph\smackw32.dll")

    # Check plague.exe
    check_module_for_trampolines(r"c:\entomorph\plague.exe")

    # Check other common DLLs in the directory
    import os
    entomorph_dir = Path(r"c:\entomorph")
    if entomorph_dir.exists():
        print(f"\n\nSearching all DLLs in {entomorph_dir}:")
        for dll_file in entomorph_dir.glob("*.dll"):
            if dll_file.name.lower() != "smackw32.dll":  # Already checked
                check_module_for_trampolines(str(dll_file))


if __name__ == '__main__':
    main()
