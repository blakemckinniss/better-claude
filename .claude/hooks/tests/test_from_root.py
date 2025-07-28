#!/usr/bin/env python3
"""Test the Stop hook when running from different directories"""
import os
import sys
import subprocess

# Test 1: Run from the project directory with CLAUDE_PROJECT_DIR set
print("Test 1: Running with CLAUDE_PROJECT_DIR environment variable...")
env = os.environ.copy()
env['CLAUDE_PROJECT_DIR'] = '/home/devcontainers/better-claude'

result = subprocess.run([
    sys.executable, 
    '/home/devcontainers/better-claude/.claude/hooks/test_stop_hook.py'
], cwd='/', env=env, capture_output=True, text=True)

print(f"Exit code: {result.returncode}")
print(f"Output:\n{result.stdout}")
if result.stderr:
    print(f"Errors:\n{result.stderr}")

# Test 2: Run from root directory without CLAUDE_PROJECT_DIR
print("\n\nTest 2: Running from root without CLAUDE_PROJECT_DIR...")
env = os.environ.copy()
env.pop('CLAUDE_PROJECT_DIR', None)  # Remove if exists

result = subprocess.run([
    sys.executable, 
    '/home/devcontainers/better-claude/.claude/hooks/test_stop_hook.py'
], cwd='/', env=env, capture_output=True, text=True)

print(f"Exit code: {result.returncode}")
print(f"Output:\n{result.stdout}")
if result.stderr:
    print(f"Errors:\n{result.stderr}")

# Check if logs were created
log_dir = '/home/devcontainers/better-claude/.claude/hooks/hook_logs/stop_hook_logs'
if os.path.exists(log_dir):
    logs = sorted(os.listdir(log_dir))
    print(f"\n\nTotal log files created: {len(logs)}")
    if logs:
        print(f"Latest log files: {logs[-3:]}")  # Show last 3