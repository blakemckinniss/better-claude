#!/usr/bin/env python3
"""Bash command validation and safety checks."""

import re
import shlex
from typing import List, Tuple

from .config import get_config
from .path_validator import check_path_access, normalize_path


class CommandValidator:
    """Validate and analyze bash commands for safety."""

    # Command patterns that require special validation
    DESTRUCTIVE_COMMANDS = {
        "rm": {"flags": ["-r", "-f", "-rf", "-fr"], "severity": "high"},
        "find": {"flags": ["-delete", "-exec rm"], "severity": "high"},
        "shred": {"flags": [], "severity": "critical"},
        "dd": {"flags": [], "severity": "critical"},
        "mkfs": {"flags": [], "severity": "critical"},
        "fdisk": {"flags": [], "severity": "critical"},
        "parted": {"flags": [], "severity": "critical"},
    }

    # Safe commands that should generally be allowed
    SAFE_COMMANDS = {
        "ls",
        "pwd",
        "echo",
        "cat",
        "grep",
        "sed",
        "awk",
        "sort",
        "uniq",
        "head",
        "tail",
        "wc",
        "date",
        "whoami",
        "which",
        "type",
        "env",
        "git",
        "npm",
        "yarn",
        "python",
        "node",
        "pip",
        "poetry",
        "rg",
        "fd",
        "bat",
        "jq",
        "curl",
        "wget",
        "diff",
        "patch",
        "ruff",
        "mypy",
        "pytest",
        "eslint",
        "prettier",
        "black",
    }

    @classmethod
    def is_protected_command(cls, command: str) -> bool:
        """Check if command matches protected patterns."""
        config = get_config()

        for pattern in config.circuit_breaker.protected_commands:
            if re.search(pattern, command):
                return True

        return False

    @classmethod
    def _validate_rm_command(
        cls,
        parts: List[str],
        command: str,
    ) -> Tuple[bool, str, List[str]]:
        """Validate rm command specifically."""
        warnings = []

        # Check for dangerous patterns
        if "/" in command and any(flag in parts for flag in ["-r", "-rf", "-fr"]):
            # Check if trying to delete system directories
            for part in parts[1:]:
                if part.startswith("-"):
                    continue

                # Normalize and check the path
                normalized = normalize_path(part)

                # Critical system paths
                critical_paths = [
                    "/",
                    "/bin",
                    "/boot",
                    "/dev",
                    "/etc",
                    "/lib",
                    "/lib64",
                    "/proc",
                    "/root",
                    "/sbin",
                    "/sys",
                    "/usr",
                    "/var",
                ]

                for critical in critical_paths:
                    if normalized == critical or normalized.startswith(f"{critical}/"):
                        return False, f"Cannot delete critical system path: {part}", []

                # Check general path access
                allowed, reason = check_path_access(part, "delete")
                if not allowed:
                    return False, reason, []

        # Check for glob patterns that might be too broad
        if "*" in command:
            glob_patterns = [p for p in parts[1:] if "*" in p and not p.startswith("-")]
            for pattern in glob_patterns:
                if pattern in ["*", "/*", "**", "/**"]:
                    return False, "Glob pattern too broad - could delete everything", []
                if pattern.startswith("/"):
                    warnings.append(
                        f"⚠️ Glob pattern '{pattern}' starts from root - be careful",
                    )

        return True, "", warnings

    @classmethod
    def _validate_find_command(
        cls,
        parts: List[str],
        command: str,
    ) -> Tuple[bool, str, List[str]]:
        """Validate find command specifically."""
        warnings = []

        # Check for -delete or -exec rm
        if "-delete" in parts:
            warnings.append("⚠️ find with -delete will remove files")

            # Make sure path is safe
            if len(parts) > 1 and not parts[1].startswith("-"):
                allowed, reason = check_path_access(parts[1], "delete")
                if not allowed:
                    return False, f"Cannot delete in path: {reason}", []

        # Check for -exec patterns
        if "-exec" in parts:
            try:
                exec_idx = parts.index("-exec")
                if exec_idx + 1 < len(parts):
                    exec_cmd = parts[exec_idx + 1]
                    if exec_cmd in ["rm", "shred", "dd"]:
                        warnings.append(f"⚠️ find with -exec {exec_cmd} is destructive")
            except (ValueError, IndexError):
                pass

        return True, "", warnings

    @classmethod
    def _extract_file_paths(cls, parts: List[str]) -> List[str]:
        """Extract potential file paths from command parts."""
        file_paths = []

        # Skip the command itself
        for i, part in enumerate(parts[1:], 1):
            # Skip flags
            if part.startswith("-"):
                continue

            # Check if it looks like a file path
            if "/" in part or part in [".", ".."]:
                file_paths.append(part)

            # Check for common file operation patterns
            if i > 1 and parts[i - 1] in [">", ">>", "<"]:
                file_paths.append(part)

        return file_paths

    @classmethod
    def _has_shell_execution(cls, command: str) -> bool:
        """Check if command might execute shell code."""
        # Patterns that indicate shell execution
        shell_patterns = [
            r"\$\(",  # Command substitution $(...)
            r"`",  # Backticks
            r"\|.*sh\s*$",  # Piping to shell
            r";\s*sh\s",  # ; sh
            r"&&\s*sh\s",  # && sh
            r"eval\s+",  # eval command
            r"exec\s+.*sh",  # exec shell
        ]

        for pattern in shell_patterns:
            if re.search(pattern, command):
                return True

        return False

    @classmethod
    def _check_redirects(cls, command: str) -> Tuple[bool, str, List[str]]:
        """Check for output redirection to sensitive files."""
        warnings = []

        # Look for > and >> redirects
        redirect_patterns = [
            (r">\s*([^>\s]+)", "write"),  # > file
            (r">>\s*([^>\s]+)", "append"),  # >> file
            (r"<\s*([^<\s]+)", "read"),  # < file
        ]

        for pattern, operation in redirect_patterns:
            matches = re.findall(pattern, command)
            for file_path in matches:
                # Remove quotes if present
                file_path = file_path.strip("\"'")

                if operation in ["write", "append"]:
                    allowed, reason = check_path_access(file_path, "write")
                    if not allowed:
                        return (
                            False,
                            f"Cannot redirect output to {file_path}: {reason}",
                            [],
                        )

                    # Warn about overwriting with >
                    if operation == "write" and ">" in command and ">>" not in command:
                        warnings.append(f"⚠️ Output redirect will overwrite {file_path}")

        return True, "", warnings

    @classmethod
    def analyze_command(cls, command: str) -> Tuple[bool, str, List[str]]:
        """Analyze a bash command for safety.

        Returns:
            (allowed, reason, warnings): Whether command is allowed, reason if blocked, and any warnings
        """
        config = get_config()
        warnings = []

        # Check if command is protected
        if cls.is_protected_command(command):
            return False, "Command matches protected pattern", []

        # Try to parse the command
        try:
            # Handle complex commands with pipes, redirects, etc.
            # For now, just look at the first command
            parts = shlex.split(command)
            if not parts:
                return True, "", []

            base_command = parts[0]

            # Check if it's a destructive command
            if base_command in cls.DESTRUCTIVE_COMMANDS:
                cmd_info = cls.DESTRUCTIVE_COMMANDS[base_command]

                # Check for dangerous flags
                for flag in cmd_info["flags"]:
                    if flag in parts[1:]:
                        if cmd_info["severity"] == "critical":
                            return (
                                False,
                                f"Critical command '{base_command}' with dangerous flag '{flag}'",
                                [],
                            )
                        else:
                            warnings.append(
                                f"⚠️ Destructive command '{base_command}' with flag '{flag}'",
                            )

                # Additional checks for specific commands
                if base_command == "rm":
                    return cls._validate_rm_command(parts, command)
                elif base_command == "find":
                    return cls._validate_find_command(parts, command)

            # Check for file operations
            file_paths = cls._extract_file_paths(parts)
            for file_path in file_paths:
                allowed, reason = check_path_access(file_path, "write")
                if not allowed:
                    return False, reason, []

            # Check for sudo usage
            if "sudo" in parts:
                if not config.circuit_breaker.allow_sudo:
                    return False, "Sudo usage is not allowed", []
                warnings.append("⚠️ Command uses sudo - elevated privileges")

            # Check for shell execution patterns
            if cls._has_shell_execution(command):
                warnings.append("🚨 Command may execute shell code")

            # Check for output redirection to critical files
            redirect_result = cls._check_redirects(command)
            if redirect_result[0] is False:
                return redirect_result
            warnings.extend(redirect_result[2])

        except Exception as e:
            # If we can't parse the command, be cautious
            warnings.append(
                f"⚠️ Complex command that couldn't be fully analyzed: {str(e)}",
            )

        return True, "", warnings

    @classmethod
    def suggest_safer_alternative(cls, command: str) -> str:
        """Suggest a safer alternative for dangerous commands."""
        # Simple suggestions for common dangerous patterns
        suggestions = {
            r"rm\s+-rf?\s+/": "Use 'rm -rf ./relative/path' instead of absolute paths",
            r"dd\s+if=.*of=/dev/": "Be extremely careful with dd - consider using a disk imaging tool",
            r"chmod\s+777": "Use more restrictive permissions like 755 or 644",
            r"curl.*\|\s*sh": "Download the script first and review it before executing",
            r"wget.*\|\s*bash": "Download the script first and review it before executing",
            r"sudo\s+rm": "Try to avoid using sudo with rm - check file ownership instead",
        }

        for pattern, suggestion in suggestions.items():
            if re.search(pattern, command):
                return suggestion

        return ""
