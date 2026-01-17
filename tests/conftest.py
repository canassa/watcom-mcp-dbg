"""
Pytest fixtures for DGB MCP Debugger black box testing.
Provides infrastructure for server lifecycle, MCP client, session management, and cleanup.
"""

import subprocess
import time
import requests
import psutil
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable


# Constants
MCP_SERVER_PORT = 8765
MCP_SERVER_URL = f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp/v1"
TEST_EXECUTABLES = [
    "variables.exe",
    "simple.exe",
    "loops.exe",
    "functions.exe",
    "multi_bp.exe",
    "crash.exe",
    "testdll.dll",
    "testdll_user.exe"
]


class MCPClient:
    """
    MCP JSON-RPC 2.0 client for making requests to the debugger server.
    """

    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url
        self.request_id = 0
        self.session = requests.Session()

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool via tools/call method.

        Args:
            name: Tool name (e.g., "debugger_create_session")
            arguments: Tool arguments as dict

        Returns:
            Tool result content

        Raises:
            Exception if JSON-RPC error occurs
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            },
            "id": self._next_id()
        }

        response = self.session.post(
            self.base_url,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()

        # Check for JSON-RPC error
        if "error" in result:
            error = result["error"]
            raise Exception(f"MCP Error: {error.get('message', 'Unknown error')} (code: {error.get('code', 'N/A')})")

        # Return the result content
        return result.get("result", {})

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available MCP tools.

        Returns:
            List of tool definitions
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._next_id()
        }

        response = self.session.post(
            self.base_url,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            error = result["error"]
            raise Exception(f"MCP Error: {error.get('message', 'Unknown error')}")

        return result.get("result", {}).get("tools", [])

    def initialize(self) -> Dict[str, Any]:
        """
        Send initialize request to MCP server.

        Returns:
            Server capabilities
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "dgb-test-client",
                    "version": "1.0.0"
                }
            },
            "id": self._next_id()
        }

        response = self.session.post(
            self.base_url,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            error = result["error"]
            raise Exception(f"MCP Error: {error.get('message', 'Unknown error')}")

        return result.get("result", {})


@pytest.fixture(scope="session")
def compiled_test_programs():
    """
    Verify that all test programs have been compiled.

    Returns:
        Path to bin32 directory containing compiled executables.

    Raises:
        FileNotFoundError if binaries are missing.
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    bin_dir = fixtures_dir / "bin32"

    # Check if all executables exist
    missing = []
    for exe_name in TEST_EXECUTABLES:
        exe_path = bin_dir / exe_name
        if not exe_path.exists():
            missing.append(exe_name)

    if missing:
        # Try to compile
        compile_script = fixtures_dir / "compile.sh"
        if compile_script.exists():
            print(f"\nMissing executables: {', '.join(missing)}")
            print("Attempting to compile test programs...")
            result = subprocess.run(
                ["bash", str(compile_script)],
                cwd=str(fixtures_dir),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to compile test programs:\n{result.stderr}")
        else:
            raise FileNotFoundError(
                f"Missing compiled executables: {', '.join(missing)}\n"
                f"Expected in: {bin_dir}"
            )

    return bin_dir


@pytest.fixture(scope="session")
def mcp_server(compiled_test_programs):
    """
    Start MCP server for the entire test session.

    Yields:
        Server process

    Cleanup:
        Kills server and all child processes.
    """
    # Start server using uv run
    # Use DEVNULL to avoid creating pipe file handles that need cleanup
    server_process = subprocess.Popen(
        ["uv", "run", "dgb-server", "--port", str(MCP_SERVER_PORT), "--log-level", "DEBUG"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent.parent  # Project root
    )

    # Wait for server to be ready
    server_ready = False
    start_time = time.time()
    timeout = 10

    while time.time() - start_time < timeout:
        try:
            # Try to connect to the MCP endpoint with a simple request
            response = requests.post(
                f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp/v1",
                json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
                timeout=1
            )
            if response.status_code in [200, 400, 500]:  # Any response means server is running
                server_ready = True
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(0.1)

    if not server_ready:
        # Kill the process and raise error
        try:
            parent = psutil.Process(server_process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except:
            pass
        raise RuntimeError("MCP server failed to start within 10 seconds")

    print(f"\nMCP server started on port {MCP_SERVER_PORT}")

    yield server_process

    # Cleanup: Kill server and all child processes
    try:
        parent = psutil.Process(server_process.pid)
        children = parent.children(recursive=True)

        # Kill all children first (debugged processes)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass

        # Kill parent
        parent.kill()
        parent.wait(timeout=5)

        # Wait for the Popen object to recognize the process is dead
        # This prevents "subprocess still running" warnings
        server_process.wait(timeout=2)
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(f"\nWarning: Error during server cleanup: {e}")


@pytest.fixture
def mcp_client(mcp_server):
    """
    Provides an MCP client for making requests to the server.

    Args:
        mcp_server: The running MCP server fixture

    Returns:
        MCPClient instance
    """
    return MCPClient()


@pytest.fixture
def debug_session(mcp_client, compiled_test_programs):
    """
    Factory fixture for creating debugging sessions.

    Returns a function that creates sessions and tracks them for cleanup.

    Usage:
        session_id = debug_session("simple.exe")
        session_id = debug_session("loops.exe", source_dirs=["custom/dir"])
    """
    created_sessions = []

    def create_session(executable_name: str, source_dirs: Optional[List[str]] = None) -> str:
        """
        Create a debugging session.

        Args:
            executable_name: Name of executable (e.g., "simple.exe")
            source_dirs: Optional list of source directories to search

        Returns:
            session_id
        """
        # Build full path to executable
        exe_path = str(compiled_test_programs / executable_name)

        # Prepare arguments
        args = {
            "executable_path": exe_path
        }
        if source_dirs:
            args["source_dirs"] = source_dirs

        # Call debugger_create_session tool
        result = mcp_client.call_tool("debugger_create_session", args)

        # Extract session_id from result
        content = result.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            # Parse session_id from text (format: "Session created: <id>" or "Session <id> created")
            import re
            match = re.search(r"Session created:\s+(\S+)", text)
            if not match:
                match = re.search(r"Session (\S+) created", text)
            if match:
                session_id = match.group(1)
                created_sessions.append(session_id)
                return session_id

        raise Exception(f"Failed to create session: {result}")

    yield create_session

    # Cleanup: Close all sessions
    for session_id in created_sessions:
        try:
            mcp_client.call_tool("debugger_close_session", {"session_id": session_id})
        except Exception as e:
            print(f"\nWarning: Failed to close session {session_id}: {e}")


@pytest.fixture(autouse=True)
def kill_stray_processes():
    """
    Automatically runs after every test to kill any stray test executables.

    This prevents process leaks between tests.
    """
    yield  # Run test first

    # Kill any stray processes after test completes
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] in TEST_EXECUTABLES:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
