"""
Debugger state management.

Tracks the current state of the debugger and provides shared state across modules.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DebuggerState(Enum):
    """Debugger execution states."""

    NOT_STARTED = "not_started"  # Process not yet created
    RUNNING = "running"  # Process is executing
    STOPPED = "stopped"  # Process stopped at breakpoint or exception
    STEP = "step"  # Single-stepping
    EXITED = "exited"  # Process has terminated


@dataclass
class StopInfo:
    """Information about why the debugger stopped."""

    reason: str  # "breakpoint", "exception", "step", "entry", "exit"
    address: Optional[int] = None
    exception_code: Optional[int] = None
    exception_address: Optional[int] = None
    thread_id: Optional[int] = None
    module_name: Optional[str] = None


class DebuggerContext:
    """Shared debugger context and state.

    This class holds the current state of the debugger including:
    - Execution state (running, stopped, etc.)
    - Current thread and address
    - Stop reason
    - Debuggee process information
    """

    def __init__(self):
        self.state = DebuggerState.NOT_STARTED
        self.stop_info: Optional[StopInfo] = None

        # Current execution context
        self.current_thread_id: Optional[int] = None
        self.current_address: Optional[int] = None

        # Process information
        self.process_id: Optional[int] = None
        self.process_handle: Optional[int] = None
        self.main_thread_id: Optional[int] = None

        # Control flags
        self.should_quit = False
        self.step_mode = False  # True when single-stepping

    def set_running(self):
        """Set state to running."""
        self.state = DebuggerState.RUNNING
        self.stop_info = None

    def set_stopped(self, stop_info: StopInfo):
        """Set state to stopped with reason."""
        self.state = DebuggerState.STOPPED
        self.stop_info = stop_info
        if stop_info.address:
            self.current_address = stop_info.address
        if stop_info.thread_id:
            self.current_thread_id = stop_info.thread_id

    def set_step_mode(self, enabled: bool):
        """Enable or disable single-step mode."""
        self.step_mode = enabled
        if enabled:
            self.state = DebuggerState.STEP

    def set_exited(self, exit_code: int):
        """Set state to exited."""
        self.state = DebuggerState.EXITED
        self.stop_info = StopInfo(
            reason="exit",
            exception_code=exit_code
        )

    def is_running(self) -> bool:
        """Check if process is currently running."""
        return self.state == DebuggerState.RUNNING

    def is_stopped(self) -> bool:
        """Check if process is stopped."""
        return self.state == DebuggerState.STOPPED

    def is_exited(self) -> bool:
        """Check if process has exited."""
        return self.state == DebuggerState.EXITED

    def get_stop_reason(self) -> Optional[str]:
        """Get the reason why the debugger stopped."""
        if self.stop_info:
            return self.stop_info.reason
        return None
