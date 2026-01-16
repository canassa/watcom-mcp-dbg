"""
Thread-safe wrapper for Debugger class.

Handles running the Win32 Debug API event loop in a background thread
and provides thread-safe communication mechanisms for async HTTP handlers.
"""

import threading
import queue
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass

from dgb.debugger.core import Debugger
from dgb.debugger.state import StopInfo


class CommandType(Enum):
    """Commands that can be sent to the debugger thread."""
    START = "start"
    CONTINUE = "continue"
    STEP = "step"
    SET_BREAKPOINT = "set_breakpoint"
    STOP = "stop"


@dataclass
class Command:
    """Command to send to debugger thread."""
    type: CommandType
    args: dict = None

    def __post_init__(self):
        if self.args is None:
            self.args = {}


@dataclass
class CommandResult:
    """Result from a command execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None


class DebuggerWrapper:
    """Thread-safe wrapper around Debugger.

    Runs the debugger event loop in a background thread and provides
    thread-safe methods for controlling the debugger from async HTTP handlers.
    """

    def __init__(self, debugger: Debugger):
        """Initialize wrapper.

        Args:
            debugger: Debugger instance to wrap
        """
        self.debugger = debugger
        self.command_queue: queue.Queue[Command] = queue.Queue()
        self.result_queue: queue.Queue[CommandResult] = queue.Queue()
        self.state_lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start_in_background(self) -> CommandResult:
        """Start the debugger and begin event loop in background thread.

        CRITICAL FIX: Moves debugger.start() into the background thread to satisfy
        Windows Debug API requirement that CreateProcess and WaitForDebugEvent
        must be called by the same thread.

        Returns:
            CommandResult with success status
        """
        if self.running:
            return CommandResult(success=False, error="Already running")

        # CRITICAL FIX: Use event for startup synchronization
        import threading
        startup_complete = threading.Event()
        startup_result = {'success': False, 'error': None, 'data': None}

        def startup_wrapper():
            """Wrapper that starts the process on the background thread."""
            try:
                # CRITICAL: Start the debugger process ON THIS THREAD
                from dgb.debugger.exceptions import (
                    ProcessCreationError, InvalidHandleError, DebuggerError
                )
                self.debugger.start()
                startup_result['success'] = True
                startup_result['data'] = {
                    'process_id': self.debugger.context.process_id,
                    'state': self.debugger.context.state.value
                }
            except (ProcessCreationError, InvalidHandleError, DebuggerError) as e:
                startup_result['error'] = f'{type(e).__name__}: {e}'
            except Exception as e:
                startup_result['error'] = f'Unexpected error: {e}'
            finally:
                startup_complete.set()

            # If startup succeeded, continue with event loop worker
            if startup_result['success']:
                self._event_loop_worker()

        # Start background thread (it will call start() internally)
        self.running = True
        self.thread = threading.Thread(target=startup_wrapper, daemon=True)
        self.thread.start()

        # Wait for startup to complete
        if not startup_complete.wait(timeout=5.0):
            self.running = False
            return CommandResult(success=False, error="Timeout waiting for process creation")

        # Check startup result
        if not startup_result['success']:
            self.running = False
            return CommandResult(success=False, error=startup_result['error'])

        return CommandResult(success=True, data=startup_result['data'])

    def _event_loop_worker(self):
        """Background thread worker that runs the debugger event loop.

        This thread:
        1. Checks for commands from the command queue
        2. Executes commands
        3. Runs the debugger event loop when process is running
        """
        while self.running:
            # Check for commands (non-blocking)
            try:
                cmd = self.command_queue.get(timeout=0.1)
                result = self._execute_command(cmd)
                self.result_queue.put(result)
            except queue.Empty:
                pass

            # Process debug events if the debugger is active
            # The event loop will poll with timeout, so this won't block forever
            if self.debugger.waiting_for_event:
                # Event loop will process events until stopped or quit
                # It has internal timeout, so this is safe to call
                pass  # Event loop is managed by commands

    def _execute_command(self, cmd: Command) -> CommandResult:
        """Execute a command on the debugger.

        Args:
            cmd: Command to execute

        Returns:
            CommandResult with execution result
        """
        try:
            with self.state_lock:
                if cmd.type == CommandType.CONTINUE:
                    self.debugger.continue_execution()
                    stop_info = self._get_stop_info()
                    return CommandResult(success=True, data=stop_info)

                elif cmd.type == CommandType.STEP:
                    self.debugger.step_over()
                    stop_info = self._get_stop_info()
                    return CommandResult(success=True, data=stop_info)

                elif cmd.type == CommandType.SET_BREAKPOINT:
                    location = cmd.args.get('location')
                    if not location:
                        return CommandResult(success=False, error="No location provided")

                    success = self.debugger.set_breakpoint(location)
                    if success:
                        # Get breakpoint info
                        bp_list = self.debugger.breakpoint_manager.get_all_breakpoints()
                        if bp_list:
                            last_bp = bp_list[-1]
                            return CommandResult(
                                success=True,
                                data={
                                    'breakpoint_id': last_bp.id,
                                    'address': last_bp.address,
                                    'file': last_bp.file,
                                    'line': last_bp.line,
                                    'module_name': last_bp.module_name
                                }
                            )
                    return CommandResult(success=False, error="Failed to set breakpoint")

                elif cmd.type == CommandType.STOP:
                    self.debugger.stop()
                    self.running = False
                    return CommandResult(success=True)

                else:
                    return CommandResult(success=False, error=f"Unknown command: {cmd.type}")

        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def _get_stop_info(self) -> dict:
        """Get current stop information as a dictionary.

        Returns:
            Dictionary with stop info
        """
        if not self.debugger.context.stop_info:
            return {
                'state': self.debugger.context.state.value,
                'stopped': False
            }

        stop_info = self.debugger.context.stop_info

        # Try to resolve source location
        source_location = None
        if stop_info.address:
            result = self.debugger.module_manager.resolve_address_to_line(stop_info.address)
            if result:
                source_location = {
                    'file': result[0],
                    'line': result[1]
                }

        return {
            'state': self.debugger.context.state.value,
            'stopped': True,
            'reason': stop_info.reason,
            'address': stop_info.address,
            'thread_id': stop_info.thread_id,
            'module_name': stop_info.module_name,
            'source_location': source_location
        }

    def send_command(self, cmd: Command, timeout: float = 30.0) -> CommandResult:
        """Send a command to the debugger thread and wait for result.

        Args:
            cmd: Command to send
            timeout: Timeout in seconds

        Returns:
            CommandResult from command execution
        """
        if not self.running and cmd.type != CommandType.STOP:
            return CommandResult(success=False, error="Debugger not running")

        # Clear result queue
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

        # Send command
        self.command_queue.put(cmd)

        # Wait for result
        try:
            result = self.result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            return CommandResult(success=False, error="Command timeout")

    def get_state(self) -> dict:
        """Get current debugger state (thread-safe).

        Returns:
            Dictionary with current state
        """
        with self.state_lock:
            return self._get_stop_info()

    def stop(self):
        """Stop the debugger and clean up."""
        if self.running:
            self.send_command(Command(type=CommandType.STOP), timeout=5.0)
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            self.running = False
