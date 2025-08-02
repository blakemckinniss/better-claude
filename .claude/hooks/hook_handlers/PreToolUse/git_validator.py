#!/usr/bin/env python3
"""Git-aware validation for safer file operations."""

import os
import subprocess
from typing import Dict, Literal, Optional

GitStatus = Literal[
    "modified", "added", "deleted", "untracked", "added-modified", "clean", "unknown"
]


class GitAwareValidator:
    """Git-aware validation for safer operations."""

    @staticmethod
    def get_git_status(file_path: str) -> GitStatus:
        """Get git status for a file."""
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            result = subprocess.run(
                ["git", "status", "--porcelain", file_path],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0 and result.stdout:
                status = result.stdout.strip()[:2]
                status_map: Dict[str, GitStatus] = {
                    "M ": "modified",
                    " M": "modified",
                    "MM": "modified",
                    "A ": "added",
                    "AM": "added-modified",
                    "D ": "deleted",
                    "??": "untracked",
                }
                return status_map.get(status.strip(), "unknown")
            return "clean"
        except Exception:
            return "unknown"

    @staticmethod
    def check_uncommitted_changes(file_path: str) -> bool:
        """Check if file has uncommitted changes."""
        status = GitAwareValidator.get_git_status(file_path)
        return status in ["modified", "added-modified"]

    @staticmethod
    def is_ignored_file(file_path: str) -> bool:
        """Check if file is git-ignored."""
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            result = subprocess.run(
                ["git", "check-ignore", file_path],
                cwd=project_dir,
                capture_output=True,
                timeout=1,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_git_root() -> Optional[str]:
        """Get the root directory of the git repository."""
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=1,
            )

            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def is_in_git_repo(file_path: str) -> bool:
        """Check if a file is within a git repository."""
        git_root = GitAwareValidator.get_git_root()
        if not git_root:
            return False

        try:
            # Normalize paths for comparison
            file_abs = os.path.abspath(file_path)
            git_abs = os.path.abspath(git_root)
            return file_abs.startswith(git_abs)
        except Exception:
            return False
