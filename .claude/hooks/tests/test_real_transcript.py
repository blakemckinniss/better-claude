#!/usr/bin/env python3
"""Test the Stop hook with real Claude Code transcript structure"""
import subprocess
import json
import os

# Create a test transcript with the real structure
test_transcript_path = "/tmp/test_real_transcript.jsonl"

# Real transcript entries
entries = [
    {
        "type": "user",
        "content": "Test message",
        "timestamp": "2025-07-28T22:30:00.000Z"
    },
    {
        "parentUuid": "f7e07887-b88a-4f87-9d6f-2d82a8ba6b49",
        "type": "assistant",
        "message": {
            "id": "msg_01Hn1b5dzmqKRrkpo7C7tmcs",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-4-20250514",
            "content": [
                {
                    "type": "text",
                    "text": "This is the last Claude message from the session!"
                }
            ]
        },
        "timestamp": "2025-07-28T22:32:05.427Z"
    }
]

# Write test transcript
with open(test_transcript_path, 'w') as f:
    for entry in entries:
        f.write(json.dumps(entry) + '\n')

# Test the hook
hook_data = {
    "hook_event_name": "Stop",
    "transcript_path": test_transcript_path
}

print("Testing Stop hook with real transcript structure...")

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

# Clean up
os.remove(test_transcript_path)