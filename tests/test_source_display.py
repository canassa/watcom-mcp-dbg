"""
Source display tests for DGB MCP Debugger.

Tests retrieving source code with DWARF info.
"""

import pytest
from pathlib import Path


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.source
def test_get_source(debug_session, mcp_client):
    """Test getting source code for a file and line."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get source for simple.c:4
    result = mcp_client.call_tool("debugger_get_source", {
        "session_id": session_id,
        "file": "simple.c",
        "line": 4
    })

    # Verify source is returned
    text = extract_text_from_result(result)

    # Should contain source code
    assert "result" in text.lower() or "int" in text.lower() or "=" in text


@pytest.mark.source
def test_get_source_with_context(debug_session, mcp_client):
    """Test getting source with context lines."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get source for simple.c:10 with 5 lines context
    result = mcp_client.call_tool("debugger_get_source", {
        "session_id": session_id,
        "file": "simple.c",
        "line": 10,
        "context_lines": 5
    })

    # Verify source is returned with context
    text = extract_text_from_result(result)
    assert text is not None
    assert len(text) > 0


@pytest.mark.source
def test_get_source_invalid_file(debug_session, mcp_client):
    """Test requesting source for non-existent file."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("simple.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Try to get source for non-existent file
    result = mcp_client.call_tool("debugger_get_source", {
        "session_id": session_id,
        "file": "nonexistent.c",
        "line": 10
    })

    # Should return error or empty result
    text = extract_text_from_result(result)
    assert "not found" in text.lower() or "error" in text.lower() or text == ""


@pytest.mark.source
def test_get_source_for_loop_code(debug_session, mcp_client):
    """Test getting source for code with loops."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("loops.exe", source_dirs=[source_dir])

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get source for loops.c:9 (inside for loop)
    result = mcp_client.call_tool("debugger_get_source", {
        "session_id": session_id,
        "file": "loops.c",
        "line": 9
    })

    # Verify source contains loop code
    text = extract_text_from_result(result)
    assert "sum" in text.lower() or "+" in text or "for" in text.lower()
