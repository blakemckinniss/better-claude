#!/usr/bin/env python3
import os
import re
import sys

# ====================================================================
# CIRCUIT BREAKER CONFIGURATION
# ====================================================================
# Control file system access for Claude
# Paths should be absolute or relative to project root

# Paths that cannot be modified (read-only)
READ_ONLY_PATHS = [
    # Example: ".claude",  # Uncomment to make entire .claude directory read-only
    # Example: "/home/devcontainers/better-claude/.claude",  # Absolute path
]

# Paths that cannot be accessed at all (no read, write, or execute)
NO_ACCESS_PATHS = [
    # Example: ".env",
    # Example: "secrets/",
]

# Paths where new files cannot be created (existing files can be edited)
WRITE_RESTRICTED_PATHS = [
    # Example: ".claude/hooks/hook_handlers",  # Prevent new hook handlers
]

# Paths that cannot be deleted
DELETE_PROTECTED_PATHS = [
    ".claude/settings.json",
    ".claude/hooks/hook_handler.py",
]

# Enable/disable circuit breaker (set to False to bypass all checks)
CIRCUIT_BREAKER_ENABLED = True

def normalize_path(path):
    """Normalize a path for consistent comparison."""
    # Convert to absolute path if relative
    if not os.path.isabs(path):
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        path = os.path.join(project_dir, path)
    return os.path.normpath(path)


def check_path_access(path, operation):
    """Check if the given path can be accessed for the specified operation.

    Args:
        path: The file/directory path to check
        operation: One of "read", "write", "edit", "delete", "execute"

    Returns:
        (allowed, reason): Tuple of (bool, str) - whether allowed and reason if blocked
    """
    if not CIRCUIT_BREAKER_ENABLED:
        return True, ""

    normalized_path = normalize_path(path)

    # Check NO_ACCESS_PATHS first (most restrictive)
    for blocked_path in NO_ACCESS_PATHS:
        normalized_blocked = normalize_path(blocked_path)
        if (
            normalized_path.startswith(normalized_blocked + os.sep)
            or normalized_path == normalized_blocked
        ):
            return False, f"Circuit breaker: {blocked_path} is in NO_ACCESS_PATHS"

    # Check operation-specific restrictions
    if operation in ["write", "edit", "delete"]:
        # Check READ_ONLY_PATHS
        for readonly_path in READ_ONLY_PATHS:
            normalized_readonly = normalize_path(readonly_path)
            if (
                normalized_path.startswith(normalized_readonly + os.sep)
                or normalized_path == normalized_readonly
            ):
                return False, f"Circuit breaker: {readonly_path} is in READ_ONLY_PATHS"

    if operation == "write":
        # Check WRITE_RESTRICTED_PATHS (only for new file creation)
        for restricted_path in WRITE_RESTRICTED_PATHS:
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
        for protected_path in DELETE_PROTECTED_PATHS:
            normalized_protected = normalize_path(protected_path)
            if normalized_path == normalized_protected:
                return (
                    False,
                    f"Circuit breaker: {protected_path} is in DELETE_PROTECTED_PATHS",
                )

    return True, ""


def handle(data):
    """Handle PreToolUse hook events."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # ====================================================================
    # CIRCUIT BREAKER CHECKS
    # ====================================================================

    # Handle Read operations
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            allowed, reason = check_path_access(file_path, "read")
            if not allowed:
                print(reason, file=sys.stderr)
                sys.exit(2)

    # Handle Write operations
    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if file_path:
            allowed, reason = check_path_access(file_path, "write")
            if not allowed:
                print(reason, file=sys.stderr)
                sys.exit(2)

    # Handle Edit operations
    elif tool_name in ["Edit", "MultiEdit"]:
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
        else:  # MultiEdit
            file_path = tool_input.get("file_path", "")

        if file_path:
            allowed, reason = check_path_access(file_path, "edit")
            if not allowed:
                print(reason, file=sys.stderr)
                sys.exit(2)

    # Handle Bash commands - check for file operations
    elif tool_name == "Bash":
        command = tool_input.get("command", "")

        # Extract file paths from common commands

        # Check for rm/unlink commands (delete operations)
        if re.search(r"\b(rm|unlink)\b", command):
            # Extract paths after rm/unlink
            matches = re.findall(r"(?:rm|unlink)\s+(?:-[rf]+\s+)?([^\s;|&]+)", command)
            for path in matches:
                path = path.strip("\"'")
                allowed, reason = check_path_access(path, "delete")
                if not allowed:
                    print(reason, file=sys.stderr)
                    sys.exit(2)

        # Check for redirect operations (write)
        if ">" in command:
            # Extract paths after > or >>
            matches = re.findall(r">\s*([^\s;|&]+)", command)
            for path in matches:
                path = path.strip("\"'")
                allowed, reason = check_path_access(path, "write")
                if not allowed:
                    print(reason, file=sys.stderr)
                    sys.exit(2)

        # Check for commands that read files
        read_commands = ["cat", "less", "more", "head", "tail", "grep", "awk", "sed"]
        for cmd in read_commands:
            if re.search(rf"\b{cmd}\b", command):
                # Simple extraction - may need refinement
                matches = re.findall(rf"{cmd}\s+(?:-[^\s]+\s+)*([^\s;|&]+)", command)
                for path in matches:
                    path = path.strip("\"'")
                    if os.path.exists(path) or not path.startswith("-"):
                        allowed, reason = check_path_access(path, "read")
                        if not allowed:
                            print(reason, file=sys.stderr)
                            sys.exit(2)

    # ====================================================================
    # EXISTING PROTECTION LOGIC
    # ====================================================================

    # Handle Bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        description = tool_input.get("description", "No description")

        # Log Bash commands
        log_dir = os.path.expanduser("~/.claude")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "bash-command-log.txt")
        with open(log_path, "a") as f:
            f.write(f"{command} - {description}\n")

        # Block dangerous commands
        dangerous_patterns = ["rm -rf /", "dd if=/dev/zero", ":(){:|:&};:"]
        if any(pattern in command for pattern in dangerous_patterns):
            print("Blocked: Dangerous command detected", file=sys.stderr)
            sys.exit(2)

        # Protect critical Claude files from deletion
        protected_files = [
            "/home/devcontainers/better-claude/.claude/settings.json",
            "/home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
        ]

        if "rm " in command or "unlink " in command:
            for protected_file in protected_files:
                if protected_file in command:
                    print(
                        f"Blocked: Cannot delete {protected_file} - critical Claude file is protected",
                        file=sys.stderr,
                    )
                    sys.exit(2)

    # Handle file modifications
    elif tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = tool_input.get("file_path", tool_input.get("path", ""))

        # Prevent recursive .claude directories
        if ".claude" in file_path:
            # Count occurrences of .claude in the path
            claude_count = file_path.count(".claude")
            if claude_count > 1:
                print(
                    f"Blocked: Cannot create recursive .claude directories in {file_path}",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Prevent new files in hook_handlers directory
        if tool_name in ["Write"]:  # Only block on file creation
            # Normalize path for comparison
            normalized_path = os.path.normpath(file_path)
            hook_handlers_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/hook_handlers",
            )

            # Check if trying to create new file in hook_handlers directory
            if (
                normalized_path.startswith(hook_handlers_dir + os.sep)
                or normalized_path == hook_handlers_dir
            ):
                print(
                    "Blocked: Cannot create new files in hook_handlers directory",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Ensure test files are only created in the tests directory
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path)
            normalized_path = os.path.normpath(file_path)
            tests_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/tests",
            )

            # Check if it's a test file (starts with test_ or ends with _test.py)
            if filename.startswith("test_") or filename.endswith("_test.py"):
                # Ensure it's in the tests directory
                if not normalized_path.startswith(tests_dir + os.sep):
                    print(
                        f"Blocked: Test files must be created in {tests_dir}",
                        file=sys.stderr,
                    )
                    sys.exit(2)

        # Ensure markdown files are only created in the docs directory
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path)
            normalized_path = os.path.normpath(file_path)
            docs_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/docs",
            )

            # Check if it's a markdown file (but allow README.md anywhere)
            if filename.endswith((".md", ".markdown")) and filename != "README.md":
                # Ensure it's in the docs directory
                if not normalized_path.startswith(docs_dir + os.sep):
                    print(
                        f"Blocked: Markdown files (except README.md) must be created in {docs_dir}",
                        file=sys.stderr,
                    )
                    sys.exit(2)

        # Prevent backwards compatibility naming patterns
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path).lower()
            # Check for bad naming patterns (but allow .bak/.backup extensions)
            bad_patterns = [
                r"\benhanced\b",
                r"\badvanced\b",
                r"\bv2\b",
                r"\bv\d+\b",
                r"\bbackup\b",
            ]
            # Extract filename without extension
            name_without_ext = os.path.splitext(filename)[0]

            for pattern in bad_patterns:
                if re.search(pattern, name_without_ext):
                    print(
                        f"Blocked: Please use descriptive names instead of '{os.path.basename(file_path)}'. Avoid 'enhanced', 'advanced', 'v2', or 'backup' in filenames.",
                        file=sys.stderr,
                    )
                    sys.exit(2)

        # Block protected file modifications
        blocked_paths = [
            ".env",
            "package-lock.json",
            ".git/",
            "yarn.lock",
            "Gemfile.lock",
        ]

        # Special protection for critical Claude files - exact match required
        protected_files = [
            "/home/devcontainers/better-claude/.claude/settings.json",
            "/home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
        ]

        normalized_file_path = os.path.normpath(file_path)
        for protected_file in protected_files:
            if normalized_file_path == os.path.normpath(protected_file):
                print(
                    f"Blocked: Cannot modify {file_path} - critical Claude file is protected",
                    file=sys.stderr,
                )
                sys.exit(2)

        if any(p in file_path for p in blocked_paths):
            print(
                f"Blocked: Cannot modify {file_path} - protected file",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)
