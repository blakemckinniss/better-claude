#!/usr/bin/env python3
"""Test that the hook correctly uses the provided transcript_path."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_simple():
    """Simple test to see what's happening."""
    print("Testing UserPromptSubmit hook directly...")
    
    hook_script = Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit.py"
    
    # Test with minimal data
    test_data = {"userPrompt": "test"}
    
    print(f"\nRunning: {hook_script}")
    print(f"Input: {json.dumps(test_data)}")
    
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=json.dumps(test_data),
        capture_output=True,
        text=True
    )
    
    print(f"\nReturn code: {result.returncode}")
    print(f"Stdout length: {len(result.stdout)} chars")
    print(f"Stderr length: {len(result.stderr)} chars")
    
    if result.stdout:
        print("\nStdout (first 500 chars):")
        print(result.stdout[:500])
    
    if result.stderr:
        print("\nStderr (first 1000 chars):")
        print(result.stderr[:1000])


if __name__ == "__main__":
    test_simple()