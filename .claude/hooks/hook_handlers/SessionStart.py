#!/usr/bin/env python3
"""SessionStart hook handler for project initialization."""

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import List, Set


def load_gitignore_patterns(project_dir: str) -> List[str]:
    """Load patterns from .gitignore file.

    Args:
        project_dir: Path to the project directory

    Returns:
        List of gitignore patterns
    """
    gitignore_path = Path(project_dir) / ".gitignore"
    patterns = []

    if gitignore_path.exists():
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)

    return patterns


def should_ignore(path: Path, patterns: List[str], project_path: Path) -> bool:
    """Check if a path should be ignored based on gitignore patterns.

    Args:
        path: Path to check
        patterns: List of gitignore patterns
        project_path: Project root path

    Returns:
        True if the path should be ignored
    """
    rel_path = path.relative_to(project_path)
    rel_path_str = str(rel_path)

    for pattern in patterns:
        if pattern.endswith("/"):
            pattern_base = pattern.rstrip("/")
            for part in rel_path.parts:
                if fnmatch.fnmatch(part, pattern_base):
                    return True

        if fnmatch.fnmatch(rel_path_str, pattern):
            return True

        for part in rel_path.parts:
            if fnmatch.fnmatch(part, pattern):
                return True

    return False


def list_project_files(project_dir: str) -> List[str]:
    """List all files in the project directory recursively, respecting .gitignore.

    Args:
        project_dir: Path to the project directory

    Returns:
        Sorted list of file paths relative to project root
    """
    files = []
    project_path = Path(project_dir)
    gitignore_patterns = load_gitignore_patterns(project_dir)
    skip_dirs: Set[str] = {".git"}

    for path in project_path.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue

        if path.is_file():
            if not should_ignore(path, gitignore_patterns, project_path):
                rel_path = path.relative_to(project_path)
                files.append(str(rel_path))

    return sorted(files)


def format_core_tools_intro() -> str:
    """Format introduction message for core MCP tools.

    Returns:
        Formatted introduction message
    """
    intro = """
=== Core MCP Tools Available ===

🧠 **ZEN** (mcp__zen__)
   Strategic AI co-pilot for complex tasks
   - Chat: General questions & brainstorming
   - ThinkDeep: Deep investigation & reasoning
   - Debug: Systematic debugging & root cause analysis
   - Analyze: Code analysis & architecture assessment
   - Consensus: Multi-model decision making
   
🔍 **Serena** (mcp__serena__)
   Python code navigation & manipulation
   - find_symbol: Navigate to functions/classes
   - replace_symbol_body: Edit code precisely
   - get_references: Find all usages
   - rename_symbol: Refactor across files
   
🌐 **Tavily** (mcp__tavily-remote__)
   Web search & content extraction
   - tavily_search: Real-time web search
   - tavily_extract: Extract content from URLs
   - tavily_crawl: Multi-page website analysis

Use these tools for efficient development!
"""
    return intro.strip()


def handle(data: dict) -> None:
    """Handle SessionStart hook event.

    Args:
        data: Hook event data
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    files = list_project_files(project_dir)

    output_lines = []

    # Add core tools introduction
    output_lines.append(format_core_tools_intro())
    output_lines.append("")

    # Add project files listing
    output_lines.append("=== Project Files ===")
    for file in files:
        output_lines.append(f"  - {file}")

    output_lines.append(f"\nTotal files: {len(files)}")

    print("\n".join(output_lines))

    if os.environ.get("DEBUG_HOOKS"):
        debug_data = {
            "hook": "SessionStart",
            "project_dir": project_dir,
            "files_count": len(files),
            "files": files,
        }
        print(json.dumps(debug_data, indent=2), file=sys.stderr)
