"""Output formatting functions for SessionStart hook."""

from typing import Any, Dict

from SessionStart.config import Config


def format_minimal_output(context: Dict[str, Any]) -> str:
    """Format minimal output per CLAUDE.md - 3-4 lines maximum."""
    # Get top file types
    top_types = []
    if context.get("file_types"):
        sorted_types = sorted(
            context["file_types"].items(), key=lambda x: x[1], reverse=True,
        )[:3]
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

   ## ONBOARDING ZEN-PRO
   Ultrathink: all user prompts MUST be followed by immediate "zen-pro" consultation for BRD/PRD planning.
   Proactively Must Use: Task(subagent_type="zen-pro") with websearch enabled for strategic analysis and multi-agent orchestration.

   ## SIGNED CLI_CONTRACT (ASSUME INSTALLED)
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


def _format_readme_section(context: Dict[str, Any]) -> str:
    """Format README section."""
    if not context.get("readme"):
        return ""

    lines = ["📋 **Project Overview**"]
    readme_lines = context["readme"].split("\n")[:10]
    for line in readme_lines:
        if line.strip():
            lines.append(f"   {line}")
    if len(context["readme"].split("\n")) > 10:
        lines.append("   ...")
    lines.append("")
    return "\n".join(lines)


def _format_metadata_section(context: Dict[str, Any]) -> str:
    """Format project metadata section."""
    if not context.get("metadata"):
        return ""

    lines = ["🔧 **Project Type**"]
    for proj_type in context["metadata"]:
        lines.append(f"   • {proj_type.title()}")
    lines.append("")
    return "\n".join(lines)


def _format_file_overview_section(context: Dict[str, Any]) -> str:
    """Format file overview section."""
    lines = [f"📁 **Files Overview** ({context['total_files']} files)"]
    if context.get("file_types"):
        lines.append("   File types:")
        for ext, count in list(context["file_types"].items())[
            : Config.MAX_FILE_TYPES_SHOWN
        ]:
            lines.append(f"   • {ext}: {count}")
    lines.append("")
    return "\n".join(lines)


def _format_git_status_section(context: Dict[str, Any]) -> str:
    """Format git status section."""
    if not context.get("status"):
        return ""

    lines = ["🔄 **Git Status**"]
    status_lines = context["status"].split("\n")[: Config.MAX_STATUS_LINES]
    for line in status_lines:
        if line.strip():
            lines.append(f"   {line}")
    lines.append("")
    return "\n".join(lines)


def _format_commits_section(context: Dict[str, Any]) -> str:
    """Format recent commits section."""
    if not context.get("commits"):
        return ""

    lines = ["📝 **Recent Commits**"]
    commit_lines = context["commits"].split("\n")[: Config.MAX_COMMIT_LINES]
    for line in commit_lines:
        if line.strip():
            lines.append(f"   {line}")
    lines.append("")
    return "\n".join(lines)


def _format_structure_section(context: Dict[str, Any]) -> str:
    """Format project structure section."""
    if not context.get("structure"):
        return ""

    lines = ["📂 **Directory Structure**"]
    structure_lines = context["structure"].split("\n")[: Config.MAX_STRUCTURE_LINES]
    for line in structure_lines:
        if line.strip():
            lines.append(f"   {line}")
    lines.append("")
    return "\n".join(lines)


def _format_files_section(context: Dict[str, Any]) -> str:
    """Format git-tracked files section."""
    if not context.get("files"):
        return ""

    lines = ["📋 **Git-tracked Files**"]
    # Show first N files to avoid overwhelming output
    for file in context["files"][: Config.MAX_FILES_SHOWN]:
        lines.append(f"   • {file}")
    if len(context["files"]) > Config.MAX_FILES_SHOWN:
        lines.append(
            f"   ... and {len(context['files']) - Config.MAX_FILES_SHOWN} more files",
        )
    return "\n".join(lines)


def format_session_context(context: Dict[str, Any]) -> str:
    """Format gathered session context for display."""
    sections = [
        f"⚡ Context loaded in {context['execution_time']:.2f}s",
        "",
        _format_readme_section(context),
        _format_metadata_section(context),
        _format_file_overview_section(context),
        _format_git_status_section(context),
        _format_commits_section(context),
        _format_structure_section(context),
        _format_files_section(context),
    ]

    # Filter out empty sections and join
    return "\n".join(section for section in sections if section)
