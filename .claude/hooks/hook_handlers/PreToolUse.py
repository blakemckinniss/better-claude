#!/usr/bin/env python3
import os
import re
import sys


def handle(data):
    """Handle PreToolUse hook events."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

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
