#!/usr/bin/env python3
"""Test CLAUDE.md snippet injection functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit")
)

from suffix_injection import ClaudeMdSnippets, get_suffix


def test_claude_md_parsing():
    """Test parsing of CLAUDE.md into snippets."""
    print("=== Testing CLAUDE.md Parsing ===")

    # Force fresh parse
    ClaudeMdSnippets._snippets_cache = None
    snippets = ClaudeMdSnippets.get_snippets()

    print(f"Found {len(snippets)} snippet categories:")
    for key in sorted(snippets.keys()):
        preview = snippets[key][:80].replace("\n", " ")
        print(f"  - {key}: {preview}...")


def test_snippet_injection_scenarios():
    """Test different scenarios for snippet injection."""
    print("\n\n=== Testing Snippet Injection Scenarios ===")

    test_cases = [
        # (prompt, expected_snippets)
        ("implement a new feature using modern tools", ["modern_tools", "code_rules"]),
        (
            "debug the performance issue in our distributed system",
            ["performance_rules", "anti_patterns"],
        ),
        (
            "design a highly scalable architecture with proper delegation",
            ["delegation_matrix"],
        ),
        (
            "fix the security vulnerability in the authentication hooks",
            ["security_rules", "hooks_system"],
        ),
        ("refactor this code to avoid anti-patterns", ["anti_patterns", "code_rules"]),
    ]

    for prompt, expected_snippets in test_cases:
        print(f"\n\nPrompt: '{prompt}'")
        suffix = get_suffix(prompt)

        print("Expected snippets:")
        for snippet in expected_snippets:
            tag = f"<claude-md-{snippet.replace('_', '')}"
            present = tag in suffix
            print(f"  - {snippet}: {'✓ Present' if present else '✗ Missing'}")

        # Show actual snippets included
        snippet_tags = [
            "claude-md-tools",
            "claude-md-parallel",
            "claude-md-delegation",
            "claude-md-performance",
            "claude-md-antipatterns",
            "claude-md-coderules",
            "claude-md-security",
            "claude-md-hooks",
            "claude-md-features",
        ]

        actual_snippets = [tag for tag in snippet_tags if f"<{tag}>" in suffix]
        if actual_snippets:
            print(f"Actually included: {', '.join(actual_snippets)}")


def test_complexity_based_injection():
    """Test that snippets are injected based on complexity."""
    print("\n\n=== Testing Complexity-Based Injection ===")

    # Simple task - should not get parallel execution or delegation matrix
    simple = "fix typo in README"
    simple_suffix = get_suffix(simple)
    print(f"\nSimple task: '{simple}'")
    print(f"Has parallel execution: {'<claude-md-parallel>' in simple_suffix}")
    print(f"Has delegation matrix: {'<claude-md-delegation>' in simple_suffix}")

    # Complex task - should get both
    complex = "implement a complete authentication system with OAuth2, JWT tokens, role-based access control, session management, and integrate it with our existing microservice architecture"
    complex_suffix = get_suffix(complex)
    print(f"\nComplex task: '{complex[:50]}...'")
    print(f"Has parallel execution: {'<claude-md-parallel>' in complex_suffix}")
    print(f"Has delegation matrix: {'<claude-md-delegation>' in complex_suffix}")


def test_always_has_next_steps():
    """Ensure Next Steps is preserved even with CLAUDE.md snippets."""
    print("\n\n=== Testing Next Steps Always Present ===")

    # Test with a prompt that should trigger many snippets
    heavy_prompt = "implement a secure authentication system with hooks integration and performance optimization"
    suffix = get_suffix(heavy_prompt)

    has_next_steps = "Next Steps" in suffix and "3 actionable suggestions" in suffix
    snippet_count = sum(1 for tag in ["<claude-md-"] if tag in suffix)

    print(f"Heavy prompt with {snippet_count} CLAUDE.md snippets")
    print(f"Still has Next Steps: {has_next_steps} {'✓' if has_next_steps else '✗'}")
    print(f"Total suffix length: {len(suffix)} chars")


def show_full_example():
    """Show a full example with all enhancements."""
    print("\n\n=== Full Example with CLAUDE.md Snippets ===")

    prompt = "implement a high-performance authentication system with proper security and hooks integration"
    suffix = get_suffix(prompt)

    print(f"Prompt: {prompt}")
    print("\nGenerated Suffix:")
    print("=" * 80)
    print(suffix)
    print("=" * 80)


if __name__ == "__main__":
    test_claude_md_parsing()
    test_snippet_injection_scenarios()
    test_complexity_based_injection()
    test_always_has_next_steps()
    show_full_example()
