#!/usr/bin/env python3
"""
PreToolUse hook handler - modular architecture for tool validation.

This module provides comprehensive validation and safety checks before
tools are executed, including:
- Path access control (circuit breaker)
- Git-aware validation
- Command safety analysis
- Pattern detection
- Operation logging
"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PreToolUse.command_validator import CommandValidator
from PreToolUse.config import get_config
from PreToolUse.dependency_analyzer import DependencyAnalyzer
from PreToolUse.git_validator import GitAwareValidator
from PreToolUse.operation_logger import OperationLogger
from PreToolUse.path_validator import (
    check_path_access,
    check_recursive_claude_directory,
    get_file_operation_from_tool,
    is_blocked_path,
    is_protected_file,
)
from PreToolUse.pattern_detector import IntelligentPatternDetector
from PreToolUse.read_blocker import check_read_operation_block

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None


def check_file_size_reduction(
    file_path: str,
    operation: str,
    tool_input: Dict[str, Any],
) -> Tuple[bool, str]:
    """Check if an edit would drastically reduce file size (potential destructive edit).

    Returns:
        (is_destructive, reason): True if edit appears destructive
    """
    if operation not in ["write", "edit"]:
        return False, ""

    # Only check if file exists
    if not os.path.exists(file_path):
        return False, ""

    try:
        # Get current file size
        current_size = os.path.getsize(file_path)
        current_lines = 0
        with open(file_path) as f:
            current_lines = sum(1 for _ in f)

        # For Write operations, check new content size
        if operation == "write":
            new_content = tool_input.get("content", "")
            new_size = len(new_content.encode("utf-8"))
            new_lines = new_content.count("\n") + (
                1 if new_content and not new_content.endswith("\n") else 0
            )

            # Check for significant reduction
            if current_size > 1000:  # Only check files larger than 1KB
                size_reduction_percent = (
                    (current_size - new_size) / current_size
                ) * 100
                line_reduction_percent = (
                    ((current_lines - new_lines) / current_lines) * 100
                    if current_lines > 0
                    else 0
                )

                if size_reduction_percent > 50 or line_reduction_percent > 50:
                    return True, (
                        f"❌ DESTRUCTIVE EDIT BLOCKED: This would remove {size_reduction_percent:.0f}% of file content\n"
                        f"   File: {file_path}\n"
                        f"   Current: {current_lines} lines ({current_size:,} bytes)\n"
                        f"   New: {new_lines} lines ({new_size:,} bytes)\n"
                        f"   Action: Review your changes - this appears to delete significant functionality\n"
                        f"   Hint: If you need to refactor, do it incrementally or explain the changes first"
                    )

        # For Edit operations, check if old_string is suspiciously large
        elif operation == "edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")

            if len(old_string) > 500 and len(new_string) < len(old_string) * 0.5:
                return True, (
                    f"❌ DESTRUCTIVE EDIT BLOCKED: Replacing {len(old_string)} chars with {len(new_string)} chars\n"
                    f"   File: {file_path}\n"
                    f"   Reduction: {((len(old_string) - len(new_string)) / len(old_string) * 100):.0f}%\n"
                    f"   Action: Break this into smaller, focused edits\n"
                    f"   Hint: Large replacements often indicate unintended deletion of functionality"
                )

    except Exception:
        # If we can't read the file, allow the operation
        pass

    return False, ""


def check_critical_file_modification(
    file_path: str,
    operation: str,
) -> Tuple[bool, str]:
    """Check if modifying a critical system file.

    Returns:
        (needs_warning, warning_message): True if this is a critical file
    """
    # List of critical files that should trigger warnings
    critical_files = [
        "UserPromptSubmit.py",
        "hook_handler.py",
        "Guard.py",
        "SessionStart.py",
        "Stop.py",
        "SubagentStop.py",
    ]

    # Check if this is a critical file
    basename = os.path.basename(file_path)
    if basename in critical_files and operation in ["write", "edit", "delete"]:
        return (
            True,
            f"⚠️ CRITICAL FILE: Modifying {basename} - this controls core hook functionality",
        )

    return False, ""


def check_technical_debt_filename(file_path: str) -> Tuple[bool, str]:
    """Check if filename contains technical debt keywords.

    Returns:
        (is_technical_debt, keyword): True if filename contains debt keywords
    """
    # Technical debt keywords to check for
    debt_keywords = [
        "backup",
        "v2",
        "enhanced",
        "legacy",
        "old",
        "revised",
        "new",
        "copy",
        "temp",
        "tmp",
        "bak",
        "orig",
        "v3",
        "v4",
        "original",
        "renamed",
        "deprecated",
        "archived",
        "obsolete",
        "draft",
        "example",
        "sample",
        "_old",
        "_new",
        "_backup",
        "_legacy",
        "_temp",
        "_copy",
    ]

    # Get the filename (not the full path)
    filename = os.path.basename(file_path).lower()

    # Check for exact matches and partial matches
    for keyword in debt_keywords:
        # Check if keyword appears in filename
        if keyword in filename:
            # Special handling for 'new' - avoid false positives like 'renewal', 'newest'
            if keyword == "new" and not any(
                [
                    filename.startswith("new"),
                    filename.endswith("new"),
                    "_new" in filename,
                    ".new" in filename,
                    "new_" in filename,
                    "new." in filename,
                ],
            ):
                continue
            return True, keyword

    return False, ""


def handle_file_operation(
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Tuple[bool, str, List[str]]:
    """Handle file operation validation."""
    warnings = []

    # Extract file path and operation
    file_path, operation = get_file_operation_from_tool(tool_name, tool_input)

    # Check for Read operation blocking FIRST (highest priority)
    should_block_read, guidance = check_read_operation_block(tool_name, operation)
    if should_block_read:
        return False, guidance, []

    if not file_path:
        return True, "", []

    # Check for destructive edits (second priority)
    is_destructive, reason = check_file_size_reduction(file_path, operation, tool_input)
    if is_destructive:
        return False, reason, []

    # Check for critical file modifications
    is_critical, warning = check_critical_file_modification(file_path, operation)
    if is_critical:
        warnings.append(warning)

    # Check for technical debt in filename for write operations
    if operation == "write":
        is_debt, keyword = check_technical_debt_filename(file_path)
        if is_debt:
            return (
                False,
                f"❌ TECHNICAL DEBT DETECTED: Filename contains '{keyword}' which suggests legacy/backup code.\n"
                f"   File: {file_path}\n"
                f"   Policy: No backup files, v2 files, or legacy files allowed.\n"
                f"   Action: Choose a proper descriptive name without technical debt keywords.\n"
                f"   Example: Instead of 'user_v2.py', use 'user.py' and update the existing file.",
                [],
            )

    # Check recursive .claude directories
    if check_recursive_claude_directory(file_path):
        return (
            False,
            "Recursive .claude directories detected - this might cause infinite loops",
            [],
        )

    # Check blocked paths
    if is_blocked_path(file_path):
        return False, f"Path contains blocked pattern: {file_path}", []

    # Check path access
    allowed, reason = check_path_access(file_path, operation)
    if not allowed:
        return False, reason, []

    # Check for protected files
    if operation in ["write", "edit", "delete"] and is_protected_file(file_path):
        # Add warning but don't block - user might have good reason
        warnings.append(f"⚠️ Modifying protected file: {file_path}")

    # Pattern detection
    pattern_warnings = IntelligentPatternDetector.check_patterns(file_path)
    for pattern_warning in pattern_warnings:
        warnings.append(pattern_warning["message"])

    # Git-aware validation
    if operation in ["edit", "delete"]:
        git_status = GitAwareValidator.get_git_status(file_path)
        if git_status == "clean":
            warnings.append(
                f"💡 File {file_path} has no uncommitted changes - "
                "changes will be in git diff",
            )
        elif git_status == "modified":
            warnings.append(
                f"⚠️ File {file_path} has uncommitted changes - "
                "be careful not to lose work",
            )

    # Check import impact for deletions
    if operation == "delete" and file_path.endswith((".py", ".js", ".ts")):
        import_count = DependencyAnalyzer.check_import_impact(file_path)
        if import_count > 0:
            importing_files = DependencyAnalyzer.get_importing_files(file_path)
            warnings.append(
                f"🚨 {import_count} files import this module: "
                f"{', '.join(importing_files[:3])}"
                f"{'...' if len(importing_files) > 3 else ''}",
            )

    return True, "", warnings


def handle_bash_command(tool_input: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """Handle bash command validation."""
    command = tool_input.get("command", "")

    if not command:
        return True, "", []

    # Analyze command for safety
    allowed, reason, warnings = CommandValidator.analyze_command(command)

    if not allowed:
        # Suggest safer alternative if available
        suggestion = CommandValidator.suggest_safer_alternative(command)
        if suggestion:
            reason = f"{reason}\n💡 Suggestion: {suggestion}"
        return False, reason, []

    # Additional pattern detection for commands
    command_warnings = IntelligentPatternDetector.check_command_patterns(command)
    for warning in command_warnings:
        warnings.append(warning["message"])

    return True, "", warnings


def handle_permission_request(
    tool_name: str,
    tool_input: Dict[str, Any],
    original_output: str,
) -> str:
    """Handle permission request formatting."""
    config = get_config()

    # Check if we should use optimistic mode
    if config.permission.mode == "optimistic":
        # In optimistic mode, try to auto-approve safe operations
        if tool_name in ["Read", "mcp__filesystem__read_text_file"]:
            return json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "Auto-approved read operation (optimistic mode)",
                    },
                },
            )

    # For other cases, return the original output
    return original_output


def handle(event_data: Dict[str, Any]) -> None:
    """Main handler for PreToolUse hook."""
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
                hook_logger.log_hook_exit(event_data, 0, result="no_tool_name")
            sys.exit(0)

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
            print(f"❌ {block_reason}", file=sys.stderr)
            print("\n📝 Note: Hooks can be temporarily disabled in", file=sys.stderr)
            print(
                "   /home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
                file=sys.stderr,
            )
            if hook_logger:
                hook_logger.log_hook_exit(event_data, 2, error=block_reason)
            sys.exit(2)

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
        
        # Successful completion
        if hook_logger:
            hook_logger.log_hook_exit(event_data, 0, result="allowed")
        sys.exit(0)

    except Exception as e:
        # Don't fail operations due to hook errors
        print(f"Hook error (operation allowed): {str(e)}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_error(event_data, e)
            hook_logger.log_hook_exit(event_data, 0, error=str(e))
        sys.exit(0)


if __name__ == "__main__":
    # When run directly, parse stdin
    try:
        event_data = json.loads(sys.stdin.read())
        handle(event_data)
    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
