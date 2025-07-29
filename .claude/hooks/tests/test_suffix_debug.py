#!/usr/bin/env python3
"""Debug suffix generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0,
    str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit"),
)

from suffix_injection import (
    ClaudeMdSnippets,
    analyze_prompt_enhanced,
    get_suffix,
)

prompt = "implement a complex authentication system with modern tools and proper security hooks integration"
print(f"Testing prompt: '{prompt}'")

# Check complexity scoring with enhanced analyzer
apply_enhanced, score, categories, snippet_suggestions = analyze_prompt_enhanced(prompt)
print(f"\nComplexity score: {score}")
print(f"Apply enhanced: {apply_enhanced}")

# Check task classification
print(f"\nTask categories: {categories}")

# Check snippet suggestions from enhanced classifier
print(f"\nSnippet suggestions: {snippet_suggestions}")

# Get CLAUDE.md snippets based on enhanced suggestions
snippets = ClaudeMdSnippets.get_relevant_snippets_enhanced(
    snippet_suggestions,
    score,
)
print(f"\nCLAUDE.md snippets length: {len(snippets)}")
if snippets:
    print("Snippets preview:")
    print(f"{snippets[:200]}...")

# Get full suffix
suffix = get_suffix(prompt)
print(f"\nFull suffix length: {len(suffix)}")
print("\nChecking for expected content:")
print(f"  - Has Next Steps: {'Next Steps' in suffix}")
print(f"  - Has task-specific: {'<task-specific>' in suffix}")
print(f"  - Has claude-md-tools: {'<claude-md-tools>' in suffix}")
print(f"  - Has claude-md-coderules: {'<claude-md-coderules>' in suffix}")
print(f"  - Has claude-md-security: {'<claude-md-security>' in suffix}")
print(f"  - Has claude-md-hooks: {'<claude-md-hooks>' in suffix}")

# Show where CLAUDE.md snippets should appear
if apply_enhanced:
    print("\nSuffix should include CLAUDE.md snippets at the end...")
    # Show last 500 chars
    print("Last 500 chars of suffix:")
    print(suffix[-500:])
