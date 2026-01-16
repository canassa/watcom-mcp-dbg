"""
Module manager for tracking loaded modules (EXE + DLLs) and their debug info.

Handles multi-module debugging where different modules may have different debug information.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dgb.dwarf.parser import WatcomDwarfParser
from dgb.dwarf.line_info import LineInfo, SourceLocation


@dataclass
class Module:
    """Represents a loaded module (EXE or DLL)."""

    name: str  # Module name (e.g., "smackw32.dll")
    base_address: int  # Base address where module is loaded
    path: str  # Full path to module file
    size: int = 0  # Module size in memory
    has_debug_info: bool = False  # Whether DWARF info was found
    parser: Optional[WatcomDwarfParser] = None  # DWARF parser if debug info exists
    line_info: Optional[LineInfo] = None  # Line info if debug info exists


class ModuleManager:
    """Manages loaded modules and their debug information.

    This is critical for multi-module debugging where:
    - The main EXE may not have debug info
    - DLLs may have debug info (like smackw32.dll)
    - Addresses must be resolved across module boundaries
    """

    def __init__(self):
        self.modules = {}  # {base_address: Module}
        self.modules_by_name = {}  # {name: Module} for quick lookup

    def on_module_loaded(self, name: str, base_address: int, path: str, size: int = 0):
        """Called when a module is loaded (CREATE_PROCESS or LOAD_DLL event).

        Args:
            name: Module name (e.g., "smackw32.dll")
            base_address: Base address where module is loaded
            path: Full path to module file
            size: Size of module in memory
        """
        print(f"[Module] Loaded: {name} at 0x{base_address:08x}")

        module = Module(
            name=name,
            base_address=base_address,
            path=path,
            size=size
        )

        self.modules[base_address] = module
        self.modules_by_name[name.lower()] = module

        # Try to extract DWARF info
        self._load_debug_info(module)

    def _load_debug_info(self, module: Module):
        """Try to load DWARF debug information for a module.

        Args:
            module: Module to load debug info for
        """
        if not module.path:
            print(f"[Module] {module.name}: No file path available")
            return

        if not Path(module.path).exists():
            print(f"[Module] {module.name}: File not found at {module.path}")
            return

        parser = WatcomDwarfParser(module.path)
        dwarf_info = parser.extract_dwarf_info()

        if dwarf_info:
            module.has_debug_info = True
            module.parser = parser

            # Build line info
            line_info = LineInfo(dwarf_info)
            module.line_info = line_info
            print(f"[Module] {module.name}: DWARF 2 debug info loaded ({parser.get_format_type()})")

            # Show source files
            files = line_info.get_files()
            if files:
                print(f"[Module] {module.name}: {len(files)} source files")
                for file in sorted(files):
                    print(f"         - {Path(file).name}")
        else:
            print(f"[Module] {module.name}: No debug info")

    def address_to_module(self, address: int) -> Optional[Module]:
        """Find which module owns an address.

        Args:
            address: Absolute memory address

        Returns:
            Module if found, None otherwise
        """
        for base_addr, module in self.modules.items():
            if module.size > 0:
                # Use size if available
                if base_addr <= address < base_addr + module.size:
                    return module
            else:
                # Without size, just check if address is >= base
                # This is less accurate but works for most cases
                if address >= base_addr:
                    # Check if there's a higher base address
                    higher_base = None
                    for other_base in self.modules.keys():
                        if base_addr < other_base <= address:
                            if higher_base is None or other_base < higher_base:
                                higher_base = other_base

                    if higher_base is None:
                        return module

        return None

    def resolve_address_to_line(self, absolute_address: int) -> Optional[tuple[str, SourceLocation, Module]]:
        """Resolve an absolute address to source location.

        Args:
            absolute_address: Absolute memory address

        Returns:
            Tuple of (module_name, SourceLocation, Module) if found, None otherwise
        """
        module = self.address_to_module(absolute_address)
        if not module or not module.line_info:
            return None

        # Convert absolute address to module-relative address
        relative_addr = absolute_address - module.base_address

        # Look up line info
        loc = module.line_info.address_to_line(relative_addr)
        if loc:
            return (module.name, loc, module)

        return None

    def resolve_line_to_address(self, filename: str, line: int) -> Optional[tuple[int, Module]]:
        """Resolve a source location to absolute address.

        Searches all modules with debug info.

        Args:
            filename: Source file name (can be basename or full path)
            line: Line number

        Returns:
            Tuple of (absolute_address, Module) if found, None otherwise
        """
        # Try each module with debug info
        for module in self.modules.values():
            if not module.line_info:
                continue

            # Try to resolve in this module
            relative_addr = module.line_info.line_to_address(filename, line)
            if relative_addr is not None:
                absolute_addr = module.base_address + relative_addr
                return (absolute_addr, module)

        return None

    def get_module_by_name(self, name: str) -> Optional[Module]:
        """Get a module by name.

        Args:
            name: Module name (case-insensitive)

        Returns:
            Module if found, None otherwise
        """
        return self.modules_by_name.get(name.lower())

    def get_all_modules(self):
        """Get all loaded modules.

        Yields:
            Module objects
        """
        # Sort by base address
        for base_addr in sorted(self.modules.keys()):
            yield self.modules[base_addr]

    def get_modules_with_debug_info(self):
        """Get modules that have debug information.

        Yields:
            Module objects with debug info
        """
        for module in self.modules.values():
            if module.has_debug_info:
                yield module

    def get_all_source_files(self):
        """Get all source files across all modules.

        Returns:
            Set of source file paths
        """
        files = set()
        for module in self.modules.values():
            if module.line_info:
                files.update(module.line_info.get_files())
        return files
