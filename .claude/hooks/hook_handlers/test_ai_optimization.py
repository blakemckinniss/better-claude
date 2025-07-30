#!/usr/bin/env python3
"""Test script to verify AI context optimization improvements."""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.ai_context_optimizer import optimize_injection_sync


def test_ai_optimization():
    """Test the AI optimization with a sample prompt and context."""

    # Sample user prompt
    user_prompt = "Help me fix the authentication bug in the login system"

    # Sample raw context (simulating what would come from various injections)
    raw_context = """
gitStatus: This is the git status at the start of the conversation.
Current branch: feature/auth-fix

Main branch (you will usually use this for PRs): main

Status:
M src/auth.py
M tests/test_auth.py
?? src/auth_utils.py

Recent commits:
abc123 WIP: Debugging auth issue
def456 Add user authentication module

Repository contains 156 tracked files

Top file types:
  .py: 89 files
  .js: 32 files
  .json: 12 files

## System Monitoring
CPU: 45%, Memory: 2.1GB used, Disk: 89% (WARNING: Low disk space)

## Test Status
pytest: 12 passed, 3 failed
Coverage: 85%

Failed tests:
- test_auth.py::test_login_with_invalid_credentials
- test_auth.py::test_token_expiration
- test_auth.py::test_session_persistence

## LSP Diagnostics
src/auth.py:42: error: Undefined variable 'user_token'
src/auth.py:58: warning: Unused import 'datetime'
src/auth.py:112: error: Missing return statement
"""

    print("Testing AI Context Optimization")
    print("=" * 50)
    print(f"User Prompt: {user_prompt}")
    print("=" * 50)

    # Test with AI optimization disabled (fallback)
    print("\n1. Testing Fallback Optimization (AI disabled):")
    print("-" * 50)
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}):
        fallback_result = optimize_injection_sync(user_prompt, raw_context)
        print(fallback_result)

    # Test with AI optimization enabled (if API key is available)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        print("\n2. Testing AI Optimization (OpenRouter):")
        print("-" * 50)
        ai_result = optimize_injection_sync(user_prompt, raw_context)
        print(ai_result)
    else:
        print("\n2. Skipping AI Optimization (no OPENROUTER_API_KEY set)")

    print(f"\n{'=' * 50}")
    print("Test Complete!")


if __name__ == "__main__":
    from unittest.mock import patch

    test_ai_optimization()
