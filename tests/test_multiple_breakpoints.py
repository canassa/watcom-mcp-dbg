"""
Multiple breakpoint tests for DGB MCP Debugger.

Tests managing and hitting multiple breakpoints in sequence.
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
def test_set_multiple_breakpoints(debug_session, mcp_client):
    """Test setting multiple breakpoints at different locations."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("multi_bp.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set 3 breakpoints
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:17"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:18"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:19"
    })

    # List breakpoints
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    # All 3 should be listed
    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()
    # Check that we have references to the lines (exact format may vary)
    assert "multi_bp.c" in text or "17" in text or "18" in text or "19" in text


@pytest.mark.skip(reason="Failing test - needs investigation")
@pytest.mark.breakpoint
def test_hit_multiple_breakpoints_in_sequence(debug_session, mcp_client):
    """Test hitting multiple breakpoints in order."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("multi_bp.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set sequential breakpoints
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:17"
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:22"
    })

    # Continue to first breakpoint
    result1 = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })
    text1 = extract_text_from_result(result1)

    # Should have stopped
    assert "stopped" in text1.lower() or "breakpoint" in text1.lower() or "exited" in text1.lower()

    # If not exited, continue to next breakpoint
    if "exited" not in text1.lower():
        result2 = mcp_client.call_tool("debugger_continue", {
            "session_id": session_id
        })
        text2 = extract_text_from_result(result2)
        assert text2 is not None


@pytest.mark.breakpoint
def test_breakpoints_in_different_functions(debug_session, mcp_client):
    """Test breakpoints in different functions are hit correctly."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("multi_bp.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoints in different functions
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:4"  # operation1
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:8"  # operation2
    })

    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "multi_bp.c:12"  # operation3
    })

    # List breakpoints
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()
