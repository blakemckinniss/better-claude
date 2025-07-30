"""Recent context history injection for workflow awareness."""

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


class ContextHistoryTracker:
    """Track and analyze recent user context and workflow patterns."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.cache_dir = Path.home() / ".claude" / "context_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # History files
        self.file_history_file = self.cache_dir / "file_access_history.json"
        self.command_history_file = self.cache_dir / "command_history.json"
        self.search_history_file = self.cache_dir / "search_history.json"

    def _get_vscode_recent_files(self, cutoff_time: float) -> List[Dict[str, Any]]:
        """Get recent files from VS Code."""
        files = []
        vscode_config_paths = [
            Path.home() / ".config" / "Code" / "User" / "globalStorage" / "state.vscdb",
            Path.home() / ".vscode" / "extensions" / "state.vscdb",
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "globalStorage"
            / "state.vscdb",
        ]

        # Also check recent workspace files
        recent_workspaces = [
            Path.home() / ".config" / "Code" / "User" / "workspaceStorage",
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "workspaceStorage",
        ]

        for workspace_dir in recent_workspaces:
            if workspace_dir.exists():
                try:
                    # Get recently modified workspace folders
                    for workspace in workspace_dir.iterdir():
                        if workspace.is_dir():
                            workspace_file = workspace / "workspace.json"
                            if (
                                workspace_file.exists()
                                and workspace_file.stat().st_mtime > cutoff_time
                            ):
                                try:
                                    with open(workspace_file) as f:
                                        data = json.load(f)
                                        if "folder" in data:
                                            files.append(
                                                {
                                                    "path": data["folder"],
                                                    "accessed": workspace_file.stat().st_mtime,
                                                    "source": "vscode_workspace",
                                                }
                                            )
                                except:
                                    pass
                except:
                    pass

        return files

    def _get_vim_recent_files(self, cutoff_time: float) -> List[Dict[str, Any]]:
        """Get recent files from Vim/Neovim."""
        files = []
        vim_files = [
            Path.home() / ".viminfo",
            Path.home() / ".config" / "nvim" / "shada" / "main.shada",
            Path.home() / ".local" / "share" / "nvim" / "shada" / "main.shada",
        ]

        for vim_file in vim_files:
            if vim_file.exists() and vim_file.stat().st_mtime > cutoff_time:
                try:
                    # Parse viminfo for recent files
                    with open(vim_file, errors="ignore") as f:
                        content = f.read()
                        # Look for file marks and recent files
                        for line in content.splitlines():
                            if line.startswith("> ") and "/" in line:
                                # Recent file entry
                                parts = line.split("\t")
                                if len(parts) > 1:
                                    file_path = parts[1].strip()
                                    if Path(file_path).exists():
                                        files.append(
                                            {
                                                "path": file_path,
                                                "accessed": vim_file.stat().st_mtime,
                                                "source": "vim",
                                            }
                                        )
                except:
                    pass

        return files

    def _get_system_recent_files(self, cutoff_time: float) -> List[Dict[str, Any]]:
        """Get recently modified files in project directory."""
        files = []

        try:
            # Walk through project directory
            for root, dirs, filenames in os.walk(self.project_dir):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "__pycache__", "target", "build"]
                ]

                for filename in filenames:
                    if filename.startswith("."):
                        continue

                    file_path = Path(root) / filename
                    try:
                        stat = file_path.stat()
                        if stat.st_mtime > cutoff_time:
                            files.append(
                                {
                                    "path": str(file_path),
                                    "accessed": stat.st_mtime,
                                    "source": "filesystem",
                                    "size": stat.st_size,
                                }
                            )
                    except:
                        pass
        except:
            pass

        return files

    def _load_cached_file_history(self) -> List[Dict[str, Any]]:
        """Load cached file access history."""
        if not self.file_history_file.exists():
            return []

        try:
            with open(self.file_history_file) as f:
                history = json.load(f)
                # Filter recent entries
                cutoff = time.time() - 3600
                return [entry for entry in history if entry.get("accessed", 0) > cutoff]
        except:
            return []

    def get_recent_file_access(self) -> List[Dict[str, Any]]:
        """Get recently accessed files from various sources."""
        recent_files = []
        cutoff_time = time.time() - 3600  # Last hour

        # Check IDE/editor temporary files and recent files
        recent_files.extend(self._get_vscode_recent_files(cutoff_time))
        recent_files.extend(self._get_vim_recent_files(cutoff_time))
        recent_files.extend(self._get_system_recent_files(cutoff_time))

        # Load cached history
        cached = self._load_cached_file_history()
        recent_files.extend(cached)

        # Deduplicate and sort by recency
        seen = set()
        unique_files = []
        for file_info in sorted(
            recent_files, key=lambda x: x["accessed"], reverse=True
        ):
            if file_info["path"] not in seen:
                seen.add(file_info["path"])
                unique_files.append(file_info)

        return unique_files[:20]  # Top 20 most recent

    def _get_shell_history(self) -> List[Dict[str, Any]]:
        """Get recent shell commands."""
        commands = []
        cutoff = time.time() - 3600  # Last hour

        # Check bash history
        bash_history = Path.home() / ".bash_history"
        if bash_history.exists() and bash_history.stat().st_mtime > cutoff:
            try:
                with open(bash_history) as f:
                    lines = f.readlines()[-50:]  # Last 50 commands
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            commands.append(
                                {
                                    "command": line,
                                    "timestamp": bash_history.stat().st_mtime,
                                    "source": "bash",
                                    "directory": str(self.project_dir),
                                }
                            )
            except:
                pass

        # Check zsh history
        zsh_history = Path.home() / ".zsh_history"
        if zsh_history.exists() and zsh_history.stat().st_mtime > cutoff:
            try:
                with open(zsh_history, "rb") as f:
                    # zsh history can be binary
                    content = f.read().decode("utf-8", errors="ignore")
                    for line in content.splitlines()[-50:]:
                        if ";" in line:
                            # zsh extended history format
                            cmd = line.split(";", 1)[1].strip()
                            if cmd:
                                commands.append(
                                    {
                                        "command": cmd,
                                        "timestamp": zsh_history.stat().st_mtime,
                                        "source": "zsh",
                                        "directory": str(self.project_dir),
                                    }
                                )
            except:
                pass

        return commands

    def _get_git_history(self) -> List[Dict[str, Any]]:
        """Get recent git commands."""
        commands = []

        # Check for .git directory
        git_dir = self.project_dir / ".git"
        if git_dir.exists():
            try:
                # Get recent commits (indicates git activity)
                import subprocess

                result = subprocess.run(
                    ["git", "log", "--oneline", "-10", "--since=1 hour ago"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if result.stdout:
                    commits = result.stdout.strip().splitlines()
                    for commit in commits:
                        commands.append(
                            {
                                "command": f"git commit: {commit}",
                                "timestamp": time.time(),
                                "source": "git",
                                "directory": str(self.project_dir),
                            }
                        )

                # Check git reflog for recent operations
                result = subprocess.run(
                    ["git", "reflog", "--since=1 hour ago", "-10"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if result.stdout:
                    for line in result.stdout.splitlines():
                        if ":" in line:
                            operation = line.split(":", 1)[1].strip()
                            commands.append(
                                {
                                    "command": f"git {operation}",
                                    "timestamp": time.time(),
                                    "source": "git_reflog",
                                    "directory": str(self.project_dir),
                                }
                            )
            except:
                pass

        return commands

    def _load_cached_command_history(self) -> List[Dict[str, Any]]:
        """Load cached command history."""
        if not self.command_history_file.exists():
            return []

        try:
            with open(self.command_history_file) as f:
                history = json.load(f)
                cutoff = time.time() - 3600
                return [
                    entry for entry in history if entry.get("timestamp", 0) > cutoff
                ]
        except:
            return []

    def get_recent_commands(self) -> List[Dict[str, Any]]:
        """Get recently executed commands."""
        commands = []

        # Check shell history
        commands.extend(self._get_shell_history())

        # Check git commands
        commands.extend(self._get_git_history())

        # Load cached command history
        cached = self._load_cached_command_history()
        commands.extend(cached)

        # Deduplicate and sort
        seen = set()
        unique_commands = []
        for cmd in sorted(commands, key=lambda x: x["timestamp"], reverse=True):
            cmd_key = f"{cmd['command']}:{cmd.get('directory', '')}"
            if cmd_key not in seen:
                seen.add(cmd_key)
                unique_commands.append(cmd)

        return unique_commands[:15]  # Top 15 most recent

    def _detect_languages(self, files: List[Dict[str, Any]]) -> List[str]:
        """Detect primary programming languages being worked on."""
        extensions = defaultdict(int)

        for file_info in files:
            path = Path(file_info["path"])
            if path.suffix:
                extensions[path.suffix.lower()] += 1

        # Map extensions to languages
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".php": "PHP",
            ".rb": "Ruby",
            ".cs": "C#",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }

        languages = []
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            if ext in language_map:
                languages.append(language_map[ext])

        return languages[:3]  # Top 3 languages

    def _get_active_directories(self, files: List[Dict[str, Any]]) -> List[str]:
        """Get most active directories."""
        dirs = defaultdict(int)

        for file_info in files:
            path = Path(file_info["path"])
            # Get relative directory from project root
            try:
                rel_path = path.relative_to(self.project_dir)
                dir_path = str(rel_path.parent) if rel_path.parent != Path(".") else "."
                dirs[dir_path] += 1
            except ValueError:
                # File outside project
                dirs[str(path.parent)] += 1

        return [
            dir_path
            for dir_path, _ in sorted(dirs.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
        ]

    def _detect_dev_phase(self, commands: List[Dict[str, Any]]) -> str:
        """Detect current development phase based on commands."""
        command_text = " ".join(cmd["command"].lower() for cmd in commands)

        if any(word in command_text for word in ["test", "pytest", "jest", "npm test"]):
            return "testing"
        elif any(
            word in command_text for word in ["build", "compile", "make", "cargo build"]
        ):
            return "building"
        elif any(
            word in command_text for word in ["deploy", "docker", "kubernetes", "helm"]
        ):
            return "deployment"
        elif any(
            word in command_text for word in ["git add", "git commit", "git push"]
        ):
            return "committing"
        elif any(word in command_text for word in ["debug", "gdb", "lldb", "pdb"]):
            return "debugging"
        else:
            return "development"

    def _extract_tools(self, commands: List[Dict[str, Any]]) -> List[str]:
        """Extract development tools being used."""
        tools = set()

        for cmd in commands:
            command = cmd["command"].lower()

            # Common dev tools
            if "npm" in command:
                tools.add("npm")
            if "pip" in command:
                tools.add("pip")
            if "cargo" in command:
                tools.add("cargo")
            if "docker" in command:
                tools.add("docker")
            if "git" in command:
                tools.add("git")
            if any(tool in command for tool in ["pytest", "jest", "mocha"]):
                tools.add("testing")
            if any(tool in command for tool in ["ruff", "eslint", "clippy"]):
                tools.add("linting")

        return list(tools)

    def _detect_focus_areas(
        self, files: List[Dict[str, Any]], commands: List[Dict[str, Any]]
    ) -> List[str]:
        """Detect what areas of the codebase are being focused on."""
        focus_areas = set()

        # Analyze file paths
        for file_info in files:
            path = file_info["path"].lower()

            if "test" in path:
                focus_areas.add("testing")
            if any(word in path for word in ["api", "endpoint", "route"]):
                focus_areas.add("api")
            if any(word in path for word in ["ui", "component", "view"]):
                focus_areas.add("frontend")
            if any(word in path for word in ["db", "model", "schema"]):
                focus_areas.add("database")
            if any(word in path for word in ["config", "setting"]):
                focus_areas.add("configuration")
            if any(word in path for word in ["doc", "readme"]):
                focus_areas.add("documentation")

        return list(focus_areas)

    def get_workflow_patterns(self) -> Dict[str, Any]:
        """Analyze workflow patterns from recent activity."""
        files = self.get_recent_file_access()
        commands = self.get_recent_commands()

        patterns = {
            "primary_languages": self._detect_languages(files),
            "active_directories": self._get_active_directories(files),
            "development_phase": self._detect_dev_phase(commands),
            "tools_used": self._extract_tools(commands),
            "focus_areas": self._detect_focus_areas(files, commands),
        }

        return patterns


async def get_context_history_injection(prompt: str, project_dir: str) -> str:
    """Create context history injection."""
    tracker = ContextHistoryTracker(project_dir)

    try:
        # Get recent activity
        recent_files = tracker.get_recent_file_access()[:10]
        recent_commands = tracker.get_recent_commands()[:8]
        patterns = tracker.get_workflow_patterns()

        if not recent_files and not recent_commands:
            return ""

        injection_parts = []

        # Recent files
        if recent_files:
            injection_parts.append("Recent files:")
            project_path = Path(project_dir)  # Cache to avoid repeated Path() calls
            current_time = time.time()  # Cache current time

            for file_info in recent_files[:5]:
                try:
                    # Ensure required keys exist
                    if "path" not in file_info or "accessed" not in file_info:
                        continue

                    path = Path(file_info["path"])
                    time_ago = max(
                        0, int((current_time - file_info["accessed"]) / 60)
                    )  # Ensure non-negative

                    try:
                        rel_path = path.relative_to(project_path)
                        injection_parts.append(f"  {rel_path} ({time_ago}m ago)")
                    except ValueError:
                        # File outside project - use just the filename
                        injection_parts.append(f"  {path.name} ({time_ago}m ago)")

                except (KeyError, OSError, ValueError):
                    # Skip malformed file_info entries
                    continue

        # Recent commands (if development-related)
        dev_commands = [
            cmd
            for cmd in recent_commands
            if any(
                tool in cmd["command"].lower()
                for tool in ["git", "npm", "pip", "cargo", "make", "test", "build"]
            )
        ]
        if dev_commands:
            injection_parts.append("Recent commands:")
            for cmd in dev_commands[:3]:
                command = (
                    f"{cmd['command'][:50]}..."
                    if len(cmd["command"]) > 50
                    else cmd["command"]
                )
                injection_parts.append(f"  {command}")

        # Workflow patterns
        if patterns["primary_languages"]:
            injection_parts.append(
                f"Languages: {', '.join(patterns['primary_languages'])}"
            )

        if patterns["development_phase"] != "development":
            injection_parts.append(f"Phase: {patterns['development_phase']}")

        if patterns["focus_areas"]:
            injection_parts.append(f"Focus: {', '.join(patterns['focus_areas'])}")

        if injection_parts:
            return (
                f"<context-history>\n{'\n'.join(injection_parts)}\n</context-history>\n"
            )
        else:
            return ""

    except Exception as e:
        # Don't let context history errors break the hook
        return f"<!-- Context history error: {str(e)} -->\n"
