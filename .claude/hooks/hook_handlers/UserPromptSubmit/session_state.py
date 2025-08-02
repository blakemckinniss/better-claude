#!/usr/bin/env python3
"""Session state management for controlling when to inject context."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class SessionState:
    """Manages session state for injection control."""

    def __init__(self, project_dir: Optional[str] = None):
        """Initialize session state manager."""
        # Ensure we always have a valid project directory
        if project_dir:
            self.project_dir = project_dir
        else:
            self.project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Handle placeholder and validate directory
        if self.project_dir == "$CLAUDE_PROJECT_DIR" or not os.path.isdir(
            self.project_dir
        ):
            self.project_dir = os.getcwd()

        # State file location - project_dir is guaranteed to be str now
        self.state_dir = Path(self.project_dir) / ".claude" / "hooks" / "session_state"
        self.state_file = self.state_dir / "injection_state.json"

        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

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
