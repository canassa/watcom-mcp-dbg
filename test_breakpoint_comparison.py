"""Test to compare file:line vs module:offset breakpoint resolution."""
import sys
from pathlib import Path

# Add src to path
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

# Try to resolve trampolines.cpp:10
dwarf_addr = line_info.line_to_address("trampolines.cpp", 10)

if dwarf_addr is not None:
    print(f"trampolines.cpp:10 resolves to DWARF address: 0x{dwarf_addr:08x}")
    print(f"Expected offset from code section: 0x{dwarf_addr:08x}")
    print(f"\nIf base = 0x01f40000 and code_section_offset = 0x1000:")
    print(f"  Absolute address = 0x01f40000 + 0x1000 + 0x{dwarf_addr:08x} = 0x{0x01f40000 + 0x1000 + dwarf_addr:08x}")
    print(f"\nIf you specify smackw32.dll:0x{dwarf_addr:x} it becomes:")
    print(f"  Absolute address = 0x01f40000 + 0x{dwarf_addr:08x} = 0x{0x01f40000 + dwarf_addr:08x}")
else:
    print("Could not resolve trampolines.cpp:10")
