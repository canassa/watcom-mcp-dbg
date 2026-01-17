"""Test pending breakpoint and verify it actually stops execution."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dgb.debugger.core import Debugger

def main():
    debugger = Debugger(r"C:\entomorph\plague.exe")

    print("=" * 60)
    print("Starting debugger...")
    debugger.start()

    # Set pending breakpoint BEFORE running
    print("\n" + "=" * 60)
    print("Setting pending breakpoint at smackw32.dll:0x3966")
    success = debugger.set_breakpoint("smackw32.dll:0x3966")
    if not success:
        print("Failed to set breakpoint")
        return

    print("\n" + "=" * 60)
    print("Listing breakpoints (should be pending):")
    debugger.list_breakpoints()

    # Start execution
    print("\n" + "=" * 60)
    print("Starting process execution...")
    debugger.continue_execution()

    # Check if we stopped
    print("\n" + "=" * 60)
    print(f"Debugger state: {debugger.context.state}")
    if debugger.context.is_stopped():
        print(f"✓ STOPPED at {debugger.context.stop_info}")
        print(f"  Address: 0x{debugger.context.current_address:08x}")
    elif debugger.context.is_exited():
        print(f"✗ Process exited (code {debugger.context.exit_code})")
    else:
        print(f"Still running...")

    print("\n" + "=" * 60)
    print("Final breakpoint status:")
    debugger.list_breakpoints()

    print("\n" + "=" * 60)
    print("Loaded modules with debug info:")
    for module in debugger.module_manager.get_modules_with_debug_info():
        print(f"  0x{module.base_address:08x}  {module.name}")
        print(f"    Code section offset: 0x{module.code_section_offset:x}")

    debugger.stop()

if __name__ == "__main__":
    main()
