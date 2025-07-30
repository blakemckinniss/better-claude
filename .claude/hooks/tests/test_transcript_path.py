#!/usr/bin/env python3
"""Test that the hook correctly uses the provided transcript_path."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_with_transcript_path():
    """Test the hook with various transcript path scenarios."""
    print("Testing UserPromptSubmit with transcript_path...")
    
    hook_script = Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit.py"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: No transcript_path in data
        print("\nTest 1: No transcript_path provided")
        test_data = {"userPrompt": "test"}
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            context_len = len(output["hookSpecificOutput"]["additionalContext"])
            print(f"  Context length: {context_len} chars")
            print(f"  Should have full context: {'✅' if context_len > 100 else '❌'}")
        else:
            print(f"  Error: {result.stderr}")
        
        # Test 2: Non-existent transcript path
        print("\nTest 2: Non-existent transcript path")
        test_data = {
            "userPrompt": "test",
            "transcript_path": str(Path(temp_dir) / "nonexistent.jsonl")
        }
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            context_len = len(output["hookSpecificOutput"]["additionalContext"])
            print(f"  Context length: {context_len} chars")
            print(f"  Should have full context: {'✅' if context_len > 100 else '❌'}")
        
        # Test 3: Empty transcript (no user messages)
        print("\nTest 3: Empty transcript (no user messages)")
        empty_transcript = Path(temp_dir) / "empty.jsonl"
        with open(empty_transcript, 'w') as f:
            f.write(json.dumps({"type": "system", "message": {"content": "Welcome"}}))
            f.write("\n")
        
        test_data = {
            "userPrompt": "test",
            "transcript_path": str(empty_transcript)
        }
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            context_len = len(output["hookSpecificOutput"]["additionalContext"])
            print(f"  Context length: {context_len} chars")
            print(f"  Should have full context: {'✅' if context_len > 100 else '❌'}")
        
        # Test 4: Transcript with user messages
        print("\nTest 4: Transcript with user messages")
        full_transcript = Path(temp_dir) / "full.jsonl"
        with open(full_transcript, 'w') as f:
            f.write(json.dumps({"type": "user", "message": {"content": "Hello"}}))
            f.write("\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": "Hi there"}}))
            f.write("\n")
        
        test_data = {
            "userPrompt": "test",
            "transcript_path": str(full_transcript)
        }
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            context_len = len(output["hookSpecificOutput"]["additionalContext"])
            print(f"  Context length: {context_len} chars")
            print(f"  Should have empty context: {'✅' if context_len == 0 else '❌'}")
        
        # Test 5: Full hook data structure
        print("\nTest 5: Full hook data structure")
        test_data = {
            "session_id": "test-session-123",
            "transcript_path": str(full_transcript),
            "cwd": "/test/directory",
            "hook_event_name": "UserPromptSubmit",
            "userPrompt": "Write a factorial function"
        }
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_data),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            context_len = len(output["hookSpecificOutput"]["additionalContext"])
            print(f"  Context length: {context_len} chars")
            print(f"  Should have empty context: {'✅' if context_len == 0 else '❌'}")
            print(f"  Hook event name: {output['hookSpecificOutput']['hookEventName']}")


if __name__ == "__main__":
    test_with_transcript_path()