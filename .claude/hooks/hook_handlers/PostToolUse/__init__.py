#!/usr/bin/env python3
"""PostToolUse hook orchestrator - coordinates formatting, validation, diagnostics, and context capture."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None

# Import session monitor
try:
    from session_monitor import get_session_monitor
    HAS_SESSION_MONITOR = True
except ImportError:
    HAS_SESSION_MONITOR = False
    get_session_monitor = None

from PostToolUse.config import get_config
from PostToolUse.context_capture import handle_context_capture
from PostToolUse.diagnostics import print_diagnostic_report, run_all_diagnostics
from PostToolUse.educational_feedback_enhanced import handle_educational_feedback
from PostToolUse.formatters import format_file
from PostToolUse.python_auto_fixer import run_auto_fixer
from PostToolUse.session_tracker import (
    WarningTypes,
    extract_session_id,
    get_session_tracker,
)
from PostToolUse.validators import print_validation_report, validate_file


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

    # 0. Run Python auto-fixer FIRST (before any other tools)
    # This fixes syntax errors that would prevent other tools from running
    if ext == ".py":
        try:
            # Import cwd from event data if available
            import json
            import os
            cwd = os.getcwd()

            # Run the auto-fixer
            run_auto_fixer(tool_name, tool_input, cwd)
        except Exception as e:
            print(f"\nWarning: Python auto-fixer failed: {e}", file=sys.stderr)

    # 1. Run formatters
    if ext in config.formatters.extensions:
        print(f"\n\n🎨 Running formatters on {file_path}...", file=sys.stderr)
        formatter_results = format_file(file_path)

        # Report formatter warnings/errors
        for tool, message in formatter_results:
            if message:
                print(f"\n  {tool}: {message}", file=sys.stderr)

    # 2. Run validators (anti-pattern detection)
    if ext in [".py", ".js", ".jsx", ".ts", ".tsx"]:
        print(f"\n\n🔍 Checking for anti-patterns in {file_path}...", file=sys.stderr)

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
            print(f"\nWarning: Failed to validate {file_path}: {e}", file=sys.stderr)

    # 3. Run diagnostics (for Python files)
    if ext == ".py" and not has_critical_issues:
        print(f"\n\n🔍 Running diagnostics on {file_path}...", file=sys.stderr)

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
                    "      /home/blake/better-claude/.claude/hooks/hook_handler.py\n",
                    file=sys.stderr,
                )
                has_critical_issues = True
        else:
            print(f"\n✅ No diagnostics found in {file_path}", file=sys.stderr)

    # Return appropriate exit code
    if has_critical_issues:
        return 2  # Exit code 2 notifies Claude
    else:
        return 0  # Success


def handle_hook(data: Dict[str, Any]) -> int:
    """Main entry point for PostToolUse hook handling."""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(data, "PostToolUse")

    try:
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
    except Exception as e:
        if hook_logger:
            hook_logger.log_error(data, e)
        sys.exit(1)

    # Initialize result code
    exit_code = 0

    # Log tool usage to session monitor
    if HAS_SESSION_MONITOR and get_session_monitor:
        try:
            session_id = data.get("session_id", "unknown")
            if session_id != "unknown":
                monitor = get_session_monitor(session_id)

                # Create tool entry
                tool_entry = {
                    "tool_name": tool_name,
                    "timestamp": datetime.now().isoformat(),
                    "success": data.get("success", True),
                    "details": ""
                }

                # Extract meaningful details based on tool type
                if tool_name in ["Read", "Glob", "Grep", "LS"]:
                    tool_entry["details"] = tool_input.get("file_path", tool_input.get("path", tool_input.get("pattern", "")))
                elif tool_name in ["Edit", "MultiEdit", "Write"]:
                    tool_entry["details"] = f"{tool_input.get('file_path', tool_input.get('path', ''))} → Modified"
                elif tool_name == "Bash":
                    tool_entry["details"] = tool_input.get("command", "")[:100]
                elif tool_name.startswith("mcp__"):
                    # MCP tools
                    tool_entry["details"] = str(tool_input)[:100]
                else:
                    tool_entry["details"] = str(tool_input)[:100]

                # Log the tool usage
                monitor.log_tools([tool_entry])
        except Exception as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"\nError logging tool to session monitor: {e}", file=sys.stderr)

    # Get session tracker and ID
    tracker = get_session_tracker()
    session_id = extract_session_id(data)

    # Check for TodoWrite first (special once-per-session behavior)
    if tool_name == "TodoWrite":
        # Get session tracker
        tracker = get_session_tracker()
        session_id = extract_session_id(data)

        # Use separate warning type for TodoWrite
        if tracker.should_show_warning(session_id, WarningTypes.TODO_PATTERN):
            print("\n⚠️  TodoWrite Usage Detected!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("📝 Task management tool used directly.", file=sys.stderr)
            print("\n✅ RECOMMENDED PATTERN:", file=sys.stderr)
            print("   1. Use Task tool to delegate to 'project-planner' for task breakdown", file=sys.stderr)
            print("   2. Use Task tool to delegate work to specialist subagents", file=sys.stderr)
            print("   3. Let subagents handle their own task tracking", file=sys.stderr)
            print("\n📚 Remember: You are the orchestrator, not the implementer!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("\n(This warning appears once per session)", file=sys.stderr)

            if hook_logger:
                hook_logger.log_decision(data, "warn", "TodoWrite usage - subagent delegation recommended")
                hook_logger.log_hook_exit(data, 2, result="warned")
            # Return 2 to show stderr to Claude (PostToolUse already ran)
            return 2
    # TodoWrite check already handled above, skip duplicate

    # 1. First, always try to capture context for the tool usage
    try:
        handle_context_capture(data)
    except Exception as e:
        print(f"\nWarning: Context capture failed: {e}", file=sys.stderr)
    
    # 2. Provide enhanced educational feedback using shared intelligence
    try:
        handle_educational_feedback(data)
    except Exception as e:
        print(f"\nWarning: Educational feedback failed: {e}", file=sys.stderr)

    # 3. Main tool handling logic with error handling
    try:
        # Handle Claude's built-in file modification tools
        # NOTE: Only process file modifications if delegation enforcement didn't already block
        if tool_name in ["Edit", "MultiEdit", "Write"] and exit_code == 0:
            exit_code = handle_file_modification(tool_name, tool_input)

        # Handle MCP filesystem operations
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

        if hook_logger:
            result = "blocked" if exit_code != 0 else "allowed"
            hook_logger.log_hook_exit(data, exit_code, result=result)
        return exit_code

    except Exception as e:
        # Log the error
        if hook_logger:
            hook_logger.log_error(data, e)
        # Don't fail operations due to hook errors
        print(f"\nHook error (operation allowed): {str(e)}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_hook_exit(data, 0, result="allowed_with_error")
        return 0  # Allow operation on error


# For backwards compatibility with existing PostToolUse.py
def handle(data: Dict[str, Any]) -> None:
    """Legacy entry point that calls sys.exit with the result."""
    exit_code = handle_hook(data)
    sys.exit(exit_code)
