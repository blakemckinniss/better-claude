#!/usr/bin/env python3
"""
Focused test to verify TodoWrite triggers PostToolUse hook warnings with sys.exit(2).

This test verifies the PostToolUse hook correctly:
1. Detects TodoWrite usage
2. Returns exit code 2 
3. Displays "⚠️ SUBAGENT PATTERN VIOLATION!" warning
4. Shows delegation guidance about using Task tool for subagents
5. Includes orchestrator reminder message

The hook should block TodoWrite and guide users to delegate to subagents instead.
"""

import sys
import os
from pathlib import Path

# Add hook handlers to path
sys.path.insert(0, str(Path(__file__).parent / "hook_handlers"))

from PostToolUse import handle_hook
import io
import contextlib

def test_todowrite_hook_warning():
    """Test that TodoWrite triggers PostToolUse hook warning with exit code 2."""
    print("Testing TodoWrite hook warning...")
    
    # Create test data
    test_data = {
        "tool_name": "TodoWrite",
        "tool_input": {"todo": "Test todo item", "priority": "high"},
        "tool_result": {"status": "created", "id": "test-123"},
        "session_id": "test-simple-session-001",
        "timestamp": "2025-08-03T10:00:00Z",
        "message_id": "msg_test_simple_123"
    }
    
    # Capture stderr
    stderr_capture = io.StringIO()
    
    with contextlib.redirect_stderr(stderr_capture):
        exit_code = handle_hook(test_data)
    
    stderr_output = stderr_capture.getvalue()
    
    # Verify results
    success = True
    errors = []
    
    print(f"Exit Code: {exit_code}")
    print(f"STDERR Output:\n{stderr_output}")
    print("-" * 60)
    
    # Test 1: Check exit code is 2
    if exit_code != 2:
        success = False
        errors.append(f"Expected exit code 2, got {exit_code}")
    
    # Test 2: Check for specific warning message
    if "SUBAGENT PATTERN VIOLATION!" not in stderr_output:
        success = False
        errors.append("Warning message 'SUBAGENT PATTERN VIOLATION!' not found in stderr")
    
    # Test 3: Check for delegation message
    if "Use Task tool to delegate" not in stderr_output:
        success = False
        errors.append("Delegation message about Task tool not found in stderr")
    
    # Test 4: Check for orchestrator reminder
    if "You are the orchestrator, not the implementer!" not in stderr_output:
        success = False
        errors.append("Orchestrator reminder message not found in stderr")
    
    # Test 5: Check for direct task management detection
    if "Direct task management detected!" not in stderr_output:
        success = False
        errors.append("Direct task management detection message not found in stderr")
    
    if success:
        print("✅ ALL TESTS PASSED")
        print("- TodoWrite correctly triggered PostToolUse hook")
        print("- Exit code 2 returned as expected")
        print("- Warning message displayed correctly")
        print("- Delegation guidance provided")
        print("- Orchestrator reminder included")
    else:
        print("❌ TESTS FAILED")
        for error in errors:
            print(f"  - {error}")
    
    return success

def test_different_tool_no_warning():
    """Test that non-TodoWrite tools don't trigger the specific warning."""
    print("\nTesting non-TodoWrite tool (should not trigger warning)...")
    
    # Create test data for a different tool
    test_data = {
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt", "content": "test"},
        "tool_result": {"status": "success"},
        "session_id": "test-write-session-001",
        "timestamp": "2025-08-03T10:00:00Z",
        "message_id": "msg_test_write_123"
    }
    
    # Capture stderr
    stderr_capture = io.StringIO()
    
    with contextlib.redirect_stderr(stderr_capture):
        exit_code = handle_hook(test_data)
    
    stderr_output = stderr_capture.getvalue()
    
    print(f"Exit Code: {exit_code}")
    print(f"STDERR Output: '{stderr_output.strip()}'")
    
    # Should not contain TodoWrite specific warning
    if "SUBAGENT PATTERN VIOLATION!" in stderr_output:
        print("❌ Unexpected TodoWrite warning for Write tool")
        return False
    
    print("✅ Write tool correctly did not trigger TodoWrite warning")
    return True

if __name__ == "__main__":
    print("TodoWrite Hook Warning Test - Simple Version")
    print("=" * 70)
    
    # Run main test
    test1_passed = test_todowrite_hook_warning()
    
    # Run negative test
    test2_passed = test_different_tool_no_warning()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED")
        print("- TodoWrite triggers correct warning with exit code 2")
        print("- Other tools don't trigger TodoWrite warning")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED")
        sys.exit(1)