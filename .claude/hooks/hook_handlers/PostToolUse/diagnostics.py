#!/usr/bin/env python3
"""Code quality diagnostics (mypy, pylint, ruff)."""

import ast
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class DiagnosticResult:
    """Represents a diagnostic issue found."""

    tool: str
    severity: str  # ERROR, WARNING, INFO
    message: str
    file_path: str
    line: Optional[int] = None
    column: Optional[int] = None
    code: Optional[str] = None


class DiagnosticRunner(ABC):
    """Base class for diagnostic runners."""

    def __init__(self):
        self.tool_cache = {}

    def check_tool_available(self, tool_name: str) -> bool:
        """Check if a diagnostic tool is available."""
        if tool_name in self.tool_cache:
            return self.tool_cache[tool_name]

        result = subprocess.run(
            ["which", tool_name],
            capture_output=True,
            text=True,
        )
        available = result.returncode == 0
        self.tool_cache[tool_name] = available
        return available

    def run_tool(self, command: List[str]) -> Tuple[int, str, str]:
        """Run a diagnostic tool and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    @abstractmethod
    def run(self, file_path: str) -> List[DiagnosticResult]:
        """Run diagnostic checks on a file and return results."""
        ...


class MyPyDiagnostics(DiagnosticRunner):
    """Run mypy type checking."""

    def run(self, file_path: str) -> List[DiagnosticResult]:
        """Run mypy on a file."""
        if not self.check_tool_available("mypy"):
            return []

        command = [
            "mypy",
            "--no-error-summary",
            "--show-error-codes",
            "--show-column-numbers",
            file_path,
        ]

        exit_code, stdout, stderr = self.run_tool(command)

        if exit_code == 0 or not stdout.strip():
            return []

        results = []
        for line in stdout.strip().split("\n"):
            # Parse mypy output: file.py:line:col: error: message [error-code]
            match = re.match(
                r"^(.+?):(\d+):(\d+):\s*(\w+):\s*(.+?)(?:\s*\[(.+?)\])?$",
                line,
            )
            if match:
                file_path, line_no, col_no, severity, message, code = match.groups()
                results.append(
                    DiagnosticResult(
                        tool="MyPy",
                        severity=severity.upper(),
                        message=message,
                        file_path=file_path,
                        line=int(line_no),
                        column=int(col_no),
                        code=code,
                    ),
                )

        return results


class PyLintDiagnostics(DiagnosticRunner):
    """Run pylint for code quality checks."""

    def run(self, file_path: str) -> List[DiagnosticResult]:
        """Run pylint on a file."""
        if not self.check_tool_available("pylint"):
            return []

        command = [
            "pylint",
            "--errors-only",
            "--output-format=parseable",
            file_path,
        ]

        exit_code, stdout, stderr = self.run_tool(command)

        if exit_code == 0 or not stdout.strip():
            return []

        results = []
        for line in stdout.strip().split("\n"):
            # Parse pylint output: file.py:line: [code] message
            match = re.match(
                r"^(.+?):(\d+):\s*\[(.+?)\]\s*(.+)$",
                line,
            )
            if match:
                file_path, line_no, code, message = match.groups()
                results.append(
                    DiagnosticResult(
                        tool="PyLint",
                        severity="ERROR",
                        message=message,
                        file_path=file_path,
                        line=int(line_no),
                        code=code,
                    ),
                )

        return results


class RuffDiagnostics(DiagnosticRunner):
    """Run ruff for fast Python linting."""

    def run(self, file_path: str) -> List[DiagnosticResult]:
        """Run ruff on a file."""
        if not self.check_tool_available("ruff"):
            return []

        command = [
            "ruff",
            "check",
            "--output-format=text",
            file_path,
        ]

        exit_code, stdout, stderr = self.run_tool(command)

        if exit_code == 0 or not stdout.strip():
            return []

        results = []
        for line in stdout.strip().split("\n"):
            # Skip fixable issues since we already ran ruff --fix
            if "[*]" in line:
                continue

            # Parse ruff output: file.py:line:col: CODE message
            match = re.match(
                r"^(.+?):(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)$",
                line,
            )
            if match:
                file_path, line_no, col_no, code, message = match.groups()
                results.append(
                    DiagnosticResult(
                        tool="Ruff",
                        severity="ERROR",
                        message=message,
                        file_path=file_path,
                        line=int(line_no),
                        column=int(col_no),
                        code=code,
                    ),
                )

        return results


class AsyncChecker:
    """Check for async/await issues."""

    def check(self, content: str, file_path: str) -> List[DiagnosticResult]:
        """Check for asyncio issues in Python code."""
        results = []

        try:
            tree = ast.parse(content)

            class AsyncVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.issues = []

                def visit_Call(self, node):
                    # Check for common asyncio mistakes
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in [
                            "create_task",
                            "ensure_future",
                            "gather",
                            "wait",
                        ]:
                            # These functions expect coroutines or futures
                            for arg in node.args:
                                if isinstance(arg, ast.Call):
                                    # Check if it's not an async call
                                    func_name = None
                                    if isinstance(arg.func, ast.Name):
                                        func_name = arg.func.id
                                    elif isinstance(arg.func, ast.Attribute):
                                        func_name = arg.func.attr

                                    if func_name:
                                        self.issues.append(
                                            DiagnosticResult(
                                                tool="AsyncChecker",
                                                severity="WARNING",
                                                message=f"Possible issue - {node.func.attr}() expects a coroutine, but {func_name}() might not be async",
                                                file_path=file_path,
                                                line=arg.lineno,
                                            ),
                                        )
                    self.generic_visit(node)

            visitor = AsyncVisitor()
            visitor.visit(tree)
            results.extend(visitor.issues)

        except SyntaxError as e:
            results.append(
                DiagnosticResult(
                    tool="SyntaxChecker",
                    severity="ERROR",
                    message=f"Syntax Error: {e.msg}",
                    file_path=file_path,
                    line=e.lineno,
                ),
            )

        return results


class UnboundVariableChecker:
    """Check for potentially unbound variables."""

    def check(self, content: str, file_path: str) -> List[DiagnosticResult]:
        """Check for unbound variable patterns."""
        results = []
        lines = content.split("\n")

        # Look for common patterns that indicate possibly unbound variables
        for i, line in enumerate(lines, 1):
            # Check for variables used in except blocks that might not be defined
            if "except" in line and "as" in line:
                # Next few lines might reference the exception variable outside the block
                pass

            # Check for variables that might not be initialized in all paths
            if re.search(r"if .* in locals\(\)", line):
                var_match = re.search(r'"(\w+)" (?:not )?in locals\(\)', line)
                if var_match:
                    var_name = var_match.group(1)
                    results.append(
                        DiagnosticResult(
                            tool="UnboundChecker",
                            severity="WARNING",
                            message=f"Variable '{var_name}' might not be defined in all code paths",
                            file_path=file_path,
                            line=i,
                        ),
                    )

        return results


def run_all_diagnostics(file_path: str) -> Tuple[List[DiagnosticResult], bool]:
    """Run all diagnostics on a file and return results and whether there are errors."""
    results = []

    # Python-specific diagnostics
    if file_path.endswith(".py"):
        # Read file content for AST-based checks
        try:
            with open(file_path) as f:
                content = f.read()
        except Exception as e:
            results.append(
                DiagnosticResult(
                    tool="FileReader",
                    severity="ERROR",
                    message=f"Failed to read file: {e}",
                    file_path=file_path,
                ),
            )
            return results, True

        # Run each diagnostic tool
        diagnostics: List[DiagnosticRunner] = [
            MyPyDiagnostics(),
            PyLintDiagnostics(),
            RuffDiagnostics(),
        ]

        for diagnostic in diagnostics:
            results.extend(diagnostic.run(file_path))

        # Run AST-based checkers
        checkers = [
            AsyncChecker(),
            UnboundVariableChecker(),
        ]

        for checker in checkers:
            if hasattr(checker, "check"):
                results.extend(checker.check(content, file_path))

    # Check if there are any errors
    has_errors = any(r.severity == "ERROR" for r in results)

    return results, has_errors


def print_diagnostic_report(results: List[DiagnosticResult], file_path: str) -> None:
    """Print a diagnostic report to stderr."""
    if not results:
        print(f"✅ No diagnostics found in {file_path}", file=sys.stderr)
        return

    print("\n❌ Diagnostics found in modified file:", file=sys.stderr)
    print(f"   File: {file_path}\n", file=sys.stderr)

    # Group by tool
    by_tool: Dict[str, List[DiagnosticResult]] = {}
    for result in results:
        if result.tool not in by_tool:
            by_tool[result.tool] = []
        by_tool[result.tool].append(result)

    for tool, tool_results in by_tool.items():
        # Only show errors, not warnings
        errors = [r for r in tool_results if r.severity == "ERROR"]
        if errors:
            print(f"📋 {tool} Errors:", file=sys.stderr)
            print("─" * 50, file=sys.stderr)

            for result in errors:
                location = f"{result.file_path}"
                if result.line:
                    location += f":{result.line}"
                    if result.column:
                        location += f":{result.column}"

                print(
                    f"{location}: {result.severity.lower()}: {result.message}",
                    file=sys.stderr,
                )
                if result.code:
                    print(f"  [{result.code}]", file=sys.stderr)

            print(f"{'─' * 50}\n", file=sys.stderr)
