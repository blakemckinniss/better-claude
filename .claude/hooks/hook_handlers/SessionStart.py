#!/usr/bin/env python3
"""SessionStart hook handler for project initialization."""

import json
import os
import subprocess
import sys
from typing import List

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.session_state import SessionState


def list_project_files(project_dir: str) -> List[str]:
    """List all files tracked by git in the project directory.

    Args:
        project_dir: Path to the project directory

    Returns:
        Sorted list of file paths relative to project root
    """
    try:
        # Use git ls-files to get all tracked files
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Split output into lines and filter out empty strings
        files = [f for f in result.stdout.strip().split('\n') if f]
        
        return sorted(files)
    except subprocess.CalledProcessError as e:
        # Fallback to empty list if git command fails
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error running git ls-files: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        # Git not installed
        if os.environ.get("DEBUG_HOOKS"):
            print("Git not found in PATH", file=sys.stderr)
        return []


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
   
📁 **Filesystem** (mcp__filesystem__)
   General file & directory operations
   - read_file: Read file contents
   - write_file: Create/overwrite files
   - edit_file: Line-based text editing
   - list_directory: Browse directory contents
   - search_files: Find files by pattern
   
🌐 **Tavily** (mcp__tavily-remote__)
   Web search & content extraction
   - tavily_search: Real-time web search
   - tavily_extract: Extract content from URLs
   - tavily_crawl: Multi-page website analysis
   
🌳 **Tree-sitter** (mcp__tree_sitter__)
   Advanced code parsing & AST analysis
   - register_project: Initialize project for analysis
   - get_ast: Parse code into abstract syntax tree
   - run_query: Execute tree-sitter queries on code
   - analyze_complexity: Measure code complexity metrics
   - find_similar_code: Detect duplicate patterns
   - get_symbols: Extract classes/functions/variables
   - analyze_project: Full project structure analysis

Use these tools for efficient development!
"""
    return intro.strip()


def handle(data: dict) -> None:
    """Handle SessionStart hook event.

    Args:
        data: Hook event data
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    
    # Clear session state for fresh start
    try:
        session_state = SessionState(project_dir)
        session_state.clear_state()
        if os.environ.get("DEBUG_HOOKS"):
            print("Cleared session injection state", file=sys.stderr)
    except Exception as e:
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error clearing session state: {e}", file=sys.stderr)

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
            "files": files[:10] if len(files) > 10 else files,  # Limit debug output
            "truncated": len(files) > 10
        }
        print(json.dumps(debug_data, indent=2), file=sys.stderr)