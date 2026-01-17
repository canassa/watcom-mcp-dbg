"""
Session management for debugger instances.

Each debugging session has a unique ID and manages its own debugger instance
running in a background thread.
"""

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

from dgb.debugger.core import Debugger
from dgb.server.source_resolver import SourceResolver


@dataclass
class DebuggerSession:
    """Represents a debugging session with its own debugger instance."""

    session_id: str
    debugger: Debugger
    source_resolver: SourceResolver
    event_thread: Optional[threading.Thread] = None
    debugger_wrapper: Optional[Any] = None  # DebuggerWrapper instance (avoid circular import)
    lock: threading.Lock = None
    created_at: float = 0.0
    last_accessed: float = 0.0
    is_running: bool = False

    def __post_init__(self):
        if self.lock is None:
            self.lock = threading.Lock()
        if self.created_at == 0.0:
            self.created_at = time.time()
        self.last_accessed = time.time()

    def touch(self):
        """Update last accessed time."""
        self.last_accessed = time.time()

    def cleanup(self):
        """Clean up session resources."""
        try:
            if self.debugger:
                self.debugger.stop()
            if self.event_thread and self.event_thread.is_alive():
                print(f"[Session.cleanup] Waiting for event thread to exit...", flush=True)
                self.event_thread.join(timeout=5.0)
                if self.event_thread.is_alive():
                    print(f"[Session.cleanup] WARNING: Event thread did not exit after 5 seconds!", flush=True)
                else:
                    print(f"[Session.cleanup] Event thread exited cleanly", flush=True)
        except Exception as e:
            print(f"[Session.cleanup] Error during cleanup: {e}", flush=True)


class SessionManager:
    """Manages all active debugging sessions.

    Provides:
    - Session creation and retrieval
    - Session timeout management
    - Thread-safe access to sessions
    """

    def __init__(self, session_timeout: float = 3600.0):
        """Initialize session manager.

        Args:
            session_timeout: Session timeout in seconds (default 1 hour)
        """
        self.sessions: Dict[str, DebuggerSession] = {}
        self.lock = threading.Lock()
        self.session_timeout = session_timeout

    def create_session(self, executable_path: str, args: Optional[list[str]] = None,
                      source_dirs: Optional[list[str]] = None) -> DebuggerSession:
        """Create a new debugging session.

        Args:
            executable_path: Path to executable to debug
            args: Command-line arguments for the executable
            source_dirs: Additional source directories to search

        Returns:
            New DebuggerSession instance

        Raises:
            FileNotFoundError: If executable doesn't exist
        """
        # Validate executable exists
        if not Path(executable_path).exists():
            raise FileNotFoundError(f"Executable not found: {executable_path}")

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Create debugger instance
        debugger = Debugger(executable_path)

        # Create source resolver
        source_resolver = SourceResolver()
        if source_dirs:
            for src_dir in source_dirs:
                source_resolver.add_source_directory(src_dir)

        # Create session
        session = DebuggerSession(
            session_id=session_id,
            debugger=debugger,
            source_resolver=source_resolver
        )

        # Store session
        with self.lock:
            self.sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[DebuggerSession]:
        """Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            DebuggerSession if found, None otherwise
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.touch()
            return session

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was found and closed, False otherwise
        """
        with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.cleanup()
                return True
            return False

    def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded the timeout."""
        current_time = time.time()
        expired_sessions = []

        with self.lock:
            for session_id, session in self.sessions.items():
                if current_time - session.last_accessed > self.session_timeout:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                session = self.sessions.pop(session_id)
                session.cleanup()

        return len(expired_sessions)

    def close_all_sessions(self):
        """Close all active sessions."""
        with self.lock:
            for session in self.sessions.values():
                session.cleanup()
            self.sessions.clear()

    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        with self.lock:
            return len(self.sessions)

    def get_all_session_ids(self) -> list[str]:
        """Get all active session IDs."""
        with self.lock:
            return list(self.sessions.keys())
