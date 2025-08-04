"""Context gathering strategies for SessionStart hook."""

import asyncio
import json
import time
from typing import Any, Dict, List, cast

from SessionStart.config import Config
from SessionStart.git_operations import (
    get_file_type_summary, get_git_status,
    get_git_tracked_files,
    get_project_metadata,
    get_project_structure,
    get_readme_content,
    get_recent_commits,
    run_batched_git_commands,
    run_fast_command,
)


async def gather_context_fast(project_dir: str) -> Dict[str, Any]:
    """Fast context gathering using batched git commands for performance."""
    start_time = time.time()

    # Batch git commands for reduced subprocess overhead
    git_commands = [
        (["git", "status", "--porcelain", "-uno"], project_dir),
        (["git", "log", "--oneline", f"-{Config.FAST_COMMIT_LIMIT}"], project_dir),
        (["git", "ls-files", "--cached", "--count-lines"], project_dir),
    ]

    # Run SCC and git commands in parallel
    scc_task = asyncio.create_task(
        run_fast_command(["scc", "--no-cocomo", "-f", "json"], cwd=project_dir),
    )
    git_results_task = asyncio.create_task(run_batched_git_commands(git_commands))

    results = await asyncio.gather(scc_task, git_results_task, return_exceptions=True)
    scc_output = results[0] if not isinstance(results[0], Exception) else ""
    git_outputs = results[1] if not isinstance(results[1], Exception) else ["", "", ""]

    # Parse scc output for file stats
    file_types = {}
    total_files = 0
    if scc_output and isinstance(scc_output, str):
        try:
            scc_data = json.loads(scc_output)
            for lang in scc_data:
                # Map language name to common extensions
                lang_name = lang.get("Name", "").lower()
                count = lang.get("Count", 0)
                ext_mapping = {
                    "python": ".py",
                    "json": ".json",
                    "markdown": ".md",
                    "shell": ".sh",
                    "javascript": ".js",
                    "typescript": ".ts",
                }
                if lang_name in ext_mapping:
                    file_types[ext_mapping[lang_name]] = count
                total_files += count
        except Exception:
            pass

    # Extract git command results (with type safety)
    git_status = ""
    git_commits = ""

    if isinstance(git_outputs, list) and len(git_outputs) >= 3:
        git_status = git_outputs[0] or ""
        git_commits = git_outputs[1] or ""
        git_outputs[2] or ""

    return {
        "files": [],  # Skip expensive file enumeration
        "structure": "",  # Skip expensive structure
        "readme": "",  # Skip readme for speed
        "commits": git_commits,
        "status": git_status,
        "metadata": {},  # Skip metadata parsing
        "file_types": file_types,
        "execution_time": time.time() - start_time,
        "total_files": total_files,
    }


async def gather_context_comprehensive(project_dir: str) -> Dict[str, Any]:
    """Comprehensive context gathering with full project analysis."""
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


async def gather_session_context(
    project_dir: str,
    fast_mode: bool = False,
) -> Dict[str, Any]:
    """Unified context gathering with strategy selection.

    Args:
        project_dir: Project directory path
        fast_mode: If True, use fast gathering strategy

    Returns:
        Context dictionary with consistent structure
    """
    if fast_mode:
        return await gather_context_fast(project_dir)
    else:
        return await gather_context_comprehensive(project_dir)


def get_fallback_context() -> Dict[str, Any]:
    """Get minimal fallback context when gathering fails."""
    return {
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
