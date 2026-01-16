"""
MCP tool implementations for debugger operations.

Each tool is a function that takes a SessionManager and tool arguments,
performs the debugger operation, and returns a result dict.
"""

from typing import Optional, Any
from pathlib import Path

from dgb.server.session_manager import SessionManager
from dgb.server.debugger_wrapper import DebuggerWrapper, Command, CommandType
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
    except Exception as e:
        return {'success': False, 'error': f"Failed to create session: {e}"}


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

    # Start the process - let exceptions propagate but catch them for MCP response
    print(f"[debugger_run] Starting process: {session.debugger.executable_path}", flush=True)
    try:
        session.debugger.start()
    except ProcessCreationError as e:
        return {'success': False, 'error': f'Process creation failed: {e}'}
    except InvalidHandleError as e:
        return {'success': False, 'error': f'Invalid handle: {e}'}
    except DebuggerError as e:
        return {'success': False, 'error': f'Debugger error: {e}'}

    print(f"[debugger_run] Process started - PID={session.debugger.context.process_id}, handle={session.debugger.process_handle}", flush=True)

    # CRITICAL: Start a PERSISTENT background thread for the event loop
    # The Win32 Debug API requires continuous event pumping - we can't stop and restart
    import threading
    import time

    # Use an event to signal when the first debug event has been processed
    initial_event_processed = threading.Event()

    def persistent_event_loop():
        """Persistent event loop that runs continuously until process exits."""
        try:
            print(f"[PersistentLoop] Starting persistent event loop", flush=True)
            session.debugger.context.set_running()

            # Signal that we're about to start processing events
            initial_event_processed.set()

            session.debugger.run_event_loop()
            print(f"[PersistentLoop] Event loop exited normally, state={session.debugger.context.state.value}", flush=True)
        except Exception as e:
            print(f"[PersistentLoop] FATAL ERROR in event loop: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            # Mark wrapper as not running when thread exits
            if hasattr(session, 'debugger_wrapper') and session.debugger_wrapper:
                session.debugger_wrapper.running = False
            print(f"[PersistentLoop] Thread exiting", flush=True)

    # Start persistent background thread IMMEDIATELY after process creation
    thread = threading.Thread(target=persistent_event_loop, daemon=True)
    thread.start()

    # Wait for the thread to start processing events (with timeout)
    if not initial_event_processed.wait(timeout=2.0):
        return {'success': False, 'error': 'Timeout waiting for debug event loop to start'}

    # Give it a moment to process the first event (initial breakpoint)
    time.sleep(0.2)

    print(f"[debugger_run] Process initialized, state={session.debugger.context.state.value}", flush=True)

    # Create wrapper for command processing
    wrapper = DebuggerWrapper(session.debugger)
    wrapper.running = True
    wrapper.thread = thread

    # Store wrapper in session for future commands
    session.debugger_wrapper = wrapper
    session.event_thread = thread

    # Check current state
    state = session.debugger.context.state.value
    modules_count = len(list(session.debugger.module_manager.get_all_modules()))

    return {
        'success': True,
        'state': state,
        'modules_loaded': modules_count,
        'message': f'Process started, {modules_count} modules loaded'
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

    print(f"[debugger_continue] Resuming execution", flush=True)

    # Simply set the state to running - the persistent event loop will continue
    session.debugger.context.set_running()
    session.debugger.waiting_for_event = True

    return {
        'success': True,
        'state': 'running',
        'message': 'Process continuing'
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
    try:
        session_id = args['session_id']
        session = session_manager.get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}

        wrapper = getattr(session, 'debugger_wrapper', None)
        if not wrapper:
            return {'success': False, 'error': 'Debugger not started'}

        # Check if stopped
        if not session.debugger.context.is_stopped():
            return {'success': False, 'error': 'Process not stopped'}

        # Queue the step command with short timeout since step should be quick
        cmd_result = wrapper.send_command(Command(type=CommandType.STEP), timeout=5.0)
        if cmd_result.success:
            return {
                'success': True,
                'stop_info': cmd_result.data
            }
        else:
            return {'success': False, 'error': cmd_result.error}

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
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
                    return {
                        'success': True,
                        'breakpoint_id': f"bp_{last_bp.id}",
                        'address': f"0x{last_bp.address:08x}",
                        'file': last_bp.file,
                        'line': last_bp.line,
                        'module_name': last_bp.module_name
                    }
            return {'success': False, 'error': 'Failed to set breakpoint'}

        # Use command queue for running debugger
        cmd_result = wrapper.send_command(
            Command(type=CommandType.SET_BREAKPOINT, args={'location': location})
        )
        if cmd_result.success:
            data = cmd_result.data
            return {
                'success': True,
                'breakpoint_id': f"bp_{data['breakpoint_id']}",
                'address': f"0x{data['address']:08x}",
                'file': data.get('file'),
                'line': data.get('line'),
                'module_name': data.get('module_name')
            }
        else:
            return {'success': False, 'error': cmd_result.error}

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
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
                'address': f"0x{bp.address:08x}",
                'enabled': bp.enabled,
                'hit_count': bp.hit_count
            }
            if bp.file and bp.line:
                bp_info['location'] = f"{Path(bp.file).name}:{bp.line}"
                bp_info['file'] = bp.file
                bp_info['line'] = bp.line
            if bp.module_name:
                bp_info['module_name'] = bp.module_name

            breakpoints.append(bp_info)

        return {'success': True, 'breakpoints': breakpoints}

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
        session_id = args['session_id']
        session = session_manager.get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}

        if not session.debugger.context.current_thread_id:
            return {'success': False, 'error': 'No current thread'}

        registers = session.debugger.process_controller.get_all_registers(
            session.debugger.context.current_thread_id
        )

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

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
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

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
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

    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    try:
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

    except Exception as e:
        return {'success': False, 'error': str(e)}


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

    try:
        result = tool_function(session_manager, arguments)
        return result
    except Exception as e:
        return {'success': False, 'error': f'Tool execution failed: {e}'}
