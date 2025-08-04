#!/usr/bin/env python3
"""SessionStart hook handler - refactored for low complexity per CLAUDE.md principles.

This hook adheres to the HOOK_CONTRACT.md specifications.
Complexity reduced from 94 to <50 through module extraction and function decomposition.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SessionStart.config import Config, EnvironmentVars, OutputMode
from SessionStart.context_gatherer import (
    gather_session_context,
    get_fallback_context,
)
from SessionStart.output_formatters import (
    format_core_tools_intro,
    format_minimal_output,
    format_session_context,
    format_zen_pro_disclaimer,
)
from SessionStart.session_validator import (
    clear_session_state,
    validate_and_get_project_dir,
    validate_required_fields,
    validate_session_id,
)

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


def log_hook_entry(input_data: Dict[str, Any]) -> None:
    """Log hook entry if logger available."""
    if hook_logger:
        hook_logger.log_hook_entry(input_data, "SessionStart")


def log_hook_exit(input_data: Dict[str, Any], exit_code: int, result: str) -> None:
    """Log hook exit if logger available."""
    if hook_logger:
        hook_logger.log_hook_exit(input_data, exit_code, result=result)


def validate_input(input_data: Dict[str, Any]) -> tuple[bool, str, str]:
    """Validate all input data and return validation result.

    Returns:
        Tuple of (is_valid, session_id, project_dir)
    """
    # Validate session ID
    session_id = validate_session_id(input_data)
    if not session_id:
        return False, "", ""

    # Validate required fields
    if not validate_required_fields(input_data, Config.REQUIRED_FIELDS):
        return False, session_id, ""

    # Validate and get project directory
    is_valid, project_dir = validate_and_get_project_dir(input_data)
    if not is_valid:
        return False, session_id, project_dir

    return True, session_id, project_dir


def prepare_session(project_dir: str) -> bool:
    """Prepare session by clearing state.

    Returns:
        True if successful, False otherwise
    """
    return clear_session_state(project_dir)


def gather_context(project_dir: str) -> Dict[str, Any]:
    """Gather session context using appropriate strategy.

    Returns:
        Context dictionary
    """
    try:
        # Determine if fast mode should be used
        fast_mode = bool(os.environ.get(EnvironmentVars.CLAUDE_MINIMAL_HOOKS))
        return asyncio.run(gather_session_context(project_dir, fast_mode=fast_mode))
    except Exception as e:
        if os.environ.get(EnvironmentVars.DEBUG_HOOKS):
            print(f"Error gathering session context: {e}", file=sys.stderr)
        return get_fallback_context()


def determine_output_mode() -> OutputMode:
    """Determine output mode from environment."""
    if os.environ.get(EnvironmentVars.CLAUDE_MINIMAL_HOOKS):
        return OutputMode.MINIMAL
    return OutputMode.FULL


def format_output(context: Dict[str, Any], mode: OutputMode) -> str:
    """Format output based on mode.

    Returns:
        Formatted output string
    """
    if mode == OutputMode.MINIMAL:
        output_lines = [
            "🧠 Zen • 📁 FS • 🌐 Tavily • 🌳 Tree-sitter",
            "",
            format_minimal_output(context),
            format_zen_pro_disclaimer(),
        ]
    else:
        output_lines = [
            format_core_tools_intro(),
            "",
            format_session_context(context),
            format_zen_pro_disclaimer(),
        ]

    return "\n".join(output_lines)


def output_debug_info(input_data: Dict[str, Any], context: Dict[str, Any]) -> None:
    """Output debug information if enabled."""
    if not os.environ.get(EnvironmentVars.DEBUG_HOOKS):
        return

    debug_data = {
        "hook": "SessionStart",
        "session_id": input_data.get("session_id", ""),
        "project_dir": input_data.get("cwd", ""),
        "execution_time": context["execution_time"],
        "total_files": context["total_files"],
        "file_types": context["file_types"],
        "has_readme": bool(context["readme"]),
        "has_commits": bool(context["commits"]),
        "has_status": bool(context["status"]),
        "metadata_types": list(context["metadata"].keys()),
    }
    print(json.dumps(debug_data, indent=2), file=sys.stderr)


def initialize_session_monitor(
    input_data: Dict[str, Any], context: Dict[str, Any],
) -> None:
    """Initialize session monitor if available."""
    if not HAS_SESSION_MONITOR or not get_session_monitor:
        return

    try:
        session_id = input_data.get("session_id", "unknown")
        if session_id == "unknown":
            return

        monitor = get_session_monitor(session_id)
        project_dir = input_data.get("cwd", "")

        # Log session start metadata
        monitor._update_summary(
            {
                "project_dir": project_dir,
                "total_files": context.get("total_files", 0),
                "file_types": context.get("file_types", {}),
                "git_status": bool(context.get("status")),
                "recent_commits": (
                    len(context.get("commits", "").split("\n"))
                    if context.get("commits")
                    else 0
                ),
            },
        )

        if os.environ.get(EnvironmentVars.DEBUG_HOOKS):
            print(f"Session monitor initialized for {session_id[:8]}", file=sys.stderr)
    except Exception as e:
        if os.environ.get(EnvironmentVars.DEBUG_HOOKS):
            print(f"Error initializing session monitor: {e}", file=sys.stderr)


def handle(input_data: Dict[str, Any]) -> None:
    """Handle SessionStart hook event - simplified main function."""
    # Step 1: Log entry
    log_hook_entry(input_data)

    # Step 2: Validate input
    is_valid, session_id, project_dir = validate_input(input_data)
    if not is_valid:
        if not session_id:
            log_hook_exit(input_data, 1, result="no_session_id")
            sys.exit(1)
        else:
            log_hook_exit(input_data, 2, result="path_traversal_blocked")
            sys.exit(2)

    # Step 3: Prepare session
    prepare_session(project_dir)

    # Step 4: Gather context
    context = gather_context(project_dir)

    # Step 5: Format and output
    output_mode = determine_output_mode()
    output = format_output(context, output_mode)
    print(output)

    # Step 6: Debug output
    output_debug_info(input_data, context)

    # Step 7: Initialize monitoring
    initialize_session_monitor(input_data, context)

    # Step 8: Exit successfully
    log_hook_exit(input_data, 0, result="success")
    sys.exit(0)


if __name__ == "__main__":
    # For direct testing
    try:
        input_data = json.load(sys.stdin)
        handle(input_data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
