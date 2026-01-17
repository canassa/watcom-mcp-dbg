"""
Test that debugger_run stops at entry point and doesn't auto-continue.

This test verifies the fix for deferred breakpoints by confirming:
1. debugger_run() stops at entry point (doesn't auto-continue)
2. Breakpoints can be set while stopped at entry
3. Calling continue() resumes execution with breakpoints ready
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import debugger_create_session, debugger_run, debugger_set_breakpoint, debugger_continue, debugger_list_breakpoints

def test_entry_point_stop():
    """Test that run stops at entry point."""
    print("\n=== Test 1: Entry Point Stop ===")

    session_manager = SessionManager()

    # Create session
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    print(f"Create session: {result}")
    assert result['success'], f"Failed to create session: {result}"

    session_id = result['session_id']

    # Run - should stop at entry point
    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"Run result: {result}")
    assert result['success'], f"Failed to run: {result}"
    assert result['state'] == 'stopped', f"Expected stopped state, got {result['state']}"
    assert result['stop_reason'] == 'entry', f"Expected entry reason, got {result['stop_reason']}"

    print("[OK] Process stopped at entry point")
    return session_manager, session_id


def test_deferred_breakpoint_workflow():
    """Test the recommended workflow for deferred breakpoints."""
    print("\n=== Test 2: Deferred Breakpoint Workflow ===")

    session_manager = SessionManager()

    # Step 1: Create session
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    print(f"1. Create session: success={result['success']}")
    assert result['success']
    session_id = result['session_id']

    # Step 2: Set deferred breakpoint BEFORE running
    # Note: We can't set this yet because process hasn't started
    # So we'll set it after run but before continue

    # Step 3: Run - stops at entry
    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"2. Run: state={result['state']}, reason={result['stop_reason']}")
    assert result['success']
    assert result['state'] == 'stopped'

    # Step 4: Set deferred breakpoint while stopped at entry
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'trampolines.cpp:10'
    })
    print(f"3. Set breakpoint: status={result.get('status')}, location={result.get('location')}")
    assert result['success']
    # Breakpoint should be pending (DLL not loaded yet)
    assert result['status'] == 'pending', f"Expected pending, got {result['status']}"

    # Verify breakpoint is in the list
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    print(f"4. List breakpoints: {result['breakpoints']}")
    assert len(result['breakpoints']) == 1
    assert result['breakpoints'][0]['status'] == 'pending'

    # Step 5: Continue - DLL loads, breakpoint resolves
    print("5. Calling continue - DLL will load and breakpoint should resolve...")
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"   Continue result: {result}")
    assert result['success']

    # Wait a moment for DLL to load
    import time
    time.sleep(2)

    # Check if breakpoint resolved (it should activate when smackw32.dll loads)
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    print(f"6. List breakpoints after continue:")
    for bp in result['breakpoints']:
        print(f"   - {bp}")

    print("\n[OK] Deferred breakpoint workflow completed")
    print("NOTE: Whether breakpoint hits depends on if trampolines.cpp:10 executes")

    return session_manager, session_id


def test_multiple_deferred_breakpoints():
    """Test setting multiple deferred breakpoints before any DLL loads."""
    print("\n=== Test 3: Multiple Deferred Breakpoints ===")

    session_manager = SessionManager()

    # Create and run
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe',
        'source_dirs': [r'c:\watcom\h', r'c:\entomorph']
    })
    session_id = result['session_id']

    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"Process stopped at entry: {result['stop_reason']}")
    assert result['state'] == 'stopped'

    # Set multiple deferred breakpoints
    locations = [
        'trampolines.cpp:10',
        'trampolines.cpp:15',
        'trampolines.cpp:20'
    ]

    for loc in locations:
        result = debugger_set_breakpoint(session_manager, {
            'session_id': session_id,
            'location': loc
        })
        print(f"Set breakpoint at {loc}: status={result.get('status')}")
        assert result['success']
        assert result['status'] == 'pending'

    # Verify all are pending
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    print(f"\nBreakpoints before continue: {len(result['breakpoints'])} pending")
    assert len(result['breakpoints']) == 3

    print("[OK] Multiple deferred breakpoints set successfully")

    return session_manager, session_id


if __name__ == '__main__':
    print("Testing Entry Point Stop Behavior")
    print("=" * 60)

    try:
        # Test 1: Basic entry point stop
        test_entry_point_stop()

        # Test 2: Recommended workflow
        test_deferred_breakpoint_workflow()

        # Test 3: Multiple deferred breakpoints
        test_multiple_deferred_breakpoints()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED [OK]")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
