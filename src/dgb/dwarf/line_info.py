"""
Line number information from DWARF debug data.

Provides bidirectional mapping between addresses and source code locations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from elftools.dwarf.dwarfinfo import DWARFInfo


@dataclass
class SourceLocation:
    """Represents a source code location."""

    file: str
    line: int
    column: int
    address: int

    def __str__(self):
        return f"{self.file}:{self.line}:{self.column}"


class LineInfo:
    """Manager for line number information from DWARF.

    Provides mapping between memory addresses and source code locations.
    """

    def __init__(self, dwarf_info: DWARFInfo):
        self.dwarf_info = dwarf_info
        self._address_to_line_cache = {}  # address -> SourceLocation
        self._line_to_address_cache = {}  # (file, line) -> address
        self._build_cache()

    def _build_cache(self):
        """Build lookup caches from DWARF line program."""
        for CU in self.dwarf_info.iter_CUs():
            try:
                # Get line program for this compilation unit
                lineprog = self.dwarf_info.line_program_for_CU(CU)
                if not lineprog:
                    continue

                # Build file paths on-demand during iteration
                # NOTE: pyelftools lazy-loads file_entry, so we can't check if empty
                # before iterating. Access it inside the loop after it's populated.
                file_paths_cache = {}

                # Process line program entries
                prev_state = None
                for entry in lineprog.get_entries():
                    state = entry.state
                    if state is None:
                        continue

                    if state.end_sequence:
                        prev_state = None
                        continue

                    # Build file path on-demand (pyelftools has now populated file_entry)
                    file_index = state.file - 1  # Convert to 0-based

                    if file_index not in file_paths_cache:
                        # Access file_entries NOW (after iteration started - will be populated!)
                        file_entries = lineprog.header.get('file_entry', [])
                        include_dirs = lineprog.header.get('include_directory', [])

                        if 0 <= file_index < len(file_entries):
                            # Build full path from file_entry
                            file_entry = file_entries[file_index]
                            file_name = file_entry.name.decode('utf-8', errors='ignore')
                            dir_index = file_entry.dir_index

                            if dir_index == 0:
                                # Current directory - use CU's compilation directory
                                try:
                                    comp_dir = CU.get_top_DIE().attributes.get('DW_AT_comp_dir')
                                    if comp_dir:
                                        comp_dir_str = comp_dir.value.decode('utf-8', errors='ignore')
                                        full_path = str(Path(comp_dir_str) / file_name)
                                    else:
                                        full_path = file_name
                                except Exception:
                                    full_path = file_name
                            elif 0 < dir_index <= len(include_dirs):
                                # Use include directory
                                inc_dir = include_dirs[dir_index - 1].decode('utf-8', errors='ignore')
                                full_path = str(Path(inc_dir) / file_name)
                            else:
                                full_path = file_name

                            file_paths_cache[file_index] = full_path
                        else:
                            # Fallback to Watcom format: use CU name
                            try:
                                top_die = CU.get_top_DIE()
                                cu_name = top_die.attributes.get('DW_AT_name')
                                if cu_name:
                                    file_paths_cache[file_index] = cu_name.value.decode('utf-8', errors='ignore')
                                else:
                                    file_paths_cache[file_index] = "unknown"
                            except Exception:
                                file_paths_cache[file_index] = "unknown"

                    file_path = file_paths_cache[file_index]

                    # Create source location
                    loc = SourceLocation(
                        file=file_path,
                        line=state.line,
                        column=state.column,
                        address=state.address
                    )

                    # Add to caches
                    self._address_to_line_cache[state.address] = loc

                    # For line-to-address, use the first address for each line
                    key = (file_path, state.line)
                    if key not in self._line_to_address_cache:
                        self._line_to_address_cache[key] = state.address

                    prev_state = state
            except Exception:
                # Skip line programs with corrupted data
                continue


    def address_to_line(self, address: int) -> Optional[SourceLocation]:
        """Convert an address to a source location.

        Args:
            address: Memory address (relative to module base)

        Returns:
            SourceLocation if found, None otherwise
        """
        # Exact match
        if address in self._address_to_line_cache:
            return self._address_to_line_cache[address]

        # Find closest address before this one
        closest_addr = None
        for addr in sorted(self._address_to_line_cache.keys()):
            if addr <= address:
                closest_addr = addr
            else:
                break

        if closest_addr is not None:
            return self._address_to_line_cache[closest_addr]

        return None

    def line_to_address(self, file: str, line: int) -> Optional[int]:
        """Convert a source location to an address.

        Args:
            file: Source file path (can be basename or full path)
            line: Line number

        Returns:
            Address if found, None otherwise
        """
        # Try exact match first
        key = (file, line)
        if key in self._line_to_address_cache:
            return self._line_to_address_cache[key]

        # Try basename match (in case user provides just the filename)
        file_basename = Path(file).name
        for (cached_file, cached_line), addr in self._line_to_address_cache.items():
            if Path(cached_file).name == file_basename and cached_line == line:
                return addr

        # Try case-insensitive match (Windows paths)
        file_lower = file.lower()
        file_basename_lower = file_basename.lower()
        for (cached_file, cached_line), addr in self._line_to_address_cache.items():
            if (cached_file.lower() == file_lower or
                Path(cached_file).name.lower() == file_basename_lower) and cached_line == line:
                return addr

        return None

    def get_all_locations(self):
        """Get all source locations.

        Yields:
            SourceLocation objects
        """
        seen = set()
        for loc in self._address_to_line_cache.values():
            key = (loc.file, loc.line)
            if key not in seen:
                seen.add(key)
                yield loc

    def get_files(self):
        """Get all source files referenced in debug info.

        Returns:
            Set of file paths
        """
        files = set()
        for loc in self._address_to_line_cache.values():
            files.add(loc.file)
        return files
