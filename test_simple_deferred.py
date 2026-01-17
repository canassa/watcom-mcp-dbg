"""Simple focused test for deferred breakpoint."""

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

print("Starting process...")
debugger.start()
debugger.run_event_loop()

print("\nSetting pending breakpoint for smackw32.dll:3966 (module+offset 0x3966)...")
debugger.set_breakpoint("smackw32.dll:3966")

print("\nPending breakpoints:", len([bp for bp in debugger.breakpoint_manager.get_all_breakpoints() if bp.status == "pending"]))

print("\nContinuing execution (watching for SMACKW32.DLL load)...\n")
debugger.context.set_running()

# Run for a short time to let SMACKW32.DLL load
import time
start = time.time()
while time.time() - start < 2:
    try:
        debugger.run_event_loop()
        if debugger.context.is_stopped():
            print(f"Stopped at 0x{debugger.context.current_address:08x}")
            break
    except Exception as e:
        print(f"Event loop done: {e}")
        break

print("\n\nFinal status:")
bps = debugger.breakpoint_manager.get_all_breakpoints()
print(f"Total breakpoints: {len(bps)}")
print(f"Pending: {len([bp for bp in bps if bp.status == 'pending'])}")
print(f"Active: {len([bp for bp in bps if bp.status == 'active'])}")

print("\nListing breakpoints:")
debugger.list_breakpoints()

print("\nStopping...")
debugger.stop()
