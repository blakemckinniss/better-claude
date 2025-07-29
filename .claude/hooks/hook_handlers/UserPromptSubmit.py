#!/usr/bin/env python3
import json
import os
import sys

# Add the current directory to the path so we can import the UserPromptSubmit module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.content_injection import get_content_injection
from UserPromptSubmit.prefix_injection import get_prefix
from UserPromptSubmit.suffix_injection import get_suffix
from UserPromptSubmit.zen_injection import get_zen_injection


def handle(data):
    """Handle UserPromptSubmit hook events."""
    # Extract user prompt from data if available
    user_prompt = data.get("userPrompt", "") if isinstance(data, dict) else ""

    prefix = get_prefix()
    zen_instruction = get_zen_injection(user_prompt)
    content_instruction = get_content_injection(user_prompt)
    suffix = get_suffix()

    # Build additional context - combine all injections
    additional_context = f"{zen_instruction}{content_instruction}{prefix}{suffix}"

    # Return JSON output with additional context
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }

    print(json.dumps(output))
    sys.exit(0)
