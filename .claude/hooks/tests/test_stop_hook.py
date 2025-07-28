#!/usr/bin/env python3
"""Test script for the Stop.py hook"""
import os
import sys
import json
from datetime import datetime

# Add the hook_handlers directory to the path
sys.path.insert(0, '/home/devcontainers/better-claude/.claude/hooks/hook_handlers')

# Import the Stop hook
import Stop

# Create a test transcript file
test_transcript_dir = os.path.expanduser('~/.claude/projects/test')
os.makedirs(test_transcript_dir, exist_ok=True)

test_transcript_path = os.path.join(test_transcript_dir, 'test_transcript.jsonl')

# Create sample transcript data
transcript_data = [
    {"role": "user", "content": "Hello Claude, how are you?", "timestamp": "2025-07-28T18:00:00Z"},
    {"role": "assistant", "content": "Hello! I'm doing well, thank you for asking. How can I help you today?", "timestamp": "2025-07-28T18:00:05Z"},
    {"role": "user", "content": "Can you help me write a Python function?", "timestamp": "2025-07-28T18:00:10Z"},
    {"role": "assistant", "content": "Of course! I'd be happy to help you write a Python function. What kind of function do you need?", "timestamp": "2025-07-28T18:00:15Z"},
    {"role": "user", "content": "Thanks, I need a function to calculate fibonacci numbers", "timestamp": "2025-07-28T18:00:20Z"},
    {"role": "assistant", "content": "Here's a Python function to calculate Fibonacci numbers:\n\n```python\ndef fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n```\n\nThis is a recursive implementation. For better performance with larger numbers, you might want to use an iterative approach or memoization.", "timestamp": "2025-07-28T18:00:25Z"}
]

# Write the test transcript
with open(test_transcript_path, 'w') as f:
    for entry in transcript_data:
        f.write(json.dumps(entry) + '\n')

print(f"Created test transcript at: {test_transcript_path}")

# Test 1: Call the hook with transcript_path in data
print("\nTest 1: Calling Stop hook with transcript_path in data...")
try:
    Stop.handle({'transcript_path': test_transcript_path})
except SystemExit:
    print("Stop hook executed successfully (SystemExit caught)")

# Check if log was created
log_dir = '/home/devcontainers/better-claude/.claude/hooks/hook_logs/stop_hook_logs'
if os.path.exists(log_dir):
    logs = sorted(os.listdir(log_dir))
    if logs:
        print(f"\nLog files created: {logs}")
        # Read and display the most recent log
        with open(os.path.join(log_dir, logs[-1]), 'r') as f:
            log_content = json.load(f)
            print("\nLast log content:")
            print(f"Timestamp: {log_content['timestamp']}")
            print(f"Transcript path: {log_content['transcript_path']}")
            print(f"Last Claude message: {log_content['last_claude_message']['content'][:100]}...")
    else:
        print("No log files found!")
else:
    print(f"Log directory does not exist: {log_dir}")