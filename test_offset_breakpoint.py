"""
Test setting breakpoint by offset: smackw32.dll:0x3966

If this works but trampolines.cpp:10 doesn't, then the bug is in source->address conversion.
"""

import sys
from pathlib import Path
import time
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import (
    debugger_create_session, debugger_run, debugger_set_breakpoint,
    debugger_continue, debugger_list_breakpoints
)

def test_offset_breakpoint():
    """Test breakpoint by offset."""
    print("\n=== Test: Breakpoint by Offset ===\n")

    session_manager = SessionManager()

    # Create session
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    print(f"1. Session created: {result['session_id']}")
    session_id = result['session_id']

    # Run - stop at entry
    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"2. Stopped at entry: {result['stop_reason']}")

    # Set breakpoint by OFFSET (as confirmed by x32dbg)
    print(f"\n3. Setting breakpoint: smackw32.dll:0x3966")
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'smackw32.dll:0x3966'
    })
    print(f"   Status: {result.get('status')}")
    if result['status'] == 'pending':
        print(f"   Location: {result.get('location')}")
    elif result['status'] == 'active':
        print(f"   Address: {result.get('address')}")
        print(f"   *** BREAKPOINT ACTIVE ***")

    # Continue
    print(f"\n4. Calling continue()...")
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"   State: {result['state']}")

    # Wait for breakpoint to hit
    print(f"\n5. Waiting for breakpoint to hit...")
    session = session_manager.get_session(session_id)

    for i in range(10):
        time.sleep(0.5)

        # Check breakpoint status
        result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
        if result['breakpoints']:
            bp = result['breakpoints'][0]
            hit_count = bp.get('hit_count', 0)

            if hit_count > 0:
                print(f"\n   *** BREAKPOINT HIT! ***")
                print(f"   Hit count: {hit_count}")
                print(f"   Status: {bp['status']}")
                print(f"   Address: {bp.get('address')}")
                return True

        # Check if process stopped
        if session.debugger.context.is_stopped():
            print(f"\n   Process stopped!")
            print(f"   Reason: {session.debugger.context.stop_info.reason if session.debugger.context.stop_info else 'unknown'}")

            result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
            if result['breakpoints']:
                bp = result['breakpoints'][0]
                print(f"   Breakpoint hit count: {bp.get('hit_count', 0)}")
            return True

    print(f"\n   Timeout - breakpoint did not hit in 5 seconds")
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    if result['breakpoints']:
        bp = result['breakpoints'][0]
        print(f"   Final status: {bp['status']}")
        print(f"   Hit count: {bp.get('hit_count', 0)}")

    return False


def test_source_breakpoint():
    """Test breakpoint by source location for comparison."""
    print("\n\n=== Test: Breakpoint by Source ===\n")

    session_manager = SessionManager()

    # Create session
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    print(f"1. Session created: {result['session_id']}")
    session_id = result['session_id']

    # Run - stop at entry
    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"2. Stopped at entry: {result['stop_reason']}")

    # Set breakpoint by SOURCE
    print(f"\n3. Setting breakpoint: trampolines.cpp:10")
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'trampolines.cpp:10'
    })
    print(f"   Status: {result.get('status')}")
    if result['status'] == 'pending':
        print(f"   Location: {result.get('location')}")
    elif result['status'] == 'active':
        print(f"   Address: {result.get('address')}")

    # Continue
    print(f"\n4. Calling continue()...")
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"   State: {result['state']}")

    # Wait for breakpoint to hit
    print(f"\n5. Waiting for breakpoint to hit...")
    session = session_manager.get_session(session_id)

    for i in range(10):
        time.sleep(0.5)

        result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
        if result['breakpoints']:
            bp = result['breakpoints'][0]
            hit_count = bp.get('hit_count', 0)

            if hit_count > 0:
                print(f"\n   *** BREAKPOINT HIT! ***")
                print(f"   Hit count: {hit_count}")
                print(f"   Address: {bp.get('address')}")
                return True

        if session.debugger.context.is_stopped():
            print(f"\n   Process stopped!")
            result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
            if result['breakpoints']:
                bp = result['breakpoints'][0]
                print(f"   Breakpoint hit count: {bp.get('hit_count', 0)}")
            return True

    print(f"\n   Timeout - breakpoint did not hit in 5 seconds")
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    if result['breakpoints']:
        bp = result['breakpoints'][0]
        print(f"   Final status: {bp['status']}")
        print(f"   Hit count: {bp.get('hit_count', 0)}")

    return False


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Offset vs Source Breakpoints")
    print("=" * 60)

    try:
        offset_worked = test_offset_breakpoint()
        source_worked = test_source_breakpoint()

        print("\n" + "=" * 60)
        print("Results:")
        print(f"  Offset breakpoint (smackw32.dll:0x3966): {'HIT' if offset_worked else 'NO HIT'}")
        print(f"  Source breakpoint (trampolines.cpp:10):  {'HIT' if source_worked else 'NO HIT'}")

        if offset_worked and not source_worked:
            print("\n*** BUG CONFIRMED: Source->Address conversion is broken ***")
        elif offset_worked and source_worked:
            print("\n*** Both work - no bug ***")
        elif not offset_worked and not source_worked:
            print("\n*** Neither works - different issue ***")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
