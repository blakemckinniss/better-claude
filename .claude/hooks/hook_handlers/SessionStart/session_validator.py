"""Session validation and security functions for SessionStart hook."""

import os
import sys
from typing import Any, Dict, Optional, Tuple


def validate_session_id(input_data: Dict[str, Any]) -> Optional[str]:
    """Validate session ID exists.

    Returns:
        Session ID if valid, None if invalid
    """
    session_id = input_data.get("session_id", "")
    if not session_id:
        return None
    return session_id


def validate_required_fields(
    input_data: Dict[str, Any], required_fields: list[str],
) -> bool:
    """Validate all required fields are present.

    Returns:
        True if all fields present, False otherwise
    """
    for field in required_fields:
        if field not in input_data:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Missing required field: {field}", file=sys.stderr)
            return False
    return True


def validate_and_get_project_dir(input_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate and get project directory with security checks.

    Returns:
        Tuple of (is_valid, project_dir)
    """
    # Use provided cwd or fallback to project dir
    project_dir = input_data.get("cwd", os.environ.get("CLAUDE_PROJECT_DIR", "."))

    # Security: Sanitize file paths
    blocked_paths = ["..", "/etc"]
    for blocked in blocked_paths:
        if blocked in project_dir or project_dir.startswith(blocked):
            print("Security: Path traversal blocked", file=sys.stderr)
            return False, project_dir

    return True, project_dir


def clear_session_state(project_dir: str) -> bool:
    """Clear session state if available.

    Returns:
        True if cleared successfully or not available, False on error
    """
    try:
        # Import conditionally to avoid import errors
        from UserPromptSubmit.session_state import SessionState

        session_state = SessionState(project_dir)
        session_state.clear_state()
        if os.environ.get("DEBUG_HOOKS"):
            print("Cleared session injection state", file=sys.stderr)
        return True
    except ImportError:
        # SessionState not available - this is fine
        return True
    except Exception as e:
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error clearing session state: {e}", file=sys.stderr)
        return False
