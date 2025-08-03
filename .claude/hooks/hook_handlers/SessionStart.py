#!/usr/bin/env python3
"""SessionStart hook handler - optimized for performance per CLAUDE.md principles.

This hook adheres to the HOOK_CONTRACT.md specifications.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from UserPromptSubmit.session_state import SessionState
    HAS_SESSION_STATE = True
except ImportError:
    HAS_SESSION_STATE = False
    SessionState = None  # type: ignore

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None

# Import session monitor
try:
    from session_monitor import get_session_monitor
    HAS_SESSION_MONITOR = True
except ImportError:
    HAS_SESSION_MONITOR = False
    get_session_monitor = None

# Fast command timeout per CLAUDE.md
FAST_TIMEOUT = 5  # Reduced from 10s

async def run_fast_command(
    command: List[str],
    cwd: Optional[str] = None,
    timeout: int = FAST_TIMEOUT,
) -> str:
    """Run command with minimal overhead - performance over error handling.

    Args:
        command: Command to execute as list
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Command output or empty string on error
    """
    try:

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            if os.environ.get("DEBUG_HOOKS"):
                print(
                    f"Command failed: {' '.join(command)}\n{stderr.decode()}",
                    file=sys.stderr,
                )
            return ""

        return stdout.decode().strip()

    except (FileNotFoundError, asyncio.TimeoutError, Exception) as e:
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error running {' '.join(command)}: {e}", file=sys.stderr)
        return ""


# Alias for backwards compatibility
run_command = run_fast_command


async def get_git_tracked_files(project_dir: str) -> List[str]:
    """Get git-tracked files using modern async approach."""
    output = await run_command(["git", "ls-files"], cwd=project_dir)
    if not output:
        return []

    files = [f for f in output.split("\n") if f.strip()]
    return sorted(files)


async def is_gitignored(path: str, project_dir: str) -> bool:
    """Check if a path is gitignored using git check-ignore."""
    result = await run_command(["git", "check-ignore", path], cwd=project_dir)
    # git check-ignore returns 0 (success) if the path is ignored
    # We need to check if the command executed successfully and returned output
    proc = await asyncio.create_subprocess_exec(
        "git",
        "check-ignore",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_dir,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode == 0


async def get_project_structure(project_dir: str) -> str:
    """Get project structure using git ls-files to respect .gitignore."""
    # Get all tracked files from git
    files_output = await run_command(["git", "ls-files"], cwd=project_dir)
    if not files_output:
        return ""

    # Extract unique directories from tracked files, limited to depth 3
    directories = set()
    for file_path in files_output.split("\n"):
        if not file_path.strip():
            continue

        path_parts = Path(file_path).parts
        # Add directories up to depth 3
        for depth in range(1, min(len(path_parts), 4)):
            dir_path = "/".join(path_parts[:depth])
            directories.add(dir_path)

    # Sort directories for consistent output
    sorted_dirs = sorted(directories)
    return "\n".join(sorted_dirs)


async def get_readme_content(project_dir: str) -> str:
    """Get README content (first 50 lines for performance), respecting .gitignore."""
    readme_files = ["README.md", "README.rst", "README.txt", "README"]

    for readme in readme_files:
        readme_path = Path(project_dir) / readme
        if readme_path.exists():
            # Check if README is gitignored before reading
            if not await is_gitignored(readme, project_dir):
                # Use head to limit output size
                return await run_command(["head", "-n", "50", str(readme_path)])

    return ""


async def get_recent_commits(project_dir: str) -> str:
    """Get recent git commits for context."""
    return await run_command(
        ["git", "log", "--oneline", "-n", "10", "--no-abbrev-commit"],
        cwd=project_dir,
    )


async def get_git_status(project_dir: str) -> str:
    """Get current git status."""
    return await run_command(["git", "status", "--porcelain"], cwd=project_dir)


async def get_project_metadata(project_dir: str) -> Dict[str, str]:
    """Get project metadata from various config files, respecting .gitignore."""
    metadata = {}

    # Check for common project files
    config_files = {
        "package.json": "npm",
        "pyproject.toml": "python",
        "Cargo.toml": "rust",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "requirements.txt": "python-pip",
        "setup.py": "python-setup",
        "go.mod": "go",
    }

    for filename, project_type in config_files.items():
        file_path = Path(project_dir) / filename
        if (
            file_path.exists() and file_path.stat().st_size < 10000
        ):  # Only read small files
            # Check if file is gitignored before reading
            if not await is_gitignored(filename, project_dir):
                content = await run_command(["head", "-n", "30", str(file_path)])
                if content:
                    metadata[project_type] = content

    return metadata


async def get_file_type_summary(files: List[str]) -> Dict[str, int]:
    """Analyze file types for project overview."""
    extensions: Dict[str, int] = {}
    for file in files:
        ext = Path(file).suffix.lower()
        if ext:
            extensions[ext] = extensions.get(ext, 0) + 1

    # Return top 10 file types
    return dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10])


async def gather_session_context_fast(project_dir: str) -> Dict[str, Any]:
    """Optimized context gathering using fast commands per CLAUDE.md."""
    start_time = time.time()
    
    # Use fast commands in true parallel
    tasks = [
        asyncio.create_task(run_fast_command(["scc", "--no-cocomo", "-f", "json"], cwd=project_dir)),
        asyncio.create_task(run_fast_command(["git", "status", "--porcelain", "-uno"], cwd=project_dir)),
        asyncio.create_task(run_fast_command(["git", "log", "--oneline", "-3"], cwd=project_dir)),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Parse scc output for file stats
    file_types = {}
    total_files = 0
    if results[0] and not isinstance(results[0], Exception):
        try:
            scc_data = json.loads(cast(str, results[0]))
            for lang in scc_data:
                # Map language name to common extensions
                lang_name = lang.get("Name", "").lower()
                count = lang.get("Count", 0)
                if lang_name == "python":
                    file_types[".py"] = count
                elif lang_name == "json":
                    file_types[".json"] = count
                elif lang_name == "markdown":
                    file_types[".md"] = count
                elif lang_name == "shell":
                    file_types[".sh"] = count
                elif lang_name == "javascript":
                    file_types[".js"] = count
                elif lang_name == "typescript":
                    file_types[".ts"] = count
                total_files += count
        except:
            pass
    
    return {
        "files": [],  # Skip expensive file enumeration
        "structure": "",  # Skip expensive structure
        "readme": "",  # Skip readme for speed
        "commits": results[2] if results[2] and not isinstance(results[2], Exception) else "",
        "status": results[1] if results[1] and not isinstance(results[1], Exception) else "",
        "metadata": {},  # Skip metadata parsing
        "file_types": file_types,
        "execution_time": time.time() - start_time,
        "total_files": total_files,
    }


async def gather_session_context(project_dir: str) -> Dict[str, Any]:
    """Gather all initial session context in parallel."""
    start_time = time.time()

    # Execute all context gathering tasks in parallel
    results = await asyncio.gather(
        get_git_tracked_files(project_dir),
        get_project_structure(project_dir),
        get_readme_content(project_dir),
        get_recent_commits(project_dir),
        get_git_status(project_dir),
        get_project_metadata(project_dir),
        return_exceptions=True,
    )

    # Handle any exceptions gracefully with explicit type casting
    files = cast(List[str], results[0]) if not isinstance(results[0], Exception) else []
    structure = cast(str, results[1]) if not isinstance(results[1], Exception) else ""
    readme = cast(str, results[2]) if not isinstance(results[2], Exception) else ""
    commits = cast(str, results[3]) if not isinstance(results[3], Exception) else ""
    status = cast(str, results[4]) if not isinstance(results[4], Exception) else ""
    metadata = (
        cast(Dict[str, Any], results[5])
        if not isinstance(results[5], Exception)
        else {}
    )

    # Generate file type summary
    file_types = await get_file_type_summary(files) if files else {}

    execution_time = time.time() - start_time

    return {
        "files": files,
        "structure": structure,
        "readme": readme,
        "commits": commits,
        "status": status,
        "metadata": metadata,
        "file_types": file_types,
        "execution_time": execution_time,
        "total_files": len(files),
    }


def format_minimal_output(context: Dict[str, Any]) -> str:
    """Format output per CLAUDE.md - 3-4 lines maximum."""
    # Get top file types
    top_types = []
    if context.get("file_types"):
        sorted_types = sorted(context["file_types"].items(), key=lambda x: x[1], reverse=True)[:3]
        top_types = [f"{ext}:{count}" for ext, count in sorted_types]
    
    # Format git info concisely
    git_changes = len(context.get("status", "").splitlines())
    commit_count = len(context.get("commits", "").splitlines())
    
    # 3-4 lines only per CLAUDE.md
    return f"""⚡ {context['total_files']} files | {context['execution_time']:.1f}s
📊 {', '.join(top_types) if top_types else 'No file stats'}
🔄 Git: {git_changes} changes, {commit_count} recent commits"""


def format_zen_pro_disclaimer() -> str:
    """Format static disclaimer for zen-pro consultation."""
    return """
🚨 **IMPORTANT**:

   ## All user prompts MUST be followed by immediate "zen-pro" consultation for BRD/PRD planning.
   
   Use: Task(subagent_type="zed-pro") for strategic analysis and multi-agent orchestration.
   
   ## MUST USE MODERN CLI COMMANDS (ASSUME INSTALLED)
  **Bash(** 
  rg (fast grep), fd (find fast), bat (color cat), fzf (fuzzy pick), zoxide (smart cd), lsd (pretty ls), sd (sed alt), jq (JSON CLI), yq (YAML CLI), mlr (CSV CLI), ctags (tag index), delta (diff view), tree (dir tree), tokei (code LOC), scc (LOC alt), exa (modern ls), dust (disk du), duf (disk df), procs (ps plus), hyperfine (bench), entr (watch run), xh (curl alt), dog (DNS dig), podman (containers), dive (layer view), trivy (vuln scan), tldr (examples) 
  **)**
   
   """


def format_core_tools_intro() -> str:
    """Format introduction message for core MCP tools."""
    intro = """=== Core MCP Tools Available ===

🧠 **ZEN** (mcp__zen__) - Strategic AI co-pilot for complex tasks
   • Chat: General questions & brainstorming  
   • ThinkDeep: Deep investigation & reasoning
   • Debug: Systematic debugging & root cause analysis
   • Analyze: Code analysis & architecture assessment
   • Consensus: Multi-model decision making
   
📁 **Filesystem** (mcp__filesystem__) - General file & directory operations
   • read_file: Read file contents
   • write_file: Create/overwrite files  
   • edit_file: Line-based text editing
   • list_directory: Browse directory contents
   • search_files: Find files by pattern
   
🌐 **Tavily** (mcp__tavily-remote__) - Web search & content extraction
   • tavily_search: Real-time web search
   • tavily_extract: Extract content from URLs
   • tavily_crawl: Multi-page website analysis
   
🌳 **Tree-sitter** (mcp__tree_sitter__) - Advanced code parsing & AST analysis
   • register_project: Initialize project for analysis
   • get_ast: Parse code into abstract syntax tree
   • run_query: Execute tree-sitter queries on code
   • analyze_complexity: Measure code complexity metrics

Use these tools for efficient development!"""
    return intro


def format_session_context(context: Dict[str, Any]) -> str:
    """Format gathered session context for display."""
    lines = []

    # Performance info
    lines.append(f"⚡ Context loaded in {context['execution_time']:.2f}s")
    lines.append("")

    # Project overview
    if context["readme"]:
        lines.append("📋 **Project Overview**")
        # Show first few lines of README
        readme_lines = context["readme"].split("\n")[:10]
        for line in readme_lines:
            if line.strip():
                lines.append(f"   {line}")
        if len(context["readme"].split("\n")) > 10:
            lines.append("   ...")
        lines.append("")

    # Project metadata
    if context["metadata"]:
        lines.append("🔧 **Project Type**")
        for proj_type, content in context["metadata"].items():
            lines.append(f"   • {proj_type.title()}")
        lines.append("")

    # File overview
    lines.append(f"📁 **Files Overview** ({context['total_files']} files)")
    if context["file_types"]:
        lines.append("   File types:")
        for ext, count in list(context["file_types"].items())[:5]:
            lines.append(f"   • {ext}: {count}")
    lines.append("")

    # Current status
    if context["status"]:
        lines.append("🔄 **Git Status**")
        status_lines = context["status"].split("\n")[:10]
        for line in status_lines:
            if line.strip():
                lines.append(f"   {line}")
        lines.append("")

    # Recent activity
    if context["commits"]:
        lines.append("📝 **Recent Commits**")
        commit_lines = context["commits"].split("\n")[:5]
        for line in commit_lines:
            if line.strip():
                lines.append(f"   {line}")
        lines.append("")

    # Project structure
    if context["structure"]:
        lines.append("📂 **Directory Structure**")
        structure_lines = context["structure"].split("\n")[:15]
        for line in structure_lines:
            if line.strip():
                lines.append(f"   {line}")
        lines.append("")

    # Git-tracked files (preserved as requested)
    if context["files"]:
        lines.append("📋 **Git-tracked Files**")
        # Show first 20 files to avoid overwhelming output
        for file in context["files"][:20]:
            lines.append(f"   • {file}")
        if len(context["files"]) > 20:
            lines.append(f"   ... and {len(context['files']) - 20} more files")

    return "\n".join(lines)


def handle(input_data):
    """Handle SessionStart hook event."""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(input_data, "SessionStart")

    # REQUIRED: Validate expected fields exist
    session_id = input_data.get("session_id", "")
    if not session_id:
        # Silent failure for non-applicable hooks per contract
        if hook_logger:
            hook_logger.log_hook_exit(input_data, 1, result="no_session_id")
        sys.exit(1)

    # Validate other required fields
    required_fields = ["transcript_path", "cwd", "hook_event_name", "source"]
    for field in required_fields:
        if field not in input_data:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Missing required field: {field}", file=sys.stderr)
            sys.exit(1)

    # Use provided cwd or fallback to project dir
    project_dir = input_data.get("cwd", os.environ.get("CLAUDE_PROJECT_DIR", "."))

    # REQUIRED: Sanitize file paths for security
    if ".." in project_dir or project_dir.startswith("/etc"):
        print("Security: Path traversal blocked", file=sys.stderr)
        if hook_logger:
            hook_logger.log_hook_exit(input_data, 2, result="path_traversal_blocked")
        sys.exit(2)

    # Clear session state for fresh start
    if HAS_SESSION_STATE and SessionState is not None:
        try:
            session_state = SessionState(project_dir)
            session_state.clear_state()
            if os.environ.get("DEBUG_HOOKS"):
                print("Cleared session injection state", file=sys.stderr)
        except Exception as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Error clearing session state: {e}", file=sys.stderr)

    # Gather context using async parallel execution
    try:
        # Use fast gathering if minimal mode is enabled
        if os.environ.get("CLAUDE_MINIMAL_HOOKS"):
            context = asyncio.run(gather_session_context_fast(project_dir))
        else:
            context = asyncio.run(gather_session_context(project_dir))
    except Exception as e:
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error gathering session context: {e}", file=sys.stderr)
        # Fallback to minimal context
        context = {
            "files": [],
            "structure": "",
            "readme": "",
            "commits": "",
            "status": "",
            "metadata": {},
            "file_types": {},
            "execution_time": 0.0,
            "total_files": 0,
        }

    # Format and output the context
    # Per contract: SessionStart stdout goes to context, not shown to user
    # Use minimal format if CLAUDE_MINIMAL_HOOKS env var is set (per CLAUDE.md)
    if os.environ.get("CLAUDE_MINIMAL_HOOKS"):
        output_lines = [
            "🧠 Zen • 📁 FS • 🌐 Tavily • 🌳 Tree-sitter",
            "",
            format_minimal_output(context),
            format_zen_pro_disclaimer(),
        ]
    else:
        output_lines = [
            format_core_tools_intro(),
            "",
            format_session_context(context),
            format_zen_pro_disclaimer(),
        ]

    print("\n".join(output_lines))

    # Enhanced debug output
    if os.environ.get("DEBUG_HOOKS"):
        debug_data = {
            "hook": "SessionStart",
            "session_id": session_id,
            "project_dir": project_dir,
            "execution_time": context["execution_time"],
            "total_files": context["total_files"],
            "file_types": context["file_types"],
            "has_readme": bool(context["readme"]),
            "has_commits": bool(context["commits"]),
            "has_status": bool(context["status"]),
            "metadata_types": list(context["metadata"].keys()),
        }
        print(json.dumps(debug_data, indent=2), file=sys.stderr)

    # Initialize session monitor if available
    if HAS_SESSION_MONITOR and get_session_monitor:
        try:
            session_id = input_data.get("session_id", "unknown")
            if session_id != "unknown":
                monitor = get_session_monitor(session_id)
                # Log session start metadata
                monitor._update_summary({
                    "project_dir": project_dir,
                    "total_files": context.get("total_files", 0),
                    "file_types": context.get("file_types", {}),
                    "git_status": bool(context.get("status")),
                    "recent_commits": len(context.get("commits", "").split("\n")) if context.get("commits") else 0
                })
                if os.environ.get("DEBUG_HOOKS"):
                    print(f"Session monitor initialized for {session_id[:8]}", file=sys.stderr)
        except Exception as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Error initializing session monitor: {e}", file=sys.stderr)

    # Exit with success
    if hook_logger:
        hook_logger.log_hook_exit(input_data, 0, result="success")
    sys.exit(0)


if __name__ == "__main__":
    # For direct testing
    try:
        input_data = json.load(sys.stdin)
        handle(input_data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
