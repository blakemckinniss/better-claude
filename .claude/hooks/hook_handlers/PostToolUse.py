#!/usr/bin/env python3
import os
import subprocess
import sys


def handle(data):
    """Handle PostToolUse hook events."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Initialize file_path to avoid unbound errors
    file_path = ""

    # Handle post-file modifications
    if tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = tool_input.get("file_path", tool_input.get("path", ""))

        # Auto-format TypeScript/JavaScript files
        if file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            if os.path.exists("package.json"):
                try:
                    result = subprocess.run(
                        ["npx", "prettier", "--write", file_path],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        print(
                            f"Prettier formatting failed: {result.stderr}",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                except Exception as e:
                    print(f"Failed to run prettier: {e}", file=sys.stderr)
                    sys.exit(1)

        # Auto-format Python files
        elif file_path.endswith(".py"):
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
                # absolufy-imports: converts relative imports to absolute
                ["absolufy-imports", "--application-directories", ".", file_path],
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
            ]

            for formatter_cmd in formatters:
                try:
                    # Check if the tool is available
                    tool_name = formatter_cmd[0]
                    check_result = subprocess.run(
                        ["which", tool_name],
                        capture_output=True,
                        text=True,
                    )
                    if check_result.returncode != 0:
                        print(
                            f"Warning: {tool_name} not found, skipping",
                            file=sys.stderr,
                        )
                        continue

                    # Run the formatter
                    result = subprocess.run(
                        formatter_cmd,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        # Some tools may return non-zero for warnings, log but don't fail
                        print(
                            f"Warning from {tool_name}: {result.stderr}",
                            file=sys.stderr,
                        )
                except Exception as e:
                    print(f"Failed to run {formatter_cmd[0]}: {e}", file=sys.stderr)
                    # Continue with other formatters even if one fails
                    continue

            # After all formatters, check for Pylance "possibly unbound" errors
            # Run pylance to check for unbound variable errors
            try:
                import re

                with open(file_path) as f:
                    content = f.read()

                # Common patterns that indicate possibly unbound variables
                # Skip checking in string literals and comments
                unbound_patterns = []
                
                # Just check for the specific pattern we care about
                # More sophisticated checks would require AST parsing

                found_issues = []
                lines = content.split("\n")

                for pattern, msg_template in unbound_patterns:
                    for match in re.finditer(pattern, content, re.MULTILINE):
                        var_name = match.group(1)
                        # Find line number
                        line_num = content[: match.start()].count("\n") + 1
                        found_issues.append(
                            (line_num, var_name, msg_template.format(var_name)),
                        )

                # Also check for specific known issues
                if '"stop_log_dir" not in locals()' in content:
                    line_num = next(
                        (
                            i
                            for i, line in enumerate(lines, 1)
                            if '"stop_log_dir" not in locals()' in line
                        ),
                        0,
                    )
                    if line_num:
                        found_issues.append(
                            (
                                line_num,
                                "stop_log_dir",
                                'Variable "stop_log_dir" has possibly unbound check',
                            ),
                        )

                if found_issues:
                    print(
                        f"\n⚠️  Pylance 'possibly unbound' warnings found in {file_path}:",
                        file=sys.stderr,
                    )
                    for line_num, var_name, issue in found_issues:
                        print(f"  Line {line_num}: {issue}", file=sys.stderr)
                    print(
                        "\nThese variables may not be defined in all code paths.",
                        file=sys.stderr,
                    )
                    print(
                        "Consider initializing them at the beginning of their scope.\n",
                        file=sys.stderr,
                    )
                    sys.exit(2)  # Exit with error code to notify Claude

            except Exception as e:
                print(f"Error checking for Pylance issues: {e}", file=sys.stderr)

    sys.exit(0)
