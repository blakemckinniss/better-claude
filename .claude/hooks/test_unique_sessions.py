#!/usr/bin/env python3
"""
Test PostToolUse warnings with unique session IDs to avoid suppression.
"""

import json
import sys
import subprocess
import uuid
from pathlib import Path


def test_posttooluse_with_unique_session(tool_name: str, tool_input: dict) -> dict:
    """Test PostToolUse hook with a unique session ID."""
    
    hook_data = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": f"test-{uuid.uuid4().hex[:8]}"  # Unique session ID
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
            "stderr": result.stderr,
            "session_id": hook_data["session_id"]
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": "Timeout"}
    except Exception as e:
        return {"exit_code": -1, "error": str(e)}


def main():
    print("🧪 Testing PostToolUse Warnings with Unique Sessions")
    print("=" * 60)
    
    # Test scenarios
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
        print("-" * 40)
        
        result = test_posttooluse_with_unique_session(test_case["tool"], test_case["input"])
        
        print(f"Session ID: {result.get('session_id', 'N/A')}")
        print(f"Exit Code: {result['exit_code']}")
        
        if result.get('stderr'):
            print("Warning Output:")
            print(result['stderr'])
        else:
            print("❌ No warning output")
        
        print()
    
    print("=" * 60)
    print("✅ Test Complete - Each test used a unique session ID")


if __name__ == "__main__":
    main()