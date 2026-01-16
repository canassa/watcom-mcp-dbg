"""
Detailed inspection of DWARF line program to understand file name issues
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.dwarf.parser import WatcomDwarfParser


def inspect_line_program(dll_path):
    """Inspect the line program structure in detail."""
    print(f"Inspecting line program in: {dll_path}")
    print("=" * 60)

    parser = WatcomDwarfParser(dll_path)
    dwarf_info = parser.extract_dwarf_info()

    if not dwarf_info:
        print("No DWARF info found")
        return

    print(f"DWARF format: {parser.get_format_type()}")
    print()

    for i, CU in enumerate(parser.get_compilation_units(), 1):
        print(f"\n{'=' * 60}")
        print(f"Compilation Unit {i}")
        print('=' * 60)

        try:
            # Get top DIE
            top_die = CU.get_top_DIE()
            cu_name = top_die.attributes.get('DW_AT_name')
            cu_comp_dir = top_die.attributes.get('DW_AT_comp_dir')
            cu_stmt_list = top_die.attributes.get('DW_AT_stmt_list')

            if cu_name:
                print(f"CU Name: {cu_name.value.decode('utf-8', errors='ignore')}")
            if cu_comp_dir:
                print(f"Comp Dir: {cu_comp_dir.value.decode('utf-8', errors='ignore')}")
            if cu_stmt_list:
                print(f"Stmt List: 0x{cu_stmt_list.value:x}")

            # Get line program
            lineprog = dwarf_info.line_program_for_CU(CU)
            if not lineprog:
                print("No line program for this CU")
                continue

            print("\nLine Program Header:")
            print(f"  Version: {lineprog.header.version}")
            print(f"  Minimum instruction length: {lineprog.header.minimum_instruction_length}")
            print(f"  Default is_stmt: {lineprog.header.default_is_stmt}")
            print(f"  Line base: {lineprog.header.line_base}")
            print(f"  Line range: {lineprog.header.line_range}")
            print(f"  Opcode base: {lineprog.header.opcode_base}")

            # Include directories
            include_dirs = lineprog.header.get('include_directory', [])
            print(f"\nInclude Directories ({len(include_dirs)}):")
            for idx, dir in enumerate(include_dirs):
                dir_str = dir.decode('utf-8', errors='ignore')
                print(f"  [{idx}] {dir_str}")

            # File entries
            file_entries = lineprog.header['file_entry']
            print(f"\nFile Entries ({len(file_entries)}):")
            for idx, entry in enumerate(file_entries):
                name = entry.name.decode('utf-8', errors='ignore')
                dir_index = entry.dir_index
                mtime = entry.mtime
                length = entry.length
                print(f"  [{idx}] {name} (dir_index={dir_index}, mtime={mtime}, length={length})")

            # Show first few line program entries
            print("\nFirst 20 line program entries:")
            for idx, entry in enumerate(lineprog.get_entries()):
                if idx >= 20:
                    break
                if entry.state:
                    state = entry.state
                    print(f"  {idx}: addr=0x{state.address:08x} file={state.file} line={state.line} col={state.column} is_stmt={state.is_stmt} end_seq={state.end_sequence}")
                else:
                    print(f"  {idx}: command only")

            # Only process first CU in detail to avoid spam
            if i >= 3:
                break

        except Exception as e:
            print(f"Error processing CU {i}: {e}")
            import traceback
            traceback.print_exc()
            if i >= 3:
                break


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_line_program.py <path_to_dll>")
        sys.exit(1)

    inspect_line_program(sys.argv[1])
