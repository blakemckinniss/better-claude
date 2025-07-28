#!/usr/bin/env python3
import fnmatch
import json
import os
import sys
from pathlib import Path


def load_gitignore_patterns(project_dir):
    """Load patterns from .gitignore file."""
    gitignore_path = Path(project_dir) / ".gitignore"
    patterns = []

    if gitignore_path.exists():
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)

    return patterns


def should_ignore(path, patterns, project_path):
    """Check if a path should be ignored based on gitignore patterns."""
    rel_path = path.relative_to(project_path)
    rel_path_str = str(rel_path)

    for pattern in patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith("/"):
            pattern_base = pattern.rstrip("/")
            # Check if any part of the path matches the directory pattern
            for part in rel_path.parts:
                if fnmatch.fnmatch(part, pattern_base):
                    return True

        # Check full path match
        if fnmatch.fnmatch(rel_path_str, pattern):
            return True

        # Check if any part of the path matches (for patterns like __pycache__)
        for part in rel_path.parts:
            if fnmatch.fnmatch(part, pattern):
                return True

    return False


def list_project_files(project_dir):
    """List all files in the project directory recursively, respecting .gitignore."""
    files = []
    project_path = Path(project_dir)

    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns(project_dir)

    # Always skip .git directory
    skip_dirs = {".git"}

    for path in project_path.rglob("*"):
        # Skip .git directory
        if any(part in skip_dirs for part in path.parts):
            continue

        if path.is_file():
            # Check against gitignore patterns
            if not should_ignore(path, gitignore_patterns, project_path):
                # Get relative path from project root
                rel_path = path.relative_to(project_path)
                files.append(str(rel_path))

    return sorted(files)


def handle(data):
    """Handle SessionStart hook event."""
    # Get project directory from environment
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

    # List all project files
    files = list_project_files(project_dir)

    # Format the output message
    output_lines = ["Project files:"]
    for file in files:
        output_lines.append(f"  - {file}")

    # Add summary
    output_lines.append(f"\nTotal files: {len(files)}")

    # Print to stdout for Claude to see
    print("\n".join(output_lines))

    # Optionally log the files list
    if os.environ.get("DEBUG_HOOKS"):
        debug_data = {
            "hook": "SessionStart",
            "project_dir": project_dir,
            "files_count": len(files),
            "files": files,
        }
        print(json.dumps(debug_data, indent=2), file=sys.stderr)
