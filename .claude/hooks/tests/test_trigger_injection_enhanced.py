#!/usr/bin/env python3
"""Test the enhanced trigger injection functionality."""

import sys
import json
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "hook_handlers"))

from hook_handlers.UserPromptSubmit.trigger_injection import (
    find_matching_tools,
    get_trigger_injection,
    check_negative_patterns,
    check_combination_patterns,
    TriggerConfig
)


def test_negative_patterns():
    """Test that negative patterns correctly exclude tools."""
    
    print("Testing negative pattern exclusions...\n")
    
    config = TriggerConfig()
    
    test_cases = [
        {
            "prompt": "This is not an issue with the code",
            "should_exclude": ["mcp__github__"],
            "description": "Negative pattern 'not an issue' excludes GitHub"
        },
        {
            "prompt": "Create a github issue for this bug",
            "should_exclude": [],
            "description": "Positive match overrides when context is clear"
        },
        {
            "prompt": "Let's avoid github for this project",
            "should_exclude": ["mcp__github__"],
            "description": "Negative pattern 'avoid github' excludes tool"
        },
        {
            "prompt": "This is a simple task, nothing complex",
            "should_exclude": ["mcp__zen__"],
            "description": "Negative pattern 'simple' excludes ZEN"
        },
        {
            "prompt": "Search code for the function",
            "should_exclude": ["mcp__tavily-remote__"],
            "description": "Negative pattern 'search code' excludes web search"
        }
    ]
    
    passed = 0
    for test in test_cases:
        prompt = test["prompt"]
        matches = find_matching_tools(prompt, config)
        matched_tools = [match[0] for match in matches]
        
        success = True
        for tool in test["should_exclude"]:
            if tool in matched_tools:
                success = False
                break
        
        status = "✓" if success else "✗"
        if success:
            passed += 1
        
        print(f"{status} {test['description']}")
        print(f"  Prompt: {prompt}")
        print(f"  Should exclude: {test['should_exclude']}")
        print(f"  Found tools: {matched_tools}")
        print()
    
    print(f"Passed: {passed}/{len(test_cases)} negative pattern tests\n")


def test_combination_patterns():
    """Test tool combination pattern matching."""
    
    print("Testing combination patterns...\n")
    
    config = TriggerConfig()
    
    test_cases = [
        {
            "prompt": "Create a pull request and set up code review process",
            "expected_tools": ["mcp__github__", "mcp__zen__"],
            "pattern": "github_workflow",
            "description": "GitHub workflow pattern"
        },
        {
            "prompt": "Debug this python error and fix the stack trace",
            "expected_tools": ["mcp__serena__", "mcp__zen__"],
            "pattern": "python_debugging",
            "description": "Python debugging pattern"
        },
        {
            "prompt": "Design system architecture for scalable deployment",
            "expected_tools": ["mcp__zen__", "mcp__filesystem__", "mcp__github__"],
            "pattern": "architecture_planning",
            "description": "Architecture planning pattern"
        },
        {
            "prompt": "Migrate the database schema to new version",
            "expected_tools": ["mcp__zen__", "mcp__filesystem__", "mcp__serena__"],
            "pattern": "migration_project",
            "description": "Migration project pattern"
        }
    ]
    
    passed = 0
    for test in test_cases:
        prompt = test["prompt"]
        expected = set(test["expected_tools"])
        
        # Check combination patterns
        combo_matches = check_combination_patterns(prompt)
        combo_tools = set()
        for name, tools, boost in combo_matches:
            if name == test["pattern"]:
                combo_tools.update(tools)
        
        # Also check full matches
        matches = find_matching_tools(prompt, config)
        matched_tools = set(match[0] for match in matches)
        
        # Success if expected tools are in top matches
        success = expected.issubset(matched_tools)
        
        status = "✓" if success else "✗"
        if success:
            passed += 1
        
        print(f"{status} {test['description']}")
        print(f"  Prompt: {prompt}")
        print(f"  Expected: {expected}")
        print(f"  Combo pattern tools: {combo_tools}")
        print(f"  All matched tools: {matched_tools}")
        
        # Show scores for matched tools
        for tool_id, tool_name, keywords, score in matches[:5]:
            if tool_id in expected:
                print(f"  - {tool_id}: score={score:.0f}, keywords={keywords}")
        print()
    
    print(f"Passed: {passed}/{len(test_cases)} combination pattern tests\n")


def test_logging_unmatched():
    """Test logging of unmatched prompts."""
    
    print("Testing unmatched prompt logging...\n")
    
    config = TriggerConfig()
    
    # Test prompts that shouldn't match
    unmatched_prompts = [
        "Calculate the square root of 144",
        "What's the weather today?",
        "Tell me a joke",
        "Explain quantum physics"
    ]
    
    for prompt in unmatched_prompts:
        injection = get_trigger_injection(prompt)
        if not injection:
            print(f"✓ Logged unmatched: {prompt}")
    
    # Check if log file was created
    if config.log_path.exists():
        with open(config.log_path, 'r') as f:
            logs = json.load(f)
        print(f"\n✓ Log file created with {len(logs)} entries")
        if logs:
            print(f"  Latest: {logs[-1]['prompt'][:50]}...")
    else:
        print("\n✗ Log file not created")


def test_priority_scoring():
    """Test the enhanced scoring system."""
    
    print("\nTesting priority scoring system...\n")
    
    test_prompts = [
        "Create a github pull request",  # Should be CRITICAL
        "Debug python code",  # Should be IMPORTANT/SUGGESTED
        "Simple file operation",  # Should be lower priority
        "Design scalable system architecture and plan deployment",  # Combo boost
        "Migrate database schema with python refactoring"  # Multiple boosts
    ]
    
    for prompt in test_prompts:
        print(f"Prompt: {prompt}")
        injection = get_trigger_injection(prompt)
        if injection:
            # Extract scores from injection
            lines = injection.split('\n')
            for line in lines:
                if "score:" in line:
                    print(f"  {line.strip()}")
        else:
            print("  No matches")
        print()


def test_full_integration():
    """Test complete integration with all features."""
    
    print("\nTesting full integration...\n")
    
    test_scenarios = [
        {
            "prompt": "Create PR on github but not an automated one",
            "description": "Mixed positive/negative signals"
        },
        {
            "prompt": "Debug python error in test suite and fix the bug",
            "description": "Multiple tools with combination boost"
        },
        {
            "prompt": "Simple calculation task",
            "description": "Should not trigger (negative patterns)"
        },
        {
            "prompt": "Set up CI/CD pipeline with github actions and deploy infrastructure",
            "description": "Complex multi-tool scenario"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"Scenario: {scenario['description']}")
        print(f"Prompt: {scenario['prompt']}")
        
        injection = get_trigger_injection(scenario['prompt'])
        if injection:
            print("Generated recommendations:")
            print(injection)
        else:
            print("No recommendations (possibly logged)")
        
        print("-" * 80)
        print()


if __name__ == "__main__":
    print("=" * 80)
    print("ENHANCED TRIGGER INJECTION TESTS")
    print("=" * 80)
    print()
    
    test_negative_patterns()
    test_combination_patterns()
    test_logging_unmatched()
    test_priority_scoring()
    test_full_integration()
    
    print("\nAll tests completed!")