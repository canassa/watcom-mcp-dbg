"""
Session management tests for DGB MCP Debugger.

Tests session creation, closing, and error handling.
"""

import pytest


@pytest.mark.session
def test_create_session(debug_session):
    """Test creating a debugging session."""
    session_id = debug_session("simple.exe")

    # Verify session ID was returned
    assert session_id is not None
    assert len(session_id) > 0


@pytest.mark.session
def test_create_session_nonexistent_file(mcp_client, compiled_test_programs):
    """Test creating session with non-existent file.

    Note: Session may be created successfully, but error will occur when trying to run.
    This test verifies the system handles nonexistent files gracefully.
    """
    nonexistent_path = str(compiled_test_programs / "nonexistent.exe")

    # Try to create session - may succeed or fail depending on when validation happens
    try:
        result = mcp_client.call_tool("debugger_create_session", {
            "executable_path": nonexistent_path
        })
        # If session created, try to run it - this should fail
        # Extract session ID
        content = result.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            import re
            match = re.search(r"Session created:\s+(\S+)", text)
            if match:
                session_id = match.group(1)
                # Try to run - should fail
                with pytest.raises(Exception):
                    mcp_client.call_tool("debugger_run", {"session_id": session_id})
                # Cleanup
                try:
                    mcp_client.call_tool("debugger_close_session", {"session_id": session_id})
                except:
                    pass
    except Exception as e:
        # Also acceptable if it fails immediately
        assert "not found" in str(e).lower() or "does not exist" in str(e).lower() or "error" in str(e).lower()


@pytest.mark.session
def test_close_session(debug_session, mcp_client):
    """Test closing a session."""
    session_id = debug_session("simple.exe")

    # Close the session
    result = mcp_client.call_tool("debugger_close_session", {
        "session_id": session_id
    })

    # Verify result indicates success
    assert result is not None


@pytest.mark.session
def test_invalid_session_id(mcp_client):
    """Test using invalid session ID.

    Server should handle invalid session IDs gracefully by returning error in response.
    """
    result = mcp_client.call_tool("debugger_run", {
        "session_id": "invalid_session_id_12345"
    })

    # Check if result indicates error
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "").lower()
        # Should mention error or unknown session
        assert "error" in text or "invalid" in text or "unknown" in text or "not found" in text
    else:
        # If isError flag is present, check that
        assert result.get("isError", False) == True


@pytest.mark.session
def test_concurrent_sessions(debug_session):
    """Test creating multiple sessions simultaneously."""
    # Create 3 sessions
    session1 = debug_session("simple.exe")
    session2 = debug_session("loops.exe")
    session3 = debug_session("functions.exe")

    # Verify all have unique IDs
    assert session1 != session2
    assert session2 != session3
    assert session1 != session3

    # All should be valid strings
    assert len(session1) > 0
    assert len(session2) > 0
    assert len(session3) > 0
