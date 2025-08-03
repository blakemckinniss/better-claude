#!/usr/bin/env python3
"""Read operation blocker with guidance for faster alternatives."""

from typing import Tuple


def check_read_operation_block(
    tool_name: str,
    operation: str,
) -> Tuple[bool, str]:
    """Check if Read operation should be blocked with Bash alternatives guidance.
    
    Args:
        tool_name: The name of the tool being used
        operation: The operation type (read, write, edit, etc.)
    
    Returns:
        (should_block, guidance_message): True if Read should be blocked
    """
    if tool_name == "Read" or (
        tool_name.startswith("mcp__filesystem__") and operation == "read"
    ):
        guidance = (
            "⚠️  Read() is disabled to conserve context.\n"
            "👉  Use these *fast* Bash commands instead:\n\n"
            "  •  ripgrep   –  Bash(command=\"rg --line-number 'def .*rate_limit' src\")\n"
            "  •  ctags     –  Bash(command=\"ctags -x --fields=+n src/api.py\")\n"
            "  •  tree-sitter – Bash(command=\"tree-sitter parse src/api.py | rg 'function_definition|class_definition'\")\n"
            "  •  sed slice –  Bash(command=\"sed -n '80,140p' src/api.py\")\n"
            "  •  scc stats –  Bash(command=\"scc --by-file --no-cocomo | head\")"
        )
        return True, guidance
    
    return False, ""