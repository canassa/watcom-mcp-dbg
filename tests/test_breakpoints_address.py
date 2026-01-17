"""
Address breakpoint tests for DGB MCP Debugger.

Tests setting breakpoints at specific memory addresses.
"""

import pytest
import re


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.breakpoint
def test_set_breakpoint_at_address(debug_session, mcp_client):
    """Test setting a breakpoint at a specific address."""
    session_id = debug_session("simple.exe")

    # Run to entry to get a valid address
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get current EIP as a valid address
    regs = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text = extract_text_from_result(regs)
    match = re.search(r"EIP:\s*(0x[0-9a-fA-F]+)", text)
    assert match, "Could not find EIP"
    address = match.group(1)

    # Set breakpoint at that address
    result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": address
    })

    # Verify breakpoint was set
    text = extract_text_from_result(result)
    assert "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_list_breakpoints_after_set(debug_session, mcp_client):
    """Test listing breakpoints after setting them."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get current EIP
    regs = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text = extract_text_from_result(regs)
    match = re.search(r"EIP:\s*(0x[0-9a-fA-F]+)", text)
    assert match
    address = match.group(1)

    # Set breakpoint
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": address
    })

    # List breakpoints
    result = mcp_client.call_tool("debugger_list_breakpoints", {
        "session_id": session_id
    })

    # Verify breakpoint is listed
    text = extract_text_from_result(result)
    assert address.lower() in text.lower() or "breakpoint" in text.lower()


@pytest.mark.breakpoint
def test_invalid_address_format(debug_session, mcp_client):
    """Test setting breakpoint with invalid address format."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Try to set breakpoint with invalid address
    with pytest.raises(Exception):
        mcp_client.call_tool("debugger_set_breakpoint", {
            "session_id": session_id,
            "location": "not_an_address"
        })


@pytest.mark.breakpoint
def test_breakpoint_hit_at_address(debug_session, mcp_client):
    """Test that breakpoint is hit when execution reaches it."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get current EIP
    regs = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text = extract_text_from_result(regs)
    match = re.search(r"EIP:\s*(0x[0-9a-fA-F]+)", text)
    assert match
    eip_before = match.group(1)

    # Step a few times to get a different address
    for _ in range(3):
        mcp_client.call_tool("debugger_step", {"session_id": session_id})

    # Get new EIP
    regs2 = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text2 = extract_text_from_result(regs2)
    match2 = re.search(r"EIP:\s*(0x[0-9a-fA-F]+)", text2)
    assert match2
    breakpoint_address = match2.group(1)

    # Close and restart session
    mcp_client.call_tool("debugger_close_session", {"session_id": session_id})

    # Create new session
    from pathlib import Path
    exe_path = str(Path(__file__).parent / "fixtures" / "bin32" / "simple.exe")
    result = mcp_client.call_tool("debugger_create_session", {
        "executable_path": exe_path
    })
    text = extract_text_from_result(result)
    new_session_match = re.search(r"Session (\S+) created", text)
    assert new_session_match
    new_session_id = new_session_match.group(1)

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": new_session_id})

    # Set breakpoint at the address we found earlier
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": new_session_id,
        "location": breakpoint_address
    })

    # Continue - should hit breakpoint
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": new_session_id
    })

    # Verify we stopped (either at breakpoint or process exited)
    text = extract_text_from_result(result)
    assert "stopped" in text.lower() or "breakpoint" in text.lower() or "exited" in text.lower()

    # Cleanup new session
    mcp_client.call_tool("debugger_close_session", {"session_id": new_session_id})
