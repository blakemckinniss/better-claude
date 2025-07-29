#!/usr/bin/env python3
"""Test the zen_injection module with agent selection feature."""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hook_handlers.UserPromptSubmit.zen_injection import (
    get_available_agents,
    get_zen_injection,
)


def test_get_available_agents():
    """Test that we can retrieve available agents."""
    agents = get_available_agents()
    print(f"Found {len(agents)} agents:")
    for name, desc in agents:
        print(f"  - {name}: {desc}")

    # Verify we found the expected agents
    agent_names = [name for name, _ in agents]
    expected_agents = [
        "code-refactorer",
        "content-writer",
        "frontend-designer",
        "prd-writer",
        "project-task-planner",
        "security-auditor",
        "vibe-coding-coach",
    ]

    for expected in expected_agents:
        assert expected in agent_names, f"Expected agent '{expected}' not found"

    print("\n✓ All expected agents found")


def test_zen_injection_with_agents():
    """Test that Zen injection includes agent selection."""
    test_prompts = [
        "Write a comprehensive PRD for a new social media app",
        "Refactor this messy authentication code",
        "Create a blog post about quantum computing",
        "What is 2+2?",  # Simple prompt that shouldn't trigger Zen
    ]

    print("\nTesting Zen injection with different prompts:")
    for prompt in test_prompts:
        result = get_zen_injection(prompt)
        if result:
            print(
                f"\nPrompt: '{prompt[:50]}...'"
                if len(prompt) > 50
                else f"\nPrompt: '{prompt}'"
            )
            # Extract and show just the key parts
            if "0-3 subagents" in result:
                print("  ✓ Includes subagent selection instruction")
            if "Available agents:" in result:
                print("  ✓ Includes available agents list")
            if "complexity_score" in result:
                import re

                score_match = re.search(r"complexity_score: ([\d.]+)", result)
                if score_match:
                    print(f"  ✓ Complexity score: {score_match.group(1)}")
        else:
            print(f"\nPrompt: '{prompt}'")
            print("  - Zen not triggered (simple task)")


if __name__ == "__main__":
    print(f"Testing Zen Agent Selection Feature\n{'=' * 40}")
    test_get_available_agents()
    print(f"\n{'=' * 40}")
    test_zen_injection_with_agents()
    print("\n✅ All tests passed!")
