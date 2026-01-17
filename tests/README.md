# DGB MCP Debugger Test Suite

Comprehensive black box test suite for the DGB MCP debugger, testing all functionality via HTTP JSON-RPC 2.0 requests.

## Overview

This test suite provides comprehensive black box testing of the DGB MCP debugger by:
- Starting a real MCP server
- Compiling test C/C++ programs with Watcom DWARF 2 debug info
- Testing all debugging functionality via HTTP JSON-RPC requests
- Automatically cleaning up processes and resources

## Test Structure

```
tests/
├── fixtures/
│   ├── src/          # C source files for test programs
│   ├── bin32/        # Compiled 32-bit executables (committed to repo)
│   ├── compile.bat   # Watcom compilation script (Windows)
│   └── compile.sh    # Watcom compilation script (bash)
├── conftest.py       # Pytest fixtures and shared utilities
└── test_*.py         # Test modules
```

## Test Programs

Seven test programs compiled with Watcom DWARF 2 debug info:

1. **simple.exe** - Basic program with function calls
   - Tests basic breakpoints and function entry/exit

2. **loops.exe** - Loop constructs
   - Tests breakpoints in for/while/do-while loops

3. **functions.exe** - Nested function calls
   - Tests call hierarchy and breakpoints at different depths

4. **multi_bp.exe** - Multiple breakpoint testing
   - Tests setting and hitting multiple breakpoints in sequence

5. **crash.exe** - Exception testing
   - Tests handling of access violations

6. **testdll.dll** - Simple DLL with exported functions
   - Tests DLL debugging and deferred breakpoint resolution

7. **testdll_user.exe** - Executable that loads testdll.dll
   - Tests multi-module debugging (EXE + DLL)

## Test Modules

### test_mcp_server.py
- Server lifecycle testing
- Protocol initialization
- Tool listing

### test_session_management.py
- Session creation and closing
- Invalid session handling
- Concurrent sessions

### test_execution_control.py
- Run to entry point
- Continue execution
- Single-step
- Multiple steps
- Run to completion

### test_breakpoints_address.py
- Address-based breakpoints
- Listing breakpoints
- Invalid address handling

### test_breakpoints_line.py
- File:line breakpoints using DWARF
- Breakpoints in functions
- Invalid line handling
- Multiple line breakpoints

### test_breakpoints_dll.py
- Deferred DLL breakpoints
- Breakpoint activation when DLL loads
- DLL breakpoint hits
- Multiple DLL breakpoints

### test_multiple_breakpoints.py
- Multiple breakpoints in different locations
- Sequential breakpoint hits
- Breakpoints in different functions

### test_registers.py
- Reading CPU registers
- Register changes after stepping
- Verification of all major registers

### test_modules.py
- Listing loaded modules
- Debug info detection
- DLL module appearance after loading
- Module base addresses

### test_source_display.py
- Source code retrieval
- Context lines
- Invalid file handling

### test_edge_cases.py
- Process crashes
- Concurrent sessions
- Rapid session creation/closure
- Double close
- Operations on closed sessions
- Invalid breakpoints
- Stepping at exit

## Running Tests

### Prerequisites

```bash
# Install dependencies
uv sync --dev
```

### Run All Tests

```bash
uv run pytest tests/ -v
```

### Run Specific Test Module

```bash
uv run pytest tests/test_mcp_server.py -v
uv run pytest tests/test_breakpoints_line.py -v
```

### Run Single Test

```bash
uv run pytest tests/test_mcp_server.py::test_server_starts -v
```

### Run with Coverage

```bash
uv run pytest tests/ --cov=src/dgb --cov-report=html
```

## Test Infrastructure

### Fixtures (conftest.py)

1. **compiled_test_programs** (session scope)
   - Verifies all test executables are compiled
   - Automatically runs compile.sh if binaries are missing

2. **mcp_server** (session scope)
   - Starts MCP server on port 8765
   - Waits for server to be ready
   - Cleans up server and all child processes on teardown

3. **mcp_client**
   - Provides MCPClient instance for making JSON-RPC requests
   - Auto-increments request IDs
   - Raises exceptions on JSON-RPC errors

4. **debug_session** (factory fixture)
   - Creates debugging sessions
   - Tracks all created sessions
   - Automatically closes all sessions on teardown

5. **kill_stray_processes** (autouse)
   - Runs after every test
   - Kills any stray test executable processes
   - Prevents process leaks between tests

### MCPClient Class

Wrapper for making JSON-RPC 2.0 requests to the MCP server:

```python
client = MCPClient()

# Call a tool
result = client.call_tool("debugger_create_session", {
    "executable_path": "path/to/exe"
})

# List available tools
tools = client.list_tools()

# Initialize protocol
capabilities = client.initialize()
```

## Compilation

Test programs are compiled with Watcom C compiler using DWARF 2 debug info.

### Manual Compilation

```bash
# On Windows
cd tests/fixtures
compile.bat

# On bash/WSL
cd tests/fixtures
bash compile.sh
```

### Compilation Flags

- `-d2` - Full debugging info (DWARF 2)
- `-hw` - Watcom debug format (appends ELF container)
- `-zc` - Place literals in code segment
- `-bt=nt` - Build target Windows NT
- `-bd` - Build DLL (for testdll.c)

## Verified Functionality

✅ Server starts and responds to HTTP requests
✅ Protocol initialization
✅ Tool listing (all 10 tools)
✅ Session creation and closing
✅ Concurrent sessions
✅ Run to entry point
✅ Continue execution
✅ Single-step
✅ Address breakpoints
✅ Line breakpoints (DWARF-based)
✅ DLL deferred breakpoints
✅ Multiple breakpoints
✅ Register reading
✅ Module listing
✅ Source code display
✅ Exception handling
✅ Process cleanup

## Known Issues

1. Resource warnings about unclosed file handles (cosmetic, doesn't affect functionality)
2. When running full test suite, port conflicts may occur if server from previous run is still active
3. Some tests are flexible about error handling (accept both immediate errors and deferred errors)

## Success Criteria

- All MCP tools tested comprehensively
- Server starts/stops cleanly without process leaks
- Sessions create/close properly with cleanup
- Address and line breakpoints work correctly
- DLL deferred breakpoints resolve when module loads
- Execution control (run/continue/step) works reliably
- No hanging processes after test suite completes
- No resource leaks

## Future Enhancements

- Hardware breakpoints
- Step over/step into (function-aware stepping)
- Breakpoint enable/disable
- Variable inspection (requires DWARF expression evaluation)
- Call stack unwinding
- Watchpoints
- 64-bit executable support
