"""
Litestar application for MCP server.

Provides HTTP transport for Model Context Protocol via JSON-RPC 2.0.
"""

import asyncio
import logging
import os
from typing import Any

from litestar import Litestar, post, Request, Response
from litestar.config.cors import CORSConfig
from litestar.logging import LoggingConfig
from litestar.status_codes import HTTP_200_OK

from dgb.server.session_manager import SessionManager
from dgb.server.mcp_handler import MCPHandler

# Configure logging
logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["console"]},
    formatters={
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    loggers={
        "dgb": {"level": "INFO", "handlers": ["console"]},
    }
)

logger = logging.getLogger(__name__)


# Application state
class AppState:
    """Application state container."""
    session_manager: SessionManager
    mcp_handler: MCPHandler


# HTTP endpoint
@post("/mcp/v1")
async def mcp_endpoint(request: Request, data: dict[str, Any]) -> Response[dict]:
    """MCP protocol endpoint.

    Handles JSON-RPC 2.0 messages for MCP protocol.

    Args:
        request: Litestar request
        data: JSON-RPC request data

    Returns:
        JSON-RPC response
    """
    # Get handler from app state
    mcp_handler: MCPHandler = request.app.state.mcp_handler

    # CRITICAL: Run the sync handler in a thread pool to avoid blocking the async event loop
    # This prevents deadlocks when sync operations (like debugger cleanup) take time
    response_data = await asyncio.to_thread(mcp_handler.handle_request, data)

    return Response(
        content=response_data,
        status_code=HTTP_200_OK
    )


def create_app(session_timeout: float = 3600.0) -> Litestar:
    """Create and configure Litestar application.

    Args:
        session_timeout: Session timeout in seconds

    Returns:
        Configured Litestar application
    """
    # Create session manager
    session_manager = SessionManager(session_timeout=session_timeout)

    # Create MCP handler
    mcp_handler = MCPHandler(session_manager)

    # Create app state
    state = AppState()
    state.session_manager = session_manager
    state.mcp_handler = mcp_handler

    # CORS configuration (allow MCP clients from any origin)
    cors_config = CORSConfig(
        allow_origins=["*"],
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["*"]
    )

    # Create Litestar app
    app = Litestar(
        route_handlers=[mcp_endpoint],
        state=state,
        cors_config=cors_config,
        logging_config=logging_config,
        debug=False
    )

    logger.info("DGB MCP Server initialized")
    logger.info(f"Session timeout: {session_timeout}s")

    return app


# Module-level app instance for Uvicorn reload mode
# Gets session timeout from environment variable if set
_session_timeout = float(os.environ.get('DGB_SESSION_TIMEOUT', '3600.0'))
app = create_app(session_timeout=_session_timeout)
