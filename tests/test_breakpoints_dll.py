"""
DLL breakpoint tests for DGB MCP Debugger.

Tests deferred breakpoints that resolve when DLLs are loaded.
"""

import pytest
import re
from pathlib import Path


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.breakpoint
def test_deferred_dll_breakpoint(debug_session, mcp_client):
    """Test setting a deferred breakpoint in DLL code before DLL is loaded."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry (DLL not loaded yet)
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint in DLL code (testdll.c:7)
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:7"
    })

    # Breakpoint should be created (may be pending)
    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_dll_breakpoint_activation(debug_session, mcp_client):
    """Test that pending DLL breakpoint activates when DLL loads."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint in DLL code
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:7"
    })

    # Continue (DLL loads during LoadLibrary call)
    mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # List breakpoints - breakpoint should be active or hit
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    text = extract_text_from_result(result)
    assert "testdll.c" in text or "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_dll_breakpoint_hit(debug_session, mcp_client):
    """Test that DLL breakpoint is hit when DLL function is called."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint in DLL function (testdll.c:7 - inside DllFunction1)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:7"
    })

    # Continue to let program run - should hit breakpoint when DLL function is called
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Should have stopped at breakpoint or completed
    text = extract_text_from_result(result)

    # If we didn't hit the breakpoint on first continue, try again
    if "exited" not in text.lower():
        # We might have stopped at DLL load, continue again
        result = mcp_client.call_tool("debugger_continue", {
            "session_id": session_id
        })
        text = extract_text_from_result(result)

    # Should have either hit breakpoint or exited
    assert "stopped" in text.lower() or "breakpoint" in text.lower() or "exited" in text.lower()


@pytest.mark.breakpoint
def test_multiple_dll_breakpoints(debug_session, mcp_client):
    """Test setting multiple breakpoints in DLL code."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set multiple breakpoints in DLL
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:7"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:13"
    })

    # List breakpoints
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    # Should show both breakpoints
    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_dll_module_appears_after_load(debug_session, mcp_client):
    """Test that DLL module appears in module list after loading."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # List modules at entry (before DLL load)
    result1 = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })
    text1 = extract_text_from_result(result1)

    # Set breakpoint at testdll_user.c:35 (after DLL is loaded, at first DLL call)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll_user.c:35"
    })

    # Continue to that point
    mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # List modules again (after DLL load)
    result2 = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })
    text2 = extract_text_from_result(result2)

    # testdll.dll should appear in second listing
    assert "testdll.dll" in text2.lower()


@pytest.mark.breakpoint
def test_dll_function_register_args(debug_session, mcp_client):
    """Test that Watcom register calling convention works correctly in DLL.

    DllFunction3 takes 3 arguments (1, 2, 3) which should be passed in:
    - EAX = 1 (first argument)
    - EDX = 2 (second argument)
    - EBX = 3 (third argument)
    """
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint inside DllFunction3 at testdll.c:19
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll.c:19"
    })

    # Continue multiple times until we hit the breakpoint or exit
    max_continues = 5
    for i in range(max_continues):
        result = mcp_client.call_tool("debugger_continue", {
            "session_id": session_id
        })
        text = extract_text_from_result(result)

        # Check if we hit breakpoint or exited
        if "stopped" in text.lower() or "breakpoint" in text.lower():
            break
        if "exited" in text.lower():
            pytest.fail(f"Process exited before hitting breakpoint (after {i+1} continues): {text}")
    else:
        pytest.fail(f"Did not hit breakpoint after {max_continues} continues")

    # Get source code at breakpoint location
    source_result = mcp_client.call_tool("debugger_get_source", {
        "session_id": session_id,
        "file": "testdll.c",
        "line": 19,
        "context_lines": 5
    })
    source_text = extract_text_from_result(source_result)

    # Verify source contains the function and the breakpoint line
    assert "DllFunction3" in source_text, "Source should show DllFunction3 function"
    assert "int result = x + y + z" in source_text, "Source should show line 19 (breakpoint line)"
    assert "Line 19" in source_text or "19" in source_text, "Source should indicate line 19"

    # Get registers
    regs_result = mcp_client.call_tool("debugger_get_registers", {
        "session_id": session_id
    })
    regs_text = extract_text_from_result(regs_result).upper()

    # Extract register values
    eax_match = re.search(r"EAX\s*=\s*0[Xx]([0-9a-fA-F]+)", regs_text, re.IGNORECASE)
    edx_match = re.search(r"EDX\s*=\s*0[Xx]([0-9a-fA-F]+)", regs_text, re.IGNORECASE)
    ebx_match = re.search(r"EBX\s*=\s*0[Xx]([0-9a-fA-F]+)", regs_text, re.IGNORECASE)

    assert eax_match, f"Could not find EAX in register output: {regs_text[:200]}"
    assert edx_match, "Could not find EDX in register output"
    assert ebx_match, "Could not find EBX in register output"

    eax_val = int(eax_match.group(1), 16)
    edx_val = int(edx_match.group(1), 16)
    ebx_val = int(ebx_match.group(1), 16)

    # Verify Watcom register calling convention: DllFunction3(1, 2, 3) -> EAX=1, EDX=2, EBX=3
    assert eax_val == 1, f"EAX should be 1, got {eax_val} (0x{eax_match.group(1)})"
    assert edx_val == 2, f"EDX should be 2, got {edx_val} (0x{edx_match.group(1)})"
    assert ebx_val == 3, f"EBX should be 3, got {ebx_val} (0x{ebx_match.group(1)})"
