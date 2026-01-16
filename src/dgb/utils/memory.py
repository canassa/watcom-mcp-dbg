"""
Memory utility helpers for reading and formatting memory.
"""

import struct


def format_hex_dump(data: bytes, base_address: int = 0, bytes_per_line: int = 16) -> str:
    """Format binary data as a hex dump.

    Args:
        data: Binary data to format
        base_address: Base address for display
        bytes_per_line: Number of bytes per line

    Returns:
        Formatted hex dump string
    """
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        addr = base_address + i

        # Hex bytes
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        hex_part = hex_part.ljust(bytes_per_line * 3 - 1)

        # ASCII representation
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

        lines.append(f'{addr:08x}  {hex_part}  {ascii_part}')

    return '\n'.join(lines)


def read_null_terminated_string(memory_reader, address: int, max_length: int = 256) -> str:
    """Read a null-terminated string from memory.

    Args:
        memory_reader: Object with read_memory(address, size) method
        address: Address to read from
        max_length: Maximum string length

    Returns:
        String value
    """
    try:
        data = memory_reader.read_memory(address, max_length)
        # Find null terminator
        null_pos = data.find(b'\x00')
        if null_pos >= 0:
            data = data[:null_pos]
        return data.decode('utf-8', errors='replace')
    except Exception:
        return "<error reading string>"


def read_wide_string(memory_reader, address: int, max_length: int = 256) -> str:
    """Read a wide (UTF-16) null-terminated string from memory.

    Args:
        memory_reader: Object with read_memory(address, size) method
        address: Address to read from
        max_length: Maximum string length in characters

    Returns:
        String value
    """
    try:
        data = memory_reader.read_memory(address, max_length * 2)
        # Find null terminator
        for i in range(0, len(data) - 1, 2):
            if data[i] == 0 and data[i + 1] == 0:
                data = data[:i]
                break
        return data.decode('utf-16-le', errors='replace')
    except Exception:
        return "<error reading wide string>"


def format_size(size: int) -> str:
    """Format a size in bytes as human-readable.

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 KB", "2.3 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
