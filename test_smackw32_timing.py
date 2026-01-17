"""
Investigate WHEN smackw32.dll loads and whether trampolines.cpp:10 executes before breakpoint is installed.

This test will:
1. Stop at entry point
2. Set pending breakpoint for trampolines.cpp:10
3. Continue and watch for DLL load events
4. Track when smackw32.dll loads
5. Track when/if breakpoint resolves
6. Track if function executes
"""

import sys
from pathlib import Path
import time
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import (
    debugger_create_session, debugger_run, debugger_set_breakpoint,
    debugger_continue, debugger_list_breakpoints, debugger_list_modules
)

def test_smackw32_load_timing():
    """Track when smackw32.dll loads and when breakpoint resolves."""
    print("\n=== Tracking smackw32.dll Load Timing ===\n")

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
    print(f"   Modules loaded: {result['modules_loaded']}")

    # Check modules at entry point
    result = debugger_list_modules(session_manager, {'session_id': session_id})
    print(f"\n3. Modules at entry point:")
    for mod in result['modules']:
        print(f"   - {mod['name']} at {mod['base_address']}")

    smackw32_loaded_at_entry = any(mod['name'] == 'smackw32.dll' for mod in result['modules'])
    print(f"\n   smackw32.dll loaded at entry? {smackw32_loaded_at_entry}")

    # Set pending breakpoint
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'trampolines.cpp:10'
    })
    print(f"\n4. Breakpoint set: status={result.get('status')}")
    if result['status'] == 'pending':
        print(f"   Location: {result.get('location')}")
        print(f"   (Waiting for module to load)")
    elif result['status'] == 'active':
        print(f"   Address: {result.get('address')}")
        print(f"   Module: {result.get('module_name')}")
        print(f"   *** BREAKPOINT ALREADY ACTIVE AT ENTRY POINT ***")

    # Continue execution
    print(f"\n5. Calling continue()...")
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"   Continue result: {result['state']}")

    # Wait and periodically check module list
    print(f"\n6. Monitoring module loads and breakpoint status...")
    for i in range(10):  # Check for 10 seconds
        time.sleep(1)

        # Check modules
        result = debugger_list_modules(session_manager, {'session_id': session_id})
        modules = result['modules']

        smackw32_now_loaded = any(mod['name'] == 'smackw32.dll' for mod in modules)

        # Check breakpoint status
        result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
        breakpoints = result['breakpoints']

        if breakpoints:
            bp_status = breakpoints[0]['status']

            if smackw32_now_loaded and bp_status == 'active':
                print(f"   [{i+1}s] smackw32.dll LOADED, breakpoint ACTIVE")
                print(f"          Address: {breakpoints[0].get('address')}")
                break
            elif smackw32_now_loaded and bp_status == 'pending':
                print(f"   [{i+1}s] *** PROBLEM: smackw32.dll LOADED but breakpoint STILL PENDING ***")
                # List all modules to see what's loaded
                print(f"\n   All modules:")
                for mod in modules:
                    print(f"      - {mod['name']}: debug_info={mod['has_debug_info']}")
                break
            elif not smackw32_now_loaded:
                print(f"   [{i+1}s] smackw32.dll not yet loaded, breakpoint={bp_status}")
            else:
                print(f"   [{i+1}s] status: smackw32={smackw32_now_loaded}, bp={bp_status}")

    # Final status
    print(f"\n7. Final status:")
    result = debugger_list_modules(session_manager, {'session_id': session_id})
    smackw32_final = next((m for m in result['modules'] if m['name'] == 'smackw32.dll'), None)
    if smackw32_final:
        print(f"   smackw32.dll: {smackw32_final['base_address']}")
        print(f"   has_debug_info: {smackw32_final['has_debug_info']}")
    else:
        print(f"   smackw32.dll: NOT LOADED")

    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    if result['breakpoints']:
        bp = result['breakpoints'][0]
        print(f"   Breakpoint: {bp['status']}")
        if bp['status'] == 'active':
            print(f"   Address: {bp.get('address')}")
            print(f"   Hit count: {bp.get('hit_count', 0)}")

    return session_manager, session_id


if __name__ == '__main__':
    print("Investigating smackw32.dll Load Timing")
    print("=" * 60)

    try:
        test_smackw32_load_timing()
        print("\n" + "=" * 60)
        print("Investigation complete")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
