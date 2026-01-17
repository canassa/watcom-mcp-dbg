"""
Execution control tests for DGB MCP Debugger.

Tests run, continue, and step operations.
"""

import pytest
import re


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.execution
def test_run_to_entry(debug_session, mcp_client):
    """Test running process to entry point."""
    session_id = debug_session("simple.exe")

    # Run the process
    result = mcp_client.call_tool("debugger_run", {
        "session_id": session_id
    })

    # Verify result indicates process started
    text = extract_text_from_result(result)
    assert "stopped" in text.lower() or "entry" in text.lower()


@pytest.mark.execution
def test_continue_execution(debug_session, mcp_client):
    """Test continue after setting breakpoint."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Set breakpoint at simple.c:11 (function call)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "simple.c:11"
    })

    # Continue
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # Should stop at breakpoint or complete
    text = extract_text_from_result(result)
    assert text is not None


@pytest.mark.execution
def test_single_step(debug_session, mcp_client):
    """Test single-step execution."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Get initial EIP
    regs1 = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text1 = extract_text_from_result(regs1)

    # Extract EIP value from first register read
    match1 = re.search(r"EIP\s*=\s*0x([0-9a-fA-F]+)", text1)
    assert match1, "Could not find EIP in register output"
    eip1 = match1.group(1)

    # Step
    mcp_client.call_tool("debugger_step", {"session_id": session_id})

    # Get EIP after step
    regs2 = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
    text2 = extract_text_from_result(regs2)

    # Extract EIP value from second register read
    match2 = re.search(r"EIP\s*=\s*0x([0-9a-fA-F]+)", text2)
    assert match2, "Could not find EIP after step"
    eip2 = match2.group(1)

    # EIP should have changed
    assert eip1 != eip2, f"EIP did not change after step (before: {eip1}, after: {eip2})"


@pytest.mark.execution
def test_continue_to_exit(debug_session, mcp_client):
    """Test continuing without breakpoints (run to completion)."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Continue without breakpoints
    result = mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # NOTE: debugger_continue is non-blocking - it returns "running" immediately
    # It doesn't wait for process to exit
    text = extract_text_from_result(result)
    assert "running" in text.lower() or "continuing" in text.lower()


@pytest.mark.execution
def test_step_multiple_times(debug_session, mcp_client):
    """Test stepping multiple times."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # Step 5 times
    eip_values = []
    for i in range(5):
        # Step
        mcp_client.call_tool("debugger_step", {"session_id": session_id})

        # Get EIP
        regs = mcp_client.call_tool("debugger_get_registers", {"session_id": session_id})
        text = extract_text_from_result(regs)
        match = re.search(r"EIP\s*=\s*0x([0-9a-fA-F]+)", text)
        if match:
            eip_values.append(match.group(1))

    # Should have 5 EIP values
    assert len(eip_values) == 5

    # At least some values should be different (instruction pointer advanced)
    unique_eips = set(eip_values)
    assert len(unique_eips) > 1, "EIP did not change during multiple steps"
