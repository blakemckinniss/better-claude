#!/usr/bin/env python3
"""Session state management for controlling when to inject context."""

import json
import sys
from typing import Any, Dict, Optional

from .path_utils import get_claude_dir, get_project_root


class SessionState:
    """Manages session state for injection control."""

    def __init__(self, project_dir: Optional[str] = None):
        """Initialize session state manager."""
        # Get the true project root
        if project_dir:
            # If project_dir is provided, validate it's not already inside .claude
            if ".claude" in str(project_dir):
                # Extract the actual project root
                self.project_dir = get_project_root()
            else:
                self.project_dir = project_dir
        else:
            self.project_dir = get_project_root()

        # State file location with validation
        try:
            claude_dir = get_claude_dir(self.project_dir)
            self.state_dir = claude_dir / "hooks" / "session_state"
            self.state_file = self.state_dir / "injection_state.json"

            # Ensure directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except ValueError as e:
            raise ValueError(f"Failed to initialize session state paths: {e}") from e

    def _default_state(self) -> Dict[str, Any]:
        """Get default state."""
        return {
            "inject_next": True,  # Whether to inject on next prompt
            "messages_since_injection": 0,  # Count of messages since last injection
            "last_transcript_path": None,  # Track transcript changes
            "reason": "initial",  # Why injection is needed
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current session state."""
        if not self.state_file.exists():
            return self._default_state()

        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._default_state()

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save session state."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            print(f"Error saving session state: {e}", file=sys.stderr)

    def should_inject(self, transcript_path: Optional[str] = None) -> bool:
        """Check if we should inject context on this prompt."""
        state = self.get_state()

        # Check if transcript changed (new session)
        if transcript_path and state["last_transcript_path"] != transcript_path:
            state["inject_next"] = True
            state["reason"] = "new_transcript"
            state["last_transcript_path"] = transcript_path
            state["messages_since_injection"] = 0
            self.save_state(state)
            return True

        # Check if forced injection is set
        if state["inject_next"]:
            return True

        # Check if we've hit the message limit (>= 5 messages since last injection)
        # This will trigger on the 6th message after injection
        if state["messages_since_injection"] >= 5:
            state["inject_next"] = True
            state["reason"] = "message_limit"
            self.save_state(state)
            return True

        return False

    def mark_injected(self, transcript_path: Optional[str] = None) -> None:
        """Mark that injection has occurred."""
        state = self.get_state()
        state["inject_next"] = False
        state["messages_since_injection"] = 0
        state["last_transcript_path"] = transcript_path
        state["reason"] = "injected"
        self.save_state(state)

    def increment_message_count(self) -> None:
        """Increment the message count."""
        state = self.get_state()
        state["messages_since_injection"] += 1
        self.save_state(state)

    def request_next_injection(self, reason: str) -> None:
        """Request injection on next prompt."""
        state = self.get_state()
        state["inject_next"] = True
        state["reason"] = reason
        self.save_state(state)

    def clear_state(self) -> None:
        """Clear the session state."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except OSError:
                pass
