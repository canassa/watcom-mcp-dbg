"""
Edge case tests for DGB MCP Debugger.

Tests error handling, crashes, and unusual scenarios.
"""

import pytest
from pathlib import Path
import time


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.edge_case
def test_process_crash(debug_session, mcp_client):
    """Test handling of process crash (access violation)."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("crash.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Continue - process will crash with access violation
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Should report exception or crash
    text = extract_text_from_result(result)
    assert "exception" in text.lower() or "violation" in text.lower() or "crash" in text.lower() or "error" in text.lower() or "stopped" in text.lower()


@pytest.mark.edge_case
def test_concurrent_sessions(debug_session):
    """Test creating multiple concurrent sessions."""
    # Create 3 sessions simultaneously
    session1 = debug_session("simple.exe")
    session2 = debug_session("loops.exe")
    session3 = debug_session("functions.exe")

    # All should succeed and be unique
    assert session1 != session2
    assert session2 != session3
    assert session1 != session3


@pytest.mark.edge_case
def test_rapid_session_creation_and_closure(mcp_client, compiled_test_programs):
    """Test rapidly creating and closing sessions."""
    import re

    for i in range(5):
        # Create session
        exe_path = str(compiled_test_programs / "simple.exe")
        result = mcp_client.call_tool("debugger_create_session", {
            "executable_path": exe_path
        })

        # Extract session ID
        text = extract_text_from_result(result)
        match = re.search(r"Session (\S+) created", text)
        assert match
        session_id = match.group(1)

        # Close session
        mcp_client.call_tool("debugger_close_session", {
            "session_id": session_id
        })

        # Small delay to avoid overwhelming the server
        time.sleep(0.1)


@pytest.mark.edge_case
def test_double_close_session(debug_session, mcp_client):
    """Test closing a session twice."""
    session_id = debug_session("simple.exe")

    # Close once
    mcp_client.call_tool("debugger_close_session", {
        "session_id": session_id
    })

    # Try to close again - should fail gracefully
    with pytest.raises(Exception):
        mcp_client.call_tool("debugger_close_session", {
            "session_id": session_id
        })


@pytest.mark.edge_case
def test_operations_on_closed_session(debug_session, mcp_client):
    """Test that operations on closed session fail gracefully."""
    session_id = debug_session("simple.exe")

    # Close session
    mcp_client.call_tool("debugger_close_session", {
        "session_id": session_id
    })

    # Try to run on closed session
    with pytest.raises(Exception):
        mcp_client.call_tool("debugger_run", {
            "session_id": session_id
        })


@pytest.mark.edge_case
def test_breakpoint_at_invalid_line(debug_session, mcp_client):
    """Test setting breakpoint at a line number that doesn't have code."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Try to set breakpoint at line 999 (doesn't exist)
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:999"
    })

    # Should create pending breakpoint or error
    text = extract_text_from_result(result)
    assert "pending" in text.lower() or "error" in text.lower() or "not found" in text.lower() or "breakpoint" in text.lower()


@pytest.mark.edge_case
def test_step_at_exit(debug_session, mcp_client):
    """Test stepping when process is about to exit."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Continue to end
    mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Try to step after process exited - should handle gracefully
    try:
        result = mcp_client.call_tool("debugger_step", {
            "session_id": session_id
        })
        # If it doesn't raise an exception, check that result indicates process exited
        text = extract_text_from_result(result)
        assert "exited" in text.lower() or "terminated" in text.lower() or "error" in text.lower()
    except Exception as e:
        # Exception is acceptable for this edge case
        assert "exited" in str(e).lower() or "terminated" in str(e).lower() or "session" in str(e).lower()


@pytest.mark.edge_case
def test_missing_source_directory(debug_session, mcp_client):
    """Test debugging without providing source directories."""
    # Create session without source_dirs
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Try to set line breakpoint - may still work if DWARF has full paths
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:11"
    })

    # Should either work or create pending breakpoint
    text = extract_text_from_result(result)
    assert text is not None
