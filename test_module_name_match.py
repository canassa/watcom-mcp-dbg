"""Test module name matching in pending breakpoint resolution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

executable = r"c:\entomorph\plague.exe"

if not Path(executable).exists():
    print(f"ERROR: {executable} not found")
    sys.exit(1)

print("Creating debugger and starting process...")
debugger = Debugger(executable)
debugger.start()
debugger.run_event_loop()  # Process initial events

print("\n=== Setting pending breakpoint ===")
bp = debugger.breakpoint_manager.set_breakpoint_deferred("smackw32.dll:3966")
print(f"Created: BP {bp.id}")
print(f"  status: {bp.status}")
print(f"  module_name: '{bp.module_name}'")
print(f"  offset: 0x{bp.offset:x}")
print(f"  pending_location: {bp.pending_location}")

print(f"\nPending breakpoints: {len(debugger.breakpoint_manager.pending_breakpoints)}")

print("\n=== Continuing execution to trigger DLL loads ===")
debugger.context.set_running()

import time
timeout = 3
start = time.time()
events_processed = 0

while time.time() - start < timeout:
    try:
        debugger.run_event_loop()
        events_processed += 1

        # Check if process stopped
        if debugger.context.is_stopped():
            print(f"\nProcess stopped at 0x{debugger.context.current_address:08x}")
            break

        # Check if any breakpoints resolved
        pending_count = len(debugger.breakpoint_manager.pending_breakpoints)
        active_count = len(debugger.breakpoint_manager.breakpoints)

        if active_count > 0 or pending_count == 0:
            print(f"\n*** Breakpoint status changed! ***")
            print(f"Active: {active_count}, Pending: {pending_count}")
            break

    except Exception as e:
        print(f"Event loop completed: {e}")
        break

print(f"\nEvents processed: {events_processed}")

print("\n=== Loaded modules ===")
for name, module in debugger.module_manager.modules.items():
    print(f"  '{name}' at 0x{module.base_address:08x}")
    # Check if this should match our breakpoint
    if "smackw32" in name.lower():
        print(f"    ^^ THIS SHOULD MATCH 'smackw32.dll'!")
        print(f"    bp.module_name='{bp.module_name}'")
        print(f"    module.name='{module.name}'")
        print(f"    Comparison: bp.module_name.lower()='{bp.module_name.lower()}' vs module.name.lower()='{module.name.lower()}'")
        print(f"    Match? {bp.module_name.lower() == module.name.lower()}")

print("\n=== Final breakpoint status ===")
all_bps = debugger.breakpoint_manager.get_all_breakpoints()
for bp in all_bps:
    if bp.status == "pending":
        print(f"  BP {bp.id}: {bp.pending_location} - PENDING")
    else:
        print(f"  BP {bp.id}: 0x{bp.address:08x} - {bp.status}")

print("\nStopping...")
debugger.stop()
