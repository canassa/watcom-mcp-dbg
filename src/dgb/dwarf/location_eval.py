"""
DWARF location expression evaluator.

Evaluates DWARF location expressions to compute variable addresses.
Implements a stack-based evaluator for common location opcodes.
"""

import struct
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dgb.debugger.process_controller import ProcessController


# DWARF location expression opcodes
DW_OP_addr = 0x03
DW_OP_const1u = 0x08
DW_OP_const1s = 0x09
DW_OP_const2u = 0x0a
DW_OP_const2s = 0x0b
DW_OP_const4u = 0x0c
DW_OP_const4s = 0x0d
DW_OP_const8u = 0x0e
DW_OP_const8s = 0x0f
DW_OP_constu = 0x10
DW_OP_consts = 0x11
DW_OP_dup = 0x12
DW_OP_drop = 0x13
DW_OP_over = 0x14
DW_OP_pick = 0x15
DW_OP_swap = 0x16
DW_OP_rot = 0x17
DW_OP_deref = 0x06
DW_OP_plus = 0x22
DW_OP_minus = 0x1b
DW_OP_plus_uconst = 0x23

# Register operations (DW_OP_reg0 through DW_OP_reg31)
DW_OP_reg0 = 0x50
DW_OP_reg31 = 0x6f

# Register with offset (DW_OP_breg0 through DW_OP_breg31)
DW_OP_breg0 = 0x70
DW_OP_breg31 = 0x8f

# Frame base relative
DW_OP_fbreg = 0x91

# x86-32 register mapping (standard DWARF x86 register numbering)
X86_REGISTER_MAP = {
    0: 'eax',
    1: 'ecx',
    2: 'edx',
    3: 'ebx',
    4: 'esp',
    5: 'ebp',
    6: 'esi',
    7: 'edi',
    8: 'eip',
}


class LocationEvaluationError(Exception):
    """Raised when location expression cannot be evaluated."""
    pass


class LocationEvaluator:
    """Evaluates DWARF location expressions.

    Uses a stack-based evaluation model as defined in DWARF specification.
    """

    def __init__(self, process_controller: 'ProcessController'):
        self.process_controller = process_controller

    def evaluate_location(
        self,
        expr: bytes,
        thread_id: int,
        frame_base: Optional[int] = None,
        module_base: int = 0
    ) -> int:
        """Evaluate a location expression to get an address.

        Args:
            expr: Location expression bytes
            thread_id: Thread ID for register access
            frame_base: Frame base address (usually EBP value)
            module_base: Module base address for relocating addresses

        Returns:
            Computed address

        Raises:
            LocationEvaluationError: If expression cannot be evaluated
        """
        if not expr:
            raise LocationEvaluationError("Empty location expression")

        stack = []
        offset = 0

        while offset < len(expr):
            opcode = expr[offset]
            offset += 1

            try:
                # Register operations (value is in register)
                if DW_OP_reg0 <= opcode <= DW_OP_reg31:
                    reg_num = opcode - DW_OP_reg0
                    reg_name = X86_REGISTER_MAP.get(reg_num)
                    if not reg_name:
                        raise LocationEvaluationError(f"Unknown register number: {reg_num}")
                    value = self.process_controller.get_register(thread_id, reg_name)
                    # For DW_OP_reg*, the value IS the variable (not an address)
                    # We return it directly
                    return value

                # Register + offset operations (address is register + offset)
                elif DW_OP_breg0 <= opcode <= DW_OP_breg31:
                    reg_num = opcode - DW_OP_breg0
                    reg_name = X86_REGISTER_MAP.get(reg_num)
                    if not reg_name:
                        raise LocationEvaluationError(f"Unknown register number: {reg_num}")

                    # Read SLEB128 offset
                    sleb_offset, bytes_read = self._decode_sleb128(expr[offset:])
                    offset += bytes_read

                    reg_value = self.process_controller.get_register(thread_id, reg_name)
                    address = reg_value + sleb_offset
                    stack.append(address)

                # Frame base relative
                elif opcode == DW_OP_fbreg:
                    if frame_base is None:
                        raise LocationEvaluationError("Frame base required for DW_OP_fbreg")

                    # Read SLEB128 offset
                    sleb_offset, bytes_read = self._decode_sleb128(expr[offset:])
                    offset += bytes_read

                    address = frame_base + sleb_offset
                    stack.append(address)

                # Absolute address
                elif opcode == DW_OP_addr:
                    # Read 4-byte address (32-bit)
                    if offset + 4 > len(expr):
                        raise LocationEvaluationError("Truncated DW_OP_addr operand")
                    addr_bytes = expr[offset:offset + 4]
                    address = struct.unpack('<I', addr_bytes)[0]
                    offset += 4

                    # Relocate with module base
                    address += module_base
                    stack.append(address)

                # Constants
                elif opcode == DW_OP_const1u:
                    value = expr[offset]
                    offset += 1
                    stack.append(value)

                elif opcode == DW_OP_const1s:
                    value = struct.unpack('<b', expr[offset:offset + 1])[0]
                    offset += 1
                    stack.append(value)

                elif opcode == DW_OP_const2u:
                    value = struct.unpack('<H', expr[offset:offset + 2])[0]
                    offset += 2
                    stack.append(value)

                elif opcode == DW_OP_const2s:
                    value = struct.unpack('<h', expr[offset:offset + 2])[0]
                    offset += 2
                    stack.append(value)

                elif opcode == DW_OP_const4u:
                    value = struct.unpack('<I', expr[offset:offset + 4])[0]
                    offset += 4
                    stack.append(value)

                elif opcode == DW_OP_const4s:
                    value = struct.unpack('<i', expr[offset:offset + 4])[0]
                    offset += 4
                    stack.append(value)

                elif opcode == DW_OP_constu:
                    value, bytes_read = self._decode_uleb128(expr[offset:])
                    offset += bytes_read
                    stack.append(value)

                elif opcode == DW_OP_consts:
                    value, bytes_read = self._decode_sleb128(expr[offset:])
                    offset += bytes_read
                    stack.append(value)

                # Stack operations
                elif opcode == DW_OP_dup:
                    if not stack:
                        raise LocationEvaluationError("DW_OP_dup on empty stack")
                    stack.append(stack[-1])

                elif opcode == DW_OP_drop:
                    if not stack:
                        raise LocationEvaluationError("DW_OP_drop on empty stack")
                    stack.pop()

                elif opcode == DW_OP_over:
                    if len(stack) < 2:
                        raise LocationEvaluationError("DW_OP_over requires 2 stack items")
                    stack.append(stack[-2])

                elif opcode == DW_OP_swap:
                    if len(stack) < 2:
                        raise LocationEvaluationError("DW_OP_swap requires 2 stack items")
                    stack[-1], stack[-2] = stack[-2], stack[-1]

                # Arithmetic operations
                elif opcode == DW_OP_plus:
                    if len(stack) < 2:
                        raise LocationEvaluationError("DW_OP_plus requires 2 stack items")
                    b = stack.pop()
                    a = stack.pop()
                    stack.append(a + b)

                elif opcode == DW_OP_minus:
                    if len(stack) < 2:
                        raise LocationEvaluationError("DW_OP_minus requires 2 stack items")
                    b = stack.pop()
                    a = stack.pop()
                    stack.append(a - b)

                elif opcode == DW_OP_plus_uconst:
                    if not stack:
                        raise LocationEvaluationError("DW_OP_plus_uconst requires 1 stack item")
                    value, bytes_read = self._decode_uleb128(expr[offset:])
                    offset += bytes_read
                    stack[-1] += value

                # Dereference
                elif opcode == DW_OP_deref:
                    if not stack:
                        raise LocationEvaluationError("DW_OP_deref on empty stack")
                    address = stack.pop()
                    # Read 4 bytes from memory (32-bit pointer)
                    try:
                        data = self.process_controller.read_memory(address, 4)
                        value = struct.unpack('<I', data)[0]
                        stack.append(value)
                    except Exception as e:
                        raise LocationEvaluationError(f"Failed to dereference 0x{address:x}: {e}")

                else:
                    raise LocationEvaluationError(f"Unsupported opcode: 0x{opcode:02x}")

            except (struct.error, IndexError) as e:
                raise LocationEvaluationError(f"Error parsing opcode 0x{opcode:02x}: {e}")

        # Result is top of stack
        if not stack:
            raise LocationEvaluationError("Expression evaluation left empty stack")

        return stack[-1]

    def evaluate_frame_base(
        self,
        frame_base_expr: bytes,
        thread_id: int,
        module_base: int = 0
    ) -> int:
        """Evaluate a frame base expression.

        Frame base is typically DW_OP_reg5 (EBP) but can be more complex.

        Args:
            frame_base_expr: Frame base location expression
            thread_id: Thread ID for register access
            module_base: Module base address

        Returns:
            Frame base address (usually EBP value)

        Raises:
            LocationEvaluationError: If expression cannot be evaluated
        """
        return self.evaluate_location(frame_base_expr, thread_id, frame_base=None, module_base=module_base)

    def _decode_uleb128(self, data: bytes) -> tuple[int, int]:
        """Decode an unsigned LEB128 value.

        Args:
            data: Bytes to decode from

        Returns:
            Tuple of (decoded value, number of bytes consumed)
        """
        result = 0
        shift = 0
        offset = 0

        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7f) << shift
            shift += 7
            if (byte & 0x80) == 0:
                break

        return result, offset

    def _decode_sleb128(self, data: bytes) -> tuple[int, int]:
        """Decode a signed LEB128 value.

        Args:
            data: Bytes to decode from

        Returns:
            Tuple of (decoded value, number of bytes consumed)
        """
        result = 0
        shift = 0
        offset = 0
        byte = 0

        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7f) << shift
            shift += 7
            if (byte & 0x80) == 0:
                break

        # Sign extend if negative
        if shift < 64 and (byte & 0x40):
            result |= -(1 << shift)

        return result, offset
