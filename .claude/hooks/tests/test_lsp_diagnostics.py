#!/usr/bin/env python3
"""Test file with various errors to verify LSP diagnostics detection."""

import asyncio
from typing import Optional


def sync_function():
    """Regular synchronous function."""
    return "sync result"


async def async_function():
    """Async function that returns a result."""
    await asyncio.sleep(0.1)
    return "async result"


# Test 1: Asyncio error - passing sync function to create_task
def test_asyncio_error():
    """This should trigger an asyncio diagnostic."""
    # This will cause an error: create_task expects a coroutine
    task = asyncio.create_task(sync_function())  # ERROR: sync function passed
    return task


# Test 2: Type error
def test_type_error(value: int) -> str:
    """This should trigger a mypy error."""
    # Type error: returning int when str is expected
    return value  # ERROR: Incompatible return type


# Test 3: Undefined variable
def test_undefined_variable():
    """This should trigger an undefined variable error."""
    if some_condition:  # ERROR: some_condition is not defined
        result = "defined"
    return result  # ERROR: result might not be defined


# Test 4: Possibly unbound variable
def test_possibly_unbound():
    """This should trigger a possibly unbound variable warning."""
    try:
        value = 1 / 0
    except ZeroDivisionError:
        error_msg = "Division by zero"

    # This checks if the variable exists (pattern we're looking for)
    if "error_msg" in locals():
        print(error_msg)

    return error_msg  # ERROR: might not be defined if no exception


# Test 5: Syntax error (commented out to not break parsing)
# def test_syntax_error()
#     """This would trigger a syntax error."""
#     return "missing colon"


# Test 6: Import error


# Test 7: Async function not awaited
async def test_not_awaited():
    """This should trigger a warning about not awaiting."""
    result = async_function()  # WARNING: coroutine not awaited
    return result


# Test 8: Multiple issues in one function
def test_multiple_issues(param: Optional[str]) -> int:
    """Function with multiple issues."""
    # Issue 1: Type error - can't add None and int
    result = param + 5  # ERROR: unsupported operand types

    # Issue 2: Undefined name
    if undefined_flag:  # ERROR: undefined_flag not defined
        pass

    # Issue 3: Wrong return type
    return "string"  # ERROR: should return int


if __name__ == "__main__":
    print("This test file contains intentional errors for testing diagnostics.")
