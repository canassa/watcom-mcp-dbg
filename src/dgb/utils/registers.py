"""
Register utility helpers.
"""

# Common x86 register names
X86_REGISTERS = [
    'eax', 'ebx', 'ecx', 'edx',
    'esi', 'edi', 'ebp', 'esp',
    'eip', 'eflags'
]

# Common x64 register names
X64_REGISTERS = [
    'rax', 'rbx', 'rcx', 'rdx',
    'rsi', 'rdi', 'rbp', 'rsp',
    'rip', 'eflags',
    'r8', 'r9', 'r10', 'r11',
    'r12', 'r13', 'r14', 'r15'
]

# EFLAGS bits
EFLAGS_BITS = {
    0: 'CF',   # Carry Flag
    2: 'PF',   # Parity Flag
    4: 'AF',   # Auxiliary Carry Flag
    6: 'ZF',   # Zero Flag
    7: 'SF',   # Sign Flag
    8: 'TF',   # Trap Flag
    9: 'IF',   # Interrupt Enable Flag
    10: 'DF',  # Direction Flag
    11: 'OF',  # Overflow Flag
    14: 'NT',  # Nested Task
    16: 'RF',  # Resume Flag
    17: 'VM',  # Virtual 8086 Mode
    18: 'AC',  # Alignment Check
    19: 'VIF', # Virtual Interrupt Flag
    20: 'VIP', # Virtual Interrupt Pending
    21: 'ID',  # ID Flag
}


def format_flags(eflags: int) -> str:
    """Format EFLAGS register value as a string of set flags.

    Args:
        eflags: EFLAGS register value

    Returns:
        String of set flags (e.g., "ZF PF CF")
    """
    flags = []
    for bit, name in EFLAGS_BITS.items():
        if eflags & (1 << bit):
            flags.append(name)
    return ' '.join(flags) if flags else 'none'


def get_instruction_pointer_register(registers: dict) -> tuple[str, int]:
    """Get the instruction pointer register name and value.

    Args:
        registers: Dictionary of register names to values

    Returns:
        Tuple of (register_name, value)
    """
    # Try x64 first, then x86
    if 'rip' in registers:
        return ('rip', registers['rip'])
    elif 'eip' in registers:
        return ('eip', registers['eip'])
    else:
        return ('ip', 0)


def is_64bit(registers: dict) -> bool:
    """Determine if registers are from 64-bit process.

    Args:
        registers: Dictionary of register names to values

    Returns:
        True if 64-bit, False if 32-bit
    """
    return 'rip' in registers or 'rax' in registers
