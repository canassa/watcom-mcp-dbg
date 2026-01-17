"""
Register tests for DGB MCP Debugger.

Tests reading CPU registers when process is stopped.
"""

import pytest
import re


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.inspection
def test_get_registers(debug_session, mcp_client):
    """Test getting CPU registers when stopped."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get registers
    result = mcp_client.call_tool("debugger_get_registers", {
        "session_id": session_id
    })

    # Verify register output contains x86 registers
    text = extract_text_from_result(result)

    # Check for common x86 registers
    assert "EIP" in text or "eip" in text.upper()

    # Should have hex values
    assert "0x" in text.lower()


@pytest.mark.inspection
def test_registers_change_after_step(debug_session, mcp_client):
    """Test that registers change after stepping."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get initial registers
    result1 = mcp_client.call_tool("debugger_get_registers", {
        "session_id": session_id
    })
    text1 = extract_text_from_result(result1)

    # Extract EIP
    match1 = re.search(r"EIP:\s*0x([0-9a-fA-F]+)", text1)
    assert match1, "Could not find EIP in register output"
    eip1 = match1.group(1)

    # Step
    mcp_client.call_tool("debugger_step", {"session_id": session_id})

    # Get registers after step
    result2 = mcp_client.call_tool("debugger_get_registers", {
        "session_id": session_id
    })
    text2 = extract_text_from_result(result2)

    # Extract EIP again
    match2 = re.search(r"EIP:\s*0x([0-9a-fA-F]+)", text2)
    assert match2, "Could not find EIP after step"
    eip2 = match2.group(1)

    # EIP should have changed
    assert eip1 != eip2, f"EIP did not change (before: {eip1}, after: {eip2})"


@pytest.mark.inspection
def test_all_registers_present(debug_session, mcp_client):
    """Test that all major x86 registers are returned."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get registers
    result = mcp_client.call_tool("debugger_get_registers", {
        "session_id": session_id
    })

    text = extract_text_from_result(result).upper()

    # Check for major x86 registers (case insensitive)
    major_registers = ["EIP", "ESP", "EBP"]

    for reg in major_registers:
        assert reg in text, f"Register {reg} not found in output"
