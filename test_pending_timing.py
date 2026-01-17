"""Test timing of pending breakpoint - must set BEFORE process starts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

executable = r"c:\entomorph\plague.exe"

if not Path(executable).exists():
    print(f"ERROR: {executable} not found")
    sys.exit(1)

print("Creating debugger...")
debugger = Debugger(executable)

print("\n=== CRITICAL: Setting pending breakpoint BEFORE process starts ===")
print("Setting pending breakpoint: smackw32.dll:3966")
bp = debugger.breakpoint_manager.set_breakpoint_deferred("smackw32.dll:3966")
print(f"Breakpoint created: ID={bp.id}, status={bp.status}, module_name={bp.module_name}, offset={bp.offset}")

print("\nPending breakpoints:", len(debugger.breakpoint_manager.pending_breakpoints))
for pending_bp in debugger.breakpoint_manager.pending_breakpoints:
    print(f"  BP {pending_bp.id}: {pending_bp.module_name}:0x{pending_bp.offset:x} (status={pending_bp.status})")

print("\n=== NOW starting process ===")
debugger.start()
debugger.run_event_loop()

print("\n=== Setting control breakpoint at 0x0045240f ===")
debugger.set_breakpoint("0x0045240f")

print("\n=== Continuing execution (will hit control BP first) ===")
debugger.context.set_running()

import time
timeout = 5
start = time.time()
while time.time() - start < timeout:
    try:
        debugger.run_event_loop()
        if debugger.context.is_stopped():
            addr = debugger.context.current_address
            print(f"\n*** STOPPED at 0x{addr:08x} ***")

            # Check breakpoint status
            all_bps = debugger.breakpoint_manager.get_all_breakpoints()
            print(f"\nAll breakpoints ({len(all_bps)}):")
            for bp in all_bps:
                if bp.status == "pending":
                    print(f"  BP {bp.id}: {bp.pending_location} - PENDING")
                else:
                    print(f"  BP {bp.id}: 0x{bp.address:08x} - {bp.status} (hits={bp.hit_count})")

            # Continue to next breakpoint
            print("\n=== Continuing to next breakpoint ===")
            debugger.context.set_running()
            start = time.time()  # Reset timeout
    except Exception as e:
        print(f"Event loop error: {e}")
        break

print("\n\n=== Final status ===")
all_bps = debugger.breakpoint_manager.get_all_breakpoints()
print(f"Total breakpoints: {len(all_bps)}")
print(f"Pending: {len([bp for bp in all_bps if bp.status == 'pending'])}")
print(f"Active: {len([bp for bp in all_bps if bp.status == 'active'])}")

for bp in all_bps:
    if bp.status == "pending":
        print(f"  BP {bp.id}: {bp.pending_location} - PENDING")
    else:
        print(f"  BP {bp.id}: 0x{bp.address:08x} - {bp.status}")

print("\nStopping...")
debugger.stop()
