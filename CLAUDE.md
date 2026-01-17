# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WatCom Debugger MCP** is a **Model Context Protocol (MCP) server** for debugging Windows PE executables with Watcom DWARF 2 debug information. It uses **direct Win32 Debug API calls via ctypes** without external debugging dependencies.

Key characteristics:
- **MCP Protocol Server** - Exposes debugging via HTTP/JSON-RPC 2.0
- **Zero external debugging dependencies** - Uses ctypes for Win32 Debug API
- **Supports Watcom DWARF format** where debug info is appended as an ELF container
- **Multi-module debugging** - Can debug EXE + DLLs with different debug info
- **Session-based architecture** - Multiple concurrent debugging sessions
- Targets legacy Windows executables compiled with Watcom compilers

## Development Commands

### Setup and Installation
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --dev
```

### Testing

**CRITICAL TESTING RULES:**
1. **ALWAYS run the full test suite before committing** using `uv run pytest -s`
2. **NEVER commit if ANY tests are failing** - all tests must pass
3. **ALL tests are currently passing** - keep it that way

```bash
# Run full test suite (REQUIRED before any commit)
uv run pytest -s

# Run with verbose output
uv run pytest -v -s

# Run specific test file
uv run pytest tests/test_breakpoints_line.py -s

# Run specific test
uv run pytest tests/test_breakpoints_line.py::test_set_breakpoint_at_line -s

# Legacy standalone test scripts (deprecated, use pytest instead)
uv run python test_parser.py c:\entomorph\smackw32.dll
uv run python test_debugger.py
uv run python test_breakpoint.py
uv run python test_line_program.py <dll_path>
```

### Running the MCP Server
```bash
# Start MCP server on default host/port (127.0.0.1:8000)
uv run dgb-server

# Customize host and port
uv run dgb-server --host 0.0.0.0 --port 8080

# Set session timeout and log level
uv run dgb-server --session-timeout 7200 --log-level DEBUG

# Enable auto-reload for development
uv run dgb-server --reload
```

## Architecture

### MCP Server Components

**Litestar Application** (`src/dgb/server/app.py`)
- Async HTTP server using Litestar framework
- POST `/mcp/v1` endpoint for JSON-RPC 2.0 messages
- CORS configuration for MCP clients
- Manages application state (SessionManager, MCPHandler)

**MCP Handler** (`src/dgb/server/mcp_handler.py`)
- Implements MCP protocol methods:
  - `initialize` - Server initialization
  - `tools/list` - List available debugging tools
  - `tools/call` - Execute debugging operations
- Translates JSON-RPC requests to debugger operations
- Formats results as MCP tool responses

**Session Manager** (`src/dgb/server/session_manager.py`)
- Creates and tracks debugging sessions
- Each session has unique ID and isolated debugger instance
- Session timeout management
- Thread-safe access to sessions

**Debugger Wrapper** (`src/dgb/server/debugger_wrapper.py`)
- Thread-safe wrapper around blocking Win32 Debug API
- Runs event loop in dedicated background thread per session
- Command queue for async-to-sync communication
- Result queue for returning debugger state

**Tools** (`src/dgb/server/tools.py`)
- 10 MCP tool implementations:
  - Session management (create, close)
  - Execution control (run, continue, step)
  - Breakpoints (set, list)
  - Inspection (registers, modules, source)
- Tool registry and metadata

**Source Resolver** (`src/dgb/server/source_resolver.py`)
- Loads source files with directory search
- Returns source code with line context
- Caches loaded files

### Debugger Core Components

**Debugger Core** (`src/dgb/debugger/core.py`)
- Main orchestration point for all debugging operations
- Implements Win32 Debug API event loop handling:
  - `CREATE_PROCESS_DEBUG_EVENT` - Initial process creation
  - `LOAD_DLL_DEBUG_EVENT` - **Critical for DLL debugging** (like smackw32.dll)
  - `EXCEPTION_DEBUG_EVENT` - Breakpoints and single-step
  - `EXIT_PROCESS_DEBUG_EVENT` - Process termination
- Coordinates between ProcessController, ModuleManager, and BreakpointManager
- Manages debugger state transitions (running, stopped, step mode)

**Module Manager** (`src/dgb/debugger/module_manager.py`)
- **Key innovation** enabling multi-module debugging scenarios:
  - Main EXE (e.g., plague.exe) may have no debug info
  - DLLs (e.g., smackw32.dll) have DWARF 2 debug info
  - Breakpoints can be set in DLL code by file:line
- Tracks all loaded modules (EXE + DLLs) with their base addresses
- Automatically extracts DWARF info from each module on load
- Resolves addresses across module boundaries:
  - `address_to_module()` - Find which module owns an address
  - `resolve_address_to_line()` - Convert absolute address to source location
  - `resolve_line_to_address()` - Convert file:line to absolute address

**Process Controller** (`src/dgb/debugger/process_controller.py`)
- Wrapper around Win32 Debug API for process operations
- Memory access (read/write process memory)
- Register access (get/set CPU registers)
- Thread management

**Breakpoint Manager** (`src/dgb/debugger/breakpoint_manager.py`)
- Software breakpoints using INT 3 (0xCC) instruction
- Works with ModuleManager to resolve breakpoint locations
- Supports both address-based and file:line breakpoints

**Win32 API Wrapper** (`src/dgb/debugger/win32api.py`)
- Direct ctypes bindings to Windows debugging APIs
- No external dependencies (replaces WinAppDbg)
- Handles all low-level Win32 structures and calls

### DWARF Parsing

**DWARF Parser** (`src/dgb/dwarf/parser.py`)
- Handles **Watcom format**: DWARF appended as ELF container at end of PE file
- Process:
  1. Checks for standard PE debug sections first
  2. Scans for ELF magic bytes (0x7F 'E' 'L' 'F') at file end
  3. Extracts the appended ELF container using pyelftools
- Uses pyelftools for DWARF 2 parsing

**Line Info** (`src/dgb/dwarf/line_info.py`)
- Builds bidirectional mapping: addresses ↔ source locations
- Handles **Watcom's empty file table** quirk:
  - Standard DWARF stores file names in line program header
  - Watcom stores file names in CU's `DW_AT_name` attribute
- Caches lookups for performance

## Critical Implementation Details

### Threading and Async Strategy

**Problem:** Win32 Debug API is blocking, Litestar is async.

**Solution:**
1. Each session runs `debugger.run_event_loop()` in a dedicated thread
2. HTTP handlers are async but communicate with debugger thread via queues
3. Command pattern: HTTP handler → command queue → debugger thread → result queue → HTTP response
4. `DebuggerWrapper` manages thread-safe communication

**Event Loop Thread:**
- Runs in background per session
- Checks command queue for instructions (continue, step, set_breakpoint)
- Executes Win32 Debug API operations synchronously
- Returns results via result queue

### MCP Protocol Flow

1. **Client sends JSON-RPC request** to `/mcp/v1`
2. **Litestar routes to `mcp_endpoint`** (async handler)
3. **MCPHandler processes request** (initialize, tools/list, tools/call)
4. **Tool function executes** (gets session, calls debugger)
5. **DebuggerWrapper sends command** to background thread
6. **Background thread executes** Win32 API operations
7. **Result returned** through queues to HTTP response

## Critical Implementation Details (Debugger Core)

### Multi-Module Address Resolution

When setting a breakpoint or resolving an address:
1. ModuleManager searches all modules with debug info
2. Converts between absolute addresses (in memory) and module-relative addresses (from DWARF)
3. Formula: `absolute_address = module.base_address + relative_address`

This is essential because:
- DWARF addresses are relative to module base (0x00000000)
- Runtime addresses depend on where Windows loads the module
- Each module (EXE + each DLL) has its own address space

### Watcom DWARF Format Quirks

Watcom compilers deviate from standard DWARF:
- **Appended ELF container** instead of PE sections
- **Empty file table** in line program header
- File names stored in `DW_AT_name` of compilation unit DIEs
- Must scan entire PE file for ELF magic bytes

### Win32 Debug API Event Loop

Key patterns:
- Call `wait_for_debug_event()` to block until event occurs
- Dispatch event to appropriate handler
- **Always call** `continue_debug_event()` with continue status
- Use `DBG_CONTINUE` for handled events
- Use `DBG_EXCEPTION_NOT_HANDLED` to let process handle first-chance exceptions

### Breakpoint Implementation

Software breakpoints work by:
1. Save original byte at breakpoint address
2. Write INT 3 (0xCC) instruction
3. When hit, CPU raises `EXCEPTION_BREAKPOINT`
4. Restore original byte
5. Decrement EIP to re-execute original instruction
6. Single-step to re-enable breakpoint

## Testing Patterns

The project uses **pytest** for comprehensive test coverage. All tests are located in the `tests/` directory.

**Test Organization:**
- `tests/conftest.py` - Shared fixtures (MCP server, client, compiled test programs, debug sessions)
- `tests/test_*.py` - Test modules organized by feature area
- `tests/fixtures/` - Test executables and source files

**Key Fixtures:**
- `mcp_server` - Starts MCP server on random port
- `mcp_client` - Client for calling MCP tools
- `compiled_test_programs` - Directory with compiled test executables
- `debug_session` - Creates and manages debug sessions

**Test Categories:**
- Breakpoints (address, line, DLL breakpoints)
- Execution control (run, continue, step)
- Session management
- Register inspection
- Module listing
- Source code display
- Edge cases and error handling

**IMPORTANT:** All tests must pass before committing. Run `uv run pytest -s` to verify.

## Dependencies

Runtime:
- `pyelftools>=0.30` - DWARF parsing only
- `pefile>=2023.2.7` - PE file parsing only
- `litestar>=2.11.0` - Async web framework for HTTP server
- `uvicorn>=0.30.0` - ASGI server
- `pydantic>=2.0` - Data validation (included with Litestar)

Dev:
- `pytest>=7.0` - Testing framework (not yet used extensively)
- `pytest-cov>=4.0` - Coverage

**No external debugging libraries** - all Win32 Debug API access is direct via ctypes.

## Common Patterns

### Reading Module Debug Info
```python
parser = WatcomDwarfParser(module_path)
dwarf_info = parser.extract_dwarf_info()
if dwarf_info:
    line_info = LineInfo(dwarf_info)
    # Use line_info for address/line mapping
```

### Resolving Breakpoint Location
```python
# File:line → absolute address
result = module_manager.resolve_line_to_address(filename, line)
if result:
    absolute_address, module = result
    # Set breakpoint at absolute_address
```

### Handling Debug Events
```python
while running:
    event = win32api.wait_for_debug_event(timeout_ms=100)
    if event:
        dispatch_event(event)
        win32api.continue_debug_event(
            event.dwProcessId,
            event.dwThreadId,
            continue_status
        )
```

## Known Limitations

1. **DWARF 2 only** - No support for DWARF 3/4/5
2. **No variable inspection** - Can't read local variables yet (needs DWARF expression evaluation)
3. **No call stack** - Can't unwind stack frames (needs frame info parsing)
4. **Basic stepping** - Only single-step, no step-over/step-into function calls
5. **Windows only** - Uses Win32 Debug API
6. **32-bit focus** - Primarily tested with 32-bit executables
