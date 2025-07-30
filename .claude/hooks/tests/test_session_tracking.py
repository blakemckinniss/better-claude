#!/usr/bin/env python3
"""Test script for session tracking in UserPromptSubmit hook."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def test_session_tracking():
    """Test the session tracking functionality."""
    print("Testing session tracking with subprocess calls...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test environment
        test_env = os.environ.copy()
        test_env["CLAUDE_PROJECT_DIR"] = temp_dir
        
        # Create .claude/hooks directory structure
        hooks_dir = Path(temp_dir) / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test script that calls the hook
        test_script = """
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from UserPromptSubmit import is_first_user_prompt
print(json.dumps({"result": is_first_user_prompt()}))
"""
        
        test_file = Path(__file__).parent.parent / "hook_handlers" / "test_session.py"
        with open(test_file, 'w') as f:
            f.write(test_script)
        
        try:
            # Test 1: First call should return True
            result1 = subprocess.run(
                [sys.executable, str(test_file)],
                env=test_env,
                capture_output=True,
                text=True
            )
            data1 = json.loads(result1.stdout)
            print(f"Test 1 - First prompt: {data1['result']} (expected: True)")
            assert data1['result'] is True, "First prompt should return True"
            
            # Test 2: Second call should return False
            result2 = subprocess.run(
                [sys.executable, str(test_file)],
                env=test_env,
                capture_output=True,
                text=True
            )
            data2 = json.loads(result2.stdout)
            print(f"Test 2 - Second prompt: {data2['result']} (expected: False)")
            assert data2['result'] is False, "Second prompt should return False"
            
            # Check session file contents
            session_file = Path(temp_dir) / ".claude" / "hooks" / "session_data" / "current_session.json"
            assert session_file.exists(), "Session file should exist"
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            print(f"\nSession data: {json.dumps(session_data, indent=2)}")
            assert session_data["prompt_count"] == 2, f"Prompt count should be 2, got {session_data['prompt_count']}"
            
            print("\nAll session tracking tests passed! ✅")
            
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()


def test_hook_output():
    """Test the hook output format."""
    print("\n\nTesting hook output format...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_env = os.environ.copy()
        test_env["CLAUDE_PROJECT_DIR"] = temp_dir
        
        # Create test data
        test_data = {
            "userPrompt": "Test prompt"
        }
        
        # Call the actual hook handler
        hook_script = Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit.py"
        
        print("Test 1: First prompt should include context")
        result1 = subprocess.run(
            [sys.executable, str(hook_script)],
            env=test_env,
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result1.returncode != 0:
            print(f"Error: {result1.stderr}")
        
        try:
            output1 = json.loads(result1.stdout)
            context1 = output1["hookSpecificOutput"]["additionalContext"]
            print(f"First prompt context length: {len(context1)} chars")
            assert len(context1) > 100, "First prompt should have substantial context"
        except Exception as e:
            print(f"Failed to parse output: {e}")
            print(f"stdout: {result1.stdout}")
            print(f"stderr: {result1.stderr}")
            raise
        
        print("\nTest 2: Second prompt should have empty context")
        result2 = subprocess.run(
            [sys.executable, str(hook_script)],
            env=test_env,
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        output2 = json.loads(result2.stdout)
        context2 = output2["hookSpecificOutput"]["additionalContext"]
        print(f"Second prompt context length: {len(context2)} chars")
        assert context2 == "", "Second prompt should have empty context"
        
        print("\nHook output tests passed! ✅")


if __name__ == "__main__":
    test_session_tracking()
    test_hook_output()