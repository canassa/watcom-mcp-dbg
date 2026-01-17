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

    # Deferred/pending breakpoint support
    status: str = "active"  # "pending" or "active"
    pending_location: Optional[str] = None  # e.g., "smackw32.dll:100" or "smack.c:45"
    offset: Optional[int] = None  # For module+offset breakpoints (e.g., smackw32.dll:0x100)


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
        self.breakpoints = {}  # {address: Breakpoint} - active breakpoints only
        self.pending_breakpoints = []  # List[Breakpoint] - pending breakpoints
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

    def _extract_module_name(self, filename: str) -> Optional[str]:
        """Extract module name from filename if it's a DLL/EXE.

        Args:
            filename: Filename or path

        Returns:
            Module name if it's a DLL/EXE, None otherwise
        """
        from pathlib import Path
        basename = Path(filename).name.lower()
        if basename.endswith('.dll') or basename.endswith('.exe'):
            return Path(filename).name
        return None

    def set_breakpoint_deferred(self, location: str) -> Optional[Breakpoint]:
        """Set a breakpoint that may be pending if module not loaded yet.

        Supports formats:
        - "module.dll:offset" - e.g., "smackw32.dll:100" (offset in hex, base_address + 0x100)
        - "file.c:line" - e.g., "smack.c:45" (source file + line number)
        - "0xaddress" - immediate, never deferred

        Args:
            location: Location specification

        Returns:
            Breakpoint object (may be pending or active)
        """
        # Handle hex address (never deferred)
        if location.startswith('0x'):
            try:
                address = int(location, 16)
                return self.set_breakpoint_at_address(address)
            except ValueError:
                print(f"Invalid hex address: {location}")
                return None

        # Parse file:line or module:offset format
        if ':' not in location:
            print(f"Invalid location format: {location} (expected file:line or 0xaddress)")
            return None

        parts = location.split(':', 1)
        if len(parts) != 2:
            print(f"Invalid location format: {location}")
            return None

        filename = parts[0].strip()
        value_str = parts[1].strip()

        # Determine if this is a module+offset or file+line
        is_module = filename.lower().endswith('.dll') or filename.lower().endswith('.exe')

        # Initialize both variables
        offset: Optional[int] = None
        line: Optional[int] = None

        if is_module:
            # Module+offset format: treat value as hex offset
            try:
                # Parse as hex (with or without 0x prefix)
                if value_str.startswith('0x') or value_str.startswith('0X'):
                    offset = int(value_str, 16)
                else:
                    # Assume hex without prefix
                    offset = int(value_str, 16)
            except ValueError:
                print(f"Invalid offset: {value_str} (expected hex value)")
                return None
        else:
            # Source file+line format: treat value as decimal line number
            try:
                line = int(value_str, 10)
            except ValueError:
                print(f"Invalid line number: {value_str}")
                return None

        # Check for duplicate pending breakpoints
        for existing_bp in self.pending_breakpoints:
            if is_module:
                # For module+offset, check module name and offset
                assert offset is not None
                if existing_bp.module_name and existing_bp.module_name.lower() == filename.lower() and existing_bp.offset == offset:
                    print(f"Pending breakpoint already exists at {filename}:0x{offset:x}")
                    return existing_bp
            else:
                # For file+line, check file name and line
                assert line is not None
                if existing_bp.file == filename and existing_bp.line == line:
                    print(f"Pending breakpoint already exists at {filename}:{line}")
                    return existing_bp

        # Try immediate resolution first
        if is_module:
            # Module+offset: check if module is loaded
            assert offset is not None
            module = self.module_manager.get_module_by_name(filename)
            if module:
                # Module is loaded, calculate absolute address
                address = module.base_address + offset
                print(f"Resolved {filename}:0x{offset:x} to 0x{address:08x} ({module.name})")
                bp = self.set_breakpoint_at_address(address)
                if bp:
                    bp.module_name = module.name
                    bp.offset = offset
                return bp
        else:
            # Source file+line: try to resolve to address
            assert line is not None
            result = self.module_manager.resolve_line_to_address(filename, line)
            if result:
                # Module is loaded, create active breakpoint
                address, module = result
                print(f"Resolved {filename}:{line} to 0x{address:08x} ({module.name})")
                bp = self.set_breakpoint_at_address(address)
                if bp:
                    bp.file = filename
                    bp.line = line
                    bp.module_name = module.name
                return bp

        # Module not loaded or source not found, create pending breakpoint
        if is_module:
            assert offset is not None
            print(f"Module not loaded for {filename}:0x{offset:x}, creating pending breakpoint")
        else:
            assert line is not None
            print(f"Module not loaded for {filename}:{line}, creating pending breakpoint")

        # Extract module name if it's a DLL/EXE
        module_name = self._extract_module_name(filename) if is_module else None

        # Create pending breakpoint
        bp = Breakpoint(
            id=self.next_id,
            address=0,  # No valid address yet
            original_byte=b'',  # Nothing installed yet
            enabled=False,
            status="pending",
            pending_location=location,
            file=filename if not is_module else None,
            line=line if not is_module else None,
            module_name=module_name,
            offset=offset if is_module else None
        )

        self.pending_breakpoints.append(bp)
        self.next_id += 1

        return bp

    def resolve_pending_breakpoints_for_module(self, module_name: str) -> list:
        """Resolve pending breakpoints for a newly loaded module.

        Called when a DLL loads. Attempts to resolve all pending breakpoints
        that match this module.

        Args:
            module_name: Name of the module that just loaded (e.g., "smackw32.dll")

        Returns:
            List of breakpoints that were successfully resolved and activated
        """
        # Early exit if no pending breakpoints
        if not self.pending_breakpoints:
            return []

        resolved_breakpoints = []
        remaining_pending = []

        for bp in self.pending_breakpoints:
            # Check if this breakpoint matches this module
            matches = False

            # Explicit module match (e.g., bp.module_name = "smackw32.dll", module_name = "smackw32.dll")
            if bp.module_name and bp.module_name.lower() == module_name.lower():
                matches = True
            # Source file match - try to resolve against this module's debug info
            elif bp.file and not bp.module_name:
                # This is a source file (e.g., "smack.c"), not a module name
                # Try resolution to see if this module has debug info for this file
                result = self.module_manager.resolve_line_to_address(bp.file, bp.line)
                if result:
                    # Check if the resolved address belongs to this module
                    address, resolved_module = result
                    if resolved_module.name.lower() == module_name.lower():
                        matches = True

            if not matches:
                # Keep in pending list
                remaining_pending.append(bp)
                continue

            # Try to resolve the breakpoint
            if bp.offset is not None:
                # Module+offset breakpoint: calculate absolute address
                module = self.module_manager.get_module_by_name(module_name)
                if not module:
                    remaining_pending.append(bp)
                    continue

                address = module.base_address + bp.offset
            else:
                # Source file+line breakpoint: resolve through DWARF
                result = self.module_manager.resolve_line_to_address(bp.file, bp.line)
                if not result:
                    # Still can't resolve, keep pending
                    remaining_pending.append(bp)
                    continue

                address, module = result

            # Check if breakpoint already exists at this address
            if address in self.breakpoints:
                print(f"  Warning: Breakpoint already exists at 0x{address:08x}")
                # Don't add duplicate, but consider this resolved
                resolved_breakpoints.append(bp)
                continue

            # Read original byte
            try:
                original_byte = self.process_controller.read_memory(address, 1)
            except Exception as e:
                print(f"  Failed to read memory at 0x{address:08x}: {e}")
                remaining_pending.append(bp)
                continue

            # Write INT 3 (0xCC)
            try:
                self.process_controller.write_memory(address, b'\xCC')
            except Exception as e:
                print(f"  Failed to write breakpoint at 0x{address:08x}: {e}")
                remaining_pending.append(bp)
                continue

            # Verify INT 3 was written
            verify_byte = self.process_controller.read_memory(address, 1)
            if verify_byte != b'\xCC':
                print(f"  Breakpoint verification failed at 0x{address:08x}")
                remaining_pending.append(bp)
                continue

            # Update breakpoint to active status
            bp.address = address
            bp.original_byte = original_byte
            bp.enabled = True
            bp.status = "active"
            bp.module_name = module.name

            # Move from pending list to active dict
            self.breakpoints[address] = bp
            resolved_breakpoints.append(bp)

            if bp.offset is not None:
                print(f"  - BP {bp.id}: {bp.module_name}:0x{bp.offset:x} -> 0x{address:08x}")
            else:
                print(f"  - BP {bp.id}: {bp.file}:{bp.line} -> 0x{address:08x}")

        # Update pending list with remaining unresolved breakpoints
        self.pending_breakpoints = remaining_pending

        return resolved_breakpoints

    def unpend_breakpoints_for_module(self, module_name: str) -> int:
        """Move active breakpoints back to pending when a module unloads.

        Args:
            module_name: Name of the module being unloaded

        Returns:
            Number of breakpoints moved back to pending
        """
        breakpoints_to_unpend = []

        # Find all breakpoints in this module
        for address, bp in list(self.breakpoints.items()):
            if bp.module_name and bp.module_name.lower() == module_name.lower():
                breakpoints_to_unpend.append((address, bp))

        # Move them back to pending
        count = 0
        for address, bp in breakpoints_to_unpend:
            # Remove from active breakpoints
            del self.breakpoints[address]

            # Reset to pending state
            bp.address = None
            bp.original_byte = None
            bp.status = "pending"
            bp.enabled = False

            # Add back to pending list
            self.pending_breakpoints.append(bp)
            count += 1

            print(f"  - BP {bp.id} ({bp.file}:{bp.line}) moved back to pending")

        return count

    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint by ID (handles both active and pending).

        Args:
            breakpoint_id: Breakpoint ID

        Returns:
            True if removed, False if not found
        """
        # Check active breakpoints first
        for bp in self.breakpoints.values():
            if bp.id == breakpoint_id:
                return self.remove_breakpoint_at_address(bp.address)

        # Check pending breakpoints
        for i, bp in enumerate(self.pending_breakpoints):
            if bp.id == breakpoint_id:
                del self.pending_breakpoints[i]
                return True

        return False

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
        """Get all breakpoints (both active and pending).

        Returns:
            List of breakpoints sorted by ID
        """
        all_bps = list(self.breakpoints.values()) + self.pending_breakpoints
        return sorted(all_bps, key=lambda bp: bp.id)

    def clear_all(self):
        """Remove all breakpoints (both active and pending)."""
        # Clear active breakpoints
        addresses = list(self.breakpoints.keys())
        for address in addresses:
            self.remove_breakpoint_at_address(address)

        # Clear pending breakpoints
        self.pending_breakpoints.clear()
