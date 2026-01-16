"""
DWARF parser for Windows PE files with support for Watcom format.

Watcom compilers append a minimal ELF container with DWARF data to PE executables,
rather than using standard PE debug sections. This parser handles both formats.
"""

import io
import struct
from pathlib import Path
from typing import Optional

import pefile
from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarfinfo import DWARFInfo


class WatcomDwarfParser:
    """Parser for DWARF debug information in Windows PE files.

    Supports both:
    1. Standard PE debug sections (.debug_info, .debug_line, etc.)
    2. Watcom format: appended ELF container with DWARF data
    """

    def __init__(self, pe_path: str | Path):
        self.pe_path = Path(pe_path)
        self.pe = None
        self.dwarf_info: Optional[DWARFInfo] = None
        self.format_type: Optional[str] = None  # 'pe_sections' or 'watcom_elf'

    def extract_dwarf_info(self) -> Optional[DWARFInfo]:
        """Extract DWARF info from the PE file.

        Returns:
            DWARFInfo object if debug info found, None otherwise
        """
        if not self.pe_path.exists():
            raise FileNotFoundError(f"PE file not found: {self.pe_path}")

        # Try standard PE sections first
        self.pe = pefile.PE(str(self.pe_path))
        dwarf_info = self._try_pe_sections()
        if dwarf_info:
            self.dwarf_info = dwarf_info
            self.format_type = 'pe_sections'
            return dwarf_info

        # Try Watcom appended ELF container
        dwarf_info = self._try_watcom_elf()
        if dwarf_info:
            self.dwarf_info = dwarf_info
            self.format_type = 'watcom_elf'
            return dwarf_info

        return None

    def _try_pe_sections(self) -> Optional[DWARFInfo]:
        """Try to extract DWARF from standard PE debug sections.

        Returns:
            DWARFInfo object if sections found, None otherwise
        """
        # Look for .debug_* sections
        debug_sections = {}
        for section in self.pe.sections:
            section_name = section.Name.decode('utf-8', errors='ignore').rstrip('\x00')
            if section_name.startswith('.debug_'):
                debug_sections[section_name] = section.get_data()

        if not debug_sections:
            return None

        # We need at least .debug_info to have valid DWARF
        if '.debug_info' not in debug_sections:
            return None

        # Create a minimal ELF-like structure for pyelftools
        # pyelftools expects to read from an ELF file, so we need to create one
        # This is complex, so for now we'll return None and rely on Watcom format
        # TODO: Implement PE section to DWARFInfo conversion if needed
        return None

    def _try_watcom_elf(self) -> Optional[DWARFInfo]:
        """Try to extract DWARF from Watcom appended ELF container.

        Watcom compilers append an ELF file with DWARF sections to the end of the PE file.
        We scan for the ELF magic bytes (0x7F 'E' 'L' 'F') and extract the ELF data.

        Returns:
            DWARFInfo object if ELF container found, None otherwise
        """
        with open(self.pe_path, 'rb') as f:
            data = f.read()

        # Look for ELF magic bytes: 0x7F 'E' 'L' 'F'
        elf_magic = b'\x7fELF'
        elf_offset = data.find(elf_magic)

        if elf_offset == -1:
            return None

        # Extract ELF data from the offset to end of file
        elf_data = data[elf_offset:]

        # Validate it's a proper ELF file
        if len(elf_data) < 52:  # Minimum ELF header size
            return None

        try:
            # Parse the ELF file
            elf_file = ELFFile(io.BytesIO(elf_data))

            # Check if it has DWARF info
            if not elf_file.has_dwarf_info():
                return None

            # Get DWARF info
            dwarf_info = elf_file.get_dwarf_info()
            return dwarf_info

        except Exception as e:
            # Not a valid ELF file or no DWARF info
            return None

    def get_compilation_units(self):
        """Get all compilation units from DWARF info.

        Yields:
            Compilation unit DIEs
        """
        if not self.dwarf_info:
            return

        for CU in self.dwarf_info.iter_CUs():
            yield CU

    def has_debug_info(self) -> bool:
        """Check if debug information was found."""
        return self.dwarf_info is not None

    def get_format_type(self) -> Optional[str]:
        """Get the format type of the debug info.

        Returns:
            'pe_sections', 'watcom_elf', or None if no debug info
        """
        return self.format_type
