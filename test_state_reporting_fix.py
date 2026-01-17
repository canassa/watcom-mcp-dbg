"""
Test the state reporting fix for MCP debugger tools.

This test verifies that:
1. debugger_run returns state="stopped" at initial breakpoint
2. debugger_get_registers returns actual register values (not zeros)
3. Process is paused and examinable at entry point
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.server.session_manager import SessionManager
from dgb.server.tools import (
    debugger_create_session,
    debugger_run,
    debugger_get_registers,
    debugger_list_modules,
    debugger_set_breakpoint,
    debugger_close_session
)


def test_state_reporting_fix():
    """Test that state reporting works correctly after the fix."""
    exe_path = "c:/entomorph/plague.exe"

    if not Path(exe_path).exists():
        print(f"Error: {exe_path} not found")
        print("Please update the exe_path in the test script to point to a valid executable")
        return False

    print("=" * 60)
    print("Testing State Reporting Fix")
    print("=" * 60)

    # Create session manager
    session_manager = SessionManager()

    # Test 1: Create session
    print("\n1. Creating debugging session...")
    result = debugger_create_session(session_manager, {
        'executable_path': exe_path
    })

    if not result['success']:
        print(f"   [FAIL] Failed to create session: {result.get('error')}")
        return False

    session_id = result['session_id']
    print(f"   [OK] Session created: {session_id}")

    # Test 2: Run debugger (should stop at initial breakpoint)
    print("\n2. Running debugger (should stop at initial breakpoint)...")
    result = debugger_run(session_manager, {
        'session_id': session_id
    })

    if not result['success']:
        print(f"   [FAIL] Failed to run debugger: {result.get('error')}")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    print(f"   State: {result.get('state')}")
    print(f"   Stop reason: {result.get('stop_reason')}")
    print(f"   Stop address: {result.get('stop_address')}")
    print(f"   Modules loaded: {result.get('modules_loaded')}")

    # Verify state is "stopped"
    if result.get('state') != 'stopped':
        print(f"   [FAIL] Expected state='stopped', got state='{result.get('state')}'")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    # Verify stop reason is "entry"
    if result.get('stop_reason') != 'entry':
        print(f"   [FAIL] Expected stop_reason='entry', got stop_reason='{result.get('stop_reason')}'")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    # Verify stop address is present
    if not result.get('stop_address'):
        print(f"   [FAIL] Expected stop_address to be present")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    print(f"   [OK] Process stopped at entry point: {result.get('stop_address')}")

    # Test 3: Get registers (should return actual values, not zeros)
    print("\n3. Reading registers...")
    result = debugger_get_registers(session_manager, {
        'session_id': session_id
    })

    if not result['success']:
        print(f"   [FAIL] Failed to get registers: {result.get('error')}")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    registers = result.get('registers', {})
    print(f"   EIP = {registers.get('EIP')}")
    print(f"   ESP = {registers.get('ESP')}")
    print(f"   EBP = {registers.get('EBP')}")

    # Verify registers are not all zeros
    if registers.get('EIP') == '0x00000000':
        print(f"   [FAIL] EIP is 0x00000000 (should have a valid value)")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    if registers.get('ESP') == '0x00000000':
        print(f"   [FAIL] ESP is 0x00000000 (should have a valid value)")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    print(f"   [OK] Registers have valid values")

    # Test 4: List modules
    print("\n4. Listing modules...")
    result = debugger_list_modules(session_manager, {
        'session_id': session_id
    })

    if not result['success']:
        print(f"   [FAIL] Failed to list modules: {result.get('error')}")
        debugger_close_session(session_manager, {'session_id': session_id})
        return False

    modules = result.get('modules', [])
    print(f"   [OK] Loaded {len(modules)} modules:")
    for module in modules[:3]:  # Show first 3
        print(f"     - {module['name']} at {module['base_address']}")

    # Test 5: Set a breakpoint (optional - just to verify we can)
    print("\n5. Setting a breakpoint at 0x00401000...")
    result = debugger_set_breakpoint(session_manager, {
        'session_id': session_id,
        'location': '0x00401000'
    })

    if result['success']:
        print(f"   [OK] Breakpoint set at {result.get('address')}")
    else:
        # This might fail if the address is invalid, which is OK for this test
        print(f"   [INFO] Could not set breakpoint (may be invalid address): {result.get('error')}")

    # Test 6: Clean up
    print("\n6. Closing session...")
    result = debugger_close_session(session_manager, {
        'session_id': session_id
    })

    if not result['success']:
        print(f"   [FAIL] Failed to close session: {result.get('error')}")
        return False

    print(f"   [OK] Session closed")

    # Summary
    print("\n" + "=" * 60)
    print("[SUCCESS] State Reporting Fix Verified!")
    print("=" * 60)
    print("\nKey verification points:")
    print("  [OK] debugger_run returns state='stopped' at initial breakpoint")
    print("  [OK] debugger_run returns stop_reason='entry'")
    print("  [OK] debugger_run returns valid stop_address")
    print("  [OK] debugger_get_registers returns actual register values")
    print("  [OK] Registers EIP and ESP have non-zero values")
    print("  [OK] Process is paused and examinable at entry point")
    print("  [OK] Modules can be listed successfully")
    return True


if __name__ == '__main__':
    try:
        success = test_state_reporting_fix()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
