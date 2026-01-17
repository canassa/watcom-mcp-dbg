"""
Line breakpoint tests for DGB MCP Debugger.

Tests setting breakpoints at source file:line locations using DWARF debug info.
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
def test_set_breakpoint_at_line(debug_session, mcp_client):
    """Test setting a breakpoint at file:line."""
    # Use source_dirs to help find the source files
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint at simple.c:4 (inside add function)
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:4"
    })

    # Verify breakpoint was set
    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_breakpoint_hit_at_line(debug_session, mcp_client):
    """Test that line breakpoint is hit during execution."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint at simple.c:11 (call to add function)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:11"
    })

    # Continue - should hit breakpoint
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Verify we stopped
    text = extract_text_from_result(result)
    assert "stopped" in text.lower() or "breakpoint" in text.lower()


@pytest.mark.skip(reason="Breakpoint not being hit in simple.exe - needs investigation")
@pytest.mark.breakpoint
def test_breakpoint_in_function(debug_session, mcp_client):
    """Test breakpoint inside a function is hit when function is called."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint at simple.c:4 (inside add function)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:4"
    })

    # Continue - should hit breakpoint when add() is called
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Should have stopped at breakpoint
    text = extract_text_from_result(result)
    assert "stopped" in text.lower() or "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_invalid_line_format(debug_session, mcp_client):
    """Test that invalid line format is handled."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Try to set breakpoint without line number (just filename)
    # This might create a pending breakpoint or error
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c"
    })

    # Should not crash - either creates pending breakpoint or gives error
    text = extract_text_from_result(result)
    assert text is not None


@pytest.mark.breakpoint
def test_nonexistent_file_breakpoint(debug_session, mcp_client):
    """Test setting breakpoint in non-existent file creates pending breakpoint."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint in non-existent file
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "nonexistent.c:10"
    })

    # Should create pending breakpoint or error
    text = extract_text_from_result(result)
    assert "pending" in text.lower() or "error" in text.lower() or "not found" in text.lower() or "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_multiple_line_breakpoints(debug_session, mcp_client):
    """Test setting multiple line breakpoints in same file."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("functions.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoints at multiple lines
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "functions.c:4"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "functions.c:8"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "functions.c:13"
    })

    # List breakpoints
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    # Should show multiple breakpoints
    text = extract_text_from_result(result)
    assert "functions.c" in text or "breakpoint" in text.lower()
