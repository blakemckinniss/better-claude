#!/usr/bin/env python3
"""Demo script to show AI context optimizer with questionnaire."""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hook_handlers.UserPromptSubmit.ai_context_optimizer import (
    AIContextOptimizer,
    optimize_injection_sync,
)


def demo_questionnaire():
    """Demonstrate the questionnaire functionality."""
    print("AI Context Optimizer Questionnaire Demo")
    print("=" * 50)

    optimizer = AIContextOptimizer()

    # Test cases
    test_cases = [
        {
            "prompt": "Fix the authentication error in user login",
            "context": """
            <lsp-diagnostics>
            ❌ Error: TypeError at auth.py:42 - Cannot read property 'password' of undefined
            </lsp-diagnostics>
            
            Git branch: bugfix/auth-error
            Recent commits:
            - Updated user model
            - Fixed password hashing
            """,
        },
        {
            "prompt": "Implement a complex microservices architecture for our e-commerce platform",
            "context": """
            Current architecture: Monolithic Rails application
            Team size: 5 developers
            Timeline: 6 months
            
            Requirements:
            - User service
            - Product service
            - Order service
            - Payment service
            """,
        },
        {
            "prompt": "Quick hack to bypass the singleton validation temporarily",
            "context": """
            Urgent production issue needs immediate workaround
            Proper fix scheduled for next sprint
            """,
        },
    ]

    for i, test in enumerate(test_cases):
        print(f"\n\n{'=' * 50}")
        print(f"Demo {i + 1}: {test['prompt'][:50]}...")
        print("=" * 50)

        # Use fallback optimization (no API key needed)
        result = optimizer._fallback_optimization(test["prompt"], test["context"])
        print(result)

        # If API key is available, also show AI optimization
        if os.environ.get("OPENROUTER_API_KEY"):
            print("\n--- AI OPTIMIZATION ---")
            ai_result = optimize_injection_sync(test["prompt"], test["context"])
            print(ai_result)


if __name__ == "__main__":
    demo_questionnaire()
