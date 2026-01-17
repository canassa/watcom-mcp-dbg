"""
Server lifecycle tests for DGB MCP Debugger.

Tests basic server functionality, initialization, and tool listing.
"""

import pytest


@pytest.mark.server
def test_server_starts(mcp_server):
    """Verify server fixture starts successfully."""
    assert mcp_server is not None
    assert mcp_server.poll() is None  # Process still running


@pytest.mark.server
def test_initialize_protocol(mcp_client):
    """Test MCP initialize handshake."""
    result = mcp_client.initialize()

    # Verify response structure
    assert "protocolVersion" in result
    assert "serverInfo" in result
    assert "capabilities" in result

    # Verify server info
    server_info = result["serverInfo"]
    assert "name" in server_info
    assert "version" in server_info


@pytest.mark.server
def test_list_tools(mcp_client):
    """Test that all 10 debugger tools are available."""
    tools = mcp_client.list_tools()

    # Extract tool names
    tool_names = [tool["name"] for tool in tools]

    # Expected tools
    expected_tools = [
        "debugger_create_session",
        "debugger_run",
        "debugger_continue",
        "debugger_step",
        "debugger_set_breakpoint",
        "debugger_list_breakpoints",
        "debugger_get_registers",
        "debugger_list_modules",
        "debugger_get_source",
        "debugger_close_session"
    ]

    # Verify all expected tools are present
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Tool '{expected_tool}' not found in tool list"

    # Verify each tool has required fields
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
