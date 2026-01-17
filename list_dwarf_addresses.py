#!/usr/bin/env python3
"""
List all addresses in SMACKW32.DLL DWARF info
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo

dll_path = r"c:\entomorph\smackw32.dll"

print(f"Analyzing {dll_path}\n")

parser = WatcomDwarfParser(dll_path)
dwarf_info = parser.extract_dwarf_info()

if dwarf_info:
    line_info = LineInfo(dwarf_info)

    # Get all source files
    files = line_info.get_files()
    print(f"Source files ({len(files)}):")
    for f in sorted(files):
        print(f"  - {f}")

    # Get all lines
    all_lines = line_info.get_all_lines()
    print(f"\nTotal addresses: {len(all_lines)}")

    # Show address range around 0x3966
    target = 0x3966
    print(f"\nAddresses near 0x{target:04x}:")

    sorted_addrs = sorted(all_lines)
    for addr in sorted_addrs:
        if abs(addr - target) < 100:
            loc = line_info.address_to_line(addr)
            if loc:
                print(f"  0x{addr:04x} -> {Path(loc.file).name}:{loc.line}")

    # Show some addresses
    print(f"\nFirst 20 addresses:")
    for addr in sorted_addrs[:20]:
        loc = line_info.address_to_line(addr)
        if loc:
            print(f"  0x{addr:04x} -> {Path(loc.file).name}:{loc.line}")

    print(f"\nLast 20 addresses:")
    for addr in sorted_addrs[-20:]:
        loc = line_info.address_to_line(addr)
        if loc:
            print(f"  0x{addr:04x} -> {Path(loc.file).name}:{loc.line}")
else:
    print("No DWARF info found")
