"""
Detailed test to see exactly what happens with breakpoint resolution.
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

def test_breakpoint_detailed():
    """Test with detailed logging."""
    print("\n=== Detailed Breakpoint Test ===\n")

    session_manager = SessionManager()

    # Create session
    result = debugger_create_session(session_manager, {
        'executable_path': r'c:\entomorph\plague.exe'
    })
    session_id = result['session_id']
    session = session_manager.get_session(session_id)
    print(f"1. Session created")

    # Run - stop at entry
    result = debugger_run(session_manager, {'session_id': session_id})
    print(f"2. Stopped at entry: {result['stop_reason']}")

    # Set breakpoint by offset (as confirmed by x32dbg)
    print(f"\n3. Setting breakpoint: smackw32.dll:0x3966")
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': 'smackw32.dll:0x3966'
    })
    print(f"   Result: {result}")

    # Check pending breakpoints
    bp_mgr = session.debugger.breakpoint_manager
    print(f"\n   Pending breakpoints:")
    for bp in bp_mgr.pending_breakpoints:
        offset_str = f"0x{bp.offset:x}" if bp.offset is not None else "None"
        print(f"      - Module: {bp.module_name}, Offset: {offset_str}")

    # Continue
    print(f"\n4. Calling continue()...")
    result = debugger_continue(session_manager, {'session_id': session_id})
    print(f"   State: {result['state']}")

    # Wait a bit and check module loads
    print(f"\n5. Waiting for smackw32.dll to load...")

    for i in range(20):  # 10 seconds
        time.sleep(0.5)

        # Check if smackw32 loaded
        module = session.debugger.module_manager.get_module_by_name('smackw32.dll')
        if module:
            print(f"\n   *** smackw32.dll LOADED at 0x{module.base_address:08x} ***")
            print(f"       Code section offset: 0x{module.code_section_offset:08x}")

            # Check if breakpoint resolved
            result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
            if result['breakpoints']:
                bp = result['breakpoints'][0]
                print(f"\n   Breakpoint after DLL load:")
                print(f"       Status: {bp['status']}")
                if bp['status'] == 'active':
                    print(f"       Address: {bp.get('address')}")
                    print(f"       Enabled: {bp.get('enabled')}")

                    # Calculate expected address
                    expected = module.base_address + 0x3966
                    print(f"\n       Expected: 0x{expected:08x}")
                    print(f"       Actual:   {bp.get('address')}")
                    print(f"       Match: {bp.get('address') == f'0x{expected:08x}'}")

            # Check if process stopped
            if session.debugger.context.is_stopped():
                print(f"\n   *** PROCESS STOPPED ***")
                stop_info = session.debugger.context.stop_info
                if stop_info:
                    print(f"       Reason: {stop_info.reason}")
                    print(f"       Address: 0x{stop_info.address:08x}")

                # Check breakpoint hit count
                result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
                if result['breakpoints']:
                    bp = result['breakpoints'][0]
                    print(f"       Hit count: {bp.get('hit_count', 0)}")

                print(f"\n   BREAKPOINT HIT!")
                return True

            break

    # Check final state
    print(f"\n6. Final check...")
    result = debugger_list_breakpoints(session_manager, {'session_id': session_id})
    if result['breakpoints']:
        bp = result['breakpoints'][0]
        print(f"   Breakpoint status: {bp['status']}")
        print(f"   Hit count: {bp.get('hit_count', 0)}")

    module = session.debugger.module_manager.get_module_by_name('smackw32.dll')
    print(f"   smackw32.dll loaded: {module is not None}")

    if session.debugger.context.is_stopped():
        print(f"   Process is STOPPED")
    else:
        print(f"   Process is RUNNING")

    return False


if __name__ == '__main__':
    print("=" * 60)
    result = test_breakpoint_detailed()
    print("\n" + "=" * 60)
    if result:
        print("SUCCESS: Breakpoint hit!")
    else:
        print("FAILED: Breakpoint did not hit")
    print("=" * 60)
