#!/usr/bin/env python3
"""
Test script to verify the warning suppression fix.

This simulates the PostToolUse hook scenarios that were showing "no feedback"
to confirm they now show proper warnings.
"""

import json
import sys
import subprocess
from pathlib import Path


def test_posttooluse_warning(tool_name: str, tool_input: dict) -> str:
    """Test PostToolUse hook and capture its output."""
    
    hook_data = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": "test-session-fix"
    }
    
    # Run PostToolUse hook
    hook_path = Path(".claude/hooks/hook_handlers/PostToolUse.py")
    
    try:
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(hook_data),
            text=True,
            capture_output=True,
            timeout=5
        )
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": "Timeout"}
    except Exception as e:
        return {"exit_code": -1, "error": str(e)}


def main():
    print("🧪 Testing PostToolUse Warning Fix")
    print("=" * 50)
    
    # Test scenarios that previously showed "no feedback"
    test_cases = [
        {
            "name": "Complex Bash Command", 
            "tool": "Bash",
            "input": {"command": "find . -name '*.py' -exec grep -l 'import' {} \\;"}
        },
        {
            "name": "Write Python File",
            "tool": "Write", 
            "input": {"file_path": "test.py", "content": "print('hello')"}
        },
        {
            "name": "Edit Tool",
            "tool": "Edit",
            "input": {"file_path": "test.py", "old_string": "hello", "new_string": "world"}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 30)
        
        result = test_posttooluse_warning(test_case["tool"], test_case["input"])
        
        print(f"Exit Code: {result['exit_code']}")
        
        if result.get('stderr'):
            print("Warning Output:")
            print(result['stderr'])
        else:
            print("❌ No warning output (this indicates the issue persists)")
        
        if result.get('stdout'):
            print("Stdout:")
            print(result['stdout'])
    
    print("\n" + "=" * 50)
    print("✅ Test Complete")
    print("\n📝 Expected Behavior:")
    print("   - Exit code should be 2 (blocking)")
    print("   - Stderr should contain detailed warning messages")
    print("   - Should NOT show 'no feedback' messages")


if __name__ == "__main__":
    main()