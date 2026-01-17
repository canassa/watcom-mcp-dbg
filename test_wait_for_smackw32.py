"""
Wait longer and specifically watch for smackw32.dll to load
"""

import sys
from pathlib import Path
import time
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import (
    debugger_create_session, debugger_run, debugger_set_breakpoint,
    debugger_continue, debugger_list_modules, debugger_list_breakpoints
)

def test_wait_for_smackw32():
    """Wait up to 30 seconds for smackw32.dll to load."""
    print("\n=== Waiting for smackw32.dll ===\n")

    session_manager = SessionManager()

    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    session_id = result['session_id']
    print(f"Session: {session_id}")

    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"Stopped at entry")

    # Set breakpoint by offset
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'smackw32.dll:0x3966'
    })
    print(f"Breakpoint set: {result['status']}")

    # Continue
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"Continuing...\n")

    # Wait and watch
    session = session_manager.get_session(session_id)
    smackw32_loaded = False

    for i in range(60):  # 30 seconds
        time.sleep(0.5)

        # Check modules
        result = debugger_list_modules(session_manager, {'session_id': session_id})
        modules = [m['name'] for m in result['modules']]

        if 'smackw32.dll' in modules and not smackw32_loaded:
            print(f"[{i*0.5:.1f}s] *** smackw32.dll LOADED ***")
            smackw32_loaded = True

            # Check if breakpoint resolved
            result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
            if result['breakpoints']:
                bp = result['breakpoints'][0]
                print(f"         Breakpoint status: {bp['status']}")
                if bp['status'] == 'active':
                    print(f"         Address: {bp.get('address')}")

        # Check if process stopped
        if session.debugger.context.is_stopped():
            stop_info = session.debugger.context.stop_info
            print(f"\n[{i*0.5:.1f}s] *** PROCESS STOPPED ***")
            print(f"         Reason: {stop_info.reason if stop_info else 'unknown'}")
            print(f"         Address: 0x{stop_info.address:08x}" if stop_info else "")

            # Check breakpoint
            result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
            if result['breakpoints']:
                bp = result['breakpoints'][0]
                print(f"         Breakpoint hit count: {bp.get('hit_count', 0)}")

            break

        # Check if exited
        if session.debugger.context.is_exited():
            print(f"\n[{i*0.5:.1f}s] Process exited")
            break

        # Print module count every 5 seconds
        if i % 10 == 0 and i > 0:
            print(f"[{i*0.5:.1f}s] {len(modules)} modules loaded, smackw32: {'YES' if smackw32_loaded else 'NO'}")

    # Final report
    print(f"\n=== Final Report ===")
    result = debugger_list_modules(session_manager, {'session_id': session_id})
    print(f"Total modules: {len(result['modules'])}")
    print(f"smackw32.dll loaded: {smackw32_loaded}")

    print(f"\nAll modules:")
    for m in result['modules']:
        print(f"  - {m['name']}")


if __name__ == '__main__':
    test_wait_for_smackw32()
