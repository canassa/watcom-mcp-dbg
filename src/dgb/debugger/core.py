"""
Core debugger implementation with Win32 Debug API event loop.

Orchestrates all debugging components and handles Win32 debug events.
"""

from pathlib import Path
from typing import Optional

from dgb.debugger import win32api
from dgb.debugger.state import DebuggerContext, StopInfo
from dgb.debugger.process_controller import ProcessController
from dgb.debugger.module_manager import ModuleManager
from dgb.debugger.breakpoint_manager import BreakpointManager


class Debugger:
    """Main debugger class.

    Handles:
    - Process creation and event loop
    - Debug event dispatching
    - Module loading
    - Breakpoint handling
    - Coordination between all components
    """

    def __init__(self, executable_path: str):
        self.executable_path = Path(executable_path)
        if not self.executable_path.exists():
            raise FileNotFoundError(f"Executable not found: {executable_path}")

        # Components
        self.context = DebuggerContext()
        self.process_controller = ProcessController()
        self.module_manager = ModuleManager()
        self.breakpoint_manager = None  # Created after process starts

        # Process/thread info
        self.process_handle: Optional[int] = None
        self.main_thread_handle: Optional[int] = None

        # Event loop control
        self.continue_status = win32api.DBG_CONTINUE
        self.last_breakpoint_address: Optional[int] = None
        self.waiting_for_event = False
        self.initial_breakpoint_hit = False  # Track if we've hit the initial system breakpoint

        # Callback for initial breakpoint notification
        self.initial_breakpoint_callback = None

    def start(self):
        """Start the debugger and create the process.

        Raises:
            ProcessCreationError: If process creation fails
            InvalidHandleError: If returned handles are invalid
            FileNotFoundError: If executable doesn't exist
        """
        print(f"Starting process: {self.executable_path}")

        # Create process with DEBUG_PROCESS flag
        # This will raise proper exceptions if it fails
        self.process_handle, self.main_thread_handle, process_id, thread_id = \
            win32api.create_process_for_debug(str(self.executable_path))

        print(f"Process created: PID={process_id}, process_handle={self.process_handle}, thread_handle={self.main_thread_handle}")

        # Set up process controller
        self.process_controller.set_process(self.process_handle, process_id)
        self.process_controller.add_thread(thread_id, self.main_thread_handle)

        self.context.process_id = process_id
        self.context.main_thread_id = thread_id
        self.context.current_thread_id = thread_id

        # Create breakpoint manager
        self.breakpoint_manager = BreakpointManager(
            self.process_controller,
            self.module_manager
        )

        print(f"Process created successfully: PID={process_id}, handles valid")

    def run_event_loop(self):
        """Run the debug event loop until process exits."""
        import time
        self.waiting_for_event = True
        loop_start = time.time()
        iteration_count = 0
        pending_continue = None  # Stores (process_id, thread_id, status) when we need to continue

        print(f"[EventLoop] Starting event loop, PID={self.context.process_id}", flush=True)

        # Loop until explicitly told to quit or process exits
        while not self.context.should_quit and not self.context.is_exited():
            # If we have a pending continue and we're ready to resume
            if pending_continue and self.waiting_for_event:
                process_id, thread_id, status = pending_continue
                print(f"[EventLoop] Resuming - calling ContinueDebugEvent", flush=True)
                win32api.continue_debug_event(process_id, thread_id, status)
                pending_continue = None

            # If stopped and not ready to resume, call pending continue and exit the event loop
            # The caller (continue_execution, step_over, etc.) will call run_event_loop() again when ready
            if self.context.is_stopped() and not self.waiting_for_event:
                # CRITICAL: Must call ContinueDebugEvent before exiting, otherwise the process
                # remains paused at Win32 API level and subsequent WaitForDebugEvent will hang
                if pending_continue:
                    process_id, thread_id, status = pending_continue
                    print(f"[EventLoop] Calling ContinueDebugEvent before exit (process stopped)", flush=True)
                    win32api.continue_debug_event(process_id, thread_id, status)
                    pending_continue = None
                print(f"[EventLoop] Exiting event loop - process stopped", flush=True)
                break

            iteration_count += 1

            # Log every 1000 iterations to monitor health
            if iteration_count % 1000 == 0:
                elapsed = time.time() - loop_start
                rate = iteration_count / elapsed
                print(f"[EventLoop] {iteration_count} iterations in {elapsed:.2f}s ({rate:.0f}/sec)", flush=True)

            # Wait for debug event
            event = win32api.wait_for_debug_event(timeout_ms=100)

            if not event:
                # Timeout - no event available (normal when process is running)
                continue

            print(f"[EventLoop] Got event: code={event.dwDebugEventCode}", flush=True)

            # Process the event
            self._dispatch_event(event)

            # If stopped at a breakpoint, save the continue for later
            if self.context.is_stopped():
                print(f"[EventLoop] Process stopped - delaying ContinueDebugEvent until resumed", flush=True)
                pending_continue = (event.dwProcessId, event.dwThreadId, self.continue_status)
                self.waiting_for_event = False
            else:
                # Not stopped - continue immediately
                win32api.continue_debug_event(
                    event.dwProcessId,
                    event.dwThreadId,
                    self.continue_status
                )

            # Reset continue status
            self.continue_status = win32api.DBG_CONTINUE

        print(f"[EventLoop] Event loop finished, total iterations={iteration_count}", flush=True)

    def _dispatch_event(self, event):
        """Dispatch a debug event to the appropriate handler.

        Args:
            event: DEBUG_EVENT structure
        """
        event_code = event.dwDebugEventCode

        if event_code == win32api.CREATE_PROCESS_DEBUG_EVENT:
            self._on_create_process(event)
        elif event_code == win32api.CREATE_THREAD_DEBUG_EVENT:
            self._on_create_thread(event)
        elif event_code == win32api.LOAD_DLL_DEBUG_EVENT:
            self._on_load_dll(event)
        elif event_code == win32api.EXIT_PROCESS_DEBUG_EVENT:
            self._on_exit_process(event)
        elif event_code == win32api.EXCEPTION_DEBUG_EVENT:
            self._on_exception(event)
        elif event_code == win32api.EXIT_THREAD_DEBUG_EVENT:
            pass  # Ignore for now
        elif event_code == win32api.OUTPUT_DEBUG_STRING_EVENT:
            pass  # Ignore for now

    def _on_create_process(self, event):
        """Handle CREATE_PROCESS_DEBUG_EVENT.

        Args:
            event: DEBUG_EVENT structure
        """
        info = event.u.CreateProcessInfo
        base_address = info.lpBaseOfImage

        # Get module filename
        filename = win32api.get_module_filename(self.process_handle, base_address)
        if filename:
            module_name = Path(filename).name
            module_path = filename
        else:
            module_name = self.executable_path.name
            module_path = str(self.executable_path)

        print(f"Main module loaded: {module_name} at 0x{base_address:08x}")

        # Load main module
        self.module_manager.on_module_loaded(
            name=module_name,
            base_address=base_address,
            path=module_path,
            size=0  # We don't have size info from this event
        )

        # Don't stop here - let the process continue to load DLLs
        # We'll stop at the system breakpoint (first EXCEPTION_BREAKPOINT)
        self.context.current_address = base_address

    def _on_create_thread(self, event):
        """Handle CREATE_THREAD_DEBUG_EVENT.

        Args:
            event: DEBUG_EVENT structure
        """
        info = event.u.CreateThread
        thread_id = event.dwThreadId
        thread_handle = info.hThread

        # Add thread to controller
        self.process_controller.add_thread(thread_id, thread_handle)

    def _on_load_dll(self, event):
        """Handle LOAD_DLL_DEBUG_EVENT.

        This is CRITICAL for debugging DLLs like smackw32.dll!

        Args:
            event: DEBUG_EVENT structure
        """
        info = event.u.LoadDll
        base_address = info.lpBaseOfDll

        # Try to get DLL filename from file handle first
        filename = None
        if info.hFile:
            filename = win32api.get_filename_from_handle(info.hFile)
            # Close the file handle - it's our responsibility per Win32 API docs
            win32api.close_handle(info.hFile)

        # Fallback to GetModuleFileNameEx if file handle method failed
        if not filename:
            filename = win32api.get_module_filename(self.process_handle, base_address)

        if filename:
            module_name = Path(filename).name
            module_path = filename
        else:
            module_name = f"module_0x{base_address:08x}"
            module_path = ""

        # Load DLL module (will try to extract DWARF info)
        self.module_manager.on_module_loaded(
            name=module_name,
            base_address=base_address,
            path=module_path,
            size=0
        )

        # Try to resolve pending breakpoints for this module
        if self.breakpoint_manager:
            resolved = self.breakpoint_manager.resolve_pending_breakpoints_for_module(module_name)
            if resolved:
                print(f"[DLL Load] Resolved {len(resolved)} pending breakpoint(s) for {module_name}")

    def _on_exception(self, event):
        """Handle EXCEPTION_DEBUG_EVENT.

        Args:
            event: DEBUG_EVENT structure
        """
        info = event.u.Exception
        exception_code = info.ExceptionRecord.ExceptionCode
        exception_address = info.ExceptionRecord.ExceptionAddress
        first_chance = info.dwFirstChance
        thread_id = event.dwThreadId

        print(f"[Exception] code=0x{exception_code:08x} at 0x{exception_address:08x}, thread={thread_id}", flush=True)

        # Handle breakpoint exception (both standard and WOW64 variants)
        if exception_code == win32api.EXCEPTION_BREAKPOINT or exception_code == win32api.STATUS_WX86_BREAKPOINT:
            self._handle_breakpoint(exception_address, thread_id, first_chance)
            return

        # Handle single-step exception (both standard and WOW64 variants)
        if exception_code == win32api.EXCEPTION_SINGLE_STEP or exception_code == win32api.STATUS_WX86_SINGLE_STEP:
            self._handle_single_step(exception_address, thread_id)
            return

        # Other exceptions - report them
        print(f"Exception 0x{exception_code:08x} at 0x{exception_address:08x}")
        if first_chance:
            # First chance - let the process handle it
            self.continue_status = win32api.DBG_EXCEPTION_NOT_HANDLED
        else:
            # Second chance - debugger must handle it
            self.context.current_thread_id = thread_id  # Update current thread
            self.context.current_address = exception_address  # Update current address
            self.context.set_stopped(StopInfo(
                reason="exception",
                address=exception_address,
                exception_code=exception_code,
                exception_address=exception_address,
                thread_id=thread_id
            ))

    def _handle_breakpoint(self, address: int, thread_id: int, first_chance: int):
        """Handle a breakpoint exception.

        Args:
            address: Exception address
            thread_id: Thread ID
            first_chance: Whether this is first-chance exception
        """
        # Check if this is one of our breakpoints
        bp = None
        if self.breakpoint_manager:
            bp = self.breakpoint_manager.on_breakpoint_hit(address, thread_id)

        if bp:
            print(f"\nBreakpoint {bp.id} hit at 0x{address:08x}")
            if bp.file and bp.line:
                print(f"  {Path(bp.file).name}:{bp.line}")
            if bp.module_name:
                print(f"  Module: {bp.module_name}")

            self.last_breakpoint_address = address
            self.context.current_thread_id = thread_id  # Update current thread
            self.context.current_address = address  # Update current address

            # Set trap flag to single-step after executing original instruction
            # This ensures we get a single-step exception to re-enable the breakpoint
            flags = self.process_controller.get_register(thread_id, 'EFlags')
            flags |= 0x100  # Set TF (Trap Flag)
            self.process_controller.set_register(thread_id, 'EFlags', flags)

            self.context.set_stopped(StopInfo(
                reason="breakpoint",
                address=address,
                thread_id=thread_id,
                module_name=bp.module_name
            ))
        else:
            # System breakpoint (not one of ours)
            if not self.initial_breakpoint_hit:
                # This is the FIRST breakpoint - the initial system breakpoint
                # Stop here so the user can inspect the process at entry
                print(f"\nInitial breakpoint at 0x{address:08x} (entry point)")
                self.initial_breakpoint_hit = True
                self.context.current_thread_id = thread_id  # Update current thread
                self.context.current_address = address  # Update current address
                self.context.set_stopped(StopInfo(
                    reason="entry",
                    address=address,
                    thread_id=thread_id
                ))

                # Call callback if registered (for MCP server synchronization)
                if self.initial_breakpoint_callback:
                    print(f"[_handle_breakpoint] Signaling initial breakpoint callback", flush=True)
                    self.initial_breakpoint_callback()
                    self.initial_breakpoint_callback = None  # Call only once
            elif first_chance:
                # Subsequent system breakpoints - just continue
                self.continue_status = win32api.DBG_CONTINUE
            else:
                # Second-chance breakpoint we don't own - stop and report
                print(f"Unknown breakpoint at 0x{address:08x}")
                self.context.current_thread_id = thread_id  # Update current thread
                self.context.current_address = address  # Update current address
                self.context.set_stopped(StopInfo(
                    reason="breakpoint",
                    address=address,
                    thread_id=thread_id
                ))

    def _handle_single_step(self, address: int, thread_id: int):
        """Handle a single-step exception.

        Args:
            address: Current address
            thread_id: Thread ID
        """
        print(f"Single step at 0x{address:08x}")

        # If we just stepped over a breakpoint, re-enable it
        if self.last_breakpoint_address and self.breakpoint_manager:
            print(f"Re-enabling breakpoint at 0x{self.last_breakpoint_address:08x}")
            self.breakpoint_manager.re_enable_breakpoint(self.last_breakpoint_address)
            self.last_breakpoint_address = None

            # Clear trap flag after re-enabling breakpoint
            flags = self.process_controller.get_register(thread_id, 'EFlags')
            flags &= ~0x100  # Clear TF
            self.process_controller.set_register(thread_id, 'EFlags', flags)

            # CRITICAL: Don't stop here - we're just re-enabling the breakpoint
            # The process should continue running after this
            self.context.current_thread_id = thread_id
            self.context.current_address = address
            # Do NOT call set_stopped() - let the process continue
            return

        # Check if this is a user-requested step
        if self.context.step_mode:
            # This is a user-requested step - stop here
            # CRITICAL: Clear trap flag to prevent extra single-step after event loop exit
            flags = self.process_controller.get_register(thread_id, 'EFlags')
            flags &= ~0x100  # Clear TF
            self.process_controller.set_register(thread_id, 'EFlags', flags)

            # Clear step mode
            self.context.set_step_mode(False)

            self.context.current_thread_id = thread_id  # Update current thread
            self.context.current_address = address  # Update current address
            self.context.set_stopped(StopInfo(
                reason="step",
                address=address,
                thread_id=thread_id
            ))
            return

        # This is an unexpected single-step (likely spurious WOW64 exception)
        # These can occur during DLL loading, thread creation, etc. on 64-bit Windows
        # CRITICAL: Must clear Trap Flag, otherwise every subsequent instruction
        # will generate single-step exceptions, preventing breakpoints from working!
        print(f"Ignoring spurious single-step exception at 0x{address:08x}")
        flags = self.process_controller.get_register(thread_id, 'EFlags')
        if flags & 0x100:  # Check if TF is set
            print(f"Clearing Trap Flag (was set)")
            flags &= ~0x100  # Clear TF
            self.process_controller.set_register(thread_id, 'EFlags', flags)

        self.context.current_thread_id = thread_id
        self.context.current_address = address
        # Do NOT call set_stopped() - let the process continue

    def _on_exit_process(self, event):
        """Handle EXIT_PROCESS_DEBUG_EVENT.

        Args:
            event: DEBUG_EVENT structure
        """
        exit_code = event.u.ExitProcess.dwExitCode
        print(f"\nProcess exited with code {exit_code}")
        self.context.set_exited(exit_code)
        self.waiting_for_event = False

    def continue_execution(self):
        """Continue execution after a stop."""
        if not self.context.is_stopped():
            print("Process not stopped")
            return

        # Trap flag and breakpoint re-enablement are now handled
        # automatically by the event loop (_handle_single_step)

        self.context.set_running()
        self.run_event_loop()

    def step_over(self):
        """Step over one instruction."""
        if not self.context.current_thread_id:
            print("No thread to step")
            return

        try:
            # Set trap flag (bit 8 of EFLAGS) to enable single-step
            flags = self.process_controller.get_register(self.context.current_thread_id, 'EFlags')
            flags |= 0x100  # Set TF
            self.process_controller.set_register(self.context.current_thread_id, 'EFlags', flags)

            self.context.set_step_mode(True)
            self.context.set_running()
            self.run_event_loop()
        except Exception as e:
            print(f"Failed to step: {e}")

    def stop(self):
        """Stop the debugger and clean up resources.

        NOTE: This should be called AFTER the event loop thread has exited
        to avoid closing handles while they're still in use.
        """
        print(f"[Debugger.stop] Cleaning up debugger resources, state={self.context.state.value}", flush=True)

        # Terminate the process if it's still running
        if self.process_handle and not self.context.is_exited():
            print(f"[Debugger.stop] Terminating process (PID={self.context.process_id})", flush=True)
            try:
                win32api.terminate_process(self.process_handle)
                print(f"[Debugger.stop] Process terminated", flush=True)
            except Exception as e:
                print(f"[Debugger.stop] WARNING: Failed to terminate process: {e}", flush=True)

        # Clean up process controller (closes thread handles)
        if self.process_controller:
            try:
                self.process_controller.cleanup()
            except Exception as e:
                print(f"[Debugger.stop] WARNING: Error in process_controller cleanup: {e}", flush=True)

        # Close main thread handle
        if self.main_thread_handle:
            try:
                win32api.close_handle(self.main_thread_handle)
            except Exception as e:
                print(f"[Debugger.stop] WARNING: Failed to close thread handle: {e}", flush=True)
            self.main_thread_handle = None

        # Close process handle
        if self.process_handle:
            try:
                win32api.close_handle(self.process_handle)
            except Exception as e:
                print(f"[Debugger.stop] WARNING: Failed to close process handle: {e}", flush=True)
            self.process_handle = None

        print(f"[Debugger.stop] Cleanup complete", flush=True)

    def set_breakpoint(self, location: str) -> bool:
        """Set a breakpoint (supports deferred/pending breakpoints).

        Args:
            location: Either "file:line", "module.dll:line", or "0xaddress"

        Returns:
            True if successful
        """
        if not self.breakpoint_manager:
            print("Process not started")
            return False

        # Use deferred breakpoint logic (handles both immediate and pending)
        bp = self.breakpoint_manager.set_breakpoint_deferred(location)
        if bp:
            if bp.status == "pending":
                print(f"Breakpoint {bp.id} set (pending): {location}")
                print(f"  Will activate when module loads")
            else:
                print(f"Breakpoint {bp.id} set at 0x{bp.address:08x}")
                if bp.file and bp.line:
                    print(f"  Location: {bp.file}:{bp.line}")
            return True
        return False

    def list_breakpoints(self):
        """List all breakpoints (including pending)."""
        if not self.breakpoint_manager:
            print("No breakpoints")
            return

        breakpoints = self.breakpoint_manager.get_all_breakpoints()
        if not breakpoints:
            print("No breakpoints")
            return

        print("Breakpoints:")
        for bp in breakpoints:
            if bp.status == "pending":
                # Pending breakpoint - not yet resolved
                print(f"  {bp.id}: {bp.pending_location} - PENDING")
                if bp.module_name:
                    print(f"      (waiting for {bp.module_name})")
            else:
                # Active breakpoint
                status = "enabled" if bp.enabled else "disabled"
                location = f"0x{bp.address:08x}"
                if bp.file and bp.line:
                    location += f" ({Path(bp.file).name}:{bp.line})"
                if bp.module_name:
                    location += f" [{bp.module_name}]"
                print(f"  {bp.id}: {location} - {status} (hit {bp.hit_count} times)")

    def list_modules(self):
        """List all loaded modules."""
        print("Loaded modules:")
        for module in self.module_manager.get_all_modules():
            debug_info = "DWARF 2" if module.has_debug_info else "no debug"
            print(f"  0x{module.base_address:08x}  {module.name:30s}  ({debug_info})")
