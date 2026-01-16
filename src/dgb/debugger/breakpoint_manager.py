"""
Breakpoint manager for software breakpoints.

Handles setting, removing, and managing breakpoints using INT 3 (0xCC) instruction.
"""

from dataclasses import dataclass
from typing import Optional

from dgb.debugger.process_controller import ProcessController
from dgb.debugger.module_manager import ModuleManager


@dataclass
class Breakpoint:
    """Represents a breakpoint."""

    id: int  # Breakpoint ID
    address: int  # Absolute memory address
    original_byte: bytes  # Original instruction byte (before 0xCC)
    enabled: bool = True  # Whether breakpoint is enabled
    hit_count: int = 0  # Number of times hit

    # Source location (if available)
    file: Optional[str] = None
    line: Optional[int] = None
    module_name: Optional[str] = None

    # Temporary flag (for step-over, etc.)
    temporary: bool = False


class BreakpointManager:
    """Manages software breakpoints.

    Software breakpoints work by:
    1. Read original byte at target address
    2. Write 0xCC (INT 3) to target address
    3. When hit, restore original byte and rewind instruction pointer
    """

    def __init__(self, process_controller: ProcessController, module_manager: ModuleManager):
        self.process_controller = process_controller
        self.module_manager = module_manager
        self.breakpoints = {}  # {address: Breakpoint}
        self.next_id = 1

    def set_breakpoint_at_address(self, address: int) -> Optional[Breakpoint]:
        """Set a breakpoint at an address.

        Args:
            address: Absolute memory address

        Returns:
            Breakpoint object if successful, None otherwise
        """
        # Check if breakpoint already exists
        if address in self.breakpoints:
            print(f"Breakpoint already exists at 0x{address:08x}")
            return self.breakpoints[address]

        # Read original byte
        original_byte = self.process_controller.read_memory(address, 1)

        # Write INT 3 (0xCC)
        self.process_controller.write_memory(address, b'\xCC')

        # Verify INT 3 was written
        verify_byte = self.process_controller.read_memory(address, 1)
        if verify_byte != b'\xCC':
            raise RuntimeError(
                f"Breakpoint verification failed at 0x{address:08x}: "
                f"wrote 0xCC but read back {verify_byte.hex()}"
            )

        # Resolve source location
        result = self.module_manager.resolve_address_to_line(address)
        if result:
            module_name, loc, module = result
            file = loc.file
            line = loc.line
        else:
            module_name = None
            file = None
            line = None

        # Create breakpoint
        bp = Breakpoint(
            id=self.next_id,
            address=address,
            original_byte=original_byte,
            enabled=True,
            file=file,
            line=line,
            module_name=module_name
        )

        self.breakpoints[address] = bp
        self.next_id += 1

        return bp

    def set_breakpoint_at_line(self, filename: str, line: int) -> Optional[Breakpoint]:
        """Set a breakpoint at a source file line.

        Args:
            filename: Source file name (can be basename or full path)
            line: Line number

        Returns:
            Breakpoint object if successful, None otherwise
        """
        # Resolve file:line to address using module manager
        result = self.module_manager.resolve_line_to_address(filename, line)
        if not result:
            print(f"Could not resolve {filename}:{line} to an address")
            return None

        address, module = result
        print(f"Resolved {filename}:{line} to 0x{address:08x} ({module.name})")

        # Set breakpoint at the resolved address
        bp = self.set_breakpoint_at_address(address)
        if bp:
            bp.file = filename
            bp.line = line
            bp.module_name = module.name

        return bp

    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint by ID.

        Args:
            breakpoint_id: Breakpoint ID

        Returns:
            True if removed, False if not found
        """
        # Find breakpoint by ID
        bp = None
        for b in self.breakpoints.values():
            if b.id == breakpoint_id:
                bp = b
                break

        if not bp:
            return False

        return self.remove_breakpoint_at_address(bp.address)

    def remove_breakpoint_at_address(self, address: int) -> bool:
        """Remove a breakpoint at an address.

        Args:
            address: Absolute memory address

        Returns:
            True if removed, False if not found
        """
        if address not in self.breakpoints:
            return False

        bp = self.breakpoints[address]

        # Restore original byte
        if bp.enabled:
            self.process_controller.write_memory(address, bp.original_byte)

        # Remove from tracking
        del self.breakpoints[address]
        return True

    def on_breakpoint_hit(self, address: int, thread_id: int) -> Optional[Breakpoint]:
        """Handle a breakpoint hit.

        Args:
            address: Address where breakpoint was hit
            thread_id: Thread ID that hit the breakpoint

        Returns:
            Breakpoint object if this is a known breakpoint, None otherwise
        """
        if address not in self.breakpoints:
            return None

        bp = self.breakpoints[address]
        bp.hit_count += 1

        # Restore original instruction
        self.process_controller.write_memory(address, bp.original_byte)

        # Rewind instruction pointer so we can re-execute the original instruction
        # Get current IP register name (Eip for 32-bit, Rip for 64-bit)
        try:
            # Try 32-bit first
            current_ip = self.process_controller.get_register(thread_id, 'Eip')
            self.process_controller.set_register(thread_id, 'Eip', address)
        except Exception:
            # Try 64-bit
            try:
                current_ip = self.process_controller.get_register(thread_id, 'Rip')
                self.process_controller.set_register(thread_id, 'Rip', address)
            except Exception as e:
                print(f"Failed to rewind instruction pointer: {e}")

        # If temporary breakpoint, remove it
        if bp.temporary:
            del self.breakpoints[address]
        else:
            # Mark as disabled (will be re-enabled on continue)
            bp.enabled = False

        return bp

    def re_enable_breakpoint(self, address: int) -> bool:
        """Re-enable a breakpoint after it was hit.

        This writes the INT 3 back after we've executed the original instruction.

        Args:
            address: Breakpoint address

        Returns:
            True if re-enabled, False otherwise
        """
        if address not in self.breakpoints:
            return False

        bp = self.breakpoints[address]
        if bp.enabled:
            return True  # Already enabled

        # Write INT 3 again
        self.process_controller.write_memory(address, b'\xCC')
        bp.enabled = True
        return True

    def get_breakpoint_at_address(self, address: int) -> Optional[Breakpoint]:
        """Get breakpoint at an address.

        Args:
            address: Address

        Returns:
            Breakpoint if found, None otherwise
        """
        return self.breakpoints.get(address)

    def get_breakpoint_by_id(self, breakpoint_id: int) -> Optional[Breakpoint]:
        """Get breakpoint by ID.

        Args:
            breakpoint_id: Breakpoint ID

        Returns:
            Breakpoint if found, None otherwise
        """
        for bp in self.breakpoints.values():
            if bp.id == breakpoint_id:
                return bp
        return None

    def get_all_breakpoints(self):
        """Get all breakpoints.

        Returns:
            List of breakpoints sorted by ID
        """
        return sorted(self.breakpoints.values(), key=lambda bp: bp.id)

    def clear_all(self):
        """Remove all breakpoints."""
        addresses = list(self.breakpoints.keys())
        for address in addresses:
            self.remove_breakpoint_at_address(address)
