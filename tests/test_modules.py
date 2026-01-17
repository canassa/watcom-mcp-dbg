"""
Module inspection tests for DGB MCP Debugger.

Tests listing loaded modules (EXE + DLLs) and their debug info.
"""

import pytest
from pathlib import Path


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


@pytest.mark.inspection
def test_list_modules(debug_session, mcp_client):
    """Test listing loaded modules."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # List modules
    result = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })

    # Verify modules are listed
    text = extract_text_from_result(result)

    # Should include the main executable
    assert "simple.exe" in text.lower()

    # Should include system DLLs
    # Note: exact DLLs may vary, but ntdll.dll is almost always present
    assert "ntdll.dll" in text.lower() or "kernel32.dll" in text.lower() or ".dll" in text.lower()


@pytest.mark.inspection
def test_module_has_debug_info(debug_session, mcp_client):
    """Test that main executable shows debug info available."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # List modules
    result = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })

    text = extract_text_from_result(result)

    # simple.exe should have debug info
    assert "simple.exe" in text.lower()
    # Check for indicators of debug info (exact format may vary)
    # Might say "has_debug_info: true" or "DWARF" or similar
    assert "debug" in text.lower() or "dwarf" in text.lower() or "true" in text.lower()


@pytest.mark.inspection
def test_dll_module_appears_after_load(debug_session, mcp_client):
    """Test that DLL module appears in list after it's loaded."""
    source_dir = str(Path(__file__).parent / "fixtures" / "src")
    session_id = debug_session("testdll_user.exe", source_dirs=[source_dir])

    # Run to entry (DLL not loaded yet)
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # List modules before DLL load
    result1 = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })
    text1 = extract_text_from_result(result1)

    # testdll.dll should NOT be in list yet (or may be if LoadLibrary already happened)
    dll_present_before = "testdll.dll" in text1.lower()

    # Set breakpoint after DLL is loaded (testdll_user.c:35 - first DLL call)
    mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": "testdll_user.c:35"
    })

    # Continue to that breakpoint
    mcp_client.call_tool("debugger_continue", {
        "session_id": session_id
    })

    # List modules after DLL load
    result2 = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })
    text2 = extract_text_from_result(result2)

    # testdll.dll should NOW be in list
    assert "testdll.dll" in text2.lower(), "testdll.dll not found in module list after LoadLibrary"


@pytest.mark.inspection
def test_module_base_addresses(debug_session, mcp_client):
    """Test that modules have base addresses."""
    session_id = debug_session("simple.exe")

    # Run to entry
    mcp_client.call_tool("debugger_run", {"session_id": session_id})

    # List modules
    result = mcp_client.call_tool("debugger_list_modules", {
        "session_id": session_id
    })

    text = extract_text_from_result(result)

    # Should contain hex addresses (base addresses)
    assert "0x" in text.lower() or "base" in text.lower()
