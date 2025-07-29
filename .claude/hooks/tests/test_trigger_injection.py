#!/usr/bin/env python3
"""Test the trigger injection functionality with scoring."""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "hook_handlers"))

from hook_handlers.UserPromptSubmit.trigger_injection import (
    find_matching_tools,
    get_trigger_injection,
    TriggerConfig
)


def test_keyword_matching_with_scores():
    """Test that keywords are correctly matched to tools with scores."""
    
    config = TriggerConfig()
    
    test_cases = [
        {
            "prompt": "Create a pull request on github",
            "expected_tools": ["mcp__github__"],
            "min_score": 70,
            "description": "GitHub keywords with high score"
        },
        {
            "prompt": "I need to debug this complex issue and analyze the architecture",
            "expected_tools": ["mcp__zen__"],
            "min_score": 30,
            "description": "ZEN analysis keywords"
        },
        {
            "prompt": "Find all references to the User class in my python code",
            "expected_tools": ["mcp__serena__"],
            "min_score": 50,
            "description": "Python navigation keywords"
        },
        {
            "prompt": "Search the web for React documentation and extract content from the official site",
            "expected_tools": ["mcp__tavily-remote__", "mcp__context7__"],
            "min_score": 40,
            "description": "Web search and library docs"
        },
        {
            "prompt": "Set up a CI/CD pipeline with github actions for deployment",
            "expected_tools": ["mcp__github__", "mcp__zen__"],
            "min_score": 50,
            "description": "CI/CD keywords triggering multiple tools"
        },
        {
            "prompt": "Create a full stack application with React frontend and Django backend",
            "expected_tools": ["mcp__zen__", "mcp__filesystem__"],
            "min_score": 30,
            "description": "Full stack development"
        }
    ]
    
    print("Testing keyword matching with scores...\n")
    
    passed = 0
    total = len(test_cases)
    
    for test in test_cases:
        prompt = test["prompt"]
        expected = set(test["expected_tools"])
        min_score = test["min_score"]
        
        # Find matching tools
        matches = find_matching_tools(prompt, config)
        matched_tools = {match[0]: match[3] for match in matches}
        
        # Check if expected tools were found with sufficient score
        success = True
        for expected_tool in expected:
            if expected_tool not in matched_tools:
                success = False
                break
            if matched_tools[expected_tool] < min_score:
                success = False
                break
        
        status = "✓" if success else "✗"
        if success:
            passed += 1
        
        print(f"{status} {test['description']}")
        print(f"  Prompt: {prompt}")
        print(f"  Expected: {expected} (min score: {min_score})")
        print(f"  Found:")
        
        for tool_id, tool_name, keywords, score in matches[:5]:
            marker = "✓" if tool_id in expected else " "
            print(f"    {marker} {tool_id}: {score:.0f} - {', '.join(keywords[:3])}")
        
        print()
    
    print(f"\nPassed: {passed}/{total} tests")


def test_injection_output_formats():
    """Test the injection output format with different score levels."""
    
    print("\nTesting injection output formats...\n")
    
    test_prompts = [
        ("Help me create a pull request on github", "High priority (GitHub)"),
        ("I need to analyze code architecture and plan implementation", "Medium priority (ZEN)"),
        ("Search for Python documentation online", "Mixed priority"),
        ("Just a simple calculation", "No injection expected"),
        ("Set up CI/CD pipeline with GitHub Actions and deploy", "Domain keywords")
    ]
    
    for prompt, description in test_prompts:
        print(f"Test: {description}")
        print(f"Prompt: {prompt}")
        injection = get_trigger_injection(prompt)
        
        if injection:
            print("Generated injection:")
            print(injection)
        else:
            print("No injection (no keywords matched)")
        
        print("-" * 70)
        print()


def test_custom_configuration():
    """Test loading custom configuration."""
    
    print("\nTesting configuration system...\n")
    
    config = TriggerConfig()
    
    # Check if example config was created
    example_path = config.config_path.with_suffix('.example.json')
    if example_path.exists():
        print(f"✓ Example configuration file exists: {example_path}")
    else:
        print(f"✗ Example configuration file missing: {example_path}")
    
    # Test with a prompt that would match custom keywords if config was loaded
    prompt = "Deploy to prod using my-org github"
    matches = find_matching_tools(prompt, config)
    
    print(f"\nTesting with prompt: {prompt}")
    if matches:
        for tool_id, tool_name, keywords, score in matches:
            print(f"  - {tool_id}: {score:.0f} - {', '.join(keywords)}")
    else:
        print("  No matches (custom config not loaded)")


if __name__ == "__main__":
    test_keyword_matching_with_scores()
    test_injection_output_formats()
    test_custom_configuration()