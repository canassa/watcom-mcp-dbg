"""
Check if event loop continues running after continue() is called
"""

import sys
from pathlib import Path
import time
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import (
    debugger_create_session, debugger_run, debugger_continue
)

def test_event_loop():
    """Test event loop continues."""
    session_manager = SessionManager()

    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe'
    })
    session_id = result['session_id']
    session = session_manager.get_session(session_id)

    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"Stopped at entry")

    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"Continue called, state={result['state']}")
    print(f"waiting_for_event={session.debugger.waiting_for_event}")
    print(f"context.state={session.debugger.context.state.value}")

    # Monitor for 5 seconds
    print(f"\nMonitoring event loop...")
    for i in range(50):
        time.sleep(0.1)

        state = session.debugger.context.state.value
        is_stopped = session.debugger.context.is_stopped()
        is_exited = session.debugger.context.is_exited()

        if i % 10 == 0:
            print(f"[{i/10:.1f}s] state={state}, stopped={is_stopped}, exited={is_exited}")

        if is_stopped:
            print(f"\n*** Process STOPPED at {i/10:.1f}s ***")
            stop_info = session.debugger.context.stop_info
            if stop_info:
                print(f"    Reason: {stop_info.reason}")
                print(f"    Address: 0x{stop_info.address:08x}")
            break

        if is_exited:
            print(f"\n*** Process EXITED at {i/10:.1f}s ***")
            break


if __name__ == '__main__':
    test_event_loop()
