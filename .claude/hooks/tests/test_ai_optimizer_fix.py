#!/usr/bin/env python3
"""Test the AI context optimizer fix for proper behavior with different prompts."""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hook_handlers'))

from UserPromptSubmit.ai_context_optimizer import AIContextOptimizer


async def test_optimizer():
    """Test the optimizer with different types of prompts."""
    optimizer = AIContextOptimizer()
    
    # Sample context that might be injected
    sample_context = """
<system-instruction>
PERFORMANCE_DIRECTIVES:
- File Operations: ALWAYS batch Read/Write/Edit operations
- Subagent Usage: Spawn subagents using Task tool
- Think optimal. Consult with ZEN whenever possible.
</system-instruction>

Git Status:
Current branch: main
Modified files: .claude/hooks/hook_handlers/PostToolUse.py

Recent commits:
175bd07 feat: add comprehensive injection modules

<response-requirements>
ALWAYS end responses with 'Next Steps' section
</response-requirements>
"""
    
    # Test Case 1: Technical question (should NOT create role)
    print("=" * 60)
    print("TEST 1: Technical Question")
    print("=" * 60)
    tech_prompt = "What are the advantages of React over Svelte?"
    
    system_prompt1, user_prompt1 = optimizer._create_optimization_prompt(tech_prompt, sample_context)
    print("SYSTEM PROMPT (excerpt):")
    print(system_prompt1.split('\n')[0:5])  # First 5 lines
    print("\nUSER PROMPT (excerpt):")
    print(user_prompt1.split('\n')[0:5])  # First 5 lines
    print("...")
    print("\nEXPECTED: Should ask to extract relevant info, NOT create role")
    print("\n")
    
    # Test Case 2: Role/Agent request (should create role)
    print("=" * 60)
    print("TEST 2: Role/Agent Request")
    print("=" * 60)
    role_prompt = "Create a specialized debugging agent role"
    
    system_prompt2, user_prompt2 = optimizer._create_optimization_prompt(role_prompt, sample_context)
    print("SYSTEM PROMPT (excerpt):")
    print(system_prompt2.split('\n')[0:5])  # First 5 lines
    print("\nUSER PROMPT (excerpt):")
    print(user_prompt2.split('\n')[0:5])  # First 5 lines
    print("...")
    print("\nEXPECTED: Should ask to create specialized AI assistant role")
    print("\n")
    
    # Test Case 3: Another technical question
    print("=" * 60)
    print("TEST 3: Another Technical Question")
    print("=" * 60)
    debug_prompt = "How do I debug a memory leak in Python?"
    
    system_prompt3, user_prompt3 = optimizer._create_optimization_prompt(debug_prompt, sample_context)
    print("SYSTEM PROMPT (excerpt):")
    print(system_prompt3.split('\n')[0:5])  # First 5 lines
    print("\nUSER PROMPT (excerpt):")
    print(user_prompt3.split('\n')[0:5])  # First 5 lines
    print("...")
    print("\nEXPECTED: Should ask to extract relevant info, NOT create role")
    print("\n")
    
    # Test fallback optimization
    print("=" * 60)
    print("TEST 4: Fallback Optimization (No AI)")
    print("=" * 60)
    
    # Test technical question with fallback
    fallback1 = optimizer._fallback_optimization(tech_prompt, sample_context)
    print("FALLBACK OUTPUT (technical question):")
    print(fallback1[:200] + "...")
    print("\nEXPECTED: Should show relevant context, NOT role definition")
    print("\n")
    
    # Test role request with fallback
    fallback2 = optimizer._fallback_optimization(role_prompt, sample_context)
    print("FALLBACK OUTPUT (role request):")
    print(fallback2[:200] + "...")
    print("\nEXPECTED: Should show role definition format")


if __name__ == "__main__":
    asyncio.run(test_optimizer())