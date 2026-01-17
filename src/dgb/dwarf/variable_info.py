"""
High-level variable inspection.

Orchestrates DIE parsing, location evaluation, and type formatting
to provide complete variable inspection at breakpoints.
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
import struct

from dgb.dwarf.die_parser import DIEParser, SubprogramInfo, VariableInfo as DIEVariableInfo
from dgb.dwarf.location_eval import LocationEvaluator, LocationEvaluationError
from dgb.dwarf.type_info import TypeResolver

if TYPE_CHECKING:
    from dgb.debugger.process_controller import ProcessController
    from elftools.dwarf.dwarfinfo import DWARFInfo


@dataclass
class Variable:
    """Represents an inspected variable with all information."""

    name: str
    type_name: str
    value: str
    location: str  # 'stack', 'register', 'global', 'unavailable'
    address: Optional[str]  # Hex address if applicable
    is_parameter: bool


class VariableInspector:
    """High-level variable inspector.

    Coordinates DIE parsing, location evaluation, and type resolution
    to provide complete variable inspection at a given address.
    """

    def __init__(self, dwarf_info: 'DWARFInfo', process_controller: 'ProcessController'):
        self.dwarf_info = dwarf_info
        self.process_controller = process_controller

        # Initialize components
        self.die_parser = DIEParser(dwarf_info)
        self.location_evaluator = LocationEvaluator(process_controller)
        self.type_resolver = TypeResolver(self.die_parser)

    def get_variables_at_address(
        self,
        address: int,
        thread_id: int,
        module_base: int = 0
    ) -> List[Variable]:
        """Get all variables visible at the given address.

        Args:
            address: Current address (relative to module base)
            thread_id: Thread ID for register/memory access
            module_base: Module base address for address relocation

        Returns:
            List of Variable objects with complete information
        """
        variables = []

        # Find subprogram containing this address
        subprogram = self.die_parser.find_subprogram_at_address(address)

        if not subprogram:
            return variables  # No function found at this address

        # Evaluate frame base (usually EBP)
        frame_base = self._evaluate_frame_base(subprogram, thread_id, module_base)

        # Get all variables in the subprogram
        die_variables = self.die_parser.get_variables_in_subprogram(subprogram)

        # Inspect each variable
        for die_var in die_variables:
            var = self._inspect_variable(die_var, thread_id, frame_base, module_base)
            if var:
                variables.append(var)

        return variables

    def _evaluate_frame_base(
        self,
        subprogram: SubprogramInfo,
        thread_id: int,
        module_base: int
    ) -> Optional[int]:
        """Evaluate the frame base for a subprogram.

        Args:
            subprogram: Subprogram information
            thread_id: Thread ID for register access
            module_base: Module base address

        Returns:
            Frame base address (usually EBP value) or None
        """
        if not subprogram.frame_base:
            # No frame base - try to use EBP directly
            try:
                return self.process_controller.get_register(thread_id, 'ebp')
            except Exception:
                return None

        try:
            return self.location_evaluator.evaluate_frame_base(
                subprogram.frame_base,
                thread_id,
                module_base
            )
        except LocationEvaluationError:
            # Fallback to EBP if frame base evaluation fails
            try:
                return self.process_controller.get_register(thread_id, 'ebp')
            except Exception:
                return None

    def _inspect_variable(
        self,
        die_var: DIEVariableInfo,
        thread_id: int,
        frame_base: Optional[int],
        module_base: int
    ) -> Optional[Variable]:
        """Inspect a single variable.

        Args:
            die_var: Variable information from DIE parser
            thread_id: Thread ID for access
            frame_base: Frame base address
            module_base: Module base address

        Returns:
            Variable object with all information, or None if inspection fails
        """
        # Get type name
        type_name = 'unknown'
        if die_var.type_offset:
            try:
                type_name = self.type_resolver.get_type_name(die_var.type_offset)
            except Exception:
                pass

        # Check for constant value (optimized-out variable with known value)
        const_value_attr = die_var.die.attributes.get('DW_AT_const_value')
        if const_value_attr:
            # Variable has constant value
            const_val = const_value_attr.value
            return Variable(
                name=die_var.name,
                type_name=type_name,
                value=str(const_val),
                location='constant',
                address=None,
                is_parameter=die_var.is_parameter
            )

        # Evaluate location
        if not die_var.location:
            # No location - variable is unavailable (optimized out)
            return Variable(
                name=die_var.name,
                type_name=type_name,
                value='<unavailable>',
                location='unavailable',
                address=None,
                is_parameter=die_var.is_parameter
            )

        # Try to evaluate location expression
        try:
            var_address = self.location_evaluator.evaluate_location(
                die_var.location,
                thread_id,
                frame_base,
                module_base
            )

            # Determine location type based on expression
            location_type = self._determine_location_type(die_var.location)

            # For register-held values, the "address" is actually the value itself
            if location_type == 'register':
                # Value is in register - no memory read needed
                value_str = self._format_register_value(var_address, die_var.type_offset)
                return Variable(
                    name=die_var.name,
                    type_name=type_name,
                    value=value_str,
                    location='register',
                    address=None,
                    is_parameter=die_var.is_parameter
                )

            # For stack/global, read memory at the address
            value_str = self._read_and_format_value(var_address, die_var.type_offset)

            return Variable(
                name=die_var.name,
                type_name=type_name,
                value=value_str,
                location=location_type,
                address=f"0x{var_address:08x}",
                is_parameter=die_var.is_parameter
            )

        except LocationEvaluationError as e:
            # Location evaluation failed
            return Variable(
                name=die_var.name,
                type_name=type_name,
                value=f'<unavailable: {e}>',
                location='unavailable',
                address=None,
                is_parameter=die_var.is_parameter
            )
        except Exception as e:
            # Unexpected error
            return Variable(
                name=die_var.name,
                type_name=type_name,
                value=f'<error: {e}>',
                location='error',
                address=None,
                is_parameter=die_var.is_parameter
            )

    def _determine_location_type(self, location_expr: bytes) -> str:
        """Determine the type of location (stack, register, global).

        Args:
            location_expr: Location expression bytes

        Returns:
            'stack', 'register', 'global', or 'unknown'
        """
        if not location_expr:
            return 'unknown'

        opcode = location_expr[0]

        # DW_OP_reg* (0x50-0x6F) - register
        if 0x50 <= opcode <= 0x6F:
            return 'register'

        # DW_OP_fbreg (0x91) - frame base relative (stack)
        if opcode == 0x91:
            return 'stack'

        # DW_OP_breg* (0x70-0x8F) - base register + offset (usually stack)
        if 0x70 <= opcode <= 0x8F:
            return 'stack'

        # DW_OP_addr (0x03) - absolute address (global)
        if opcode == 0x03:
            return 'global'

        return 'unknown'

    def _format_register_value(self, value: int, type_offset: Optional[int]) -> str:
        """Format a value that's held in a register.

        Args:
            value: Register value
            type_offset: Type offset for formatting

        Returns:
            Formatted string
        """
        if not type_offset:
            return f"0x{value:08x}"

        try:
            # Pack the value as 4 bytes and format according to type
            raw_bytes = struct.pack('<I', value & 0xFFFFFFFF)
            return self.type_resolver.format_value(raw_bytes, type_offset)
        except Exception:
            return f"0x{value:08x}"

    def _read_and_format_value(self, address: int, type_offset: Optional[int]) -> str:
        """Read memory at address and format according to type.

        Args:
            address: Memory address to read
            type_offset: Type offset for formatting

        Returns:
            Formatted string
        """
        if not type_offset:
            # No type info - just show address
            return f"<at 0x{address:08x}>"

        try:
            # Determine size to read from type
            type_obj = self.type_resolver.resolve_type(type_offset)

            size = 4  # Default size
            if hasattr(type_obj, 'byte_size'):
                size = type_obj.byte_size

            # Read memory
            raw_bytes = self.process_controller.read_memory(address, size)

            # Format according to type
            return self.type_resolver.format_value(raw_bytes, type_offset)

        except Exception as e:
            return f"<unreadable: {e}>"

    def get_statistics(self) -> dict:
        """Get statistics about indexed debug information.

        Returns:
            Dictionary with counts of indexed items
        """
        return {
            'subprograms': self.die_parser.get_subprogram_count(),
            'types': self.die_parser.get_type_count(),
        }
