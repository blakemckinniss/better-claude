#!/usr/bin/env python3
"""Path access control and validation for PreToolUse hook."""

import os
from typing import Tuple

from .config import get_config


def normalize_path(path: str) -> str:
    """Normalize a path for consistent comparison."""
    # Convert to absolute path if relative
    if not os.path.isabs(path):
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        path = os.path.join(project_dir, path)
    return os.path.normpath(path)


def check_path_access(path: str, operation: str) -> Tuple[bool, str]:
    """Check if the given path can be accessed for the specified operation.

    Args:
        path: The file/directory path to check
        operation: One of "read", "write", "edit", "delete", "execute"

    Returns:
        (allowed, reason): Tuple of (bool, str) - whether allowed and reason if blocked
    """
    config = get_config()

    if not config.circuit_breaker.enabled:
        return True, ""

    normalized_path = normalize_path(path)

    # Check NO_ACCESS_PATHS first (most restrictive)
    for blocked_path in config.circuit_breaker.no_access_paths:
        normalized_blocked = normalize_path(blocked_path)
        if (
            normalized_path.startswith(normalized_blocked + os.sep)
            or normalized_path == normalized_blocked
        ):
            return False, f"Circuit breaker: {blocked_path} is in NO_ACCESS_PATHS"

    # Check operation-specific restrictions
    if operation in ["write", "edit", "delete"]:
        # Check READ_ONLY_PATHS
        for readonly_path in config.circuit_breaker.read_only_paths:
            normalized_readonly = normalize_path(readonly_path)
            if (
                normalized_path.startswith(normalized_readonly + os.sep)
                or normalized_path == normalized_readonly
            ):
                return False, f"Circuit breaker: {readonly_path} is in READ_ONLY_PATHS"

    if operation == "write":
        # Check WRITE_RESTRICTED_PATHS (only for new file creation)
        for restricted_path in config.circuit_breaker.write_restricted_paths:
            normalized_restricted = normalize_path(restricted_path)
            if (
                normalized_path.startswith(normalized_restricted + os.sep)
                or normalized_path == normalized_restricted
            ):
                # Check if file already exists
                if not os.path.exists(normalized_path):
                    return (
                        False,
                        f"Circuit breaker: Cannot create new files in {restricted_path}",
                    )

    if operation == "delete":
        # Check DELETE_PROTECTED_PATHS
        for protected_path in config.circuit_breaker.delete_protected_paths:
            normalized_protected = normalize_path(protected_path)
            if normalized_path == normalized_protected:
                return (
                    False,
                    f"Circuit breaker: {protected_path} is in DELETE_PROTECTED_PATHS",
                )

    return True, ""


def is_protected_file(file_path: str) -> bool:
    """Check if a file is in the protected files list."""
    config = get_config()
    normalized_path = normalize_path(file_path)

    for protected_file in config.circuit_breaker.protected_files:
        if normalized_path == normalize_path(protected_file):
            return True

    return False


def is_blocked_path(file_path: str) -> bool:
    """Check if a file path contains blocked patterns."""
    config = get_config()

    for blocked_pattern in config.circuit_breaker.blocked_paths:
        if blocked_pattern in file_path:
            return True

    return False


def check_recursive_claude_directory(file_path: str) -> bool:
    """Check if path contains recursive .claude directories."""
    # Count occurrences of .claude in the path
    claude_count = file_path.count(".claude")
    return claude_count > 1


def get_file_operation_from_tool(tool_name: str, tool_input: dict) -> Tuple[str, str]:
    """Extract file path and operation type from tool input.

    Returns:
        (file_path, operation): The file path and operation type
    """
    file_path = ""
    operation = ""

    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        operation = "read"
    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        operation = "write"
    elif tool_name in ["Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        operation = "edit"
    elif tool_name.startswith("mcp__filesystem__"):
        # Handle MCP filesystem operations
        if tool_name == "mcp__filesystem__read_text_file":
            file_path = tool_input.get("path", "")
            operation = "read"
        elif tool_name == "mcp__filesystem__write_file":
            file_path = tool_input.get("path", "")
            operation = "write"
        elif tool_name == "mcp__filesystem__edit_file":
            file_path = tool_input.get("path", "")
            operation = "edit"
        elif tool_name == "mcp__filesystem__move_file":
            # For move, check both source and destination
            source = tool_input.get("source", "")
            dest = tool_input.get("destination", "")
            # Check source for delete permission
            if source:
                allowed, reason = check_path_access(source, "delete")
                if not allowed:
                    return source, "delete"
            # Check destination for write permission
            file_path = dest
            operation = "write"

    return file_path, operation
