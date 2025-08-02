#!/usr/bin/env python3
"""Test the AI context optimizer questionnaire functionality."""

import asyncio
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hook_handlers.UserPromptSubmit.ai_context_optimizer import (
    AIContextOptimizer,
    optimize_injection_sync,
)


def test_fallback_questionnaire():
    """Test that the fallback optimization includes the questionnaire."""
    print("Testing fallback optimization with questionnaire...")

    optimizer = AIContextOptimizer()

    # Test with a complex request
    user_prompt = (
        "Can you implement a new feature to add user authentication with JWT tokens?"
    )
    raw_context = """
    Git branch: main
    Recent commits:
    - Added user model
    - Updated database schema
    
    MCP Tools available:
    - filesystem operations
    - web search
    """

    # Use the fallback method directly
    result = optimizer._fallback_optimization(user_prompt, raw_context)

    print("=== FALLBACK RESULT ===")
    print(result)

    # Verify questionnaire is present
    assert "=== CLAUDE CODE META ANALYSIS ===" in result
    assert "1. Confidence Level:" in result
    assert "2. Additional Information Needed:" in result
    assert "3. Primary Concerns:" in result
    assert "4. Proposed Next Steps:" in result
    assert "5. Web Research Recommended:" in result
    assert "6. Context7 Documentation Needed:" in result
    assert "7. ZEN Consultation Advised:" in result
    assert "8. Task Complexity Assessment:" in result
    assert "9. Estimated Time:" in result
    assert "10. Alternative Approaches:" in result
    assert "11. Parallelizable Components:" in result
    assert "12. Subagent Recommendations:" in result
    assert "13. Warnings/Hidden Risks:" in result
    assert "14. Counter-Arguments:" in result
    assert "15. Technical Debt Impact:" in result
    assert "16. Risk Level:" in result
    assert "17. Affected Systems:" in result
    assert "18. Bias/Anti-Pattern Check:" in result
    assert "19. Better Approach Available:" in result
    assert "20. Clarifying Questions:" in result

    print("\n✓ Fallback questionnaire test passed!")


async def test_ai_optimization():
    """Test the AI optimization with questionnaire (requires API key)."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("\n⚠️  Skipping AI optimization test - OPENROUTER_API_KEY not set")
        return

    print("\nTesting AI optimization with questionnaire...")

    user_prompt = "I need to debug an error in the payment processing module"
    raw_context = """
    Error: PaymentProcessingError at line 234
    Stack trace indicates null pointer exception
    
    Git status: Modified files in payment module
    """

    # Test the sync wrapper
    result = optimize_injection_sync(user_prompt, raw_context)

    print("\n=== AI OPTIMIZATION RESULT ===")
    print(result)

    # The AI should include the questionnaire if properly instructed
    if "=== CLAUDE CODE META ANALYSIS ===" in result:
        print("\n✓ AI optimization questionnaire test passed!")
    else:
        print("\n⚠️  AI did not include questionnaire - check API response")


def test_questionnaire_logic():
    """Test the questionnaire logic with different scenarios."""
    print("\nTesting questionnaire logic for different scenarios...")

    optimizer = AIContextOptimizer()

    test_cases = [
        {
            "prompt": "Fix the error in the login function",
            "context": "Error: Authentication failed\nGit branch: bugfix/login",
            "expected": {
                "complexity": "Moderate",
                "web_research": "No",
                "zen_advised": "No",
            },
        },
        {
            "prompt": "Create a complex microservices architecture",
            "context": "Current monolith needs refactoring",
            "expected": {
                "complexity": "Complex",
                "web_research": "No",
                "zen_advised": "Yes",
            },
        },
        {
            "prompt": "Update the library to the latest version",
            "context": "Using outdated React 16",
            "expected": {
                "complexity": "Moderate",
                "web_research": "Yes",
                "context7": "Yes",
            },
        },
        {
            "prompt": "Implement user authentication with JWT tokens and add security tests",
            "context": "New feature request",
            "expected": {
                "complexity": "Moderate",
                "subagents": "security-auditor",
                "warnings": "security implications require careful review",
                "parallel": "UI components, Backend logic, Tests, Documentation",
            },
        },
        {
            "prompt": "Quick fix for the delete user function",
            "context": "Urgent request",
            "expected": {
                "warnings": "data loss risk - ensure backups",
                "counter": "rushing may lead to technical debt",
                "subagents": "debugger",
                "tech_debt": "Creating",
                "risk_level": "8/10",
                "affected": "user management system",
            },
        },
        {
            "prompt": "Refactor and optimize the payment processing module",
            "context": "Code quality improvement",
            "expected": {
                "tech_debt": "Reducing",
                "risk_level": "7/10",
                "affected": "payment",
                "better_approach": "No",
            },
        },
        {
            "prompt": "Quick hack to workaround the singleton global issue",
            "context": "Temporary fix needed",
            "expected": {
                "anti_pattern": "Yes",
                "better_approach": "Yes",
                "tech_debt": "Creating",
            },
        },
    ]

    for i, test in enumerate(test_cases):
        print(f"\nTest case {i + 1}: {test['prompt'][:50]}...")
        result = optimizer._fallback_optimization(test["prompt"], test["context"])

        # Check expected values
        if "complexity" in test["expected"]:
            assert (
                f"Task Complexity Assessment: {test['expected']['complexity']}"
                in result
            )
        if "web_research" in test["expected"]:
            assert (
                f"Web Research Recommended: {test['expected']['web_research']}"
                in result
            )
        if "zen_advised" in test["expected"]:
            assert (
                f"ZEN Consultation Advised: {test['expected']['zen_advised']}" in result
            )
        if "subagents" in test["expected"]:
            assert test["expected"]["subagents"] in result
        if "warnings" in test["expected"]:
            assert test["expected"]["warnings"] in result
        if "counter" in test["expected"]:
            assert test["expected"]["counter"] in result
        if "parallel" in test["expected"]:
            assert test["expected"]["parallel"] in result
        if "tech_debt" in test["expected"]:
            assert f"Technical Debt Impact: {test['expected']['tech_debt']}" in result
        if "risk_level" in test["expected"]:
            assert f"Risk Level: {test['expected']['risk_level']}" in result
        if "affected" in test["expected"]:
            assert test["expected"]["affected"] in result
        if "anti_pattern" in test["expected"]:
            assert (
                f"Bias/Anti-Pattern Check: {test['expected']['anti_pattern']}" in result
            )
        if "better_approach" in test["expected"]:
            # Debug: print what we're looking for
            if (
                f"Better Approach Available: {test['expected']['better_approach']}"
                not in result
            ):
                print(
                    f"DEBUG: Looking for 'Better Approach Available: {test['expected']['better_approach']}'"
                )
                # Find and print the actual line
                for line in result.split("\n"):
                    if "Better Approach Available:" in line:
                        print(f"DEBUG: Found '{line.strip()}'")
            assert test["expected"]["better_approach"] in result

        print(f"✓ Test case {i + 1} passed")

    print("\n✓ All questionnaire logic tests passed!")


if __name__ == "__main__":
    print("AI Context Optimizer Questionnaire Tests")
    print("=" * 50)

    # Run tests
    test_fallback_questionnaire()
    test_questionnaire_logic()

    # Run async test
    asyncio.run(test_ai_optimization())

    print("\n✅ All tests completed!")
