"""
Investigate why DWARF says 0x2966 but x32dbg says 0x3966 for trampolines.cpp:10
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo
import pefile

def analyze_smackw32_addresses():
    dll_path = r"c:\entomorph\smackw32.dll"

    print("=" * 60)
    print("Analyzing smackw32.dll address layout")
    print("=" * 60)

    # Parse PE file
    print("\n1. PE File Analysis:")
    pe = pefile.PE(dll_path)

    print(f"   ImageBase: 0x{pe.OPTIONAL_HEADER.ImageBase:08x}")
    print(f"   BaseOfCode: 0x{pe.OPTIONAL_HEADER.BaseOfCode:08x}")

    print(f"\n   Sections:")
    for section in pe.sections:
        name = section.Name.decode('utf-8').rstrip('\x00')
        print(f"      {name:8s} VirtualAddress=0x{section.VirtualAddress:08x} VirtualSize=0x{section.Misc_VirtualSize:08x}")

    # Parse DWARF
    print("\n2. DWARF Analysis:")
    parser = WatcomDwarfParser(dll_path)
    dwarf_info = parser.extract_dwarf_info()

    if not dwarf_info:
        print("   No DWARF info!")
        return

    line_info = LineInfo(dwarf_info)

    # Find trampolines.cpp:10
    address = line_info.line_to_address("trampolines.cpp", 10)
    print(f"   trampolines.cpp:10 -> 0x{address:08x} (from DWARF)")

    # Check what x32dbg expects
    print(f"\n3. Expected address (from x32dbg):")
    print(f"   0x3966 (module-relative)")

    print(f"\n4. Difference:")
    print(f"   DWARF:  0x{address:08x}")
    print(f"   x32dbg: 0x00003966")
    print(f"   Delta:  0x{0x3966 - address:08x} ({0x3966 - address} bytes)")

    # Check code section offset calculation
    print(f"\n5. Code Section Detection:")
    code_section = None
    for section in pe.sections:
        name = section.Name.decode('utf-8').rstrip('\x00')
        if name == '.text' or (section.Characteristics & 0x20000000):  # IMAGE_SCN_MEM_EXECUTE
            code_section = section
            print(f"   Code section: {name}")
            print(f"   VirtualAddress: 0x{section.VirtualAddress:08x}")
            break

    if code_section:
        # What our module_manager.py does
        code_offset = code_section.VirtualAddress
        print(f"\n6. Our calculation (module_manager.py):")
        print(f"   code_section_offset = 0x{code_offset:08x}")
        print(f"   We would store: base_address + 0x{code_offset:08x}")

        # When resolving address
        dwarf_relative = address
        our_calculation = code_offset + dwarf_relative
        print(f"\n7. Address Resolution:")
        print(f"   DWARF address: 0x{dwarf_relative:08x}")
        print(f"   + code_offset: 0x{code_offset:08x}")
        print(f"   = 0x{our_calculation:08x}")
        print(f"   But should be: 0x00003966")

        if our_calculation != 0x3966:
            print(f"\n   *** BUG: Our calculation is WRONG ***")
            print(f"   We calculate: 0x{our_calculation:08x}")
            print(f"   Should be:    0x00003966")


if __name__ == '__main__':
    analyze_smackw32_addresses()
