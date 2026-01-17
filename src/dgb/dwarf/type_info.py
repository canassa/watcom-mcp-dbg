"""
Type system for DWARF debug information.

Represents types and provides value formatting based on type information.
"""

import struct
from dataclasses import dataclass
from typing import Optional, List, Dict, TYPE_CHECKING
from elftools.dwarf.die import DIE

if TYPE_CHECKING:
    from dgb.dwarf.die_parser import DIEParser


# DWARF type encodings for base types
DW_ATE_address = 0x01
DW_ATE_boolean = 0x02
DW_ATE_complex_float = 0x03
DW_ATE_float = 0x04
DW_ATE_signed = 0x05
DW_ATE_signed_char = 0x06
DW_ATE_unsigned = 0x07
DW_ATE_unsigned_char = 0x08


@dataclass
class BaseType:
    """Represents a primitive base type."""

    name: str
    byte_size: int
    encoding: int  # DW_ATE_* encoding


@dataclass
class PointerType:
    """Represents a pointer type."""

    pointee_offset: Optional[int]  # Type offset of what it points to
    byte_size: int = 4  # 32-bit pointers


@dataclass
class StructMember:
    """Represents a member of a structure."""

    name: str
    type_offset: Optional[int]
    offset: int  # Byte offset within struct


@dataclass
class StructType:
    """Represents a structure type."""

    name: Optional[str]
    byte_size: int
    members: List[StructMember]


@dataclass
class ArrayType:
    """Represents an array type."""

    element_type_offset: Optional[int]
    element_count: Optional[int]  # None for unbounded arrays


@dataclass
class TypedefType:
    """Represents a typedef."""

    name: str
    type_offset: Optional[int]


class TypeResolver:
    """Resolves and formats types from DWARF information.

    Handles recursive type resolution and value formatting.
    """

    def __init__(self, die_parser: 'DIEParser'):
        self.die_parser = die_parser
        self._type_cache: Dict[int, object] = {}  # offset -> resolved type object

    def resolve_type(self, type_offset: int) -> Optional[object]:
        """Resolve a type by its DIE offset.

        Args:
            type_offset: DIE offset of the type

        Returns:
            Type object (BaseType, PointerType, etc.) or None
        """
        # Check cache
        if type_offset in self._type_cache:
            return self._type_cache[type_offset]

        # Get DIE
        type_die = self.die_parser.get_type_die(type_offset)
        if not type_die:
            return None

        # Resolve based on tag
        tag = type_die.tag
        result = None

        if tag == 'DW_TAG_base_type':
            result = self._resolve_base_type(type_die)
        elif tag == 'DW_TAG_pointer_type':
            result = self._resolve_pointer_type(type_die)
        elif tag == 'DW_TAG_structure_type':
            result = self._resolve_struct_type(type_die)
        elif tag == 'DW_TAG_typedef':
            result = self._resolve_typedef(type_die)
        elif tag == 'DW_TAG_const_type':
            result = self._resolve_const_type(type_die)
        elif tag == 'DW_TAG_array_type':
            result = self._resolve_array_type(type_die)

        # Cache result
        if result:
            self._type_cache[type_offset] = result

        return result

    def _resolve_base_type(self, die: DIE) -> Optional[BaseType]:
        """Resolve a base type DIE."""
        try:
            attrs = die.attributes

            name_attr = attrs.get('DW_AT_name')
            name = name_attr.value.decode('utf-8', errors='ignore') if name_attr else 'unknown'

            size_attr = attrs.get('DW_AT_byte_size')
            byte_size = size_attr.value if size_attr else 0

            encoding_attr = attrs.get('DW_AT_encoding')
            encoding = encoding_attr.value if encoding_attr else DW_ATE_signed

            return BaseType(name=name, byte_size=byte_size, encoding=encoding)

        except Exception:
            return None

    def _resolve_pointer_type(self, die: DIE) -> Optional[PointerType]:
        """Resolve a pointer type DIE."""
        try:
            attrs = die.attributes

            size_attr = attrs.get('DW_AT_byte_size')
            byte_size = size_attr.value if size_attr else 4

            type_attr = attrs.get('DW_AT_type')
            pointee_offset = type_attr.value + type_attr.cu_offset if type_attr else None

            return PointerType(pointee_offset=pointee_offset, byte_size=byte_size)

        except Exception:
            return None

    def _resolve_struct_type(self, die: DIE) -> Optional[StructType]:
        """Resolve a structure type DIE."""
        try:
            attrs = die.attributes

            name_attr = attrs.get('DW_AT_name')
            name = name_attr.value.decode('utf-8', errors='ignore') if name_attr else None

            size_attr = attrs.get('DW_AT_byte_size')
            byte_size = size_attr.value if size_attr else 0

            # Parse members
            members = []
            for child in die.iter_children():
                if child.tag == 'DW_TAG_member':
                    member = self._parse_struct_member(child)
                    if member:
                        members.append(member)

            return StructType(name=name, byte_size=byte_size, members=members)

        except Exception:
            return None

    def _parse_struct_member(self, die: DIE) -> Optional[StructMember]:
        """Parse a struct member DIE."""
        try:
            attrs = die.attributes

            name_attr = attrs.get('DW_AT_name')
            name = name_attr.value.decode('utf-8', errors='ignore') if name_attr else 'unnamed'

            type_attr = attrs.get('DW_AT_type')
            type_offset = type_attr.value + type_attr.cu_offset if type_attr else None

            # Member offset can be in DW_AT_data_member_location
            offset_attr = attrs.get('DW_AT_data_member_location')
            offset = offset_attr.value if offset_attr else 0

            return StructMember(name=name, type_offset=type_offset, offset=offset)

        except Exception:
            return None

    def _resolve_typedef(self, die: DIE) -> Optional[TypedefType]:
        """Resolve a typedef DIE."""
        try:
            attrs = die.attributes

            name_attr = attrs.get('DW_AT_name')
            name = name_attr.value.decode('utf-8', errors='ignore') if name_attr else 'unnamed'

            type_attr = attrs.get('DW_AT_type')
            type_offset = type_attr.value + type_attr.cu_offset if type_attr else None

            return TypedefType(name=name, type_offset=type_offset)

        except Exception:
            return None

    def _resolve_const_type(self, die: DIE) -> Optional[object]:
        """Resolve a const type DIE by following the underlying type."""
        try:
            attrs = die.attributes
            type_attr = attrs.get('DW_AT_type')

            if type_attr:
                type_offset = type_attr.value + type_attr.cu_offset
                return self.resolve_type(type_offset)

            return None

        except Exception:
            return None

    def _resolve_array_type(self, die: DIE) -> Optional[ArrayType]:
        """Resolve an array type DIE."""
        try:
            attrs = die.attributes

            type_attr = attrs.get('DW_AT_type')
            element_type_offset = type_attr.value + type_attr.cu_offset if type_attr else None

            # Array bounds are in subrange DIE
            element_count = None
            for child in die.iter_children():
                if child.tag == 'DW_TAG_subrange_type':
                    upper_bound = child.attributes.get('DW_AT_upper_bound')
                    if upper_bound:
                        element_count = upper_bound.value + 1  # upper_bound is inclusive

            return ArrayType(element_type_offset=element_type_offset, element_count=element_count)

        except Exception:
            return None

    def format_value(self, raw_bytes: bytes, type_offset: int, max_depth: int = 3) -> str:
        """Format a raw value based on its type.

        Args:
            raw_bytes: Raw bytes read from memory
            type_offset: DIE offset of the type
            max_depth: Maximum recursion depth for struct formatting

        Returns:
            Formatted string representation
        """
        if max_depth <= 0:
            return "..."

        type_obj = self.resolve_type(type_offset)

        if isinstance(type_obj, BaseType):
            return self._format_base_type(raw_bytes, type_obj)
        elif isinstance(type_obj, PointerType):
            return self._format_pointer(raw_bytes, type_obj)
        elif isinstance(type_obj, StructType):
            return self._format_struct(raw_bytes, type_obj, max_depth - 1)
        elif isinstance(type_obj, TypedefType):
            # Follow typedef to underlying type
            if type_obj.type_offset:
                return self.format_value(raw_bytes, type_obj.type_offset, max_depth)
            return "<unknown typedef>"
        elif isinstance(type_obj, ArrayType):
            return self._format_array(raw_bytes, type_obj, max_depth - 1)
        else:
            # Unknown type - show hex dump
            return self._format_hex_dump(raw_bytes)

    def _format_base_type(self, raw_bytes: bytes, type_obj: BaseType) -> str:
        """Format a base type value."""
        try:
            if type_obj.byte_size == 1:
                if type_obj.encoding in (DW_ATE_signed, DW_ATE_signed_char):
                    value = struct.unpack('<b', raw_bytes[:1])[0]
                    return str(value)
                else:
                    value = struct.unpack('<B', raw_bytes[:1])[0]
                    return str(value)

            elif type_obj.byte_size == 2:
                if type_obj.encoding == DW_ATE_signed:
                    value = struct.unpack('<h', raw_bytes[:2])[0]
                    return str(value)
                else:
                    value = struct.unpack('<H', raw_bytes[:2])[0]
                    return str(value)

            elif type_obj.byte_size == 4:
                if type_obj.encoding == DW_ATE_signed:
                    value = struct.unpack('<i', raw_bytes[:4])[0]
                    return str(value)
                elif type_obj.encoding == DW_ATE_float:
                    value = struct.unpack('<f', raw_bytes[:4])[0]
                    return f"{value:.6g}"
                else:
                    value = struct.unpack('<I', raw_bytes[:4])[0]
                    return str(value)

            elif type_obj.byte_size == 8:
                if type_obj.encoding == DW_ATE_signed:
                    value = struct.unpack('<q', raw_bytes[:8])[0]
                    return str(value)
                elif type_obj.encoding == DW_ATE_float:
                    value = struct.unpack('<d', raw_bytes[:8])[0]
                    return f"{value:.15g}"
                else:
                    value = struct.unpack('<Q', raw_bytes[:8])[0]
                    return str(value)

            else:
                return self._format_hex_dump(raw_bytes[:type_obj.byte_size])

        except Exception:
            return self._format_hex_dump(raw_bytes[:type_obj.byte_size])

    def _format_pointer(self, raw_bytes: bytes, type_obj: PointerType) -> str:
        """Format a pointer value."""
        try:
            if type_obj.byte_size == 4:
                value = struct.unpack('<I', raw_bytes[:4])[0]
                return f"0x{value:08x}"
            elif type_obj.byte_size == 8:
                value = struct.unpack('<Q', raw_bytes[:8])[0]
                return f"0x{value:016x}"
            else:
                return self._format_hex_dump(raw_bytes[:type_obj.byte_size])
        except Exception:
            return self._format_hex_dump(raw_bytes[:type_obj.byte_size])

    def _format_struct(self, raw_bytes: bytes, type_obj: StructType, max_depth: int) -> str:
        """Format a structure value."""
        if not type_obj.members:
            return "{}"

        parts = ["{"]
        for member in type_obj.members:
            if member.type_offset and member.offset < len(raw_bytes):
                member_bytes = raw_bytes[member.offset:]
                member_value = self.format_value(member_bytes, member.type_offset, max_depth)
                parts.append(f" {member.name}={member_value}")
        parts.append(" }")
        return "".join(parts)

    def _format_array(self, raw_bytes: bytes, type_obj: ArrayType, max_depth: int) -> str:
        """Format an array value."""
        if not type_obj.element_type_offset:
            return "[...]"

        # Resolve element type to get size
        element_type = self.resolve_type(type_obj.element_type_offset)
        if isinstance(element_type, BaseType):
            element_size = element_type.byte_size
        elif isinstance(element_type, PointerType):
            element_size = element_type.byte_size
        else:
            return "[...]"

        # Show first few elements
        max_elements = min(type_obj.element_count or 3, 3)
        parts = ["["]
        for i in range(max_elements):
            offset = i * element_size
            if offset + element_size <= len(raw_bytes):
                element_bytes = raw_bytes[offset:offset + element_size]
                element_value = self.format_value(element_bytes, type_obj.element_type_offset, max_depth)
                if i > 0:
                    parts.append(", ")
                parts.append(element_value)
        if type_obj.element_count and type_obj.element_count > max_elements:
            parts.append(", ...")
        parts.append("]")
        return "".join(parts)

    def _format_hex_dump(self, raw_bytes: bytes) -> str:
        """Format raw bytes as hex dump."""
        if len(raw_bytes) == 0:
            return "<empty>"
        hex_str = " ".join(f"{b:02x}" for b in raw_bytes[:16])
        if len(raw_bytes) > 16:
            hex_str += "..."
        return f"<{hex_str}>"

    def get_type_name(self, type_offset: int) -> str:
        """Get a human-readable name for a type.

        Args:
            type_offset: DIE offset of the type

        Returns:
            Type name string
        """
        type_obj = self.resolve_type(type_offset)

        if isinstance(type_obj, BaseType):
            return type_obj.name
        elif isinstance(type_obj, PointerType):
            if type_obj.pointee_offset:
                pointee_name = self.get_type_name(type_obj.pointee_offset)
                return f"{pointee_name}*"
            return "void*"
        elif isinstance(type_obj, StructType):
            if type_obj.name:
                return f"struct {type_obj.name}"
            return "struct <anonymous>"
        elif isinstance(type_obj, TypedefType):
            return type_obj.name
        elif isinstance(type_obj, ArrayType):
            if type_obj.element_type_offset:
                element_name = self.get_type_name(type_obj.element_type_offset)
                if type_obj.element_count:
                    return f"{element_name}[{type_obj.element_count}]"
                return f"{element_name}[]"
            return "array"
        else:
            return "unknown"
