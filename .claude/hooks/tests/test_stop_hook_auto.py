#!/usr/bin/env python3
"""Test script for the Stop.py hook with automatic transcript discovery"""
import os
import sys

# Add the hook_handlers directory to the path
sys.path.insert(0, '/home/devcontainers/better-claude/.claude/hooks/hook_handlers')

# Import the Stop hook
import Stop

# Test 2: Call the hook without transcript_path (should auto-discover)
print("Test 2: Calling Stop hook without transcript_path (auto-discovery)...")
try:
    Stop.handle({})  # Empty data dict
except SystemExit:
    print("Stop hook executed successfully (SystemExit caught)")

# Check if log was created
log_dir = '/home/devcontainers/better-claude/.claude/hooks/hook_logs/stop_hook_logs'
if os.path.exists(log_dir):
    logs = sorted(os.listdir(log_dir))
    print(f"\nTotal log files: {len(logs)}")
    if len(logs) >= 2:
        print(f"Latest log file: {logs[-1]}")
else:
    print(f"Log directory does not exist: {log_dir}")