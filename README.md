# DGB - MCP Server for Windows PE Debugging with Watcom DWARF 2

**Model Context Protocol (MCP) server** for debugging Windows PE executables with Watcom DWARF 2 debug information.

**Zero external debugging dependencies** - Uses direct Win32 Debug API calls via ctypes!

## Overview

DGB is an MCP server that exposes Windows PE debugging capabilities through the Model Context Protocol. This allows AI assistants and other MCP clients to debug legacy Windows executables with Watcom DWARF 2 debug information.

### Key Features

- **MCP Protocol Support** - HTTP transport with JSON-RPC 2.0
- **Multi-module debugging** - Debug EXE + DLLs with different debug info
- **Watcom DWARF 2 parsing** - Handles Watcom's appended ELF format
- **Session-based architecture** - Multiple concurrent debugging sessions
- **Source-level debugging** - Breakpoints by file:line, source code display
- **Direct Win32 Debug API** - No external debugging dependencies

### Architecture

```
┌─────────────────┐
│  MCP Client     │  (AI Assistant, IDE, etc.)
│  (HTTP)         │
└────────┬────────┘
         │ JSON-RPC 2.0
         ▼
┌─────────────────┐
│  Litestar       │  HTTP Server (async)
│  Application    │
└────────┬────────┘
         │
┌────────▼────────┐
│  MCP Handler    │  Protocol implementation
│                 │
├─────────────────┤
│ Session Manager │  Manages debugging sessions
│                 │
├─────────────────┤
│ Debugger Core   │  Win32 Debug API (sync)
│ (Background     │  • Event loop
│  Thread)        │  • Breakpoints
│                 │  • Module tracking
└─────────────────┘
```

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dgb.git
cd dgb

# Install dependencies
uv sync
```

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

# Enable auto-reload for development (watches for code changes)
uv run dgb-server --reload

# Note: You may see duplicate log messages in reload mode - this is normal
# as the app is initialized once at module load time for Uvicorn's reloader
```

### Available MCP Tools

The server exposes 10 debugging tools via MCP protocol:

1. **`debugger_create_session`** - Create a new debugging session
2. **`debugger_run`** - Start execution from entry point
3. **`debugger_continue`** - Continue after breakpoint
4. **`debugger_step`** - Single-step one instruction
5. **`debugger_set_breakpoint`** - Set breakpoint at location
6. **`debugger_list_breakpoints`** - List all breakpoints
7. **`debugger_get_registers`** - Get CPU register values
8. **`debugger_list_modules`** - List loaded modules
9. **`debugger_get_source`** - Get source code with context
10. **`debugger_close_session`** - Close debugging session

## MCP Protocol Examples

### Create Session

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "debugger_create_session",
    "arguments": {
      "executable_path": "c:\\entomorph\\plague.exe",
      "source_dirs": ["c:\\entomorph\\src"]
    }
  }
}
```

Response:
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

### Set Breakpoint

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "debugger_set_breakpoint",
    "arguments": {
      "session_id": "abc-123-def",
      "location": "dllmain.cpp:75"
    }
  }
}
```

### Get Registers

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "debugger_get_registers",
    "arguments": {
      "session_id": "abc-123-def"
    }
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [{
      "type": "text",
      "text": "Registers:\n  EAX    = 0x00000001\n  EBX    = 0x7efde000\n  ...\n  EIP    = 0x10000441\n  EFlags = 0x00000246"
    }]
  }
}
```

## Debugging Workflow

1. **Create Session** - Create a debugging session for your executable
2. **Set Breakpoints** - Set breakpoints before running or after loading modules
3. **Run** - Start execution, process will stop at first breakpoint
4. **Inspect** - Get registers, source code, modules
5. **Continue/Step** - Continue execution or single-step
6. **Close** - Clean up session when done

## Technical Details

### Win32 Debug API

DGB uses the Windows Debug API directly via ctypes:
- `CreateProcess` with `DEBUG_PROCESS` flag
- `WaitForDebugEvent` / `ContinueDebugEvent`
- Debug events: `CREATE_PROCESS`, `LOAD_DLL`, `EXCEPTION`, `EXIT_PROCESS`
- `ReadProcessMemory` / `WriteProcessMemory`
- `GetThreadContext` / `SetThreadContext`

### Watcom DWARF Format

Watcom compilers append DWARF 2 data as an ELF container at the end of PE files:

1. Parser checks for standard PE debug sections
2. Scans for ELF magic bytes (0x7F 'E' 'L' 'F') at file end
3. Extracts the appended ELF container using pyelftools
4. Handles Watcom's empty file table (file names in CU `DW_AT_name`)

### Multi-Module Address Resolution

- DWARF addresses are relative to module base (0x00000000)
- Runtime addresses depend on Windows module loading
- Formula: `absolute_address = module.base_address + relative_address`
- Module manager tracks all loaded modules (EXE + DLLs)
- Critical for debugging scenarios where main EXE has no debug info but DLLs do

### Threading Model

- **Litestar (Main Thread)** - Async HTTP server handling MCP requests
- **Event Loop Thread (Per Session)** - Win32 Debug API is blocking, runs in dedicated background thread
- **Communication** - Thread-safe queues for commands and results
- **Synchronization** - Locks protect shared debugger state

## Dependencies

```toml
dependencies = [
    "pyelftools>=0.30",    # DWARF parsing only
    "pefile>=2023.2.7",    # PE file parsing only
    "litestar>=2.11.0",    # Async web framework
    "uvicorn>=0.30.0",     # ASGI server
    "pydantic>=2.0",       # Data validation
]
```

**No external debugging libraries!** All Win32 Debug API access is direct via ctypes.

## Project Structure

```
dgb/
├── src/dgb/
│   ├── server/
│   │   ├── main.py              # Server entry point
│   │   ├── app.py               # Litestar application
│   │   ├── mcp_handler.py       # MCP protocol handler
│   │   ├── tools.py             # Tool implementations
│   │   ├── models.py            # Pydantic models
│   │   ├── session_manager.py   # Session lifecycle
│   │   ├── debugger_wrapper.py  # Thread-safe wrapper
│   │   └── source_resolver.py   # Source file handling
│   ├── debugger/
│   │   ├── core.py              # Main debugger, event loop
│   │   ├── breakpoint_manager.py # Software breakpoints
│   │   ├── process_controller.py # Win32 API wrapper
│   │   ├── module_manager.py    # Multi-module tracking
│   │   ├── state.py             # State management
│   │   └── win32api.py          # Win32 Debug API ctypes
│   └── dwarf/
│       ├── parser.py            # Watcom DWARF extraction
│       └── line_info.py         # Address/line mapping
├── test_parser.py               # Test DWARF parser
├── test_debugger.py             # Test debugger core
└── test_breakpoint.py           # Test breakpoints
```

## Testing

### Test DWARF Parser

```bash
# Test parser on a DLL with Watcom debug info
uv run python test_parser.py c:\entomorph\smackw32.dll
```

### Test Debugger Core

```bash
# Run end-to-end debugger test
uv run python test_debugger.py

# Test breakpoint functionality
uv run python test_breakpoint.py
```

### Test MCP Server

```bash
# Start server in one terminal
uv run dgb-server --log-level DEBUG

# In another terminal, send test requests
curl -X POST http://localhost:8000/mcp/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## Known Limitations

1. **DWARF 2 only** - No support for DWARF 3/4/5
2. **No variable inspection** - Can't read local variables yet
3. **No call stack** - Can't unwind stack frames
4. **Basic stepping** - Only single-step, no step-over/step-into
5. **Windows only** - Uses Win32 Debug API
6. **32-bit focus** - Primarily tested with 32-bit executables

## Future Enhancements

1. **Variable inspection** - DWARF expression evaluation
2. **Call stack unwinding** - Frame info parsing
3. **Enhanced stepping** - Step over/into function calls
4. **DWARF 3/4/5 support** - Extended format support
5. **64-bit support** - Support for x64 executables
6. **WebSocket transport** - Real-time debugging updates

## Migration from CLI

**Previous version** was an interactive CLI debugger. This version is a complete rewrite as an MCP server.

**Key changes:**
- No more interactive CLI - use HTTP API instead
- Session-based architecture for concurrent debugging
- Can integrate with AI assistants via MCP
- Can build custom UIs/clients using HTTP API

**Core functionality unchanged:**
- DWARF parsing and Win32 API code unchanged
- Same debugging capabilities, different interface

## License

MIT

## See Also

- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol specification
- [Litestar](https://litestar.dev/) - Python ASGI framework
- [pyelftools](https://github.com/eliben/pyelftools) - DWARF parsing
