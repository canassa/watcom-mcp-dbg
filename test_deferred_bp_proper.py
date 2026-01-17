"""Test deferred breakpoint with proper event loop handling."""
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    debugger = Debugger(r"C:\entomorph\plague.exe")

    print("=" * 60)
    print("Starting debugger (creates process)...")
    debugger.start()

    # Set pending breakpoint BEFORE running event loop
    print("\n" + "=" * 60)
    print("Setting deferred breakpoint at smackw32.dll:0x3966")
    success = debugger.set_breakpoint("smackw32.dll:0x3966")

    print("\nInitial breakpoint status:")
    debugger.list_breakpoints()

    # Run event loop in background thread (like MCP server does)
    print("\n" + "=" * 60)
    print("Starting persistent event loop in background...")

    should_quit = False

    def event_loop_thread():
        """Mimics the MCP server's persistent event loop."""
        print("[EventLoop] Starting...")
        while not debugger.context.should_quit and not debugger.context.is_exited():
            debugger.run_event_loop()

            if debugger.context.is_stopped():
                stop_reason = debugger.context.stop_info.reason if debugger.context.stop_info else "unknown"
                addr = debugger.context.current_address
                print(f"\n[EventLoop] STOPPED: reason={stop_reason}, address=0x{addr:08x if addr else 0:08x}")

                if stop_reason == "entry":
                    print("[EventLoop] Hit initial breakpoint, continuing...")
                    time.sleep(0.5)
                    debugger.context.set_running()
                    debugger.waiting_for_event = True
                elif stop_reason == "breakpoint":
                    print("[EventLoop] HIT USER BREAKPOINT!")
                    debugger.list_breakpoints()
                    # Stay stopped
                    break
                else:
                    print(f"[EventLoop] Stopped for {stop_reason}, continuing...")
                    time.sleep(0.5)
                    debugger.context.set_running()
                    debugger.waiting_for_event = True

            # Brief sleep while stopped
            while debugger.context.is_stopped() and not debugger.context.is_exited():
                time.sleep(0.01)

        print(f"[EventLoop] Exited: state={debugger.context.state.value}")

    loop_thread = threading.Thread(target=event_loop_thread, daemon=True)
    loop_thread.start()

    # Wait for completion (max 15 seconds)
    loop_thread.join(timeout=15)

    print("\n" + "=" * 60)
    print("Final state:")
    print(f"  State: {debugger.context.state.value}")
    if debugger.context.is_exited():
        print(f"  Exit code: {debugger.context.exit_code}")

    print("\nFinal breakpoint status:")
    debugger.list_breakpoints()

    debugger.stop()

if __name__ == "__main__":
    main()
