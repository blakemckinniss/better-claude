#!/usr/bin/env python3
"""Enhanced logging with structured data for PreToolUse operations."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .git_validator import GitAwareValidator


class OperationLogger:
    """Enhanced logging with structured data."""

    def __init__(self):
        self.log_dir = Path("~/.claude/hooks/operation_logs").expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    def _extract_operation_type(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> str:
        """Extract operation type from tool and input."""
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if "rm" in command or "unlink" in command:
                return "delete"
            elif "mv" in command:
                return "move"
            elif "cp" in command:
                return "copy"
            elif ">" in command:
                return "write"
            return "execute"
        return tool_name.lower()

    def _extract_target(self, tool_input: Dict[str, Any]) -> str:
        """Extract target file/path from tool input."""
        # Try different common keys
        for key in ["file_path", "path", "filename", "target"]:
            if key in tool_input:
                return tool_input[key]

        # For bash commands, try to extract from command
        if "command" in tool_input:
            return tool_input["command"]

        return ""

    def log_operation(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: str,
        warnings: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Log operation with structured data."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "tool": tool_name,
            "operation": self._extract_operation_type(tool_name, tool_input),
            "target": self._extract_target(tool_input),
            "result": result,
            "warnings": warnings or [],
            "git_status": None,
        }

        # Add git status for file operations
        if target := log_entry.get("target"):
            if isinstance(target, str) and os.path.exists(target):
                log_entry["git_status"] = GitAwareValidator.get_git_status(target)

        # Write to daily log file
        log_file = (
            self.log_dir / f"operations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        try:
            with open(log_file, "a") as f:
                f.write(f"{json.dumps(log_entry)}\n")
        except Exception as e:
            # Don't fail the operation if logging fails
            print(f"Warning: Failed to log operation: {e}")

    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent operations from logs."""
        operations = []

        # Get today's log file
        log_file = (
            self.log_dir / f"operations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        if log_file.exists():
            try:
                with open(log_file) as f:
                    lines = f.readlines()
                    # Get last N lines
                    for line in lines[-limit:]:
                        try:
                            operations.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass

        return operations

    def get_operations_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all operations that affected a specific file."""
        operations = []
        normalized_path = os.path.normpath(file_path)

        # Check all log files
        for log_file in sorted(self.log_dir.glob("operations_*.jsonl")):
            try:
                with open(log_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            target = entry.get("target", "")
                            if target and os.path.normpath(target) == normalized_path:
                                operations.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue

        return operations

    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Clean up log files older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

        for log_file in self.log_dir.glob("operations_*.jsonl"):
            try:
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
            except Exception:
                # Don't fail if we can't delete old logs
                pass
