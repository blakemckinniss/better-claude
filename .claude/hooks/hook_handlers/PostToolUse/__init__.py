#!/usr/bin/env python3
"""PostToolUse hook orchestrator - coordinates formatting, validation, diagnostics, and context capture."""

import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PostToolUse.config import get_config
from PostToolUse.diagnostics import (
    print_diagnostic_report,
    run_all_diagnostics,
)
from PostToolUse.formatters import format_file
from PostToolUse.validators import print_validation_report, validate_file
from PostToolUse.context_capture import handle_context_capture


def handle_file_modification(tool_name: str, tool_input: Dict[str, Any]) -> int:
    """Handle post-file modification tasks."""
    # Get configuration
    config = get_config()

    if not config.enabled:
        return 0

    # Extract file path
    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    if not file_path:
        return 0

    # Check if file should be skipped
    if config.should_skip_file(file_path):
        print(
            f"✅ Skipping checks for {file_path} (in skip directory)", file=sys.stderr
        )
        return 0

    # Get file extension
    ext = Path(file_path).suffix.lower()

    # Track if we found any critical issues
    has_critical_issues = False

    # 1. Run formatters
    if ext in config.formatters.extensions:
        print(f"\n🎨 Running formatters on {file_path}...", file=sys.stderr)
        formatter_results = format_file(file_path)

        # Report formatter warnings/errors
        for tool, message in formatter_results:
            if message:
                print(f"  {tool}: {message}", file=sys.stderr)

    # 2. Run validators (anti-pattern detection)
    if ext in [".py", ".js", ".jsx", ".ts", ".tsx"]:
        print(f"\n🔍 Checking for anti-patterns in {file_path}...", file=sys.stderr)

        try:
            with open(file_path) as f:
                content = f.read()

            validation_issues, has_critical = validate_file(file_path, content)

            # Only report if we have issues matching our severity filter
            reportable_issues = [
                issue
                for issue in validation_issues
                if issue.severity in config.validators.report_severity
            ]

            if reportable_issues:
                print_validation_report(reportable_issues, file_path)
            else:
                print("✅ No critical anti-patterns found", file=sys.stderr)

            # Check if we should block
            if has_critical and any(
                issue.severity in config.validators.block_on_severity
                for issue in validation_issues
            ):
                has_critical_issues = True

        except Exception as e:
            print(f"Warning: Failed to validate {file_path}: {e}", file=sys.stderr)

    # 3. Run diagnostics (for Python files)
    if ext == ".py" and not has_critical_issues:
        print(f"\n🔍 Running diagnostics on {file_path}...", file=sys.stderr)

        diagnostic_results, has_errors = run_all_diagnostics(file_path)

        if diagnostic_results:
            print_diagnostic_report(diagnostic_results, file_path)

            if has_errors:
                print(
                    "💡 Recommendation: Fix these issues before continuing.",
                    file=sys.stderr,
                )
                print(
                    "   Claude will be notified of these diagnostics.",
                    file=sys.stderr,
                )
                print(
                    "   📝 Note: Hooks can be temporarily disabled in",
                    file=sys.stderr,
                )
                print(
                    "      /home/devcontainers/better-claude/.claude/hooks/hook_handler.py\n",
                    file=sys.stderr,
                )
                has_critical_issues = True
        else:
            print(f"✅ No diagnostics found in {file_path}", file=sys.stderr)

    # Return appropriate exit code
    if has_critical_issues:
        return 2  # Exit code 2 notifies Claude
    else:
        return 0  # Success


def handle_hook(data: Dict[str, Any]) -> int:
    """Main entry point for PostToolUse hook handling."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    
    # Initialize result code
    exit_code = 0
    
    # 1. First, always try to capture context for the tool usage
    try:
        handle_context_capture(data)
    except Exception as e:
        print(f"Warning: Context capture failed: {e}", file=sys.stderr)
    
    # 2. Handle Claude's built-in file modification tools
    if tool_name in ["Edit", "MultiEdit", "Write"]:
        exit_code = handle_file_modification(tool_name, tool_input)
    
    # 3. Handle MCP filesystem operations
    elif tool_name.startswith("mcp__filesystem__"):
        # MCP filesystem tools that modify files
        if tool_name in [
            "mcp__filesystem__write_file",
            "mcp__filesystem__edit_file",
            "mcp__filesystem__create_directory",
            "mcp__filesystem__move_file",
        ]:
            # Extract path from MCP tool input
            file_path = tool_input.get("path", "")
            if not file_path and tool_name == "mcp__filesystem__move_file":
                # For move operations, check destination
                file_path = tool_input.get("destination", "")
            
            if file_path:
                # Reuse the same file modification handler
                exit_code = handle_file_modification(tool_name, {"file_path": file_path})

    return exit_code


# For backwards compatibility with existing PostToolUse.py
def handle(data: Dict[str, Any]) -> None:
    """Legacy entry point that calls sys.exit with the result."""
    exit_code = handle_hook(data)
    sys.exit(exit_code)
