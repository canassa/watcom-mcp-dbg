"""
Pydantic models for MCP JSON-RPC protocol messages.

Defines request/response structures for MCP protocol communication.
"""

from typing import Optional, Any, Union
from pydantic import BaseModel, Field


# JSON-RPC Base Models

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[dict] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


# MCP Protocol Models

class ServerInfo(BaseModel):
    """MCP server information."""
    name: str
    version: str


class ClientInfo(BaseModel):
    """MCP client information."""
    name: str
    version: str


class InitializeParams(BaseModel):
    """Parameters for initialize method."""
    protocolVersion: str
    capabilities: dict
    clientInfo: ClientInfo


class InitializeResult(BaseModel):
    """Result from initialize method."""
    protocolVersion: str
    capabilities: dict
    serverInfo: ServerInfo


# Tool Models

class ToolInputSchema(BaseModel):
    """Schema for tool input parameters."""
    type: str = "object"
    properties: dict
    required: Optional[list[str]] = None


class Tool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: ToolInputSchema


class ToolsListResult(BaseModel):
    """Result from tools/list method."""
    tools: list[Tool]


class ToolCallParams(BaseModel):
    """Parameters for tools/call method."""
    name: str
    arguments: dict


class TextContent(BaseModel):
    """Text content block."""
    type: str = "text"
    text: str


class ToolCallResult(BaseModel):
    """Result from tools/call method."""
    content: list[TextContent]
    isError: bool = False


# Debugger-specific Models

class SourceLocation(BaseModel):
    """Source code location."""
    file: str
    line: int


class StopInfoModel(BaseModel):
    """Information about why debugger stopped."""
    state: str
    stopped: bool
    reason: Optional[str] = None
    address: Optional[int] = None
    thread_id: Optional[int] = None
    module_name: Optional[str] = None
    source_location: Optional[SourceLocation] = None


class BreakpointModel(BaseModel):
    """Breakpoint information."""
    breakpoint_id: str
    address: int
    enabled: bool = True
    hit_count: int = 0
    file: Optional[str] = None
    line: Optional[int] = None
    module_name: Optional[str] = None
    source_location: Optional[SourceLocation] = None


class ModuleModel(BaseModel):
    """Loaded module information."""
    name: str
    base_address: int
    path: str
    has_debug_info: bool


class RegistersModel(BaseModel):
    """CPU register state."""
    EAX: int
    EBX: int
    ECX: int
    EDX: int
    ESI: int
    EDI: int
    EBP: int
    ESP: int
    EIP: int
    EFlags: int


class SourceLine(BaseModel):
    """Single line of source code."""
    line_number: int
    content: str
    is_current: bool = False


class SourceCodeModel(BaseModel):
    """Source code with context."""
    file: str
    full_path: str
    lines: list[SourceLine]


# Tool-specific Request/Response Models

class CreateSessionRequest(BaseModel):
    """Request to create debugging session."""
    executable_path: str
    args: Optional[list[str]] = None
    source_dirs: Optional[list[str]] = None


class CreateSessionResponse(BaseModel):
    """Response from creating session."""
    session_id: str
    status: str
    process_id: Optional[int] = None


class SessionCommandRequest(BaseModel):
    """Request with session ID."""
    session_id: str


class BreakpointRequest(BaseModel):
    """Request to set breakpoint."""
    session_id: str
    location: str  # "file:line" or "0xADDRESS"


class GetSourceRequest(BaseModel):
    """Request to get source code."""
    session_id: str
    file: str
    line: int
    context_lines: int = 5
