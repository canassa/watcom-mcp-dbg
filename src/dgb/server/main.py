"""
DGB MCP Server entry point.

Starts the MCP server with Uvicorn.
"""

import argparse
import logging
import sys
import signal

import uvicorn

from dgb.server.app import create_app

logger = logging.getLogger(__name__)


def main():
    """Main entry point for dgb-server."""
    parser = argparse.ArgumentParser(
        description="DGB MCP Server - Debug Windows PE with Watcom DWARF 2 via MCP"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--session-timeout",
        type=float,
        default=3600.0,
        help="Session timeout in seconds (default: 3600)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (development mode)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Start server
    logger.info(f"Starting DGB MCP Server on {args.host}:{args.port}")
    if args.reload:
        logger.info("Auto-reload enabled (development mode)")
    logger.info("Press Ctrl+C to stop")

    if args.reload:
        # In reload mode, pass app as import string
        # Store session_timeout in env var for app factory
        import os
        os.environ['DGB_SESSION_TIMEOUT'] = str(args.session_timeout)

        uvicorn.run(
            "dgb.server.app:app",
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            reload=True
        )
    else:
        # In normal mode, create app directly and handle shutdown
        app = create_app(session_timeout=args.session_timeout)

        def signal_handler(sig, frame):
            logger.info("Shutting down...")
            # Close all sessions
            app.state.session_manager.close_all_sessions()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower()
        )


if __name__ == "__main__":
    main()
