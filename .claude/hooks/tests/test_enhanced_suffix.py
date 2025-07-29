#!/usr/bin/env python3
"""Test the enhanced suffix injection with smart classifier."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit")
)

from suffix_injection import (
    ClaudeMdSnippets,
    EnhancedTaskClassifier,
    analyze_prompt_enhanced,
    get_suffix,
)


def test_enhanced_classifier():
    """Test the enhanced task classifier."""
    print("=== Testing Enhanced Task Classifier ===")

    classifier = EnhancedTaskClassifier()

    test_cases = [
        # (prompt, expected_snippets)
        ("implement a new feature using modern tools", ["modern_tools", "code_rules"]),
        (
            "debug the performance issue in our distributed system",
            ["anti_patterns", "performance_rules"],
        ),
        (
            "design a scalable architecture with proper delegation",
            ["delegation_matrix", "performance_rules"],
        ),
        (
            "fix the security vulnerability in the authentication hooks",
            ["security_rules", "hooks_system"],
        ),
        (
            "refactor this code to avoid anti-patterns and use grep efficiently",
            ["modern_tools", "anti_patterns"],
        ),
        (
            "implement parallel processing for multiple files",
            ["parallel_execution", "modern_tools"],
        ),
        ("what is 2+2?", []),  # Simple query, no snippets
    ]

    for prompt, expected_snippets in test_cases:
        task_scores, snippet_suggestions, complexity = classifier.analyze(prompt)

        print(f"\nPrompt: '{prompt[:60]}...'")
        print(f"Complexity: {complexity:.2f}")
        print(f"Tasks detected: {[t for t, s in task_scores.items() if s > 0]}")
        print(f"Snippets suggested: {snippet_suggestions}")

        # Check if expected snippets are present
        for snippet in expected_snippets:
            status = "✓" if snippet in snippet_suggestions else "✗"
            print(f"  {snippet}: {status}")


def test_complexity_thresholds():
    """Test that complexity thresholds work correctly."""
    print("\n\n=== Testing Complexity Thresholds ===")

    test_prompts = [
        ("hi", 0.1),  # Very simple
        ("fix typo", 0.15),  # Simple
        ("implement authentication", 0.4),  # Moderate
        (
            "design and implement a complex distributed system with multiple microservices",
            0.7,
        ),  # Complex
    ]

    for prompt, expected_min in test_prompts:
        apply_enhanced, complexity, categories, snippets = analyze_prompt_enhanced(
            prompt
        )
        print(f"\nPrompt: '{prompt}'")
        print(f"Complexity: {complexity:.2f} (expected >= {expected_min})")
        print(f"Apply enhanced: {apply_enhanced}")
        print(f"Categories: {categories}")
        print(f"Snippet count: {len(snippets)}")


def test_snippet_triggers():
    """Test specific keyword triggers for snippets."""
    print("\n\n=== Testing Snippet Triggers ===")

    classifier = EnhancedTaskClassifier()

    trigger_tests = [
        ("how to use hooks in the system", "hooks_system"),
        ("implement parallel processing", "parallel_execution"),
        ("replace grep with something better", "modern_tools"),
        ("run multiple async operations", "parallel_execution"),
    ]

    for prompt, expected_snippet in trigger_tests:
        _, snippets, _ = classifier.analyze(prompt)
        found = expected_snippet in snippets
        print(f"\nPrompt: '{prompt}'")
        print(
            f"Expected snippet '{expected_snippet}': {'✓ Found' if found else '✗ Missing'}"
        )
        print(f"All snippets: {snippets}")


def test_full_suffix_generation():
    """Test complete suffix generation with CLAUDE.md snippets."""
    print("\n\n=== Testing Full Suffix Generation ===")

    # Clear cache to ensure fresh snippets
    ClaudeMdSnippets._snippets_cache = None

    test_prompts = [
        "what is 2+2?",  # Simple - should only get Next Steps
        "implement a secure authentication system with hooks",  # Complex - should get multiple snippets
        "debug performance issues using grep and find",  # Should trigger modern tools
    ]

    for prompt in test_prompts:
        suffix = get_suffix(prompt)

        print(f"\n{'=' * 60}")
        print(f"Prompt: '{prompt}'")
        print(f"Suffix length: {len(suffix)} chars")
        print("\nSuffix contains:")
        print(f"  Next Steps: {'✓' if 'Next Steps' in suffix else '✗'}")
        print(f"  Task-specific: {'✓' if '<task-specific>' in suffix else '✗'}")
        print(f"  CLAUDE.md snippets: {'✓' if '<claude-md-' in suffix else '✗'}")

        # Count specific snippets
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

        found_snippets = [tag for tag in snippet_tags if f"<{tag}>" in suffix]
        if found_snippets:
            print(f"  Found snippets: {', '.join(found_snippets)}")


def test_caching():
    """Test that caching works for repeated prompts."""
    print("\n\n=== Testing LRU Cache ===")

    prompt = "implement a complex authentication system"

    # Clear cache stats
    analyze_prompt_enhanced.cache_clear()

    # First call
    result1 = analyze_prompt_enhanced(prompt)
    cache_info1 = analyze_prompt_enhanced.cache_info()

    # Second call (should hit cache)
    result2 = analyze_prompt_enhanced(prompt)
    cache_info2 = analyze_prompt_enhanced.cache_info()

    print(f"Prompt: '{prompt}'")
    print(f"Cache hits increased: {cache_info2.hits > cache_info1.hits}")
    print(f"Results identical: {result1 == result2}")
    print(f"Cache stats: hits={cache_info2.hits}, misses={cache_info2.misses}")


if __name__ == "__main__":
    test_enhanced_classifier()
    test_complexity_thresholds()
    test_snippet_triggers()
    test_full_suffix_generation()
    test_caching()
