#!/usr/bin/env python3
"""Test file with the exact broken print pattern."""

import sys

def test_function():
    block_reason = "Test reason"
    
    # This is the exact pattern that gets broken
    print(f"❌ {block_reason}", file=sys.stderr)
    print("📝 Note: Hooks can be temporarily disabled in", file=sys.stderr)
    print(
        "   /home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
        file=sys.stderr,
    )