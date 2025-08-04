"""Path utilities for hooks system to handle .claude directory detection."""

import os
from pathlib import Path
from typing import Optional


def get_true_project_root(current_dir: Optional[str] = None) -> str:
    """Get the true project root directory, detecting if we're inside .claude.

    This function properly handles cases where the current working directory
    is inside a .claude subdirectory and finds the actual project root.

    Args:
        current_dir: Optional current directory override

    Returns:
        str: Path to the actual project root (parent of .claude directory)
    """
    if current_dir is None:
        current_dir = os.getcwd()

    current_path = Path(current_dir).resolve()
    parts = current_path.parts

    # Find all .claude indices in the path
    claude_indices = [i for i, part in enumerate(parts) if part == ".claude"]

    if claude_indices:
        # Use the first (outermost) .claude directory to find project root
        first_claude_index = claude_indices[0]
        if first_claude_index > 0:
            project_root = Path(*parts[:first_claude_index])
            return str(project_root)

    # If no .claude in path, walk up to find project root
    for path in [current_path] + list(current_path.parents):
        # If we find a .claude directory, this path is the project root
        if (path / ".claude").is_dir():
            return str(path)

        # If we find a .git directory and no .claude above it, this is likely the root
        if (path / ".git").is_dir():
            return str(path)

    # Last resort: use current directory
    return str(current_path)


def get_project_root() -> str:
    """Get the true project root directory, handling cases where we might already be
    inside .claude. Legacy wrapper for get_true_project_root().

    Returns:
        str: Path to the actual project root (parent of .claude directory)
    """
    # Try environment variable first
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if (
        project_dir
        and project_dir != "$CLAUDE_PROJECT_DIR"
        and os.path.isdir(project_dir)
    ):
        # If env var points to .claude directory, get its parent
        if project_dir.endswith("/.claude") or project_dir.endswith("\\.claude"):
            return str(Path(project_dir).parent)
        # Validate it's not inside a .claude directory
        return get_true_project_root(project_dir)

    return get_true_project_root()


def get_claude_dir(project_root: Optional[str] = None) -> Path:
    """Get the .claude directory path, ensuring it's relative to the true project root.

    Args:
        project_root: Optional project root override

    Returns:
        Path: Path to .claude directory
    """
    if project_root:
        # Ensure the provided project_root is not inside .claude
        root = get_true_project_root(project_root)
    else:
        root = get_project_root()

    claude_dir = Path(root) / ".claude"

    # Sanity check: ensure we're not creating nested .claude directories
    if (
        ".claude" in str(claude_dir).split(os.sep)[:-1]
    ):  # [:-1] excludes the final .claude
        raise ValueError(f"Attempting to create nested .claude directory: {claude_dir}")

    return claude_dir


def validate_claude_path(path: Path) -> bool:
    """Validate that a path doesn't create recursive .claude directories.

    Args:
        path: Path to validate

    Returns:
        bool: True if path is safe, False if it would create nested .claude
    """
    path_str = str(path)
    parts = path_str.split(os.sep)

    # Count .claude occurrences
    claude_count = parts.count(".claude")

    # Should have at most one .claude in the path
    return claude_count <= 1
