#!/usr/bin/env python3
"""
PreToolUse hook handler - now uses the global Guard module.

This file maintains backwards compatibility while delegating to the modular system
with proper guard protection.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None

# Import the global guard
try:
    from Guard import create_guarded_handler
except ImportError as e:
    print(f"Error importing Guard module: {e}", file=sys.stderr)
    sys.exit(1)

# Import the modular handler's components
try:
    from PreToolUse.__init__ import (
        handle_bash_command,
        handle_file_operation,
        handle_permission_request,
    )
    from PreToolUse.config import get_config
    from PreToolUse.operation_logger import OperationLogger
except ImportError as e:
    print(f"Error importing PreToolUse module: {e}", file=sys.stderr)
    sys.exit(1)


def handle_hook(event_data: Dict[str, Any]) -> int:
    """PreToolUse hook handler that returns exit code instead of calling sys.exit."""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(event_data, "PreToolUse")

    try:
        # Extract tool information
        tool_name = event_data.get("tool_name", "")
        tool_input = event_data.get("tool_input", {})

        # Skip if no tool name
        if not tool_name:
            if hook_logger:
                hook_logger.log_hook_exit(event_data, 0, "No tool name provided")
            return 0

        # Initialize components
        config = get_config()
        logger = OperationLogger()

        # Track all warnings
        all_warnings = []
        block_reason = ""

        # Handle different tool types
        if tool_name in ["Read", "Write", "Edit", "MultiEdit"] or tool_name.startswith(
            "mcp__filesystem__",
        ):
            # File operation
            allowed, reason, warnings = handle_file_operation(tool_name, tool_input)
            if not allowed:
                block_reason = reason
            all_warnings.extend(warnings)

        elif tool_name == "Bash":
            # Bash command
            allowed, reason, warnings = handle_bash_command(tool_input)
            if not allowed:
                block_reason = reason
            all_warnings.extend(warnings)

        # Log the operation
        result = "blocked" if block_reason else "allowed"
        # Convert string warnings to dict format for logger
        warning_dicts = [{"message": w, "severity": "warning"} for w in all_warnings]
        logger.log_operation(tool_name, tool_input, result, warning_dicts)

        # Handle blocking
        if block_reason:
            if hook_logger:
                hook_logger.log_decision(event_data, "block", block_reason)
            print(f"❌ {block_reason}", file=sys.stderr)
            print("📝 Note: Hooks can be temporarily disabled in", file=sys.stderr)
            print("/home/devcontainers/better-claude/.claude/hooks/hook_handler.py",file=sys.stderr)
            if hook_logger:
                hook_logger.log_hook_exit(event_data, 2, result="blocked")
            return 2  # Exit code 2 for blocking

        # Show warnings if any
        if all_warnings and config.display.show_warnings:
            for warning in all_warnings:
                print(warning, file=sys.stderr)

        # Handle permission requests if needed
        if event_data.get("permission_request"):
            output = handle_permission_request(
                tool_name,
                tool_input,
                event_data.get("original_output", ""),
            )
            if output:
                print(output)

        if hook_logger:
            hook_logger.log_hook_exit(event_data, 0, result="allowed")
        return 0  # Success

    except Exception as e:
        # Log the error
        if hook_logger:
            hook_logger.log_error(event_data, e)
        # Don't fail operations due to hook errors
        print(f"Hook error (operation allowed): {str(e)}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_hook_exit(event_data, 0, result="allowed_with_error")
        return 0  # Allow operation on error


# Create the guarded handler for PreToolUse
handle = create_guarded_handler(handle_hook, "PreToolUse")


if __name__ == "__main__":
    try:
        # Read event data from stdin
        event_data = json.loads(sys.stdin.read())

        # Use the guarded handler
        handle(event_data)

    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
