"""
DIE (Debug Information Entry) parser for DWARF debug information.

Parses the DIE tree to extract information about subprograms (functions),
variables, parameters, and types for variable inspection.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.die import DIE


@dataclass
class SubprogramInfo:
    """Represents a function/subprogram with debug information."""

    name: str
    low_pc: int  # Start address (relative to module base)
    high_pc: int  # End address (relative to module base)
    frame_base: Optional[bytes]  # Frame base location expression
    die: DIE  # Original DIE for additional attribute access

    def contains_address(self, address: int) -> bool:
        """Check if address is within this subprogram's range."""
        return self.low_pc <= address < self.high_pc


@dataclass
class VariableInfo:
    """Represents a variable or parameter with debug information."""

    name: str
    type_offset: Optional[int]  # DIE offset of the type
    location: Optional[bytes]  # Location expression
    is_parameter: bool  # True for parameters, False for local variables
    die: DIE  # Original DIE for additional attribute access


class DIEParser:
    """Parser for DWARF DIE tree.

    Builds searchable indexes for subprograms, variables, and types
    to enable efficient variable inspection.
    """

    def __init__(self, dwarf_info: DWARFInfo):
        self.dwarf_info = dwarf_info

        # Indexes built during initialization
        self.subprograms: List[SubprogramInfo] = []
        self.types: Dict[int, DIE] = {}  # type_offset -> type DIE

        # Build indexes
        self._build_indexes()

    def _build_indexes(self):
        """Build indexes by traversing all compilation units."""
        for CU in self.dwarf_info.iter_CUs():
            try:
                top_die = CU.get_top_DIE()
                self._index_die_tree(top_die, CU)
            except Exception:
                # Skip CUs with errors
                continue

    def _index_die_tree(self, die: DIE, cu):
        """Recursively index DIEs in the tree.

        Args:
            die: Current DIE to process
            cu: Compilation unit (for offset calculations)
        """
        # Index based on tag type
        tag = die.tag

        if tag == 'DW_TAG_subprogram':
            self._index_subprogram(die, cu)
        elif tag in ('DW_TAG_base_type', 'DW_TAG_pointer_type',
                     'DW_TAG_structure_type', 'DW_TAG_typedef',
                     'DW_TAG_const_type', 'DW_TAG_array_type'):
            self._index_type(die, cu)

        # Recursively process children
        for child in die.iter_children():
            self._index_die_tree(child, cu)

    def _index_subprogram(self, die: DIE, cu):
        """Index a subprogram (function) DIE.

        Args:
            die: Subprogram DIE
            cu: Compilation unit
        """
        try:
            # Extract attributes
            attrs = die.attributes

            # Get name
            name_attr = attrs.get('DW_AT_name')
            if not name_attr:
                return  # Skip unnamed subprograms
            name = name_attr.value.decode('utf-8', errors='ignore')

            # Get address range
            low_pc_attr = attrs.get('DW_AT_low_pc')
            high_pc_attr = attrs.get('DW_AT_high_pc')

            if not low_pc_attr:
                return  # Skip subprograms without address info

            low_pc = low_pc_attr.value

            # high_pc can be absolute address or offset from low_pc
            if high_pc_attr:
                high_pc_value = high_pc_attr.value
                # Check if it's a constant (offset) or address
                if high_pc_attr.form in ('DW_FORM_data1', 'DW_FORM_data2',
                                         'DW_FORM_data4', 'DW_FORM_data8'):
                    # It's an offset
                    high_pc = low_pc + high_pc_value
                else:
                    # It's an absolute address
                    high_pc = high_pc_value
            else:
                # No high_pc, use low_pc + 1 as a minimal range
                high_pc = low_pc + 1

            # Get frame base (usually DW_OP_reg5 for EBP)
            frame_base_attr = attrs.get('DW_AT_frame_base')
            frame_base = frame_base_attr.value if frame_base_attr else None

            # Create and store subprogram info
            subprog = SubprogramInfo(
                name=name,
                low_pc=low_pc,
                high_pc=high_pc,
                frame_base=frame_base,
                die=die
            )
            self.subprograms.append(subprog)

        except Exception:
            # Skip malformed subprogram DIEs
            pass

    def _index_type(self, die: DIE, cu):
        """Index a type DIE.

        Args:
            die: Type DIE
            cu: Compilation unit
        """
        try:
            # Store type DIE by its offset
            type_offset = die.offset
            self.types[type_offset] = die
        except Exception:
            pass

    def find_subprogram_at_address(self, address: int) -> Optional[SubprogramInfo]:
        """Find the subprogram containing the given address.

        Args:
            address: Address (relative to module base)

        Returns:
            SubprogramInfo if found, None otherwise
        """
        for subprog in self.subprograms:
            if subprog.contains_address(address):
                return subprog
        return None

    def get_variables_in_subprogram(self, subprog: SubprogramInfo) -> List[VariableInfo]:
        """Get all variables and parameters in a subprogram.

        Args:
            subprog: Subprogram to extract variables from

        Returns:
            List of VariableInfo objects
        """
        variables = []

        try:
            # Recursively collect variables from the subprogram and all lexical blocks
            self._collect_variables_recursive(subprog.die, variables)

        except Exception:
            # Return what we have if error occurs
            pass

        return variables

    def _collect_variables_recursive(self, die: DIE, variables: List[VariableInfo]):
        """Recursively collect variables from a DIE and its lexical blocks.

        Args:
            die: Current DIE (subprogram or lexical block)
            variables: List to append variables to
        """
        # Iterate through child DIEs
        for child in die.iter_children():
            tag = child.tag

            if tag == 'DW_TAG_variable':
                var_info = self._parse_variable(child, is_parameter=False)
                if var_info:
                    variables.append(var_info)

            elif tag == 'DW_TAG_formal_parameter':
                var_info = self._parse_variable(child, is_parameter=True)
                if var_info:
                    variables.append(var_info)

            elif tag == 'DW_TAG_lexical_block':
                # Recursively search inside lexical blocks
                self._collect_variables_recursive(child, variables)

    def _parse_variable(self, die: DIE, is_parameter: bool) -> Optional[VariableInfo]:
        """Parse a variable or parameter DIE.

        Args:
            die: Variable or parameter DIE
            is_parameter: True if this is a formal parameter

        Returns:
            VariableInfo if valid, None otherwise
        """
        try:
            attrs = die.attributes

            # Get name
            name_attr = attrs.get('DW_AT_name')
            if not name_attr:
                return None  # Skip unnamed variables
            name = name_attr.value.decode('utf-8', errors='ignore')

            # Skip artificial variables (e.g., .return, compiler-generated temps)
            artificial_attr = attrs.get('DW_AT_artificial')
            if artificial_attr and artificial_attr.value:
                return None

            # Get type reference
            # Type reference is CU-relative, need to add CU offset
            type_attr = attrs.get('DW_AT_type')
            if type_attr:
                # Type offset is relative to CU, add CU offset to get absolute offset
                type_offset = type_attr.value + die.cu.cu_offset
            else:
                type_offset = None

            # Get location expression
            location_attr = attrs.get('DW_AT_location')
            location = location_attr.value if location_attr else None

            return VariableInfo(
                name=name,
                type_offset=type_offset,
                location=location,
                is_parameter=is_parameter,
                die=die
            )

        except Exception:
            return None

    def get_type_die(self, type_offset: int) -> Optional[DIE]:
        """Get a type DIE by its offset.

        Args:
            type_offset: DIE offset

        Returns:
            DIE if found, None otherwise
        """
        return self.types.get(type_offset)

    def get_subprogram_count(self) -> int:
        """Get the number of indexed subprograms."""
        return len(self.subprograms)

    def get_type_count(self) -> int:
        """Get the number of indexed types."""
        return len(self.types)
