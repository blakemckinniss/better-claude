#!/usr/bin/env python3
"""Auto-formatting logic for different file types."""

import os
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple


class FormatterError(Exception):
    """Raised when a formatter fails."""


class CodeFormatter(ABC):
    """Base class for code formatters."""

    def __init__(self):
        self.formatters_cache = {}

    @abstractmethod
    def format(self, file_path: str) -> List[Tuple[str, str]]:
        """Format a file.

        Must be implemented by subclasses.
        """

    def check_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available in the system."""
        if tool_name in self.formatters_cache:
            return self.formatters_cache[tool_name]

        result = subprocess.run(
            ["which", tool_name],
            capture_output=True,
            text=True,
        )
        available = result.returncode == 0
        self.formatters_cache[tool_name] = available
        return available

    def run_formatter(
        self,
        command: List[str],
        file_path: str,
    ) -> Tuple[bool, Optional[str]]:
        """Run a formatter command and return success status and any error message."""
        tool_name = command[0]

        if not self.check_tool_available(tool_name):
            return True, f"{tool_name} not found, skipping"

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Some tools return non-zero for warnings
                return True, f"Warning from {tool_name}: {result.stderr}"

            return True, None

        except Exception as e:
            return False, f"Failed to run {tool_name}: {e}"


class PythonFormatter(CodeFormatter):
    """Formatter for Python files."""

    def format(self, file_path: str) -> List[Tuple[str, str]]:
        """Format a Python file with multiple tools."""
        results = []
        
        # Check if this is a hooks module that uses relative imports
        is_hooks_module = ".claude/hooks/hook_handlers" in file_path

        # List of formatters to run in order
        formatters = [
            # autoflake: removes unused imports and variables
            [
                "autoflake",
                "--in-place",
                "--remove-all-unused-imports",
                "--remove-unused-variables",
                file_path,
            ],
        ]
        
        # Only add absolufy-imports if not a hooks module
        # Hooks modules use relative imports for better modularity
        if not is_hooks_module:
            formatters.append(
                # absolufy-imports: converts relative imports to absolute
                ["absolufy-imports", "--application-directories", ".", file_path]
            )
        
        # Continue with remaining formatters
        formatters.extend([
            # isort: sorts and organizes imports
            ["isort", file_path],
            # flynt: converts old string formatting to f-strings
            ["flynt", "--line-length", "88", "--transform-concats", file_path],
            # pyupgrade: upgrades syntax to newer Python versions
            ["pyupgrade", "--py38-plus", file_path],
            # docformatter: formats docstrings to PEP 257
            [
                "docformatter",
                "--in-place",
                "--wrap-summaries",
                "88",
                "--wrap-descriptions",
                "88",
                file_path,
            ],
            # add-trailing-comma: adds trailing commas for better diffs
            ["add-trailing-comma", "--py36-plus", file_path],
            # ssort: sorts class members
            ["ssort", file_path],
            # black: code formatter
            ["black", file_path],
            # ruff: linter and formatter (with fixes)
            ["ruff", "check", "--fix", file_path],
            # ruff format: additional formatting
            ["ruff", "format", file_path],
            # refurb: additional code modernization
            ["refurb", "--write", file_path],
        ])

        for formatter_cmd in formatters:
            success, message = self.run_formatter(formatter_cmd, file_path)
            if message:
                results.append((formatter_cmd[0], message))
            if not success:
                print(f"Error: {message}", file=sys.stderr)

        return results


class JavaScriptFormatter(CodeFormatter):
    """Formatter for JavaScript/TypeScript files."""

    def format(self, file_path: str) -> List[Tuple[str, str]]:
        """Format a JavaScript/TypeScript file."""
        results = []

        # Check if package.json exists (indicates Node.js project)
        if not os.path.exists("package.json"):
            return [("prettier", "No package.json found, skipping formatting")]

        # Run prettier
        success, message = self.run_formatter(
            ["npx", "prettier", "--write", file_path],
            file_path,
        )

        if not success:
            raise FormatterError(f"Prettier formatting failed: {message}")

        if message:
            results.append(("prettier", message))

        return results


def format_file(file_path: str) -> List[Tuple[str, str]]:
    """Format a file based on its extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    formatter: Optional[CodeFormatter] = None

    if ext == ".py":
        formatter = PythonFormatter()
    elif ext in [".js", ".jsx", ".ts", ".tsx"]:
        formatter = JavaScriptFormatter()

    if formatter:
        return formatter.format(file_path)
    else:
        return [("general", f"No formatter configured for {ext} files")]
