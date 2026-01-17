"""Test deferred/pending breakpoint functionality.

This test verifies that we can set breakpoints in DLLs before they're loaded,
and that they automatically activate when the DLL loads.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger


def test_deferred_breakpoint():
    """Test setting a breakpoint in a DLL before it loads."""
    print("=" * 80)
    print("Testing Deferred/Pending Breakpoint Functionality")
    print("=" * 80)

    # Use plague.exe which loads smackw32.dll
    executable = r"c:\entomorph\plague.exe"

    if not Path(executable).exists():
        print(f"ERROR: {executable} not found")
        print("Please update the path to your test executable")
        return False

    print(f"\n1. Creating debugger for: {executable}")
    debugger = Debugger(executable)

    print("\n2. Starting process and running to initial breakpoint...")
    try:
        debugger.start()
        debugger.run_event_loop()  # Run until first breakpoint/event

        if debugger.context.is_stopped():
            print(f"   Stopped at 0x{debugger.context.current_address:08x}")
    except Exception as e:
        print(f"ERROR: Failed to start process: {e}")
        return False

    print("\n3. Setting PENDING breakpoint in smackw32.dll BEFORE it loads...")
    # Try to set a breakpoint in smackw32.dll at line 100
    # This should create a pending breakpoint since the DLL isn't loaded yet
    success = debugger.set_breakpoint("smackw32.dll:100")

    if not success:
        print("ERROR: Failed to set pending breakpoint")
        debugger.stop()
        return False

    print("\n4. Listing breakpoints (should show as PENDING)...")
    debugger.list_breakpoints()

    # Verify we have exactly 1 pending breakpoint
    bps = debugger.breakpoint_manager.get_all_breakpoints()
    pending_bps = [bp for bp in bps if bp.status == "pending"]

    if len(pending_bps) != 1:
        print(f"\nERROR: Expected 1 pending breakpoint, found {len(pending_bps)}")
        debugger.stop()
        return False

    print("\n5. Continuing execution to let smackw32.dll load...")
    print("   (Watch for '[DLL Load] Resolved X pending breakpoint(s)' message)")

    try:
        # Continue execution - this should load smackw32.dll
        debugger.context.set_running()
        debugger.run_event_loop()

        print("\n6. Checking if breakpoint was resolved...")
        bps = debugger.breakpoint_manager.get_all_breakpoints()
        pending_bps = [bp for bp in bps if bp.status == "pending"]
        active_bps = [bp for bp in bps if bp.status == "active"]

        print(f"\n   Pending breakpoints: {len(pending_bps)}")
        print(f"   Active breakpoints: {len(active_bps)}")

        if len(active_bps) > 0:
            print("\n   SUCCESS! Breakpoint was resolved when DLL loaded:")
            for bp in active_bps:
                print(f"     BP {bp.id}: 0x{bp.address:08x} ({bp.file}:{bp.line}) [{bp.module_name}]")

        print("\n7. Listing all breakpoints...")
        debugger.list_breakpoints()

        print("\n8. Listing loaded modules...")
        debugger.list_modules()

    except Exception as e:
        print(f"\nERROR during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n9. Stopping debugger...")
        debugger.stop()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

    return True


def test_multiple_deferred_breakpoints():
    """Test setting multiple deferred breakpoints."""
    print("\n\n" + "=" * 80)
    print("Testing Multiple Deferred Breakpoints")
    print("=" * 80)

    executable = r"c:\entomorph\plague.exe"

    if not Path(executable).exists():
        print(f"ERROR: {executable} not found")
        return False

    print(f"\n1. Creating debugger for: {executable}")
    debugger = Debugger(executable)

    print("\n2. Starting process and running to initial breakpoint...")
    try:
        debugger.start()
        debugger.run_event_loop()

        if debugger.context.is_stopped():
            print(f"   Stopped at 0x{debugger.context.current_address:08x}")
    except Exception as e:
        print(f"ERROR: Failed to start process: {e}")
        return False

    print("\n3. Setting MULTIPLE pending breakpoints...")
    locations = [
        "smackw32.dll:100",
        "smackw32.dll:200",
        "smackw32.dll:300"
    ]

    for loc in locations:
        success = debugger.set_breakpoint(loc)
        if not success:
            print(f"ERROR: Failed to set breakpoint at {loc}")

    print("\n4. Listing breakpoints (should all be PENDING)...")
    debugger.list_breakpoints()

    print("\n5. Continuing execution...")
    try:
        debugger.context.set_running()
        debugger.run_event_loop()

        print("\n6. Checking resolved breakpoints...")
        debugger.list_breakpoints()

    except Exception as e:
        print(f"\nERROR during execution: {e}")
    finally:
        print("\n7. Stopping debugger...")
        debugger.stop()

    print("\n" + "=" * 80)
    print("Multiple breakpoints test completed!")
    print("=" * 80)

    return True


def test_mixed_breakpoints():
    """Test setting a mix of immediate and deferred breakpoints."""
    print("\n\n" + "=" * 80)
    print("Testing Mixed Immediate and Deferred Breakpoints")
    print("=" * 80)

    executable = r"c:\entomorph\plague.exe"

    if not Path(executable).exists():
        print(f"ERROR: {executable} not found")
        return False

    print(f"\n1. Creating debugger for: {executable}")
    debugger = Debugger(executable)

    print("\n2. Starting process and running to let modules load...")
    try:
        debugger.start()
        debugger.run_event_loop()  # Initial breakpoint

        # Continue to let DLLs load
        debugger.context.set_running()
        debugger.run_event_loop()
    except Exception as e:
        print(f"Note: Process may have stopped: {e}")

    print("\n3. Listing loaded modules...")
    debugger.list_modules()

    print("\n4. Setting breakpoints (mix of immediate and deferred)...")

    # Try to set a breakpoint in already-loaded smackw32.dll (should be immediate)
    print("   - Setting breakpoint in loaded DLL (should be ACTIVE)...")
    debugger.set_breakpoint("smackw32.dll:100")

    # Try to set a breakpoint in a DLL that doesn't exist (should be pending)
    print("   - Setting breakpoint in non-existent DLL (should be PENDING)...")
    debugger.set_breakpoint("nonexistent.dll:50")

    print("\n5. Listing breakpoints (should show mix of ACTIVE and PENDING)...")
    debugger.list_breakpoints()

    print("\n6. Stopping debugger...")
    debugger.stop()

    print("\n" + "=" * 80)
    print("Mixed breakpoints test completed!")
    print("=" * 80)

    return True


if __name__ == '__main__':
    print("\nDeferred/Pending Breakpoint Test Suite\n")

    # Run tests
    test_deferred_breakpoint()

    # Uncomment to run additional tests
    # test_multiple_deferred_breakpoints()
    # test_mixed_breakpoints()

    print("\n\nAll tests completed!")
