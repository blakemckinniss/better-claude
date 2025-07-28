#!/usr/bin/env python3
"""Test the Stop hook through hook_handler.py with debugging"""
import subprocess
import json
import sys

# Prepare the data that would be sent to the hook
hook_data = {
    "hook_event_name": "Stop",
    "transcript_path": "/home/devcontainers/.claude/projects/test/test_transcript.jsonl"
}

print("Testing Stop hook through hook_handler.py...")
print(f"Sending data: {json.dumps(hook_data, indent=2)}")

# Run the hook handler
process = subprocess.Popen(
    ["python", "/home/devcontainers/better-claude/.claude/hooks/hook_handler.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = process.communicate(input=json.dumps(hook_data))

print(f"\nExit code: {process.returncode}")
print(f"\nStdout:\n{stdout}")
print(f"\nStderr:\n{stderr}")