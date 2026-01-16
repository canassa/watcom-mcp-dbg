"""
Debugger exception classes.

Maps Win32 error codes and debugger states to proper Python exceptions.
"""


class DebuggerError(Exception):
    """Base exception for all debugger errors."""
    pass


class ProcessCreationError(DebuggerError):
    """Failed to create debugged process."""
    pass


class InvalidHandleError(DebuggerError):
    """Invalid process or thread handle."""
    def __init__(self, handle_type: str, handle_value):
        super().__init__(
            f"Invalid {handle_type} handle: {handle_value}. "
            f"The handle may have been closed or the process may have exited."
        )
        self.handle_type = handle_type
        self.handle_value = handle_value


class DebugEventError(DebuggerError):
    """Error waiting for or processing debug events."""
    pass


class DebugEventTimeoutError(DebugEventError):
    """Timeout waiting for debug event (not necessarily an error)."""
    pass


class ProcessNotFoundError(DebuggerError):
    """The debugged process does not exist or has exited."""
    def __init__(self, process_id: int):
        super().__init__(
            f"Process {process_id} not found. It may have exited or was terminated."
        )
        self.process_id = process_id


class AccessDeniedError(DebuggerError):
    """Access denied when accessing process or memory."""
    pass


class MemoryReadError(DebuggerError):
    """Failed to read process memory."""
    def __init__(self, address: int, size: int, reason: str):
        super().__init__(
            f"Failed to read {size} bytes at address 0x{address:08x}: {reason}"
        )
        self.address = address
        self.size = size


class MemoryWriteError(DebuggerError):
    """Failed to write process memory."""
    def __init__(self, address: int, size: int, reason: str):
        super().__init__(
            f"Failed to write {size} bytes at address 0x{address:08x}: {reason}"
        )
        self.address = address
        self.size = size


class InvalidAddressError(DebuggerError):
    """Invalid memory address."""
    def __init__(self, address: int):
        super().__init__(
            f"Invalid memory address: 0x{address:08x}"
        )
        self.address = address


class BreakpointError(DebuggerError):
    """Error setting or managing breakpoints."""
    pass


class ModuleNotFoundError(DebuggerError):
    """Module not found in debugged process."""
    def __init__(self, module_name: str):
        super().__init__(
            f"Module '{module_name}' not found in debugged process"
        )
        self.module_name = module_name


class DebugInfoNotFoundError(DebuggerError):
    """Debug information not found for module."""
    def __init__(self, module_name: str):
        super().__init__(
            f"No debug information found for module '{module_name}'"
        )
        self.module_name = module_name


class SourceFileNotFoundError(DebuggerError):
    """Source file not found."""
    def __init__(self, filename: str, search_dirs: list[str]):
        dirs = ", ".join(search_dirs) if search_dirs else "none"
        super().__init__(
            f"Source file '{filename}' not found. Searched directories: {dirs}"
        )
        self.filename = filename
        self.search_dirs = search_dirs


# Win32 error code mapping
WIN32_ERROR_MESSAGES = {
    2: "The system cannot find the file specified",
    5: "Access is denied",
    6: "The handle is invalid",
    87: "The parameter is incorrect",
    121: "The semaphore timeout period has expired",
    299: "Only part of a ReadProcessMemory or WriteProcessMemory request was completed",
    998: "Invalid access to memory location",
}


def map_win32_error(error_code: int, context: str = "") -> DebuggerError:
    """Map a Win32 error code to a proper exception.

    Args:
        error_code: Win32 error code from GetLastError()
        context: Additional context about what operation failed

    Returns:
        Appropriate DebuggerError subclass
    """
    error_msg = WIN32_ERROR_MESSAGES.get(error_code, f"Unknown error code {error_code}")
    full_msg = f"{context}: {error_msg}" if context else error_msg

    # Map specific error codes to specific exceptions
    if error_code == 2:  # ERROR_FILE_NOT_FOUND
        return ProcessCreationError(full_msg)
    elif error_code == 5:  # ERROR_ACCESS_DENIED
        return AccessDeniedError(full_msg)
    elif error_code == 6:  # ERROR_INVALID_HANDLE
        return InvalidHandleError("unknown", "Win32 handle")
    elif error_code == 121:  # ERROR_SEM_TIMEOUT
        return DebugEventTimeoutError(full_msg)
    elif error_code == 299:  # ERROR_PARTIAL_COPY
        return MemoryReadError(0, 0, error_msg)
    else:
        return DebuggerError(full_msg)
