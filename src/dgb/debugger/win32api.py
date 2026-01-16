"""
Win32 Debug API wrapper using ctypes.

Direct wrapper around Windows debugging APIs without external dependencies.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional


# Constants
DEBUG_PROCESS = 0x00000001
DEBUG_ONLY_THIS_PROCESS = 0x00000002
CREATE_NEW_CONSOLE = 0x00000010
CREATE_SUSPENDED = 0x00000004

INFINITE = 0xFFFFFFFF

# Debug event codes
EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9

# Continue status
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

# Exception codes
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_ACCESS_VIOLATION = 0xC0000005

# Context flags
CONTEXT_i386 = 0x00010000
CONTEXT_CONTROL = CONTEXT_i386 | 0x00000001
CONTEXT_INTEGER = CONTEXT_i386 | 0x00000002
CONTEXT_SEGMENTS = CONTEXT_i386 | 0x00000004
CONTEXT_FLOATING_POINT = CONTEXT_i386 | 0x00000008
CONTEXT_DEBUG_REGISTERS = CONTEXT_i386 | 0x00000010
CONTEXT_EXTENDED_REGISTERS = CONTEXT_i386 | 0x00000020
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS
CONTEXT_ALL = CONTEXT_FULL | CONTEXT_FLOATING_POINT | CONTEXT_DEBUG_REGISTERS | CONTEXT_EXTENDED_REGISTERS

# Memory protection
PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000

# Process access rights
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

# Thread access rights
THREAD_ALL_ACCESS = 0x1F03FF
THREAD_GET_CONTEXT = 0x0008
THREAD_SET_CONTEXT = 0x0010
THREAD_SUSPEND_RESUME = 0x0002


# Structures
class EXCEPTION_RECORD(ctypes.Structure):
    pass


EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wintypes.DWORD),
    ("ExceptionFlags", wintypes.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", wintypes.LPVOID),
    ("NumberParameters", wintypes.DWORD),
    ("ExceptionInformation", wintypes.LPVOID * 15),
]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("ExceptionRecord", EXCEPTION_RECORD),
        ("dwFirstChance", wintypes.DWORD),
    ]


class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hThread", wintypes.HANDLE),
        ("lpThreadLocalBase", wintypes.LPVOID),
        ("lpStartAddress", wintypes.LPVOID),
    ]


class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("lpBaseOfImage", wintypes.LPVOID),
        ("dwDebugInfoFileOffset", wintypes.DWORD),
        ("nDebugInfoSize", wintypes.DWORD),
        ("lpThreadLocalBase", wintypes.LPVOID),
        ("lpStartAddress", wintypes.LPVOID),
        ("lpImageName", wintypes.LPVOID),
        ("fUnicode", wintypes.WORD),
    ]


class EXIT_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("dwExitCode", wintypes.DWORD),
    ]


class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("dwExitCode", wintypes.DWORD),
    ]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wintypes.HANDLE),
        ("lpBaseOfDll", wintypes.LPVOID),
        ("dwDebugInfoFileOffset", wintypes.DWORD),
        ("nDebugInfoSize", wintypes.DWORD),
        ("lpImageName", wintypes.LPVOID),
        ("fUnicode", wintypes.WORD),
    ]


class UNLOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", wintypes.LPVOID),
    ]


class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [
        ("lpDebugStringData", wintypes.LPSTR),
        ("fUnicode", wintypes.WORD),
        ("nDebugStringLength", wintypes.WORD),
    ]


class RIP_INFO(ctypes.Structure):
    _fields_ = [
        ("dwError", wintypes.DWORD),
        ("dwType", wintypes.DWORD),
    ]


class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("CreateThread", CREATE_THREAD_DEBUG_INFO),
        ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
        ("ExitThread", EXIT_THREAD_DEBUG_INFO),
        ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
        ("LoadDll", LOAD_DLL_DEBUG_INFO),
        ("UnloadDll", UNLOAD_DLL_DEBUG_INFO),
        ("DebugString", OUTPUT_DEBUG_STRING_INFO),
        ("RipInfo", RIP_INFO),
    ]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", DEBUG_EVENT_UNION),
    ]


class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", wintypes.DWORD),
        ("Dr0", wintypes.DWORD),
        ("Dr1", wintypes.DWORD),
        ("Dr2", wintypes.DWORD),
        ("Dr3", wintypes.DWORD),
        ("Dr6", wintypes.DWORD),
        ("Dr7", wintypes.DWORD),
        ("FloatSave", wintypes.BYTE * 112),
        ("SegGs", wintypes.DWORD),
        ("SegFs", wintypes.DWORD),
        ("SegEs", wintypes.DWORD),
        ("SegDs", wintypes.DWORD),
        ("Edi", wintypes.DWORD),
        ("Esi", wintypes.DWORD),
        ("Ebx", wintypes.DWORD),
        ("Edx", wintypes.DWORD),
        ("Ecx", wintypes.DWORD),
        ("Eax", wintypes.DWORD),
        ("Ebp", wintypes.DWORD),
        ("Eip", wintypes.DWORD),
        ("SegCs", wintypes.DWORD),
        ("EFlags", wintypes.DWORD),
        ("Esp", wintypes.DWORD),
        ("SegSs", wintypes.DWORD),
        ("ExtendedRegisters", wintypes.BYTE * 512),
    ]


# Load kernel32.dll
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Function prototypes
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
    wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)
]
kernel32.CreateProcessW.restype = wintypes.BOOL

kernel32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wintypes.DWORD]
kernel32.WaitForDebugEvent.restype = wintypes.BOOL

kernel32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
kernel32.ContinueDebugEvent.restype = wintypes.BOOL

kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
kernel32.ReadProcessMemory.restype = wintypes.BOOL

kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenThread.restype = wintypes.HANDLE

kernel32.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(CONTEXT)]
kernel32.GetThreadContext.restype = wintypes.BOOL

kernel32.SetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(CONTEXT)]
kernel32.SetThreadContext.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL

# Psapi for module info
psapi = ctypes.WinDLL('psapi', use_last_error=True)
psapi.GetModuleFileNameExW.argtypes = [
    wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD
]
psapi.GetModuleFileNameExW.restype = wintypes.DWORD


# Helper functions
def create_process_for_debug(executable_path: str) -> tuple[int, int, int, int]:
    """Create a process for debugging.

    Args:
        executable_path: Path to executable to debug

    Returns:
        Tuple of (process_handle, thread_handle, process_id, thread_id)

    Raises:
        ProcessCreationError: If process creation fails
        InvalidHandleError: If returned handles are invalid
    """
    from dgb.debugger.exceptions import ProcessCreationError, InvalidHandleError, map_win32_error

    startup_info = STARTUPINFO()
    startup_info.cb = ctypes.sizeof(STARTUPINFO)
    process_info = PROCESS_INFORMATION()

    # Convert to wide string
    exe_path_w = executable_path

    success = kernel32.CreateProcessW(
        exe_path_w,  # Application name
        None,  # Command line
        None,  # Process security attributes
        None,  # Thread security attributes
        False,  # Inherit handles
        DEBUG_PROCESS | DEBUG_ONLY_THIS_PROCESS,  # Creation flags
        None,  # Environment
        None,  # Current directory
        ctypes.byref(startup_info),
        ctypes.byref(process_info)
    )

    if not success:
        error_code = kernel32.GetLastError()
        raise map_win32_error(error_code, f"Failed to create process '{executable_path}'")

    # Validate handles
    if not process_info.hProcess or process_info.hProcess == -1:
        raise InvalidHandleError("process", process_info.hProcess)

    if not process_info.hThread or process_info.hThread == -1:
        raise InvalidHandleError("thread", process_info.hThread)

    if not process_info.dwProcessId:
        raise ProcessCreationError(f"CreateProcessW returned invalid process ID: {process_info.dwProcessId}")

    if not process_info.dwThreadId:
        raise ProcessCreationError(f"CreateProcessW returned invalid thread ID: {process_info.dwThreadId}")

    return (
        process_info.hProcess,
        process_info.hThread,
        process_info.dwProcessId,
        process_info.dwThreadId
    )


def wait_for_debug_event(timeout_ms: int = INFINITE) -> Optional[DEBUG_EVENT]:
    """Wait for a debug event.

    Args:
        timeout_ms: Timeout in milliseconds

    Returns:
        DEBUG_EVENT if available, None on timeout

    Raises:
        InvalidHandleError: If the debug session handle is invalid (ERROR_INVALID_HANDLE = 6)
        ProcessNotFoundError: If the process has exited or doesn't exist
        DebugEventError: For other errors waiting for debug events
    """
    from dgb.debugger.exceptions import (
        InvalidHandleError, ProcessNotFoundError, DebugEventError, map_win32_error
    )

    ERROR_SEM_TIMEOUT = 121
    ERROR_INVALID_HANDLE = 6

    event = DEBUG_EVENT()
    success = kernel32.WaitForDebugEvent(ctypes.byref(event), timeout_ms)

    if success:
        return event

    # Check what type of error occurred
    error_code = kernel32.GetLastError()

    if error_code == ERROR_SEM_TIMEOUT:
        # Normal timeout - no event available
        return None
    elif error_code == ERROR_INVALID_HANDLE:
        # The debug session is invalid - process likely exited or wasn't properly attached
        raise InvalidHandleError(
            "debug session",
            "The debug session handle is invalid. "
            "The process may have exited immediately after creation, "
            "or the debugger was not attached properly."
        )
    else:
        # Other error
        raise map_win32_error(error_code, "WaitForDebugEvent failed")


def continue_debug_event(process_id: int, thread_id: int, continue_status: int = DBG_CONTINUE) -> bool:
    """Continue from a debug event.

    Args:
        process_id: Process ID
        thread_id: Thread ID
        continue_status: DBG_CONTINUE or DBG_EXCEPTION_NOT_HANDLED

    Returns:
        True if successful
    """
    return kernel32.ContinueDebugEvent(process_id, thread_id, continue_status) != 0


def read_process_memory(process_handle: int, address: int, size: int) -> Optional[bytes]:
    """Read memory from a process.

    Args:
        process_handle: Process handle
        address: Address to read from
        size: Number of bytes to read

    Returns:
        Bytes read, or None on failure
    """
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)

    success = kernel32.ReadProcessMemory(
        process_handle,
        address,
        buffer,
        size,
        ctypes.byref(bytes_read)
    )

    if success:
        return buffer.raw[:bytes_read.value]
    return None


def write_process_memory(process_handle: int, address: int, data: bytes) -> bool:
    """Write memory to a process.

    Args:
        process_handle: Process handle
        address: Address to write to
        data: Bytes to write

    Returns:
        True if successful
    """
    bytes_written = ctypes.c_size_t(0)

    success = kernel32.WriteProcessMemory(
        process_handle,
        address,
        data,
        len(data),
        ctypes.byref(bytes_written)
    )

    return success != 0 and bytes_written.value == len(data)


def get_thread_context(thread_handle: int) -> Optional[CONTEXT]:
    """Get thread context (registers).

    Args:
        thread_handle: Thread handle

    Returns:
        CONTEXT structure or None on failure
    """
    context = CONTEXT()
    context.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS

    success = kernel32.GetThreadContext(thread_handle, ctypes.byref(context))

    if success:
        return context
    return None


def set_thread_context(thread_handle: int, context: CONTEXT) -> bool:
    """Set thread context (registers).

    Args:
        thread_handle: Thread handle
        context: CONTEXT structure

    Returns:
        True if successful
    """
    return kernel32.SetThreadContext(thread_handle, ctypes.byref(context)) != 0


def open_thread(thread_id: int, access: int = THREAD_ALL_ACCESS) -> Optional[int]:
    """Open a thread handle.

    Args:
        thread_id: Thread ID
        access: Desired access rights

    Returns:
        Thread handle or None on failure
    """
    handle = kernel32.OpenThread(access, False, thread_id)
    if handle:
        return handle
    return None


def close_handle(handle: int):
    """Close a handle."""
    if handle:
        kernel32.CloseHandle(handle)


def get_module_filename(process_handle: int, module_base: int) -> Optional[str]:
    """Get module filename.

    Args:
        process_handle: Process handle
        module_base: Module base address (HMODULE)

    Returns:
        Module filename or None
    """
    buffer = ctypes.create_unicode_buffer(260)
    length = psapi.GetModuleFileNameExW(process_handle, module_base, buffer, 260)

    if length:
        return buffer.value
    return None
