#!/usr/bin/env python3
"""
Global hook guard module - ensures all hooks adhere to Claude Code documentation.

This module provides validation and execution guards for all hook types to ensure:
- Proper exit codes (0, 2, or other integers)
- Valid JSON output structures per hook type
- Appropriate stdout/stderr handling
- Consistent error reporting
"""

import json
import sys
import traceback
from io import StringIO
from typing import Any, Callable, Dict, Optional, Tuple


class HookOutputValidator:
    """Validates hook output according to Claude Code documentation."""

    @staticmethod
    def validate_common_fields(data: Dict[str, Any]) -> Optional[str]:
        """Validate common JSON fields available to all hooks."""
        # Check field types
        if "continue" in data and not isinstance(data["continue"], bool):
            return "'continue' must be a boolean"

        if "stopReason" in data and not isinstance(data["stopReason"], str):
            return "'stopReason' must be a string"

        if "suppressOutput" in data and not isinstance(data["suppressOutput"], bool):
            return "'suppressOutput' must be a boolean"

        # stopReason requires continue=false
        if "stopReason" in data and data.get("continue", True):
            return "'stopReason' can only be used when 'continue' is false"

        return None

    @staticmethod
    def validate_pretooluse_output(data: Dict[str, Any]) -> Optional[str]:
        """Validate PreToolUse-specific output."""
        # Check for hookSpecificOutput
        if "hookSpecificOutput" in data:
            hso = data["hookSpecificOutput"]
            if not isinstance(hso, dict):
                return "'hookSpecificOutput' must be a dictionary"

            if hso.get("hookEventName") != "PreToolUse":
                return "'hookEventName' must be 'PreToolUse'"

            # Validate permission decision
            if "permissionDecision" in hso:
                valid_decisions = ["allow", "deny", "ask"]
                if hso["permissionDecision"] not in valid_decisions:
                    return f"'permissionDecision' must be one of: {valid_decisions}"

                if "permissionDecisionReason" not in hso:
                    return "'permissionDecisionReason' is required with 'permissionDecision'"

        # Check deprecated fields
        if "decision" in data:
            # Handle None separately to avoid type issues
            if data["decision"] is not None and data["decision"] not in [
                "approve",
                "block",
            ]:
                return "'decision' must be 'approve', 'block', or null/undefined"

            if data["decision"] in ["approve", "block"] and "reason" not in data:
                return "'reason' is required with 'decision'"

        return None

    @staticmethod
    def validate_posttooluse_output(data: Dict[str, Any]) -> Optional[str]:
        """Validate PostToolUse-specific output."""
        if "decision" in data:
            valid_decisions = ["block", None]
            if data["decision"] not in valid_decisions:
                return "'decision' must be 'block' or null/undefined for PostToolUse"

            if data["decision"] == "block" and "reason" not in data:
                return "'reason' is required when decision is 'block'"

        return None

    @staticmethod
    def validate_userpromptsubmit_output(data: Dict[str, Any]) -> Optional[str]:
        """Validate UserPromptSubmit-specific output."""
        if "decision" in data:
            valid_decisions = ["block", None]
            if data["decision"] not in valid_decisions:
                return (
                    "'decision' must be 'block' or null/undefined for UserPromptSubmit"
                )

            if data["decision"] == "block" and "reason" not in data:
                return "'reason' is required when decision is 'block'"

        # Check for hookSpecificOutput
        if "hookSpecificOutput" in data:
            hso = data["hookSpecificOutput"]
            if not isinstance(hso, dict):
                return "'hookSpecificOutput' must be a dictionary"

            if hso.get("hookEventName") != "UserPromptSubmit":
                return "'hookEventName' must be 'UserPromptSubmit'"

            if "additionalContext" in hso and not isinstance(
                hso["additionalContext"],
                str,
            ):
                return "'additionalContext' must be a string"

        return None

    @staticmethod
    def validate_stop_output(data: Dict[str, Any]) -> Optional[str]:
        """Validate Stop/SubagentStop-specific output."""
        if "decision" in data:
            valid_decisions = ["block", None]
            if data["decision"] not in valid_decisions:
                return (
                    "'decision' must be 'block' or null/undefined for Stop/SubagentStop"
                )

            if data["decision"] == "block" and "reason" not in data:
                return "'reason' is required when decision is 'block'"

        return None

    @staticmethod
    def validate_sessionstart_output(data: Dict[str, Any]) -> Optional[str]:
        """Validate SessionStart-specific output."""
        # Check for hookSpecificOutput
        if "hookSpecificOutput" in data:
            hso = data["hookSpecificOutput"]
            if not isinstance(hso, dict):
                return "'hookSpecificOutput' must be a dictionary"

            if hso.get("hookEventName") != "SessionStart":
                return "'hookEventName' must be 'SessionStart'"

            if "additionalContext" in hso and not isinstance(
                hso["additionalContext"],
                str,
            ):
                return "'additionalContext' must be a string"

        return None

    @staticmethod
    def validate_json_output(
        output: str,
        hook_event: str,
    ) -> Tuple[bool, Optional[str]]:
        """Validate JSON output structure according to hook type.

        Returns: (is_valid, error_message)
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            # Not JSON, which is valid (plain text output)
            return True, None

        # Validate common fields first
        error = HookOutputValidator.validate_common_fields(data)
        if error:
            return False, error

        # Get valid fields for this hook type
        valid_common = {"continue", "stopReason", "suppressOutput"}
        valid_hook_specific = set()

        # Add hook-specific valid fields
        if hook_event == "PreToolUse":
            valid_hook_specific = {"hookSpecificOutput", "decision", "reason"}
            error = HookOutputValidator.validate_pretooluse_output(data)
        elif hook_event == "PostToolUse":
            valid_hook_specific = {"decision", "reason"}
            error = HookOutputValidator.validate_posttooluse_output(data)
        elif hook_event == "UserPromptSubmit":
            valid_hook_specific = {"decision", "reason", "hookSpecificOutput"}
            error = HookOutputValidator.validate_userpromptsubmit_output(data)
        elif hook_event in ["Stop", "SubagentStop"]:
            valid_hook_specific = {"decision", "reason"}
            error = HookOutputValidator.validate_stop_output(data)
        elif hook_event == "SessionStart":
            valid_hook_specific = {"hookSpecificOutput"}
            error = HookOutputValidator.validate_sessionstart_output(data)
        # Notification and PreCompact have no special fields

        if error:
            return False, error

        # Check for unknown fields
        all_valid_fields = valid_common | valid_hook_specific
        unknown_fields = set(data.keys()) - all_valid_fields
        if unknown_fields:
            return False, f"Unknown JSON fields for {hook_event}: {unknown_fields}"

        return True, None


class HookGuard:
    """Guards hook execution to ensure proper behavior."""

    @staticmethod
    def guard_execution(
        hook_func: Callable[[Dict[str, Any]], int],
        event_data: Dict[str, Any],
        hook_event: str,
    ) -> None:
        """Execute hook with proper guards for exit codes and output.

        This wrapper ensures:
        1. Exit codes are valid (0, 2, or other integers)
        2. JSON output follows documented schema for the hook type
        3. Errors are properly reported
        4. Claude gets appropriate feedback based on exit code

        Args:
            hook_func: The hook function to execute (should return exit code)
            event_data: The event data passed to the hook
            hook_event: The type of hook event (PreToolUse, PostToolUse, etc.)
        """
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # Capture stdout and stderr
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            # Temporarily redirect stdout/stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Run the actual hook
            try:
                exit_code = hook_func(event_data)
            except SystemExit as e:
                # SystemExit.code can be int, str, or None
                if isinstance(e.code, int):
                    exit_code = e.code
                elif e.code is None:
                    exit_code = 0
                else:
                    # Non-int exit code (likely string)
                    exit_code = 1
            except Exception as e:
                # Unexpected error - report to stderr and continue
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                print(
                    f"❌ Hook execution error in {hook_event}: {str(e)}",
                    file=sys.stderr,
                )
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                sys.exit(1)  # Non-blocking error

            # Restore original streams
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            # Get captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            # Validate exit code
            if not isinstance(exit_code, int):
                print(
                    f"⚠️ Invalid exit code type in {hook_event}: {type(exit_code)}. Using 1.",
                    file=sys.stderr,
                )
                exit_code = 1

            # Validate JSON output if present
            if stdout_content.strip():
                is_valid, error_msg = HookOutputValidator.validate_json_output(
                    stdout_content.strip(),
                    hook_event,
                )
                if not is_valid:
                    print(
                        f"⚠️ Invalid JSON output in {hook_event}: {error_msg}\n"
                        f"Output will be treated as plain text.",
                        file=sys.stderr,
                    )

            # Handle output according to exit code and hook type
            HookGuard._handle_output(
                exit_code,
                stdout_content,
                stderr_content,
                hook_event,
            )

            sys.exit(exit_code)

        except Exception as e:
            # Catastrophic error - ensure we don't break Claude
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            print(
                f"❌ Critical hook guard error in {hook_event}: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}",
                file=sys.stderr,
            )
            sys.exit(1)  # Non-blocking error

    @staticmethod
    def _handle_output(
        exit_code: int,
        stdout_content: str,
        stderr_content: str,
        hook_event: str,
    ) -> None:
        """Handle output based on exit code and hook type."""
        # Exit code 0: Success
        if exit_code == 0:
            # Special handling for UserPromptSubmit and SessionStart
            if hook_event in ["UserPromptSubmit", "SessionStart"]:
                # stdout goes to context (Claude sees it)
                if stdout_content:
                    print(stdout_content, end="")
            else:
                # stdout shown to user only
                if stdout_content:
                    print(stdout_content, end="")

            # Always show stderr warnings
            if stderr_content:
                print(stderr_content, file=sys.stderr, end="")

        # Exit code 2: Blocking/feedback to Claude
        elif exit_code == 2:
            # Handle based on hook type
            if hook_event == "UserPromptSubmit":
                # Special case: blocks prompt, shows stderr to user only
                if stderr_content:
                    print(stderr_content, file=sys.stderr, end="")
                else:
                    print(
                        "Prompt blocked by hook but no reason provided.",
                        file=sys.stderr,
                    )
            elif hook_event in ["Notification", "PreCompact", "SessionStart"]:
                # These don't support exit code 2 blocking
                print(
                    f"⚠️ {hook_event} hook returned exit code 2, but this hook type "
                    f"doesn't support blocking. Treating as error.",
                    file=sys.stderr,
                )
                if stderr_content:
                    print(stderr_content, file=sys.stderr, end="")
            else:
                # PreToolUse, PostToolUse, Stop, SubagentStop: stderr to Claude
                if stderr_content:
                    print(stderr_content, file=sys.stderr, end="")
                else:
                    print(
                        f"{hook_event} hook blocked but provided no feedback.",
                        file=sys.stderr,
                    )

        # Other exit codes: Non-blocking error
        else:
            # stderr to user only
            if stderr_content:
                print(stderr_content, file=sys.stderr, end="")
            else:
                print(
                    f"{hook_event} hook exited with code {exit_code}",
                    file=sys.stderr,
                )


def create_guarded_handler(
    hook_func: Callable[[Dict[str, Any]], int],
    hook_event: str,
) -> Callable[[Dict[str, Any]], None]:
    """Create a guarded version of a hook handler.

    Args:
        hook_func: The hook function that returns an exit code
        hook_event: The type of hook event

    Returns:
        A function that executes the hook with guards and calls sys.exit
    """

    def guarded_handler(event_data: Dict[str, Any]) -> None:
        HookGuard.guard_execution(hook_func, event_data, hook_event)

    return guarded_handler
