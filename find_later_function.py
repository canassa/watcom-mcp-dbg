"""Find a function in smackw32.dll that's likely called after initialization."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo

dll_path = r"C:\entomorph\smackw32.dll"
parser = WatcomDwarfParser(dll_path)
dwarf_info = parser.extract_dwarf_info()

if not dwarf_info:
    print("No DWARF info found")
    sys.exit(1)

print("Functions in smackw32.dll (showing first 30):")
print("=" * 60)

count = 0
for CU in dwarf_info.iter_CUs():
    try:
        for DIE in CU.iter_DIEs():
            if DIE.tag == 'DW_TAG_subprogram':
                name_attr = DIE.attributes.get('DW_AT_name')
                low_pc_attr = DIE.attributes.get('DW_AT_low_pc')

                if name_attr and low_pc_attr:
                    func_name = name_attr.value.decode('utf-8', errors='ignore')
                    low_pc = low_pc_attr.value

                    # Skip internal/initialization functions
                    if any(skip in func_name.lower() for skip in ['initialize', '_start', 'crt', 'init_', '__']):
                        continue

                    print(f"  0x{low_pc:08x}  {func_name}")
                    count += 1

                    if count >= 30:
                        break
    except:
        continue

    if count >= 30:
        break

print("\n" + "=" * 60)
print("Try setting a breakpoint on one of these functions (they're more")
print("likely to be called during normal execution, not DLL initialization)")
