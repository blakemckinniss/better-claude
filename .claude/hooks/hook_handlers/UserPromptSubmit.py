#!/usr/bin/env python3
import json
import os
import sys

# Add the current directory to the path so we can import the UserPromptSubmit module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.content_injection import get_content_injection
from UserPromptSubmit.git_injection import get_git_injection
from UserPromptSubmit.mcp_injector import get_mcp_injection
from UserPromptSubmit.prefix_injection import get_prefix
from UserPromptSubmit.suffix_injection import get_suffix
from UserPromptSubmit.tree_sitter_injection import (
    create_tree_sitter_injection,
    get_tree_sitter_hints,
)
from UserPromptSubmit.trigger_injection import get_trigger_injection
from UserPromptSubmit.zen_injection import get_zen_injection


def handle(data):
    """Handle UserPromptSubmit hook events."""
    # Extract user prompt from data if available
    user_prompt = data.get("userPrompt", "") if isinstance(data, dict) else ""

    # Get project directory from environment
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    prefix = get_prefix()
    git_injection = get_git_injection(project_dir)
    zen_instruction = get_zen_injection(user_prompt)
    content_instruction = get_content_injection(user_prompt)
    trigger_instruction = get_trigger_injection(user_prompt)
    tree_sitter_injection = create_tree_sitter_injection(user_prompt)
    tree_sitter_hints = get_tree_sitter_hints(user_prompt)
    mcp_recommendations = get_mcp_injection(user_prompt)
    suffix = get_suffix(user_prompt)

    # Import and get agent recommendations
    from UserPromptSubmit.agent_injector import get_agent_injection

    agent_recommendations = get_agent_injection(user_prompt)

    # Build additional context - combine all injections
    # Git injection goes early for foundational context
    additional_context = (
        f"{git_injection}\n{zen_instruction}{content_instruction}{prefix}{trigger_instruction}"
        f"{tree_sitter_injection}{tree_sitter_hints}{mcp_recommendations}{agent_recommendations}{suffix}"
    )

    # Return JSON output with additional context
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }

    print(json.dumps(output))
    sys.exit(0)
