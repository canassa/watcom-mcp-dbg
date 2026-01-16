"""
Process controller using direct Win32 Debug API.

Wraps Win32 Debug API for process control, memory access, and register manipulation.
"""

from typing import Optional

from dgb.debugger import win32api


class ProcessController:
    """Controller for debuggee process using Win32 Debug API.

    Provides high-level interface for:
    - Memory read/write operations
    - Register access
    - Thread control
    """

    def __init__(self):
        self.process_handle: Optional[int] = None
        self.process_id: Optional[int] = None
        self.thread_handles = {}  # {thread_id: thread_handle}

    def set_process(self, process_handle: int, process_id: int):
        """Set the process handle (called after CREATE_PROCESS event).

        Args:
            process_handle: Process handle from debug event
            process_id: Process ID
        """
        self.process_handle = process_handle
        self.process_id = process_id

    def add_thread(self, thread_id: int, thread_handle: int):
        """Add a thread handle.

        Args:
            thread_id: Thread ID
            thread_handle: Thread handle from debug event
        """
        self.thread_handles[thread_id] = thread_handle

    def get_thread_handle(self, thread_id: int) -> Optional[int]:
        """Get thread handle for a thread ID.

        Args:
            thread_id: Thread ID

        Returns:
            Thread handle or None
        """
        if thread_id in self.thread_handles:
            return self.thread_handles[thread_id]

        # Try to open the thread
        handle = win32api.open_thread(thread_id)
        if handle:
            self.thread_handles[thread_id] = handle
            return handle

        return None

    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from the process.

        Args:
            address: Memory address to read from
            size: Number of bytes to read

        Returns:
            Bytes read from memory

        Raises:
            RuntimeError: If read fails or no process attached
        """
        if not self.process_handle:
            raise RuntimeError("No process attached")

        data = win32api.read_process_memory(self.process_handle, address, size)
        if data is None:
            raise RuntimeError(f"Failed to read memory at 0x{address:x}")

        return data

    def write_memory(self, address: int, data: bytes):
        """Write memory to the process.

        Args:
            address: Memory address to write to
            data: Bytes to write

        Raises:
            RuntimeError: If write fails or no process attached
        """
        if not self.process_handle:
            raise RuntimeError("No process attached")

        success = win32api.write_process_memory(self.process_handle, address, data)
        if not success:
            raise RuntimeError(f"Failed to write memory at 0x{address:x}")

    def get_register(self, thread_id: int, register_name: str) -> int:
        """Get a register value.

        Args:
            thread_id: Thread ID
            register_name: Register name (e.g., 'Eax', 'Eip', 'EFlags')

        Returns:
            Register value

        Raises:
            RuntimeError: If thread not found or register invalid
        """
        thread_handle = self.get_thread_handle(thread_id)
        if not thread_handle:
            raise RuntimeError(f"Thread {thread_id} not found")

        context = win32api.get_thread_context(thread_handle)
        if not context:
            raise RuntimeError(f"Failed to get context for thread {thread_id}")

        # Map register name to context field
        reg_map = {
            'eax': 'Eax', 'ebx': 'Ebx', 'ecx': 'Ecx', 'edx': 'Edx',
            'esi': 'Esi', 'edi': 'Edi', 'ebp': 'Ebp', 'esp': 'Esp',
            'eip': 'Eip', 'eflags': 'EFlags'
        }

        reg_key = register_name.lower()
        if reg_key not in reg_map:
            raise ValueError(f"Unknown register: {register_name}")

        context_field = reg_map[reg_key]
        return getattr(context, context_field)

    def set_register(self, thread_id: int, register_name: str, value: int):
        """Set a register value.

        Args:
            thread_id: Thread ID
            register_name: Register name (e.g., 'Eax', 'Eip', 'EFlags')
            value: New register value

        Raises:
            RuntimeError: If thread not found or register invalid
        """
        thread_handle = self.get_thread_handle(thread_id)
        if not thread_handle:
            raise RuntimeError(f"Thread {thread_id} not found")

        context = win32api.get_thread_context(thread_handle)
        if not context:
            raise RuntimeError(f"Failed to get context for thread {thread_id}")

        # Map register name to context field
        reg_map = {
            'eax': 'Eax', 'ebx': 'Ebx', 'ecx': 'Ecx', 'edx': 'Edx',
            'esi': 'Esi', 'edi': 'Edi', 'ebp': 'Ebp', 'esp': 'Esp',
            'eip': 'Eip', 'eflags': 'EFlags'
        }

        reg_key = register_name.lower()
        if reg_key not in reg_map:
            raise ValueError(f"Unknown register: {register_name}")

        context_field = reg_map[reg_key]
        setattr(context, context_field, value)

        success = win32api.set_thread_context(thread_handle, context)
        if not success:
            raise RuntimeError(f"Failed to set register {register_name}")

    def get_all_registers(self, thread_id: int) -> dict:
        """Get all register values for a thread.

        Args:
            thread_id: Thread ID

        Returns:
            Dictionary of register names to values

        Raises:
            RuntimeError: If thread not found
        """
        thread_handle = self.get_thread_handle(thread_id)
        if not thread_handle:
            raise RuntimeError(f"Thread {thread_id} not found")

        context = win32api.get_thread_context(thread_handle)
        if not context:
            raise RuntimeError(f"Failed to get context for thread {thread_id}")

        # Extract all general-purpose registers
        return {
            'eax': context.Eax,
            'ebx': context.Ebx,
            'ecx': context.Ecx,
            'edx': context.Edx,
            'esi': context.Esi,
            'edi': context.Edi,
            'ebp': context.Ebp,
            'esp': context.Esp,
            'eip': context.Eip,
            'eflags': context.EFlags,
        }

    def cleanup(self):
        """Clean up resources."""
        # Close thread handles
        for handle in self.thread_handles.values():
            win32api.close_handle(handle)
        self.thread_handles.clear()

        # Note: process_handle is owned by debug event loop, don't close it here
        self.process_handle = None
        self.process_id = None
