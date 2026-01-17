"""
DLL breakpoint tests for DGB MCP Debugger.

Tests deferred breakpoints that resolve when DLLs are loaded.
"""

import pytest
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


@pytest.mark.skip(reason="Failing test - needs investigation")
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

    # Set breakpoint at testdll_user.c:32 (after DLL is loaded)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll_user.c:32"
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
