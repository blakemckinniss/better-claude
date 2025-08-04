#!/usr/bin/env python3
"""Session-based warning tracking for PostToolUse hooks."""

import json
import time
from pathlib import Path
from typing import Dict, Set
from threading import Lock


class SessionWarningTracker:
    """Tracks warnings shown per session to avoid repetition."""

    def __init__(self, storage_path: str = None):
        """Initialize tracker with persistent storage."""
        if storage_path is None:
            # Use hook directory for storage
            hook_dir = Path(__file__).parent
            storage_path = hook_dir / "session_warnings.json"

        self.storage_path = Path(storage_path)
        self._lock = Lock()
        self._cache: Dict[str, Dict[str, float]] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load session data from persistent storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path) as f:
                    self._cache = json.load(f)
            else:
                self._cache = {}
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or can't read, start fresh
            self._cache = {}

    def _save_data(self) -> None:
        """Save session data to persistent storage."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            # If we can't save, continue without persistence
            pass

    def _cleanup_old_sessions(self, max_age_hours: int = 24) -> None:
        """Remove session data older than max_age_hours."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        sessions_to_remove = []
        for session_id, warnings in self._cache.items():
            # Check if all warnings in this session are old
            if all(timestamp < cutoff_time for timestamp in warnings.values()):
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self._cache[session_id]

    def has_shown_warning(self, session_id: str, warning_type: str) -> bool:
        """Check if warning has been shown to this session."""
        with self._lock:
            session_warnings = self._cache.get(session_id, {})
            return warning_type in session_warnings

    def mark_warning_shown(self, session_id: str, warning_type: str) -> None:
        """Mark that a warning has been shown to this session."""
        with self._lock:
            if session_id not in self._cache:
                self._cache[session_id] = {}

            self._cache[session_id][warning_type] = time.time()

            # Cleanup old sessions periodically (1 in 10 chance)
            if hash(session_id) % 10 == 0:
                self._cleanup_old_sessions()

            self._save_data()

    def should_show_warning(self, session_id: str, warning_type: str) -> bool:
        """Check if warning should be shown (and mark as shown if it should)."""
        if self.has_shown_warning(session_id, warning_type):
            return False

        self.mark_warning_shown(session_id, warning_type)
        return True

    def clear_session(self, session_id: str) -> None:
        """Clear all warnings for a specific session."""
        with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                self._save_data()

    def get_session_stats(self) -> Dict[str, int]:
        """Get statistics about tracked sessions."""
        with self._lock:
            return {
                "total_sessions": len(self._cache),
                "total_warnings": sum(len(warnings) for warnings in self._cache.values())
            }



    def should_show_warning_check_only(self, session_id: str, warning_type: str) -> bool:
        """Check if warning should be shown WITHOUT marking it as shown."""
        return not self.has_shown_warning(session_id, warning_type)

    def force_show_warning(self, session_id: str, warning_type: str) -> bool:
        """Always show warning and mark as shown (for demo/test purposes)."""
        self.mark_warning_shown(session_id, warning_type)
        return True

# Global instance for use across the hook
_tracker: SessionWarningTracker = None


def get_session_tracker() -> SessionWarningTracker:
    """Get or create the global session tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = SessionWarningTracker()
    return _tracker


def extract_session_id(data: Dict) -> str:
    """Extract session ID from hook event data."""
    # Try various fields that might contain session info
    session_id = (
        data.get("session_id") or
        data.get("conversation_id") or
        data.get("thread_id") or
        data.get("context_id") or
        "default"
    )

    # If no session ID found, try to generate one from available data
    if session_id == "default":
        # Use a combination of tool name and timestamp rounded to hour
        # This gives us roughly session-like behavior
        tool_name = data.get("tool_name", "unknown")
        hour_timestamp = int(time.time() // 3600)
        session_id = f"{tool_name}_{hour_timestamp}"

    return str(session_id)


# Warning type constants
class WarningTypes:
    """Constants for different warning types."""
    SUBAGENT_DELEGATION = "subagent_delegation"
    COMPLEX_BASH = "complex_bash"
    TODO_PATTERN = "todo_pattern"