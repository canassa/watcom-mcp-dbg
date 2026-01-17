"""
MCP (Model Context Protocol) handler for JSON-RPC message processing.

Handles the MCP protocol methods:
- initialize: Initialize the MCP server
- tools/list: List available debugging tools
- tools/call: Execute a debugging tool
"""

from typing import Any
import logging

from dgb.server.session_manager import SessionManager
from dgb.server.models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCError,
    InitializeParams, InitializeResult, ServerInfo,
    ToolsListResult, ToolCallParams, ToolCallResult, TextContent
)
from dgb.server import tools

logger = logging.getLogger(__name__)


class MCPHandler:
    """Handles MCP protocol JSON-RPC requests."""

    def __init__(self, session_manager: SessionManager):
        """Initialize handler.

        Args:
            session_manager: SessionManager for debugging sessions
        """
        self.session_manager = session_manager
        self.protocol_version = "2024-11-05"
        self.server_info = ServerInfo(
            name="dgb-mcp-server",
            version="0.1.0"
        )

    def handle_request(self, request_data: dict) -> dict:
        """Handle a JSON-RPC request.

        Args:
            request_data: Raw JSON-RPC request dict

        Returns:
            JSON-RPC response dict
        """
        try:
            request = JSONRPCRequest(**request_data)

            # Dispatch to handler based on method
            if request.method == "initialize":
                result = self._handle_initialize(request)
            elif request.method == "tools/list":
                result = self._handle_tools_list(request)
            elif request.method == "tools/call":
                result = self._handle_tools_call(request)
            else:
                # Unknown method
                response = JSONRPCResponse(
                    id=request.id,
                    error=JSONRPCError(
                        code=-32601,
                        message=f"Method not found: {request.method}"
                    )
                )
                return response.model_dump(exclude_none=True)

            # Success response
            response = JSONRPCResponse(
                id=request.id,
                result=result
            )
            return response.model_dump(exclude_none=True)

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            # Return error response
            response = JSONRPCResponse(
                id=request_data.get('id'),
                error=JSONRPCError(
                    code=-32603,
                    message="Internal error",
                    data=str(e)
                )
            )
            return response.model_dump(exclude_none=True)

    def _handle_initialize(self, request: JSONRPCRequest) -> dict:
        """Handle initialize method.

        Args:
            request: JSON-RPC request

        Returns:
            InitializeResult dict
        """
        if not request.params:
            raise ValueError("Missing initialize parameters")

        params = InitializeParams(**request.params)

        # Build capabilities
        capabilities = {
            "tools": {}
        }

        result = InitializeResult(
            protocolVersion=self.protocol_version,
            capabilities=capabilities,
            serverInfo=self.server_info
        )

        return result.model_dump()

    def _handle_tools_list(self, request: JSONRPCRequest) -> dict:
        """Handle tools/list method.

        Args:
            request: JSON-RPC request

        Returns:
            ToolsListResult dict
        """
        all_tools = tools.get_all_tools()

        result = ToolsListResult(tools=all_tools)
        return result.model_dump()

    def _handle_tools_call(self, request: JSONRPCRequest) -> dict:
        """Handle tools/call method.

        Args:
            request: JSON-RPC request

        Returns:
            ToolCallResult dict
        """
        if not request.params:
            raise ValueError("Missing tool call parameters")

        params = ToolCallParams(**request.params)

        # Call the tool
        tool_result = tools.call_tool(
            self.session_manager,
            params.name,
            params.arguments
        )

        # Check if tool execution failed
        if not tool_result.get('success', False):
            error_msg = tool_result.get('error', 'Unknown error')
            result = ToolCallResult(
                content=[TextContent(text=f"Error: {error_msg}")],
                isError=True
            )
            return result.model_dump()

        # Format successful result
        # Build a text response
        text_lines = []

        # Special formatting based on tool
        if params.name == "debugger_create_session":
            text_lines.append(f"✓ Session created: {tool_result['session_id']}")
            text_lines.append(f"Status: {tool_result['status']}")

        elif params.name == "debugger_run" or params.name == "debugger_continue" or params.name == "debugger_step":
            # Get state from top level (debugger_run returns state, stop_reason, stop_address at top level)
            state = tool_result.get('state', 'unknown')
            stop_reason = tool_result.get('stop_reason')
            stop_address = tool_result.get('stop_address')

            if state == 'stopped' or stop_reason:
                # Stopped state
                reason = stop_reason or 'breakpoint'
                text_lines.append(f"✓ Stopped: {reason}")
                if stop_address:
                    text_lines.append(f"Address: {stop_address}")
            else:
                # Running or other state
                text_lines.append(f"✓ State: {state}")

        elif params.name == "debugger_set_breakpoint":
            bp_id = tool_result.get('breakpoint_id')
            bp_status = tool_result.get('status', 'active')

            if bp_status == 'pending':
                # Pending breakpoint
                location = tool_result.get('location', '')
                message = tool_result.get('message', '')
                text_lines.append(f"✓ Breakpoint {bp_id} set (pending): {location}")
                if message:
                    text_lines.append(f"  {message}")
            else:
                # Active breakpoint
                address = tool_result.get('address')
                location = ""
                if tool_result.get('file') and tool_result.get('line'):
                    location = f" ({tool_result['file']}:{tool_result['line']})"
                text_lines.append(f"✓ Breakpoint {bp_id} set at {address}{location}")

        elif params.name == "debugger_list_breakpoints":
            breakpoints = tool_result.get('breakpoints', [])
            if not breakpoints:
                text_lines.append("No breakpoints set")
            else:
                text_lines.append(f"Breakpoints ({len(breakpoints)}):")
                for bp in breakpoints:
                    bp_id = bp['breakpoint_id']
                    bp_status = bp.get('status', 'active')

                    if bp_status == 'pending':
                        # Pending breakpoint - no address yet
                        location = bp.get('location', '')
                        text_lines.append(f"  {bp_id}: {location} - PENDING")
                    else:
                        # Active breakpoint
                        address = bp['address']
                        location = bp.get('location', '')
                        status = "enabled" if bp['enabled'] else "disabled"
                        hits = bp['hit_count']
                        text_lines.append(f"  {bp_id}: {address} {location} - {status} (hit {hits}x)")

        elif params.name == "debugger_get_registers":
            registers = tool_result.get('registers', {})
            text_lines.append("Registers:")
            for reg, value in registers.items():
                text_lines.append(f"  {reg:6s} = {value}")

        elif params.name == "debugger_list_modules":
            modules = tool_result.get('modules', [])
            text_lines.append(f"Loaded modules ({len(modules)}):")
            for mod in modules:
                debug_info = "DWARF 2" if mod['has_debug_info'] else "no debug"
                text_lines.append(f"  {mod['base_address']}  {mod['name']:30s}  ({debug_info})")

        elif params.name == "debugger_get_source":
            file = tool_result.get('file')
            lines = tool_result.get('lines', [])
            text_lines.append(f"Source: {file}")
            text_lines.append("-" * 60)
            for line_info in lines:
                marker = ">>>" if line_info.get('is_current') else "   "
                text_lines.append(f"{marker} {line_info['line_number']:4d} | {line_info['content']}")

        elif params.name == "debugger_list_variables":
            import json
            variables = tool_result.get('variables', [])
            count = tool_result.get('count', 0)

            if count == 0:
                text_lines.append("No variables in current scope")
            else:
                text_lines.append(f"Variables ({count}):")
                for var in variables:
                    name = var.get('name', '?')
                    type_name = var.get('type', '?')
                    value = var.get('value', '?')
                    location = var.get('location', '?')
                    text_lines.append(f"  {name:20s} = {value:30s} ({type_name}, {location})")

                # Include JSON for testing/programmatic access
                text_lines.append("")
                text_lines.append("JSON:")
                text_lines.append("```json")
                text_lines.append(json.dumps(tool_result, indent=2))
                text_lines.append("```")

        elif params.name == "debugger_close_session":
            text_lines.append(f"✓ {tool_result.get('message', 'Session closed')}")

        else:
            # Generic success message
            text_lines.append(f"✓ {params.name} completed successfully")

        # Join all lines
        text_response = "\n".join(text_lines)

        result = ToolCallResult(
            content=[TextContent(text=text_response)],
            isError=False
        )
        return result.model_dump()
