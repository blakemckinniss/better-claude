"""Git operations for SessionStart hook."""

import asyncio
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from SessionStart.config import Config


# Global cache for git operations with TTL
class GitCache:
    def __init__(self, ttl: int = 30):
        self._cache: Dict[str, Tuple[float, str]] = {}
        self._ttl = ttl

    def _make_key(self, command: List[str], cwd: str) -> str:
        key_data = f"{':'.join(command)}@{cwd}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, command: List[str], cwd: str) -> Optional[str]:
        key = self._make_key(command, cwd)
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, command: List[str], cwd: str, value: str) -> None:
        key = self._make_key(command, cwd)
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()


# Global cache instance
_git_cache = GitCache()


# Subprocess connection pool for better resource management
class SubprocessPool:
    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_processes: List[Any] = []

    async def run_command(
        self,
        command: List[str],
        cwd: str,
        timeout: int = Config.FAST_TIMEOUT,
    ) -> Tuple[str, str, int]:
        async with self._semaphore:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                self._active_processes.append(proc)
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
                returncode = proc.returncode or 0
                return stdout.decode().strip(), stderr.decode().strip(), returncode
            finally:
                if proc in self._active_processes:
                    self._active_processes.remove(proc)


# Global subprocess pool
_subprocess_pool = SubprocessPool()


async def run_batched_git_commands(
    commands: List[Tuple[List[str], str]],
    timeout: int = Config.FAST_TIMEOUT,
) -> List[str]:
    """Run multiple git commands in parallel with caching and pooling.

    Args:
        commands: List of (command, cwd) tuples
        timeout: Command timeout in seconds

    Returns:
        List of command outputs (empty string on error)
    """
    results: List[Optional[str]] = []
    uncached_commands = []

    # Check cache first
    for cmd, cwd in commands:
        cached = _git_cache.get(cmd, cwd)
        if cached is not None:
            results.append(cached)
        else:
            results.append(None)  # Placeholder
            uncached_commands.append((len(results) - 1, cmd, cwd))

    # Run uncached commands in parallel
    if uncached_commands:
        tasks = [
            _subprocess_pool.run_command(cmd, cwd, timeout)
            for _, cmd, cwd in uncached_commands
        ]

        command_results = await asyncio.gather(*tasks, return_exceptions=True)

        for (result_idx, cmd, cwd), result in zip(uncached_commands, command_results):
            if isinstance(result, Exception):
                output = ""
                if os.environ.get("DEBUG_HOOKS"):
                    print(f"Command failed: {' '.join(cmd)}: {result}", file=sys.stderr)
            else:
                stdout, stderr, returncode = result  # type: ignore
                if returncode != 0:
                    output = ""
                    if os.environ.get("DEBUG_HOOKS"):
                        print(
                            f"Command failed: {' '.join(cmd)}\n{stderr}",
                            file=sys.stderr,
                        )
                else:
                    output = stdout
                    # Cache successful results
                    _git_cache.set(cmd, cwd, output)

            results[result_idx] = output

    return [r or "" for r in results]


async def run_fast_command(
    command: List[str],
    cwd: str | None = None,
    timeout: int = Config.FAST_TIMEOUT,
) -> str:
    """Run single command with caching and pooling.

    Args:
        command: Command to execute as list
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Command output or empty string on error
    """
    if cwd is None:
        cwd = os.getcwd()

    # Check cache first
    cached = _git_cache.get(command, cwd)
    if cached is not None:
        return cached

    try:
        stdout, stderr, returncode = await _subprocess_pool.run_command(
            command,
            cwd,
            timeout,
        )

        if returncode != 0:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Command failed: {' '.join(command)}\n{stderr}", file=sys.stderr)
            return ""

        # Cache successful results
        _git_cache.set(command, cwd, stdout)
        return stdout

    except Exception as e:
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Error running {' '.join(command)}: {e}", file=sys.stderr)
        return ""


async def get_git_tracked_files(project_dir: str) -> List[str]:
    """Get git-tracked files using modern async approach."""
    output = await run_fast_command(["git", "ls-files"], cwd=project_dir)
    if not output:
        return []

    files = [f for f in output.split("\n") if f.strip()]
    return sorted(files)


async def is_gitignored(path: str, project_dir: str) -> bool:
    """Check if a path is gitignored using git check-ignore."""
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
    files_output = await run_fast_command(["git", "ls-files"], cwd=project_dir)
    if not files_output:
        return ""

    # Extract unique directories from tracked files, limited to depth 3
    directories = set()
    for file_path in files_output.split("\n"):
        if not file_path.strip():
            continue

        path_parts = Path(file_path).parts
        # Add directories up to depth 3
        for depth in range(1, min(len(path_parts), Config.MAX_PROJECT_DEPTH + 1)):
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
                return await run_fast_command(
                    ["head", "-n", str(Config.MAX_README_LINES), str(readme_path)],
                )

    return ""


async def get_recent_commits(project_dir: str) -> str:
    """Get recent git commits for context."""
    return await run_fast_command(
        [
            "git",
            "log",
            "--oneline",
            "-n",
            str(Config.MAX_RECENT_COMMITS),
            "--no-abbrev-commit",
        ],
        cwd=project_dir,
    )


async def get_git_status(project_dir: str) -> str:
    """Get current git status."""
    return await run_fast_command(["git", "status", "--porcelain"], cwd=project_dir)


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
            file_path.exists()
            and file_path.stat().st_size < Config.MAX_CONFIG_FILE_SIZE
        ):  # Only read small files
            # Check if file is gitignored before reading
            if not await is_gitignored(filename, project_dir):
                content = await run_fast_command(
                    ["head", "-n", str(Config.MAX_CONFIG_LINES), str(file_path)],
                )
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

    # Return top file types
    return dict(
        sorted(extensions.items(), key=lambda x: x[1], reverse=True)[
            : Config.MAX_FILE_TYPES_SHOWN
        ],
    )
