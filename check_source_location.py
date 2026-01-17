#!/usr/bin/env python3
"""
Check source location for address 0x3966 in SMACKW32.DLL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo

dll_path = r"c:\entomorph\smackw32.dll"
target_offset = 0x3966

print(f"Analyzing {dll_path}")
print(f"Looking for offset 0x{target_offset:04x}\n")

parser = WatcomDwarfParser(dll_path)
dwarf_info = parser.extract_dwarf_info()

if dwarf_info:
    line_info = LineInfo(dwarf_info)

    # Get location for this address
    loc = line_info.address_to_line(target_offset)

    if loc:
        print(f"Found source location:")
        print(f"  File: {loc.file}")
        print(f"  Line: {loc.line}")
        print(f"  Address: 0x{loc.address:08x}")

        # Try to read the source file
        source_path = Path(loc.file)
        if source_path.exists():
            print(f"\nSource code at {loc.file}:{loc.line}:")
            with open(source_path, 'r') as f:
                lines = f.readlines()
                start = max(0, loc.line - 6)
                end = min(len(lines), loc.line + 5)
                for i in range(start, end):
                    marker = ">>>" if i + 1 == loc.line else "   "
                    print(f"{marker} {i+1:4d}: {lines[i].rstrip()}")
        else:
            print(f"\nSource file not found at: {loc.file}")
            print(f"The file may need to be at this path for source viewing to work")
    else:
        print(f"No source location found for offset 0x{target_offset:04x}")

        # Show what addresses we DO have
        print("\nAvailable addresses in DWARF:")
        all_lines = line_info.get_all_lines()
        if all_lines:
            print(f"  First address: 0x{min(all_lines):08x}")
            print(f"  Last address:  0x{max(all_lines):08x}")
            print(f"  Total lines:   {len(all_lines)}")
else:
    print("No DWARF info found")
