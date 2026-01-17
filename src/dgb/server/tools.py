"""
MCP tool implementations for debugger operations.

Each tool is a function that takes a SessionManager and tool arguments,
performs the debugger operation, and returns a result dict.
"""

from typing import Optional, Any
from pathlib import Path
import time

from dgb.server.session_manager import SessionManager
from dgb.server.debugger_wrapper import DebuggerWrapper, Command, CommandType, CommandResult
from dgb.server.models import (
    Tool, ToolInputSchema, TextContent, ToolCallResult
)


# Tool Registry - maps tool names to (function, schema)
TOOL_REGISTRY = {}


def register_tool(name: str, description: str, schema: dict):
    """Decorator to register a tool."""
    def decorator(func):
        TOOL_REGISTRY[name] = {
            'function': func,
            'tool': Tool(
                name=name,
                description=description,
                inputSchema=ToolInputSchema(
                    type="object",
                    properties=schema.get('properties', {}),
                    required=schema.get('required', [])
                )
            )
        }
        return func
    return decorator


# Tool Implementations

@register_tool(
    name="debugger_create_session",
    description="Create a new debugging session for a Windows PE executable",
    schema={
        'properties': {
            'executable_path': {
                'type': 'string',
                'description': 'Path to the executable to debug'
            },
            'args': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Command-line arguments for the executable (optional)'
            },
            'source_dirs': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Additional source directories to search (optional)'
            }
        },
        'required': ['executable_path']
    }
)
def debugger_create_session(session_manager: SessionManager, args: dict) -> dict:
    """Create a new debugging session."""
    try:
        executable_path = args['executable_path']
        cmd_args = args.get('args', [])
        source_dirs = args.get('source_dirs', [])

        session = session_manager.create_session(
            executable_path=executable_path,
            args=cmd_args,
            source_dirs=source_dirs
        )

        return {
            'success': True,
            'session_id': session.session_id,
            'status': 'created',
            'message': f"Debugging session created for {Path(executable_path).name}"
        }
    except FileNotFoundError as e:
        return {'success': False, 'error': str(e)}


@register_tool(
    name="debugger_run",
    description="Start execution of the debugged process from entry point",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID from debugger_create_session'
            }
        },
        'required': ['session_id']
    }
)
def debugger_run(session_manager: SessionManager, args: dict) -> dict:
    """Start execution of the debugged process."""
    from dgb.debugger.exceptions import (
        ProcessCreationError, InvalidHandleError, DebuggerError
    )

    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    # Check if already running
    if hasattr(session, 'debugger_wrapper') and session.debugger_wrapper and session.debugger_wrapper.running:
        return {'success': False, 'error': 'Debugger already running'}

    print(f"[debugger_run] Preparing to start process: {session.debugger.executable_path}", flush=True)

    # CRITICAL: Start a PERSISTENT background thread for the event loop
    # The Win32 Debug API requires continuous event pumping - we can't stop and restart
    # CRITICAL FIX: CreateProcess and WaitForDebugEvent MUST happen on the SAME thread
    import threading
    import time

    # Use events to signal when startup is complete (success or failure)
    startup_complete = threading.Event()
    initial_breakpoint_hit = threading.Event()  # NEW: Wait for initial breakpoint
    startup_error = {'error': None}  # Shared dict for error propagation

    def persistent_event_loop():
        """Persistent event loop that runs continuously until process exits.

        CRITICAL: This function calls debugger.start() to create the process on THIS thread,
        then immediately runs the event loop on the SAME thread. This satisfies the Windows
        Debug API requirement that WaitForDebugEvent must be called by the same thread that
        created/attached to the process.
        """
        try:
            # CRITICAL: Start the process ON THIS THREAD
            print(f"[PersistentLoop] Creating process on background thread: {session.debugger.executable_path}", flush=True)
            session.debugger.start()
            print(f"[PersistentLoop] Process created - PID={session.debugger.context.process_id}, handle={session.debugger.process_handle}", flush=True)

            # Signal successful startup
            startup_complete.set()

            # NOTE: Do NOT call set_running() here - let the event loop manage state transitions
            # The initial breakpoint handler will set state to "stopped" when hit

            # Run event loop on the SAME thread in a persistent loop
            # With the new event loop behavior, run_event_loop() exits when the process stops,
            # so we need to keep calling it until the process actually exits
            print(f"[PersistentLoop] Starting persistent event loop on same thread", flush=True)
            while not session.debugger.context.should_quit and not session.debugger.context.is_exited():
                session.debugger.run_event_loop()
                # Event loop exited - either stopped, exited, or should quit
                if session.debugger.context.is_stopped():
                    # Process stopped at breakpoint - wait for continue command
                    print(f"[PersistentLoop] Event loop paused at stop, state={session.debugger.context.state.value}", flush=True)
                    # CRITICAL: Wait in a loop while stopped until continue command
                    # Do NOT call run_event_loop() while stopped or it will process events one at a time!
                    import time
                    while session.debugger.context.is_stopped() and not session.debugger.context.is_exited() and not session.debugger.context.should_quit:
                        time.sleep(0.01)
                    # State changed (continued or exited), loop back to check
                elif session.debugger.context.is_exited():
                    print(f"[PersistentLoop] Process exited, state={session.debugger.context.state.value}", flush=True)
                    break
            print(f"[PersistentLoop] Persistent loop exited, state={session.debugger.context.state.value}", flush=True)
        except (ProcessCreationError, InvalidHandleError, DebuggerError) as e:
            # Store startup error for HTTP handler
            error_type = type(e).__name__
            startup_error['error'] = f'{error_type}: {e}'
            startup_complete.set()  # Signal completion even on error
            print(f"[PersistentLoop] Startup error: {startup_error['error']}", flush=True)
        except Exception as e:
            # Store unexpected error
            startup_error['error'] = f'Unexpected error: {e}'
            startup_complete.set()
            print(f"[PersistentLoop] FATAL ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            # Mark wrapper as not running when thread exits
            if hasattr(session, 'debugger_wrapper') and session.debugger_wrapper:
                session.debugger_wrapper.running = False
            print(f"[PersistentLoop] Thread exiting", flush=True)

    # Register callback so event loop can signal when initial breakpoint is hit
    session.debugger.initial_breakpoint_callback = lambda: initial_breakpoint_hit.set()

    # Start persistent background thread
    thread = threading.Thread(target=persistent_event_loop, daemon=True)
    thread.start()

    # Wait for startup to complete (success or failure)
    if not startup_complete.wait(timeout=5.0):
        return {'success': False, 'error': 'Timeout waiting for process creation'}

    # Check for startup errors
    if startup_error['error']:
        return {'success': False, 'error': startup_error['error']}

    # NEW: Wait for initial breakpoint to be hit
    print(f"[debugger_run] Waiting for initial breakpoint...", flush=True)
    if not initial_breakpoint_hit.wait(timeout=5.0):
        return {'success': False, 'error': 'Timeout waiting for initial breakpoint'}

    print(f"[debugger_run] Initial breakpoint hit, state={session.debugger.context.state.value}", flush=True)

    # Verify we're actually stopped
    if not session.debugger.context.is_stopped():
        return {
            'success': False,
            'error': f'Expected stopped state, got {session.debugger.context.state.value}'
        }

    # Create wrapper for command processing
    wrapper = DebuggerWrapper(session.debugger)
    wrapper.running = True
    wrapper.thread = thread

    # Store wrapper in session for future commands
    session.debugger_wrapper = wrapper
    session.event_thread = thread

    # Get stop info and state
    stop_info = session.debugger.context.stop_info
    state = session.debugger.context.state.value
    modules_count = len(list(session.debugger.module_manager.get_all_modules()))

    return {
        'success': True,
        'state': state,
        'stop_reason': stop_info.reason if stop_info else None,
        'stop_address': f"0x{stop_info.address:08x}" if stop_info and stop_info.address else None,
        'modules_loaded': modules_count,
        'message': f'Process stopped at entry point, {modules_count} modules loaded'
    }


@register_tool(
    name="debugger_continue",
    description="Continue execution after breakpoint or stop",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_continue(session_manager: SessionManager, args: dict) -> dict:
    """Continue execution."""
    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    # Check if stopped
    if not session.debugger.context.is_stopped():
        return {'success': False, 'error': 'Process not stopped'}

    print(f"[debugger_continue] Resuming execution, state={session.debugger.context.state.value}", flush=True)

    # Set state to running - the persistent event loop will continue
    # The breakpoint restoration logic happens automatically:
    # 1. on_breakpoint_hit() already restored original byte and rewound EIP
    # 2. _handle_breakpoint() already set trap flag for single-step
    # 3. When we set state to running, persistent loop calls run_event_loop()
    # 4. Single-step fires, _handle_single_step() re-enables breakpoint
    session.debugger.context.set_running()

    # CRITICAL: Must set waiting_for_event = True so run_event_loop() will continue processing
    # When breakpoint hits, event loop sets this to False and exits (line 141 in core.py)
    session.debugger.waiting_for_event = True

    print(f"[debugger_continue] State changed to running, waiting for next stop event...", flush=True)

    # Wait for process to stop at next breakpoint or exit
    timeout = 10.0
    start_time = time.time()
    while time.time() - start_time < timeout:
        if session.debugger.context.is_stopped():
            break
        if session.debugger.context.is_exited():
            # Process exited
            return {
                'success': True,
                'state': 'exited',
                'message': 'Process exited during continue'
            }
        time.sleep(0.01)
    else:
        # Timeout waiting for stop
        return {'success': False, 'error': 'Timeout waiting for process to stop'}

    # Get current state after continue (should be stopped)
    stop_info = session.debugger.context.stop_info
    state = session.debugger.context.state.value

    print(f"[debugger_continue] Continue complete, state={state}, reason={stop_info.reason if stop_info else None}", flush=True)

    return {
        'success': True,
        'state': state,
        'stop_reason': stop_info.reason if stop_info else None,
        'stop_address': f"0x{stop_info.address:08x}" if stop_info and stop_info.address else None,
        'message': f'Stopped: {stop_info.reason}' if stop_info else 'Process stopped'
    }


@register_tool(
    name="debugger_step",
    description="Single-step one CPU instruction",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_step(session_manager: SessionManager, args: dict) -> dict:
    """Single-step execution."""
    import time

    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    # Check if stopped
    if not session.debugger.context.is_stopped():
        return {'success': False, 'error': 'Process not stopped'}

    if not session.debugger.context.current_thread_id:
        return {'success': False, 'error': 'No current thread'}

    print(f"[debugger_step] Executing step, state={session.debugger.context.state.value}", flush=True)

    # Set trap flag to enable single-step (like step_over does)
    try:
        flags = session.debugger.process_controller.get_register(
            session.debugger.context.current_thread_id, 'EFlags'
        )
        flags |= 0x100  # Set TF (Trap Flag)
        session.debugger.process_controller.set_register(
            session.debugger.context.current_thread_id, 'EFlags', flags
        )
    except Exception as e:
        return {'success': False, 'error': f'Failed to set trap flag: {e}'}

    # Set step mode and running state (like debugger_continue does)
    session.debugger.context.set_step_mode(True)
    session.debugger.context.set_running()
    session.debugger.waiting_for_event = True

    print(f"[debugger_step] State set to running with step mode, waiting for step to complete...", flush=True)

    # Wait for step to complete (process should stop again)
    timeout = 5.0
    start_time = time.time()
    while time.time() - start_time < timeout:
        if session.debugger.context.is_stopped():
            break
        if session.debugger.context.is_exited():
            return {'success': False, 'error': 'Process exited during step'}
        time.sleep(0.01)
    else:
        return {'success': False, 'error': 'Timeout waiting for step to complete'}

    # Get current state after step
    stop_info = session.debugger.context.stop_info
    state = session.debugger.context.state.value

    print(f"[debugger_step] Step complete, state={state}, reason={stop_info.reason if stop_info else None}", flush=True)

    return {
        'success': True,
        'state': state,
        'stop_reason': stop_info.reason if stop_info else None,
        'stop_address': f"0x{stop_info.address:08x}" if stop_info and stop_info.address else None
    }


@register_tool(
    name="debugger_set_breakpoint",
    description="Set a breakpoint at a source location or address",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            },
            'location': {
                'type': 'string',
                'description': 'Breakpoint location: "file:line" or "0xADDRESS"'
            }
        },
        'required': ['session_id', 'location']
    }
)
def debugger_set_breakpoint(session_manager: SessionManager, args: dict) -> dict:
    """Set a breakpoint."""
    session_id = args['session_id']
    location = args['location']

    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    # If process is stopped or wrapper not running, set breakpoint directly
    wrapper = getattr(session, 'debugger_wrapper', None)
    use_direct = (not wrapper or
                  not wrapper.running or
                  session.debugger.context.is_stopped())

    if use_direct:
        # Set breakpoint directly on stopped debugger
        success = session.debugger.set_breakpoint(location)
        if success:
            bp_list = session.debugger.breakpoint_manager.get_all_breakpoints()
            if bp_list:
                last_bp = bp_list[-1]
                result = {
                    'success': True,
                    'breakpoint_id': f"bp_{last_bp.id}",
                    'status': last_bp.status
                }

                if last_bp.status == "active":
                    result.update({
                        'address': f"0x{last_bp.address:08x}",
                        'file': last_bp.file,
                        'line': last_bp.line,
                        'module_name': last_bp.module_name
                    })
                else:  # pending
                    result.update({
                        'location': last_bp.pending_location,
                        'message': 'Breakpoint pending - will activate when module loads'
                    })
                return result
        return {'success': False, 'error': 'Failed to set breakpoint'}

    # Use command queue for running debugger
    cmd_result = wrapper.send_command(
        Command(type=CommandType.SET_BREAKPOINT, args={'location': location})
    )
    if cmd_result.success:
        data = cmd_result.data
        result = {
            'success': True,
            'breakpoint_id': f"bp_{data['breakpoint_id']}",
            'status': data['status']
        }

        if data['status'] == "active":
            result.update({
                'address': f"0x{data['address']:08x}",
                'file': data.get('file'),
                'line': data.get('line'),
                'module_name': data.get('module_name')
            })
        else:  # pending
            result.update({
                'location': data.get('pending_location'),
                'message': 'Breakpoint pending - will activate when module loads'
            })
        return result
    else:
        return {'success': False, 'error': cmd_result.error}


@register_tool(
    name="debugger_list_breakpoints",
    description="List all breakpoints in the debugging session",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_list_breakpoints(session_manager: SessionManager, args: dict) -> dict:
    """List all breakpoints."""
    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    if not session.debugger.breakpoint_manager:
        return {'success': True, 'breakpoints': []}

    breakpoints = []
    for bp in session.debugger.breakpoint_manager.get_all_breakpoints():
        bp_info = {
            'breakpoint_id': f"bp_{bp.id}",
            'status': bp.status
        }

        if bp.status == "active":
            bp_info.update({
                'address': f"0x{bp.address:08x}",
                'enabled': bp.enabled,
                'hit_count': bp.hit_count
            })
            if bp.file and bp.line:
                bp_info['location'] = f"{Path(bp.file).name}:{bp.line}"
                bp_info['file'] = bp.file
                bp_info['line'] = bp.line
            if bp.module_name:
                bp_info['module_name'] = bp.module_name
        else:  # pending
            bp_info['location'] = bp.pending_location
            if bp.module_name:
                bp_info['module_name'] = bp.module_name

        breakpoints.append(bp_info)

    return {'success': True, 'breakpoints': breakpoints}


@register_tool(
    name="debugger_get_registers",
    description="Get CPU register values (32-bit x86 registers)",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_get_registers(session_manager: SessionManager, args: dict) -> dict:
    """Get CPU registers."""
    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    # Check if process is stopped
    if not session.debugger.context.is_stopped():
        return {
            'success': False,
            'error': f'Cannot read registers: process is {session.debugger.context.state.value}. Process must be stopped.'
        }

    if not session.debugger.context.current_thread_id:
        return {'success': False, 'error': 'No current thread'}

    registers = session.debugger.process_controller.get_all_registers(
        session.debugger.context.current_thread_id
    )

    # Verify registers are valid (not all zeros)
    if all(v == 0 for v in registers.values()):
        return {
            'success': False,
            'error': 'Register read returned all zeros - thread context may not be available'
        }

    # Format as uppercase hex for display
    formatted = {
        'EAX': f"0x{registers['eax']:08x}",
        'EBX': f"0x{registers['ebx']:08x}",
        'ECX': f"0x{registers['ecx']:08x}",
        'EDX': f"0x{registers['edx']:08x}",
        'ESI': f"0x{registers['esi']:08x}",
        'EDI': f"0x{registers['edi']:08x}",
        'EBP': f"0x{registers['ebp']:08x}",
        'ESP': f"0x{registers['esp']:08x}",
        'EIP': f"0x{registers['eip']:08x}",
        'EFlags': f"0x{registers['eflags']:08x}"
    }

    return {'success': True, 'registers': formatted}


@register_tool(
    name="debugger_list_modules",
    description="List all loaded modules (EXE + DLLs) with debug information",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_list_modules(session_manager: SessionManager, args: dict) -> dict:
    """List loaded modules."""
    session_id = args['session_id']
    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    modules = []
    for module in session.debugger.module_manager.get_all_modules():
        modules.append({
            'name': module.name,
            'base_address': f"0x{module.base_address:08x}",
            'path': module.path,
            'has_debug_info': module.has_debug_info
        })

    return {'success': True, 'modules': modules}


@register_tool(
    name="debugger_get_source",
    description="Get source code with context around a specific line",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            },
            'file': {
                'type': 'string',
                'description': 'Source file name or path'
            },
            'line': {
                'type': 'integer',
                'description': 'Line number'
            },
            'context_lines': {
                'type': 'integer',
                'description': 'Number of context lines before/after (default 5)'
            }
        },
        'required': ['session_id', 'file', 'line']
    }
)
def debugger_get_source(session_manager: SessionManager, args: dict) -> dict:
    """Get source code."""
    session_id = args['session_id']
    file = args['file']
    line = args['line']
    context_lines = args.get('context_lines', 5)

    session = session_manager.get_session(session_id)
    if not session:
        return {'success': False, 'error': 'Session not found'}

    source_info = session.source_resolver.get_source_lines(
        file, line, context_lines
    )

    if not source_info:
        return {'success': False, 'error': f'Source file not found: {file}'}

    return {
        'success': True,
        'file': source_info['file'],
        'full_path': source_info['full_path'],
        'lines': source_info['lines']
    }


@register_tool(
    name="debugger_close_session",
    description="Close a debugging session and clean up resources",
    schema={
        'properties': {
            'session_id': {
                'type': 'string',
                'description': 'Session ID'
            }
        },
        'required': ['session_id']
    }
)
def debugger_close_session(session_manager: SessionManager, args: dict) -> dict:
    """Close a debugging session."""
    session_id = args['session_id']
    success = session_manager.close_session(session_id)

    if success:
        return {
            'success': True,
            'status': 'closed',
            'message': 'Session closed successfully'
        }
    else:
        return {'success': False, 'error': 'Session not found'}


# Helper Functions

def get_all_tools() -> list[Tool]:
    """Get all registered tools."""
    return [entry['tool'] for entry in TOOL_REGISTRY.values()]


def call_tool(session_manager: SessionManager, tool_name: str, arguments: dict) -> dict:
    """Call a tool by name.

    Args:
        session_manager: SessionManager instance
        tool_name: Name of the tool to call
        arguments: Tool arguments

    Returns:
        Tool result dict
    """
    if tool_name not in TOOL_REGISTRY:
        return {'success': False, 'error': f'Unknown tool: {tool_name}'}

    tool_entry = TOOL_REGISTRY[tool_name]
    tool_function = tool_entry['function']

    result = tool_function(session_manager, arguments)
    return result
