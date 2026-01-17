# DWARF Lazy-Loading Bug Fix - Summary

## Problem

When querying DWARF debug information for addresses in SMACKW32.DLL, source file paths were incorrectly returned as "unknown" instead of actual file paths like `C:\code\dll-trampoline2\src\trampolines.cpp`.

## Root Cause

**pyelftools lazy-loading bug in `src/dgb/dwarf/line_info.py`**

The code checked if `lineprog.header['file_entry']` was empty BEFORE iterating through the line program. However, pyelftools uses lazy-loading and only populates `file_entry` DURING iteration over `lineprog.get_entries()`.

This caused the code to incorrectly assume it was dealing with Watcom's "empty file table" format and use a hardcoded 3-element fallback array, when in reality pyelftools correctly parses Watcom DWARF and populates 6+ file entries.

## Solution

**Modified `_build_cache()` method in `src/dgb/dwarf/line_info.py`:**

1. **Removed pre-iteration file_entry check** that was always seeing an empty list
2. **Build file paths lazily during iteration** after pyelftools has populated the data
3. **Use dictionary cache** (`file_paths_cache`) instead of pre-built array
4. **Access file_entries inside the iteration loop** where it's actually populated
5. **Deleted unused helper methods** (`_build_file_paths_watcom`, `_build_file_paths`)

## Changes Made

### File: `src/dgb/dwarf/line_info.py`

**Before:**
```python
# Get file entries BEFORE iteration (always empty due to lazy-loading!)
file_entries = lineprog.header.get('file_entry', [])
if not file_entries:
    file_paths = self._build_file_paths_watcom(cu)  # Wrong!
else:
    file_paths = self._build_file_paths(file_entries, include_dirs, CU)

for entry in lineprog.get_entries():
    # Use pre-built file_paths array
```

**After:**
```python
# Build file paths on-demand DURING iteration
file_paths_cache = {}

for entry in lineprog.get_entries():
    file_index = state.file - 1

    if file_index not in file_paths_cache:
        # Access file_entries NOW (after iteration started - populated!)
        file_entries = lineprog.header.get('file_entry', [])

        if 0 <= file_index < len(file_entries):
            # Build full path from file_entry
            file_entry = file_entries[file_index]
            # ... build path logic ...
            file_paths_cache[file_index] = full_path
        else:
            # Fallback to Watcom CU name
            file_paths_cache[file_index] = cu_name or "unknown"

    file_path = file_paths_cache[file_index]
```

## Test Results

### Before Fix
```
Address 0x3966 maps to:
  File: unknown  ❌
  Line: 258
```

### After Fix
```
Address 0x3966 maps to:
  File: C:\code\dll-trampoline2\src\trampolines.cpp  ✅
  Line: 258
  Column: 1
```

### Comprehensive Verification

All tests pass:
- ✅ Address 0x3966 correctly maps to trampolines.cpp:258
- ✅ All 8 source files correctly resolved (no "unknown" entries)
- ✅ All addresses across different files correctly mapped
- ✅ Cache populated with 241 locations

**Source files found:**
1. `C:\code\dll-trampoline2\src\dllmain.cpp`
2. `C:\code\dll-trampoline2\src\function_pointers.cpp`
3. `C:\code\dll-trampoline2\src\trampolines.cpp`
4. `C:\WATCOM\h\exceptio`
5. `C:\WATCOM\h\stdexcep`
6. `C:\WATCOM\h\string`
7. `C:\WATCOM\h\memory`
8. `C:\WATCOM\h\_strdef.h`

## Impact

- **Fixes source file resolution** for all Watcom DWARF debugging
- **Enables MCP debugger** to show actual source code instead of "unknown"
- **No breaking changes** - all existing functionality preserved
- **Works with pyelftools** as-is, no need for external patches

## Verification

Run the verification script:
```bash
uv run python verify_fix.py
```

Expected output: `VERIFICATION RESULT: ALL TESTS PASSED`
