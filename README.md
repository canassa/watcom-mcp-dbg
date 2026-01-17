# DGB - DWARF Debugger for Windows (MCP Server)

A **Model Context Protocol (MCP) server** for debugging Windows PE executables with Watcom DWARF 2 debug information. Uses direct Win32 Debug API calls via ctypes with zero external debugging dependencies.

## Overview

DGB enables debugging of legacy Windows executables compiled with Watcom compilers through the Model Context Protocol. This allows AI assistants, IDEs, and other MCP clients to debug retro/legacy Windows applications (such as DOS4GW games ported to Win32) that use Watcom's unique DWARF debug format.

### Key Features

- **MCP Protocol Server** - HTTP/JSON-RPC 2.0 transport for debugging operations
- **Multi-Module Debugging** - Debug EXE + DLLs with different debug info (e.g., EXE without debug info, DLL with debug info)
- **Watcom DWARF 2 Support** - Handles Watcom's appended ELF container format
- **Session-Based Architecture** - Multiple concurrent debugging sessions
- **Full Variable Inspection** - View local variables, parameters, pointers, structs, arrays with type information
- **Source-Level Debugging** - Breakpoints by file:line, source code display with context
- **Direct Win32 Debug API** - No external debugging dependencies (no WinDbg, no GDB)

### Target Use Case

Debugging retro Windows games and applications compiled with Watcom tools, such as:
- DOS4GW games ported to Win32
- Legacy Windows applications with Watcom debug info
- Games using middleware DLLs (e.g., Smacker video, Miles Sound System)

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dgb.git
cd dgb

# Install with uv
uv sync
```

**Requirements:**
- Python 3.11+
- Windows (uses Win32 Debug API)
- Executables compiled with Watcom DWARF 2 debug info

## Usage

### Starting the Server

```bash
# Start on default host/port (127.0.0.1:8000)
uv run dgb-server

# Customize host and port
uv run dgb-server --host 0.0.0.0 --port 8080

# Set session timeout (default: 3600 seconds)
uv run dgb-server --session-timeout 7200

# Set log level
uv run dgb-server --log-level DEBUG

# Enable auto-reload for development
uv run dgb-server --reload
```

### Available MCP Tools

The server exposes 11 debugging tools via MCP protocol:

| Tool | Description |
|------|-------------|
| `debugger_create_session` | Create a new debugging session for an executable |
| `debugger_run` | Start execution from entry point |
| `debugger_continue` | Continue execution after breakpoint |
| `debugger_step` | Single-step one CPU instruction |
| `debugger_set_breakpoint` | Set breakpoint at address or file:line |
| `debugger_list_breakpoints` | List all breakpoints in session |
| `debugger_get_registers` | Get CPU register values (32-bit x86) |
| `debugger_list_modules` | List loaded modules (EXE + DLLs) with debug info |
| `debugger_get_source` | Get source code with line context |
| `debugger_list_variables` | List local variables and parameters at current location |
| `debugger_close_session` | Close debugging session and clean up |

## Quick Start Example

### 1. Start the Server

```bash
uv run dgb-server
```

### 2. Create a Debugging Session

```json
POST http://localhost:8000/mcp/v1

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "debugger_create_session",
    "arguments": {
      "executable_path": "c:\\path\\to\\game.exe",
      "source_dirs": ["c:\\path\\to\\source"]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "✓ Session created: abc-123-def\nStatus: created"
    }],
    "isError": false
  }
}
```

### 3. Set Breakpoint and Run

```json
// Set breakpoint
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "debugger_set_breakpoint",
    "arguments": {
      "session_id": "abc-123-def",
      "location": "main.c:42"
    }
  }
}

// Start execution
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "debugger_run",
    "arguments": {
      "session_id": "abc-123-def"
    }
  }
}
```

### 4. Inspect Variables

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "debugger_list_variables",
    "arguments": {
      "session_id": "abc-123-def"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "variables": [
    {
      "name": "player_x",
      "type": "int",
      "value": "42",
      "location": "stack",
      "address": "0x0019fe10",
      "is_parameter": false
    },
    {
      "name": "name_ptr",
      "type": "char*",
      "value": "0x00401000",
      "location": "stack",
      "address": "0x0019fe0c",
      "is_parameter": true
    }
  ],
  "count": 2
}
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  MCP Client (AI Assistant, IDE, etc.)          │
└────────────────────┬────────────────────────────┘
                     │ HTTP/JSON-RPC 2.0
                     ▼
┌─────────────────────────────────────────────────┐
│  Litestar HTTP Server (Async)                  │
│  ├─ MCP Handler (Protocol Implementation)      │
│  └─ Session Manager (Multi-session)            │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │Session │  │Session │  │Session │  (Background Threads)
   │   1    │  │   2    │  │   3    │
   └───┬────┘  └───┬────┘  └───┬────┘
       │           │           │
       ▼           ▼           ▼
┌──────────────────────────────────────────────────┐
│  Debugger Core (Win32 Debug API - Blocking)     │
│  ├─ Event Loop (WaitForDebugEvent)              │
│  ├─ Breakpoint Manager (INT 3 breakpoints)      │
│  ├─ Module Manager (EXE + DLL tracking)         │
│  ├─ Variable Inspector (DWARF type resolution)  │
│  └─ Process Controller (Memory/Register access) │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  DWARF Parser (Watcom Format Support)           │
│  ├─ ELF Container Extraction                    │
│  ├─ DIE Parser (Types, Variables, Subprograms)  │
│  ├─ Line Info (Address ↔ Source Mapping)        │
│  └─ Type Resolver (Pointers, Structs, Arrays)   │
└──────────────────────────────────────────────────┘
```

## Technical Details

### Win32 Debug API

DGB uses Windows Debug API directly via ctypes:

- **Process Control**: `CreateProcess` with `DEBUG_PROCESS` flag
- **Event Loop**: `WaitForDebugEvent` / `ContinueDebugEvent`
- **Debug Events**: `CREATE_PROCESS`, `LOAD_DLL`, `EXCEPTION`, `EXIT_PROCESS`
- **Memory Access**: `ReadProcessMemory` / `WriteProcessMemory`
- **Register Access**: `GetThreadContext` / `SetThreadContext`

### Watcom DWARF Format

Watcom compilers use a unique format where DWARF 2 data is appended as an ELF container:

1. Parser checks for standard PE debug sections
2. Scans backward from end of file for ELF magic bytes (0x7F 'E' 'L' 'F')
3. Extracts the appended ELF container using pyelftools
4. Handles Watcom quirks (empty file table, file names in CU `DW_AT_name`)

### Multi-Module Debugging

Critical for scenarios where the main EXE has no debug info but DLLs do:

- **DWARF addresses** are relative to module base (0x00000000)
- **Runtime addresses** depend on where Windows loads the module
- **Formula**: `absolute_address = module.base_address + relative_address`
- **Module Manager** tracks all loaded modules and resolves addresses across boundaries

### Variable Inspection

Full variable inspection with DWARF type resolution:

- **Supported Types**: Base types (int, char, float, etc.), pointers, arrays, structs, typedefs
- **Location Evaluation**: Stack (DW_OP_fbreg), registers (DW_OP_reg*), globals (DW_OP_addr)
- **Value Formatting**: Type-aware formatting (signed/unsigned integers, floats, hex pointers)
- **Parameters**: Distinguishes function parameters from local variables

### Threading Model

- **Main Thread**: Litestar async HTTP server handling MCP requests
- **Event Loop Threads**: One per session, running Win32 Debug API (blocking)
- **Communication**: Thread-safe queues for commands and results
- **Synchronization**: Locks protect shared debugger state

## Project Structure

```
dgb/
├── src/dgb/
│   ├── server/
│   │   ├── main.py              # Server entry point
│   │   ├── app.py               # Litestar application setup
│   │   ├── mcp_handler.py       # MCP protocol implementation
│   │   ├── tools.py             # Tool implementations (11 tools)
│   │   ├── session_manager.py   # Session lifecycle management
│   │   ├── debugger_wrapper.py  # Thread-safe debugger wrapper
│   │   └── source_resolver.py   # Source file loading
│   ├── debugger/
│   │   ├── core.py              # Main debugger orchestration
│   │   ├── breakpoint_manager.py # Software breakpoint handling
│   │   ├── process_controller.py # Win32 API wrapper
│   │   ├── module_manager.py    # Multi-module tracking
│   │   ├── state.py             # Debugger state management
│   │   └── win32api.py          # Win32 Debug API ctypes bindings
│   └── dwarf/
│       ├── parser.py            # Watcom DWARF extraction
│       ├── line_info.py         # Address/line bidirectional mapping
│       ├── die_parser.py        # DWARF DIE parsing (types, subprograms)
│       ├── type_info.py         # Type resolution and formatting
│       ├── location_eval.py     # DWARF location expression evaluation
│       └── variable_info.py     # High-level variable inspection
├── tests/
│   ├── conftest.py              # Pytest fixtures (MCP server, sessions)
│   ├── test_breakpoints_*.py    # Breakpoint tests (address, line, DLL)
│   ├── test_execution_control.py # Run, continue, step tests
│   ├── test_variable_inspection.py # Variable inspection tests
│   ├── test_registers.py        # Register access tests
│   ├── test_modules.py          # Module listing tests
│   ├── test_source_display.py   # Source code display tests
│   └── test_session_management.py # Session lifecycle tests
├── CLAUDE.md                    # Project instructions for Claude Code
├── README.md                    # This file
├── pyproject.toml               # Project configuration
└── pytest.ini                   # Pytest configuration
```

## Testing

The project has a comprehensive test suite with 74 tests covering all functionality:

```bash
# Run all tests
uv run pytest -s

# Run specific test file
uv run pytest tests/test_variable_inspection.py -s

# Run specific test
uv run pytest tests/test_breakpoints_line.py::test_breakpoint_in_function -s

# Run with verbose output
uv run pytest -v -s
```

**Test Coverage:**
- ✅ Breakpoints (address, file:line, DLL breakpoints)
- ✅ Execution control (run, continue, step)
- ✅ Variable inspection (all types, parameters, locals)
- ✅ Register access (all x86 registers)
- ✅ Module tracking (EXE + DLLs)
- ✅ Source display with context
- ✅ Session management (create, concurrent, cleanup)
- ✅ Edge cases (crashes, invalid operations)

**All tests must pass before committing.** Run `uv run pytest -s` to verify.

## Dependencies

```toml
dependencies = [
    "pyelftools>=0.30",    # DWARF parsing
    "pefile>=2023.2.7",    # PE file parsing
    "litestar>=2.11.0",    # Async web framework (MCP server)
    "uvicorn>=0.30.0",     # ASGI server
    "pydantic>=2.0",       # Data validation
]

[tool.uv.dev-dependencies]
pytest = ">=7.0"           # Testing framework
pytest-cov = ">=4.0"       # Coverage reporting
faker = ">=40.0.0"         # Test data generation
```

**No external debugging libraries!** All Win32 Debug API access is direct via ctypes.

## Known Limitations

1. **DWARF 2 only** - No support for DWARF 3/4/5
2. **No call stack unwinding** - Can't unwind stack frames yet (needs frame info parsing)
3. **Basic stepping** - Only single-step instruction, no step-over/step-into function calls
4. **Windows only** - Uses Win32 Debug API
5. **32-bit focus** - Primarily tested with 32-bit executables
6. **Struct formatting** - Some struct types may show formatting errors (pyelftools issue with DW_AT_data_member_location)

## Future Enhancements

1. **Call stack unwinding** - Parse DWARF frame information for stack traces
2. **Enhanced stepping** - Step over/into function calls (requires call stack)
3. **String dereferencing** - Read strings from char* pointers
4. **DWARF 3/4/5 support** - Extended format support for modern compilers
5. **64-bit support** - Support for x64 executables
6. **WebSocket transport** - Real-time debugging updates for better UX

## Use with AI Assistants

This MCP server is designed to work with AI assistants that support the Model Context Protocol:

```python
# Example: AI assistant debugging a legacy game
"Set a breakpoint in smackw32.dll at SmackOpen function"
→ Tool: debugger_set_breakpoint(location="smackw32.c:145")

"What are the current register values?"
→ Tool: debugger_get_registers()

"Show me the local variables"
→ Tool: debugger_list_variables()

"Continue execution"
→ Tool: debugger_continue()
```

## License

MIT

## See Also

- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [Litestar Documentation](https://litestar.dev/) - Python ASGI framework
- [pyelftools](https://github.com/eliben/pyelftools) - DWARF parsing library
- [Win32 Debug API](https://learn.microsoft.com/en-us/windows/win32/debug/debugging-functions) - Windows debugging reference
