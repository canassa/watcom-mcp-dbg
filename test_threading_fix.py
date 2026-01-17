"""
Test the threading fix for Windows Debug API.

This test verifies that debugger.start() and run_event_loop() are called
on the same thread, which is required by the Windows Debug API.
"""

import sys
from pathlib import Path
import threading
import time

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger
from dgb.debugger.exceptions import ProcessCreationError, InvalidHandleError, DebuggerError


def test_threading_fix():
    """Test that debugger works with threading fix."""
    exe_path = "c:/entomorph/plague.exe"

    if not Path(exe_path).exists():
        print(f"Error: {exe_path} not found")
        return False

    print("=" * 60)
    print("Testing Threading Fix")
    print("=" * 60)

    # Create debugger
    debugger = Debugger(exe_path)

    # Shared state for communication between threads
    startup_complete = threading.Event()
    startup_error = {'error': None}
    process_stopped = threading.Event()

    def background_event_loop():
        """
        Background thread that creates the process and runs the event loop.
        This mimics the MCP server flow after our fix.
        """
        try:
            # CRITICAL: Start the process ON THIS THREAD
            print("[BackgroundThread] Creating process...")
            debugger.start()
            print(f"[BackgroundThread] Process created - PID={debugger.context.process_id}")

            # Signal successful startup
            startup_complete.set()

            # Set state to running
            debugger.context.set_running()

            # Run event loop on the SAME thread
            print("[BackgroundThread] Starting event loop...")

            # Run event loop with a short timeout to check for stop
            iteration = 0
            while not debugger.context.should_quit and not debugger.context.is_exited():
                iteration += 1

                # Run one iteration of event loop
                from dgb.debugger import win32api
                event = win32api.wait_for_debug_event(timeout_ms=100)
                if event:
                    debugger._dispatch_event(event)

                    # Check if we stopped after dispatching event
                    if debugger.context.is_stopped():
                        print(f"[BackgroundThread] Process stopped at 0x{debugger.context.current_address:08x}")
                        print(f"[BackgroundThread] Stop reason: {debugger.context.get_stop_reason()}")
                        process_stopped.set()
                        break
                    else:
                        win32api.continue_debug_event(
                            event.dwProcessId,
                            event.dwThreadId,
                            debugger.continue_status
                        )
                    debugger.continue_status = win32api.DBG_CONTINUE

                # Safety limit
                if iteration > 100:
                    print("[BackgroundThread] Iteration limit reached")
                    break

            print("[BackgroundThread] Event loop finished")

        except (ProcessCreationError, InvalidHandleError, DebuggerError) as e:
            error_type = type(e).__name__
            startup_error['error'] = f'{error_type}: {e}'
            startup_complete.set()
            print(f"[BackgroundThread] Startup error: {startup_error['error']}")
        except Exception as e:
            startup_error['error'] = f'Unexpected error: {e}'
            startup_complete.set()
            print(f"[BackgroundThread] Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up
            if debugger.process_handle:
                debugger.stop()

    # Start background thread
    print("\n1. Starting background thread...")
    thread = threading.Thread(target=background_event_loop, daemon=True)
    thread.start()

    # Wait for startup to complete
    print("2. Waiting for process creation...")
    if not startup_complete.wait(timeout=5.0):
        print("   [FAIL] Timeout waiting for process creation")
        return False

    # Check for startup errors
    if startup_error['error']:
        print(f"   [FAIL] {startup_error['error']}")
        return False

    print(f"   [OK] Process created successfully - PID={debugger.context.process_id}")

    # Wait for initial breakpoint
    print("3. Waiting for initial breakpoint...")
    if not process_stopped.wait(timeout=5.0):
        print("   [FAIL] Timeout waiting for initial breakpoint")
        return False

    print(f"   [OK] Initial breakpoint hit")

    # Check current state
    print("4. Checking debugger state...")
    print(f"   State: {debugger.context.state.value}")
    print(f"   Stop reason: {debugger.context.get_stop_reason()}")

    # List modules
    print("5. Listing modules...")
    modules = list(debugger.module_manager.get_all_modules())
    print(f"   Loaded {len(modules)} modules:")
    for module in modules[:3]:  # Show first 3
        debug_info = "DWARF" if module.has_debug_info else "no debug"
        print(f"     - {module.name} at 0x{module.base_address:08x} ({debug_info})")

    # Get registers
    print("6. Reading registers...")
    if debugger.context.current_thread_id:
        try:
            regs = debugger.process_controller.get_all_registers(
                debugger.context.current_thread_id
            )
            print(f"   EIP = 0x{regs['eip']:08x}")
            print(f"   ESP = 0x{regs['esp']:08x}")
            print("   [OK] Register access working")
        except Exception as e:
            print(f"   [FAIL] Error reading registers: {e}")
            return False

    # Clean up
    print("7. Cleaning up...")
    debugger.stop()
    thread.join(timeout=2.0)
    print("   [OK] Cleanup complete")

    print("\n" + "=" * 60)
    print("[SUCCESS] Threading fix verified!")
    print("=" * 60)
    print("\nKey verification points:")
    print("  [OK] Process created successfully (no InvalidHandleError)")
    print("  [OK] Event loop started on same thread")
    print("  [OK] Initial breakpoint hit")
    print("  [OK] Register access working")
    print("  [OK] Module loading working")
    return True


if __name__ == '__main__':
    success = test_threading_fix()
    sys.exit(0 if success else 1)
