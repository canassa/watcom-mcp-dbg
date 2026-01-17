"""Check what function trampolines.cpp:10 is in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo

# Load smackw32.dll debug info
dll_path = r"C:\entomorph\smackw32.dll"
parser = WatcomDwarfParser(dll_path)
dwarf_info = parser.extract_dwarf_info()

if not dwarf_info:
    print("No DWARF info found")
    sys.exit(1)

line_info = LineInfo(dwarf_info)

# Get locations around line 10
print("Source locations in trampolines.cpp around line 10:")
print("=" * 60)

for loc in sorted(line_info.get_all_locations(), key=lambda x: (x.file, x.line)):
    if 'trampolines.cpp' in loc.file.lower() and 5 <= loc.line <= 15:
        print(f"  Line {loc.line:3d} @ 0x{loc.address:08x}")

# Try to find function names from DIEs
print("\n" + "=" * 60)
print("Searching for function containing address 0x2966...")

target_addr = 0x2966

for CU in dwarf_info.iter_CUs():
    for DIE in CU.iter_DIEs():
        if DIE.tag == 'DW_TAG_subprogram':
            # This is a function
            name_attr = DIE.attributes.get('DW_AT_name')
            low_pc_attr = DIE.attributes.get('DW_AT_low_pc')
            high_pc_attr = DIE.attributes.get('DW_AT_high_pc')

            if name_attr and low_pc_attr:
                func_name = name_attr.value.decode('utf-8', errors='ignore')
                low_pc = low_pc_attr.value

                # high_pc can be an address or an offset
                if high_pc_attr:
                    high_pc_value = high_pc_attr.value
                    if high_pc_attr.form in ['DW_FORM_addr']:
                        high_pc = high_pc_value
                    else:
                        # It's an offset from low_pc
                        high_pc = low_pc + high_pc_value
                else:
                    high_pc = low_pc

                # Check if target address is in this function
                if low_pc <= target_addr <= high_pc:
                    print(f"\nFound function: {func_name}")
                    print(f"  Range: 0x{low_pc:08x} - 0x{high_pc:08x}")
                    print(f"  Target 0x{target_addr:08x} is in this function")
