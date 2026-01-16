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

                # Get the directory and file name tables
                file_entries = lineprog.header.get('file_entry', [])
                include_dirs = lineprog.header.get('include_directory', [])

                # Build file path map
                # Watcom format: If no file entries, use CU name as file 1
                if not file_entries or len(file_entries) == 0:
                    file_paths = self._build_file_paths_watcom(CU)
                else:
                    file_paths = self._build_file_paths(file_entries, include_dirs, CU)
            except Exception:
                # Skip CUs with corrupted DWARF data
                continue

            try:
                # Process line program entries
                prev_state = None
                for entry in lineprog.get_entries():
                    state = entry.state
                    if state is None:
                        continue

                    if state.end_sequence:
                        prev_state = None
                        continue

                    # Get file path for this entry
                    file_index = state.file - 1  # File indices are 1-based
                    if 0 <= file_index < len(file_paths):
                        file_path = file_paths[file_index]
                    else:
                        file_path = "unknown"

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

    def _build_file_paths_watcom(self, CU):
        """Build file paths for Watcom format where file table is empty.

        In Watcom DWARF, the file table in the line program header is empty,
        and the CU's DW_AT_name attribute contains the main source file.
        File index 1 maps to this source file.

        Args:
            CU: Compilation unit

        Returns:
            List of file paths indexed by file number (0-based)
        """
        try:
            top_die = CU.get_top_DIE()
            cu_name = top_die.attributes.get('DW_AT_name')

            if cu_name:
                file_path = cu_name.value.decode('utf-8', errors='ignore')
            else:
                file_path = "unknown"

            # Return array where index 0 = file 1, index 1 = file 2, etc.
            # Most Watcom line programs reference file 1 or 2
            return ["unknown", file_path, file_path]
        except Exception:
            return ["unknown", "unknown", "unknown"]

    def _build_file_paths(self, file_entries, include_dirs, CU):
        """Build full file paths from line program tables.

        Args:
            file_entries: File entry table from line program
            include_dirs: Include directory table from line program
            CU: Compilation unit

        Returns:
            List of file paths indexed by file number (0-based)
        """
        file_paths = ["unknown"]  # Index 0 is usually unused (files start at 1)

        for file_entry in file_entries:
            # Get directory index (0 means current directory)
            dir_index = file_entry.dir_index

            # Get file name
            file_name = file_entry.name.decode('utf-8', errors='ignore')

            # Build full path
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
            else:
                # Use include directory
                if dir_index - 1 < len(include_dirs):
                    inc_dir = include_dirs[dir_index - 1].decode('utf-8', errors='ignore')
                    full_path = str(Path(inc_dir) / file_name)
                else:
                    full_path = file_name

            file_paths.append(full_path)

        return file_paths

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
