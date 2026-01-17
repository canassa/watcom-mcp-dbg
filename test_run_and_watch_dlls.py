"""
Run plague.exe WITHOUT pausing and watch for smackw32.dll to load
"""

import sys
from pathlib import Path
import time
import threading
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def test_watch_dll_loads():
    """Run debugger and watch for DLL loads."""
    print("\n=== Watching for smackw32.dll Load ===\n")

    debugger = Debugger(executable_path=r'c:\entomorph\plague.exe')

    # Track when smackw32 loads
    smackw32_loaded = False
    smackw32_base = None

    def run_debugger():
        nonlocal smackw32_loaded, smackw32_base

        try:
            # Start process
            debugger.start()
            print(f"Process started: PID={debugger.context.process_id}")

            # Set to running (don't stop at entry)
            debugger.context.set_running()
            debugger.waiting_for_event = True

            # Run event loop and watch for smackw32
            iteration = 0
            while not debugger.context.should_quit and not debugger.context.is_exited():
                debugger.run_event_loop()
                iteration += 1

                # Check if smackw32 loaded
                module = debugger.module_manager.get_module_by_name('smackw32.dll')
                if module and not smackw32_loaded:
                    smackw32_loaded = True
                    smackw32_base = module.base_address
                    print(f"\n*** smackw32.dll LOADED at 0x{smackw32_base:08x} ***")
                    print(f"    Iteration: {iteration}")
                    print(f"    Has debug info: {module.has_debug_info}")

                    # Try to resolve trampolines.cpp:10
                    if module.line_info:
                        addr = module.line_info.line_to_address("trampolines.cpp", 10)
                        if addr:
                            print(f"    trampolines.cpp:10 -> 0x{addr:08x} (DWARF relative)")
                            absolute = smackw32_base + module.code_section_offset + addr
                            print(f"    Absolute address: 0x{absolute:08x}")
                            print(f"    (base=0x{smackw32_base:08x} + code_offset=0x{module.code_section_offset:08x} + dwarf=0x{addr:08x})")

                    # Stop after finding it
                    debugger.context.should_quit = True
                    break

                # Stop after 100 iterations or 10 seconds
                if iteration > 100:
                    print(f"\nStopped after {iteration} iterations, no smackw32.dll")
                    break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    # Run in thread
    thread = threading.Thread(target=run_debugger, daemon=True)
    thread.start()

    # Wait for completion (max 15 seconds)
    thread.join(timeout=15.0)

    print(f"\n=== Result ===")
    print(f"smackw32.dll loaded: {smackw32_loaded}")
    if smackw32_loaded:
        print(f"Base address: 0x{smackw32_base:08x}")


if __name__ == '__main__':
    test_watch_dll_loads()
