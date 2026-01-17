"""
COMPREHENSIVE BLACK BOX TESTS for Variable Inspection.

Tests EVERY type, edge case, and scenario with real Watcom-compiled code.
"""

import pytest
import json


def extract_text_from_result(result):
    """Extract text content from MCP tool result."""
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "")
    return ""


def parse_json_from_text(text):
    """Parse JSON from text content."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def find_variable(variables, name):
    """Find a variable by name in the list."""
    for var in variables:
        if var["name"] == name:
            return var
    return None


def set_breakpoint_and_continue(mcp_client, session_id, location):
    """Helper to set breakpoint and continue to it."""
    # Set breakpoint
    bp_result = mcp_client.call_tool("debugger_set_breakpoint", {
        "session_id": session_id,
        "location": location
    })
    bp_text = extract_text_from_result(bp_result)
    # MCP returns text, not JSON - check if breakpoint was set successfully
    assert "breakpoint" in bp_text.lower(), f"Failed to set breakpoint at {location}: {bp_text}"

    # Continue to breakpoint
    cont_result = mcp_client.call_tool("debugger_continue", {"session_id": session_id})
    cont_text = extract_text_from_result(cont_result)
    assert "breakpoint" in cont_text.lower() or "stopped" in cont_text.lower()


def get_variables(mcp_client, session_id):
    """Helper to get variables at current location."""
    result = mcp_client.call_tool("debugger_list_variables", {"session_id": session_id})
    text = extract_text_from_result(result)

    # Extract JSON from code block (format: ```json\n{...}\n```)
    import re
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        json_text = json_match.group(1)
        data = parse_json_from_text(json_text)
        assert data is not None, "Failed to parse JSON from response"
        assert data.get("success"), f"Variable listing failed: {data.get('error')}"
        print(f"\n[get_variables] Found {len(data['variables'])} variables:")
        for v in data["variables"]:
            print(f"  - {v['name']} = {v['value']} (is_param={v.get('is_parameter', False)})")
        return data["variables"]
    else:
        raise AssertionError(f"No JSON found in response: {text}")


# ============================================================================
# BASIC TYPE TESTS
# ============================================================================

@pytest.mark.inspection
def test_basic_types_all(debug_session, mcp_client):
    """Test ALL basic types: char, short, int, long, float, double, signed/unsigned."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:37")

    variables = get_variables(mcp_client, session_id)

    # Test char
    c = find_variable(variables, "c")
    assert c is not None, "Variable 'c' not found"
    assert c["type"] == "char" or "char" in c["type"].lower()
    assert c["value"] == "65" or c["value"] == "'A'"  # ASCII 65 is 'A'

    # Test signed char
    sc = find_variable(variables, "sc")
    assert sc is not None, "Variable 'sc' not found"
    assert "char" in sc["type"].lower()
    assert sc["value"] == "-5"

    # Test unsigned char
    uc = find_variable(variables, "uc")
    assert uc is not None, "Variable 'uc' not found"
    assert "char" in uc["type"].lower()
    assert sc["value"] == "200" or uc["value"] == "200"

    # Test short
    s = find_variable(variables, "s")
    assert s is not None, "Variable 's' not found"
    assert "short" in s["type"].lower()
    assert s["value"] == "-1000"

    # Test unsigned short
    us = find_variable(variables, "us")
    assert us is not None, "Variable 'us' not found"
    assert "short" in us["type"].lower()
    assert us["value"] == "50000"

    # Test int
    i = find_variable(variables, "i")
    assert i is not None, "Variable 'i' not found"
    assert "int" in i["type"].lower()
    assert i["value"] == "-42"

    # Test unsigned int
    ui = find_variable(variables, "ui")
    assert ui is not None, "Variable 'ui' not found"
    assert "int" in ui["type"].lower()
    # Should be a large positive number
    assert int(ui["value"]) > 2000000000

    # Test long
    l = find_variable(variables, "l")
    assert l is not None, "Variable 'l' not found"
    assert "long" in l["type"].lower() or "int" in l["type"].lower()
    assert l["value"] == "-100000"


@pytest.mark.inspection
def test_float_and_double(debug_session, mcp_client):
    """Test floating point types."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:37")

    variables = get_variables(mcp_client, session_id)

    # Test float
    f = find_variable(variables, "f")
    assert f is not None, "Variable 'f' not found"
    assert "float" in f["type"].lower()
    # Allow some floating point tolerance
    f_val = float(f["value"])
    assert 3.13 < f_val < 3.15, f"Float value {f_val} not near 3.14"

    # Test double
    d = find_variable(variables, "d")
    assert d is not None, "Variable 'd' not found"
    assert "double" in d["type"].lower()
    d_val = float(d["value"])
    assert 2.71 < d_val < 2.72, f"Double value {d_val} not near 2.718"


# ============================================================================
# POINTER TESTS
# ============================================================================

@pytest.mark.inspection
def test_simple_pointer(debug_session, mcp_client):
    """Test simple int pointer."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:55")

    variables = get_variables(mcp_client, session_id)

    # Test value
    value = find_variable(variables, "value")
    assert value is not None
    assert value["value"] == "42"

    # Test pointer
    ptr = find_variable(variables, "ptr")
    assert ptr is not None
    assert "*" in ptr["type"] or "ptr" in ptr["type"].lower()
    assert "0x" in ptr["value"].lower(), "Pointer should be hex address"


@pytest.mark.inspection
def test_pointer_to_pointer(debug_session, mcp_client):
    """Test pointer to pointer (int**)."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:55")

    variables = get_variables(mcp_client, session_id)

    # Test pointer to pointer
    ptr_ptr = find_variable(variables, "ptr_ptr")
    assert ptr_ptr is not None
    assert "0x" in ptr_ptr["value"].lower()


@pytest.mark.inspection
def test_char_pointer_string(debug_session, mcp_client):
    """Test char pointer (string)."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:55")

    variables = get_variables(mcp_client, session_id)

    # Test string pointer
    str_ptr = find_variable(variables, "str_ptr")
    assert str_ptr is not None
    assert "char" in str_ptr["type"].lower() and "*" in str_ptr["type"]
    assert "0x" in str_ptr["value"].lower()


@pytest.mark.inspection
def test_void_pointer(debug_session, mcp_client):
    """Test void pointer."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:55")

    variables = get_variables(mcp_client, session_id)

    # Test void pointer
    void_ptr = find_variable(variables, "void_ptr")
    assert void_ptr is not None
    assert "0x" in void_ptr["value"].lower()


# ============================================================================
# ARRAY TESTS
# ============================================================================

@pytest.mark.inspection
def test_int_array(debug_session, mcp_client):
    """Test integer array."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:69")

    variables = get_variables(mcp_client, session_id)

    # Test int array
    int_array = find_variable(variables, "int_array")
    assert int_array is not None
    # Array should show address or first elements
    assert "int" in int_array["type"].lower()


@pytest.mark.inspection
def test_char_array(debug_session, mcp_client):
    """Test char array (string)."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:69")

    variables = get_variables(mcp_client, session_id)

    # Test char array
    char_array = find_variable(variables, "char_array")
    assert char_array is not None
    assert "char" in char_array["type"].lower()


# ============================================================================
# STRUCT TESTS
# ============================================================================

@pytest.mark.inspection
def test_struct_members(debug_session, mcp_client):
    """Test struct with members."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:81")

    variables = get_variables(mcp_client, session_id)

    # Test struct
    p = find_variable(variables, "p")
    assert p is not None
    assert "struct" in p["type"].lower() or "point" in p["type"].lower()


@pytest.mark.inspection
def test_struct_pointer(debug_session, mcp_client):
    """Test pointer to struct."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:81")

    variables = get_variables(mcp_client, session_id)

    # Test struct pointer
    p_ptr = find_variable(variables, "p_ptr")
    assert p_ptr is not None
    assert "*" in p_ptr["type"] or "ptr" in p_ptr["type"].lower()
    assert "0x" in p_ptr["value"].lower()


# ============================================================================
# PARAMETER TESTS
# ============================================================================

@pytest.mark.inspection
def test_function_parameters(debug_session, mcp_client):
    """Test function parameters are listed and marked."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:87")

    variables = get_variables(mcp_client, session_id)

    # Test parameters
    a = find_variable(variables, "a")
    assert a is not None
    assert a.get("is_parameter") == True, "Parameter 'a' should be marked as parameter"
    assert a["value"] == "10"

    b = find_variable(variables, "b")
    assert b is not None
    assert b.get("is_parameter") == True
    assert b["value"] == "20"

    # Test local variable
    result = find_variable(variables, "result")
    assert result is not None
    assert result.get("is_parameter") != True, "Local variable should not be marked as parameter"
    assert result["value"] == "30"


@pytest.mark.inspection
def test_many_parameters(debug_session, mcp_client):
    """Test function with 5 parameters."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:93")

    variables = get_variables(mcp_client, session_id)

    # Should have 5 parameters + 1 local
    param_count = sum(1 for v in variables if v.get("is_parameter"))
    assert param_count == 5, f"Expected 5 parameters, found {param_count}"

    # Verify parameter values
    a = find_variable(variables, "a")
    assert a and a["value"] == "1"

    e = find_variable(variables, "e")
    assert e and e["value"] == "5"

    # Verify local sum
    sum_var = find_variable(variables, "sum")
    assert sum_var is not None
    assert sum_var["value"] == "15"


@pytest.mark.inspection
def test_mixed_type_parameters(debug_session, mcp_client):
    """Test function with different parameter types."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:102")

    variables = get_variables(mcp_client, session_id)

    # Test char parameter
    ch = find_variable(variables, "ch")
    assert ch is not None
    assert ch.get("is_parameter") == True
    assert "char" in ch["type"].lower()

    # Test int parameter
    num = find_variable(variables, "num")
    assert num is not None
    assert num["value"] == "100"

    # Test float parameter
    fval = find_variable(variables, "fval")
    assert fval is not None
    f_val = float(fval["value"])
    assert 3.0 < f_val < 3.2


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.inspection
def test_zero_values(debug_session, mcp_client):
    """Test variables with zero values."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:112")

    variables = get_variables(mcp_client, session_id)

    # Test zero int
    zero_int = find_variable(variables, "zero_int")
    assert zero_int is not None
    assert zero_int["value"] == "0"

    # Test zero char
    zero_char = find_variable(variables, "zero_char")
    assert zero_char is not None
    assert zero_char["value"] == "0" or zero_char["value"] == "'\\0'"

    # Test null pointer
    null_ptr = find_variable(variables, "null_ptr")
    assert null_ptr is not None
    assert null_ptr["value"] == "0x00000000" or null_ptr["value"] == "0"


@pytest.mark.inspection
def test_negative_values(debug_session, mcp_client):
    """Test negative values for signed types."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:122")

    variables = get_variables(mcp_client, session_id)

    # Test negative int
    neg_int = find_variable(variables, "neg_int")
    assert neg_int is not None
    assert neg_int["value"] == "-42"

    # Test negative char
    neg_char = find_variable(variables, "neg_char")
    assert neg_char is not None
    assert neg_char["value"] == "-100"

    # Test negative short
    neg_short = find_variable(variables, "neg_short")
    assert neg_short is not None
    assert neg_short["value"] == "-30000"


@pytest.mark.inspection
def test_max_unsigned_values(debug_session, mcp_client):
    """Test maximum values for unsigned types."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:131")

    variables = get_variables(mcp_client, session_id)

    # Test max unsigned char
    max_uchar = find_variable(variables, "max_uchar")
    assert max_uchar is not None
    assert max_uchar["value"] == "255"

    # Test max unsigned short
    max_ushort = find_variable(variables, "max_ushort")
    assert max_ushort is not None
    assert max_ushort["value"] == "65535"

    # Test max unsigned int
    max_uint = find_variable(variables, "max_uint")
    assert max_uint is not None
    assert int(max_uint["value"]) == 4294967295 or max_uint["value"] == "-1"  # May show as -1 if interpreted as signed


# ============================================================================
# VARIABLE COUNT AND STRUCTURE TESTS
# ============================================================================

@pytest.mark.inspection
def test_locals_only_count(debug_session, mcp_client):
    """Test function with only local variables."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:141")

    variables = get_variables(mcp_client, session_id)

    # Should have 4 local variables (x, y, z, result)
    local_count = len([v for v in variables if not v.get("is_parameter")])
    assert local_count == 4, f"Expected 4 locals, found {local_count}"


@pytest.mark.inspection
def test_params_only_count(debug_session, mcp_client):
    """Test function with only parameters."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:146")

    variables = get_variables(mcp_client, session_id)

    # Should have 3 parameters only
    param_count = sum(1 for v in variables if v.get("is_parameter"))
    assert param_count == 3, f"Expected 3 parameters, found {param_count}"

    # Verify values
    p1 = find_variable(variables, "p1")
    assert p1 and p1["value"] == "5"
    p2 = find_variable(variables, "p2")
    assert p2 and p2["value"] == "10"
    p3 = find_variable(variables, "p3")
    assert p3 and p3["value"] == "15"


@pytest.mark.inspection
def test_locals_and_params_mixed(debug_session, mcp_client):
    """Test function with both locals and parameters."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:155")

    variables = get_variables(mcp_client, session_id)

    param_count = sum(1 for v in variables if v.get("is_parameter"))
    local_count = len([v for v in variables if not v.get("is_parameter")])

    assert param_count == 2, f"Expected 2 parameters, found {param_count}"
    assert local_count == 3, f"Expected 3 locals, found {local_count}"

    # Verify parameter values
    param1 = find_variable(variables, "param1")
    assert param1 and param1["value"] == "7"
    param2 = find_variable(variables, "param2")
    assert param2 and param2["value"] == "11"

    # Verify local values
    local1 = find_variable(variables, "local1")
    assert local1 and local1["value"] == "14"
    local2 = find_variable(variables, "local2")
    assert local2 and local2["value"] == "33"
    sum_var = find_variable(variables, "sum")
    assert sum_var and sum_var["value"] == "47"


@pytest.mark.inspection
def test_char_as_param(debug_session, mcp_client):
    """Test char passed as parameter."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:163")

    variables = get_variables(mcp_client, session_id)

    ch = find_variable(variables, "ch")
    assert ch is not None
    assert ch.get("is_parameter") == True
    # 'Z' is ASCII 90
    assert ch["value"] == "90" or ch["value"] == "'Z'"

    as_int = find_variable(variables, "as_int")
    assert as_int is not None
    assert as_int["value"] == "90"


# ============================================================================
# LOCATION TESTS
# ============================================================================

@pytest.mark.inspection
def test_variable_locations(debug_session, mcp_client):
    """Test that variables report their location (stack/register/etc)."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:87")

    variables = get_variables(mcp_client, session_id)

    # All variables should have a location field
    for var in variables:
        assert "location" in var, f"Variable {var['name']} missing location field"
        assert var["location"] in ["stack", "register", "global", "constant", "unavailable"], \
            f"Invalid location '{var['location']}' for {var['name']}"


@pytest.mark.inspection
def test_variable_addresses(debug_session, mcp_client):
    """Test that stack variables have addresses."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:87")

    variables = get_variables(mcp_client, session_id)

    # Stack variables should have addresses
    for var in variables:
        if var["location"] == "stack":
            assert "address" in var and var["address"], \
                f"Stack variable {var['name']} should have an address"
            assert "0x" in var["address"].lower(), \
                f"Address should be hex format, got {var['address']}"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.inspection
def test_list_variables_tool_exists(mcp_client):
    """Test that debugger_list_variables tool is registered."""
    tools = mcp_client.list_tools()
    tool_names = [tool["name"] for tool in tools]
    assert "debugger_list_variables" in tool_names


@pytest.mark.inspection
def test_list_variables_requires_stopped_process(debug_session, mcp_client):
    """Test that listing variables requires process to be stopped."""
    session_id = debug_session("variables.exe")

    # Try before running
    result = mcp_client.call_tool("debugger_list_variables", {"session_id": session_id})
    text = extract_text_from_result(result)
    data = parse_json_from_text(text)

    if data:
        assert data.get("success") == False


@pytest.mark.inspection
def test_list_variables_invalid_session(mcp_client):
    """Test that invalid session ID fails gracefully."""
    result = mcp_client.call_tool("debugger_list_variables", {
        "session_id": "invalid_session_id"
    })

    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "").lower()
        assert "error" in text or "not found" in text
    else:
        assert result.get("isError", False) == True


@pytest.mark.inspection
def test_response_structure(debug_session, mcp_client):
    """Test that response has correct JSON structure."""
    session_id = debug_session("variables.exe")
    mcp_client.call_tool("debugger_run", {"session_id": session_id})
    set_breakpoint_and_continue(mcp_client, session_id, "variables.c:87")

    result = mcp_client.call_tool("debugger_list_variables", {"session_id": session_id})
    text = extract_text_from_result(result)
    data = parse_json_from_text(text)

    assert data is not None
    assert "success" in data
    assert "variables" in data
    assert "count" in data
    assert isinstance(data["variables"], list)
    assert data["count"] == len(data["variables"])

    # Check variable structure
    for var in data["variables"]:
        assert "name" in var
        assert "type" in var
        assert "value" in var
        assert "location" in var
