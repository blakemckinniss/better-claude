"""Consolidated system monitoring module combining runtime, test, and context
tracking."""

import asyncio
import json
import os
import re
import socket
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:
    psutil = None  # type: ignore


class SystemMonitor:
    """Unified system monitor combining runtime, test, and context functionality."""

    def __init__(self, project_dir: Optional[str] = None) -> None:
        project_path = (
            project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )
        self.project_dir = Path(project_path)
        if psutil:
            self.process = psutil.Process()
        self.start_time = time.time()

        # Cache setup
        self.cache_dir = Path.home() / ".claude" / "system_monitor_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._default_cache_duration = 30  # 30 seconds

        # History tracking
        self.file_history_file = self.cache_dir / "file_access_history.json"
        self.command_history_file = self.cache_dir / "command_history.json"

    def _get_cached_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Any],
        cache_duration: Optional[int] = None,
    ) -> Any:
        """Get cached value or compute new one with TTL."""
        cache_duration = cache_duration or self._default_cache_duration
        current_time = time.time()

        if (
            key in self._cache
            and key in self._cache_ttl
            and current_time - self._cache_ttl[key] < cache_duration
        ):
            return self._cache[key]

        result = compute_func()
        self._cache[key] = result
        self._cache_ttl[key] = current_time
        return result

    # ============================================================================
    # RUNTIME MONITORING FUNCTIONALITY
    # ============================================================================

    def _get_disk_io_stat(self, stat_name: str) -> float:
        """Safely get disk I/O statistics, handling None return values."""
        if not psutil:
            return 0.0
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io is not None and hasattr(disk_io, stat_name):
                return getattr(disk_io, stat_name) / 1024 / 1024  # Convert to MB
            return 0.0
        except (AttributeError, OSError):
            return 0.0

    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage with caching."""

        def _compute_resources():
            if not psutil:
                return {
                    "cpu": {
                        "system_percent": 0.0,
                        "process_percent": 0.0,
                        "count": 1,
                    },
                    "memory": {
                        "system_percent": 0.0,
                        "process_mb": 0.0,
                        "available_gb": 0.0,
                    },
                    "disk": {
                        "usage_percent": 0.0,
                        "io_read_mb": 0.0,
                        "io_write_mb": 0.0,
                    },
                }
            
            try:
                virtual_memory = psutil.virtual_memory()
                return {
                    "cpu": {
                        "system_percent": psutil.cpu_percent(interval=0.1),
                        "process_percent": self.process.cpu_percent() if self.process else 0.0,
                        "count": psutil.cpu_count(),
                    },
                    "memory": {
                        "system_percent": virtual_memory.percent,
                        "process_mb": self.process.memory_info().rss / 1024 / 1024 if self.process else 0.0,
                        "available_gb": virtual_memory.available / 1024 / 1024 / 1024,
                    },
                    "disk": {
                        "usage_percent": psutil.disk_usage("/").percent,
                        "io_read_mb": self._get_disk_io_stat("read_bytes"),
                        "io_write_mb": self._get_disk_io_stat("write_bytes"),
                    },
                }
            except (AttributeError, OSError) as e:
                print(f"Error getting system resources: {e}")
                return {
                    "cpu": {
                        "system_percent": 0.0,
                        "process_percent": 0.0,
                        "count": 1,
                    },
                    "memory": {
                        "system_percent": 0.0,
                        "process_mb": 0.0,
                        "available_gb": 0.0,
                    },
                    "disk": {
                        "usage_percent": 0.0,
                        "io_read_mb": 0.0,
                        "io_write_mb": 0.0,
                    },
                }

        return self._get_cached_or_compute("system_resources", _compute_resources, 10)

    def get_process_info(self) -> Dict[str, Any]:
        """Get information about relevant processes with caching."""

        def _compute_processes():
            if not psutil:
                return {
                    "relevant_processes": [],
                    "total_processes": 0,
                }
            
            relevant_processes = []

            # Look for language servers, IDEs, and dev tools
            target_names = [
                "node",
                "python",
                "typescript-language-server",
                "pyright",
                "ruff-lsp",
                "mypy",
                "code",
                "cursor",
                "docker",
                "postgres",
                "redis",
                "nginx",
                "webpack",
                "vite",
                "pytest",
                "jest",
            ]

            try:
                for proc in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent"],
                ):
                    try:
                        if any(
                            target in proc.info["name"].lower() for target in target_names
                        ):
                            relevant_processes.append(
                                {
                                    "name": proc.info["name"],
                                    "pid": proc.info["pid"],
                                    "cpu": proc.info["cpu_percent"],
                                    "memory": proc.info["memory_percent"],
                                },
                            )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                return {
                    "relevant_processes": sorted(
                        relevant_processes,
                        key=lambda x: x["cpu"],
                        reverse=True,
                    )[:5],
                    "total_processes": len(psutil.pids()),
                }
            except (AttributeError, OSError) as e:
                print(f"Error getting process info: {e}")
                return {
                    "relevant_processes": [],
                    "total_processes": 0,
                }

        return self._get_cached_or_compute("process_info", _compute_processes, 15)

    async def get_network_status(self) -> Dict[str, Any]:
        """Get network connectivity and latency with caching."""

        def _compute_network():
            if not psutil:
                connections = {
                    "active_connections": 0,
                    "can_reach_github": False,
                    "can_reach_pypi": False,
                    "can_reach_npm": False,
                }
            else:
                try:
                    connections = {
                        "active_connections": len(psutil.net_connections()),
                        "can_reach_github": False,
                        "can_reach_pypi": False,
                        "can_reach_npm": False,
                    }
                except (AttributeError, OSError) as e:
                    print(f"Error getting network connections: {e}")
                    connections = {
                        "active_connections": 0,
                        "can_reach_github": False,
                        "can_reach_pypi": False,
                        "can_reach_npm": False,
                    }
            return connections

        cached_result = self._get_cached_or_compute(
            "network_base",
            _compute_network,
            30,
        )

        # Quick connectivity checks in parallel
        async def check_connectivity(host: str) -> bool:
            try:
                future = asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: socket.create_connection((host, 443), timeout=1).close(),
                )
                await asyncio.wait_for(future, timeout=2)
                return True
            except (OSError, asyncio.TimeoutError, ConnectionError) as e:
                print(f"Network connectivity error for {host}: {e}")
                return False

        targets = [
            ("github.com", "can_reach_github"),
            ("pypi.org", "can_reach_pypi"),
            ("registry.npmjs.org", "can_reach_npm"),
        ]

        # Run connectivity checks in parallel
        tasks = [check_connectivity(host) for host, _ in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (host, key), result in zip(targets, results):
            if isinstance(result, bool) and result:
                cached_result[key] = True

        return cached_result

    def get_file_system_activity(self) -> Dict[str, Any]:
        """Get recent file system activity with caching."""

        def _compute_file_activity():
            recent_files = []
            cutoff_time = time.time() - 300  # Last 5 minutes

            try:
                for root, _, files in os.walk(self.project_dir):
                    # Skip hidden and cache directories
                    if any(
                        part.startswith(".") or part == "__pycache__"
                        for part in root.split(os.sep)
                    ):
                        continue

                    for file in files[:10]:  # Limit per directory
                        filepath = os.path.join(root, file)
                        try:
                            stat = os.stat(filepath)
                            if stat.st_mtime > cutoff_time:
                                recent_files.append(
                                    {
                                        "path": os.path.relpath(
                                            filepath,
                                            self.project_dir,
                                        ),
                                        "modified": datetime.fromtimestamp(
                                            stat.st_mtime,
                                        ).isoformat(),
                                        "size_kb": stat.st_size / 1024,
                                    },
                                )
                        except (OSError, PermissionError) as e:
                            print(f"File stat error for {filepath}: {e}")
            except (OSError, PermissionError) as e:
                print(f"File system walk error: {e}")

            return {
                "recently_modified": sorted(
                    recent_files,
                    key=lambda x: x["modified"],
                    reverse=True,
                )[:10],
            }

        return self._get_cached_or_compute("file_activity", _compute_file_activity, 60)

    # ============================================================================
    # TEST STATUS FUNCTIONALITY
    # ============================================================================

    def _get_failure_message(self, testcase_element) -> str:
        """Safely extract failure message from testcase element."""
        failure_elem = testcase_element.find(".//failure")
        if failure_elem is not None:
            return failure_elem.get("message", "Unknown failure")

        error_elem = testcase_element.find(".//error")
        if error_elem is not None:
            return error_elem.get("message", "Unknown error")

        return "Unknown error"

    def _find_pytest_results(self) -> Optional[Dict[str, Any]]:
        """Find pytest results from various sources."""
        # Check for pytest-json-report output
        json_reports = list(
            self.project_dir.glob("**/.pytest_cache/pytest-report.json"),
        )
        if json_reports:
            try:
                with open(json_reports[0]) as f:
                    report = json.load(f)
                    return {
                        "passed": report.get("summary", {}).get("passed", 0),
                        "failed": report.get("summary", {}).get("failed", 0),
                        "skipped": report.get("summary", {}).get("skipped", 0),
                        "duration": report.get("duration", 0),
                        "failures": [
                            {
                                "test": test["nodeid"],
                                "message": test.get("call", {}).get(
                                    "longrepr",
                                    "Unknown error",
                                ),
                            }
                            for test in report.get("tests", [])
                            if test.get("outcome") == "failed"
                        ][:3],
                    }
            except (json.JSONDecodeError, OSError) as e:
                print(f"Pytest JSON report error: {e}")

        # Check for junit XML output
        junit_files = list(self.project_dir.glob("**/pytest-junit.xml")) + list(
            self.project_dir.glob("**/test-results.xml"),
        )
        if junit_files:
            try:
                tree = ET.parse(junit_files[0])
                root = tree.getroot()

                testsuite = root.find(".//testsuite") or root
                return {
                    "passed": int(testsuite.get("tests", 0))
                    - int(testsuite.get("failures", 0))
                    - int(testsuite.get("errors", 0)),
                    "failed": int(testsuite.get("failures", 0))
                    + int(testsuite.get("errors", 0)),
                    "skipped": int(testsuite.get("skipped", 0)),
                    "duration": float(testsuite.get("time", 0)),
                    "failures": [
                        {
                            "test": tc.get("name", "Unknown"),
                            "message": self._get_failure_message(tc),
                        }
                        for tc in root.findall(".//testcase")
                        if tc.find(".//failure") is not None
                        or tc.find(".//error") is not None
                    ][:3],
                }
            except (ET.ParseError, OSError) as e:
                print(f"Pytest XML report error: {e}")

        return None

    def _find_jest_results(self) -> Optional[Dict[str, Any]]:
        """Find Jest test results."""
        jest_results = list(self.project_dir.glob("**/jest-results.json"))
        if jest_results:
            try:
                with open(jest_results[0]) as f:
                    data = json.load(f)
                    return {
                        "passed": data.get("numPassedTests", 0),
                        "failed": data.get("numFailedTests", 0),
                        "skipped": data.get("numPendingTests", 0),
                        "duration": (data.get("endTime", 0) - data.get("startTime", 0))
                        / 1000,
                        "failures": [
                            {
                                "test": (
                                    result.get("ancestorTitles", [])[-1]
                                    if result.get("ancestorTitles")
                                    else "Unknown"
                                ),
                                "message": result.get(
                                    "failureMessages",
                                    ["Unknown error"],
                                )[0],
                            }
                            for result in data.get("testResults", [])
                            for assertion in result.get("assertionResults", [])
                            if assertion.get("status") == "failed"
                        ][:3],
                    }
            except (json.JSONDecodeError, OSError) as e:
                print(f"Jest results error: {e}")
        return None

    def _find_coverage_data(self) -> Optional[Dict[str, Any]]:
        """Find coverage data from various sources."""

        def _compute_coverage():
            coverage_data = {}

            # Python coverage
            coverage_files = list(self.project_dir.glob("**/.coverage")) + list(
                self.project_dir.glob("**/coverage.json"),
            )
            if coverage_files:
                try:
                    json_cov = self.project_dir / "coverage.json"
                    if json_cov.exists():
                        with open(json_cov) as f:
                            data = json.load(f)
                            total_lines = sum(
                                len(v["executed_lines"]) + len(v["missing_lines"])
                                for v in data["files"].values()
                            )
                            covered_lines = sum(
                                len(v["executed_lines"]) for v in data["files"].values()
                            )
                            coverage_data["python"] = {
                                "percentage": (
                                    (covered_lines / total_lines * 100)
                                    if total_lines > 0
                                    else 0
                                ),
                                "files": len(data["files"]),
                                "uncovered_files": [
                                    {
                                        "file": f,
                                        "coverage": len(d["executed_lines"])
                                        / (
                                            len(d["executed_lines"])
                                            + len(d["missing_lines"])
                                        )
                                        * 100,
                                    }
                                    for f, d in data["files"].items()
                                    if len(d["missing_lines"]) > 0
                                ][:5],
                            }
                    else:
                        # Try to parse .coverage SQLite file
                        conn = sqlite3.connect(coverage_files[0])
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(DISTINCT file_id) FROM line_bits")
                        file_count = cursor.fetchone()[0]
                        coverage_data["python"] = {
                            "files": file_count,
                            "status": "Coverage data found (details in .coverage file)",
                        }
                        conn.close()
                except (json.JSONDecodeError, OSError, sqlite3.Error) as e:
                    print(f"Coverage data error: {e}")

            # JavaScript coverage (Jest/NYC)
            lcov_files = list(self.project_dir.glob("**/lcov.info")) + list(
                self.project_dir.glob("**/coverage-final.json"),
            )
            if lcov_files:
                try:
                    if lcov_files[0].name == "coverage-final.json":
                        with open(lcov_files[0]) as f:
                            data = json.load(f)
                            total_statements = 0
                            covered_statements = 0

                            for file_data in data.values():
                                statements = file_data.get("s", {})
                                total_statements += len(statements)
                                covered_statements += sum(
                                    1 for v in statements.values() if v > 0
                                )

                            coverage_data["javascript"] = {
                                "percentage": (
                                    (covered_statements / total_statements * 100)
                                    if total_statements > 0
                                    else 0
                                ),
                                "files": len(data),
                            }
                    else:
                        # Parse lcov.info
                        with open(lcov_files[0]) as f:
                            content = f.read()
                            match = re.search(r"LF:(\d+)\s+LH:(\d+)", content)
                            if match:
                                total_lines = int(match.group(1))
                                hit_lines = int(match.group(2))
                                coverage_data["javascript"] = {
                                    "percentage": (
                                        (hit_lines / total_lines * 100)
                                        if total_lines > 0
                                        else 0
                                    ),
                                }
                except (json.JSONDecodeError, OSError) as e:
                    print(f"JavaScript coverage error: {e}")

            return coverage_data

        return self._get_cached_or_compute("coverage_data", _compute_coverage, 120)

    def find_test_results(self) -> Dict[str, Any]:
        """Find and parse recent test results with caching."""

        def _compute_test_results():
            results = {
                "pytest": self._find_pytest_results(),
                "jest": self._find_jest_results(),
                "coverage": self._find_coverage_data(),
            }
            return {k: v for k, v in results.items() if v}

        return self._get_cached_or_compute("test_results", _compute_test_results, 60)

    def get_ci_status(self) -> Optional[Dict[str, Any]]:
        """Get CI/CD pipeline status if available."""

        def _compute_ci_status():
            ci_data = {}

            # GitHub Actions
            ga_dir = self.project_dir / ".github" / "workflows"
            if ga_dir.exists():
                ci_data["github_actions"] = {
                    "workflows": len(list(ga_dir.glob("*.yml")))
                    + len(list(ga_dir.glob("*.yaml"))),
                    "status": "Check GitHub for latest run status",
                }

            # GitLab CI
            if (self.project_dir / ".gitlab-ci.yml").exists():
                ci_data["gitlab_ci"] = {"configured": True}

            # Jenkins
            if (self.project_dir / "Jenkinsfile").exists():
                ci_data["jenkins"] = {"configured": True}

            return ci_data if ci_data else None

        return self._get_cached_or_compute("ci_status", _compute_ci_status, 300)

    # ============================================================================
    # CONTEXT HISTORY FUNCTIONALITY
    # ============================================================================

    def _get_recent_files_from_editors(
        self,
        cutoff_time: float,
    ) -> List[Dict[str, Any]]:
        """Get recent files from various editors."""
        files = []

        # VS Code recent files
        vscode_config_paths = [
            Path.home() / ".config" / "Code" / "User" / "workspaceStorage",
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "workspaceStorage",
        ]

        for workspace_dir in vscode_config_paths:
            if workspace_dir.exists():
                try:
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
                                                },
                                            )
                                except (json.JSONDecodeError, OSError) as e:
                                    print(f"VS Code workspace error: {e}")
                except (OSError, PermissionError) as e:
                    print(f"VS Code workspace directory error: {e}")

        # Vim/Neovim recent files
        vim_files = [
            Path.home() / ".viminfo",
            Path.home() / ".config" / "nvim" / "shada" / "main.shada",
            Path.home() / ".local" / "share" / "nvim" / "shada" / "main.shada",
        ]

        for vim_file in vim_files:
            if vim_file.exists() and vim_file.stat().st_mtime > cutoff_time:
                try:
                    with open(vim_file, errors="ignore") as f:
                        content = f.read()
                        for line in content.splitlines():
                            if line.startswith("> ") and "/" in line:
                                parts = line.split("\t")
                                if len(parts) > 1:
                                    file_path = parts[1].strip()
                                    if Path(file_path).exists():
                                        files.append(
                                            {
                                                "path": file_path,
                                                "accessed": vim_file.stat().st_mtime,
                                                "source": "vim",
                                            },
                                        )
                except (OSError, UnicodeDecodeError) as e:
                    print(f"Vim history file error: {e}")

        return files

    def _get_system_recent_files(self, cutoff_time: float) -> List[Dict[str, Any]]:
        """Get recently modified files in project directory."""
        files = []

        try:
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
                                },
                            )
                    except (OSError, PermissionError) as e:
                        print(f"File stat error for {file_path}: {e}")
        except (OSError, PermissionError) as e:
            print(f"System recent files error: {e}")

        return files

    def get_recent_file_access(self) -> List[Dict[str, Any]]:
        """Get recently accessed files from various sources."""

        def _compute_recent_files():
            recent_files = []
            cutoff_time = time.time() - 3600  # Last hour

            # Check IDE/editor temporary files and recent files
            recent_files.extend(self._get_recent_files_from_editors(cutoff_time))
            recent_files.extend(self._get_system_recent_files(cutoff_time))

            # Load cached history
            if self.file_history_file.exists():
                try:
                    with open(self.file_history_file) as f:
                        history = json.load(f)
                        cutoff = time.time() - 3600
                        cached = [
                            entry
                            for entry in history
                            if entry.get("accessed", 0) > cutoff
                        ]
                        recent_files.extend(cached)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"File history error: {e}")

            # Deduplicate and sort by recency
            seen = set()
            unique_files = []
            for file_info in sorted(
                recent_files,
                key=lambda x: x["accessed"],
                reverse=True,
            ):
                if file_info["path"] not in seen:
                    seen.add(file_info["path"])
                    unique_files.append(file_info)

            return unique_files[:20]

        return self._get_cached_or_compute("recent_files", _compute_recent_files, 120)

    def _get_shell_and_git_history(self) -> List[Dict[str, Any]]:
        """Get recent shell and git commands."""
        commands = []
        cutoff = time.time() - 3600  # Last hour

        # Check bash history
        bash_history = Path.home() / ".bash_history"
        if bash_history.exists() and bash_history.stat().st_mtime > cutoff:
            try:
                with open(bash_history) as f:
                    lines = f.readlines()[-50:]
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            commands.append(
                                {
                                    "command": line,
                                    "timestamp": bash_history.stat().st_mtime,
                                    "source": "bash",
                                    "directory": str(self.project_dir),
                                },
                            )
            except (OSError, UnicodeDecodeError) as e:
                print(f"Bash history error: {e}")

        # Check zsh history
        zsh_history = Path.home() / ".zsh_history"
        if zsh_history.exists() and zsh_history.stat().st_mtime > cutoff:
            try:
                with open(zsh_history, "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    for line in content.splitlines()[-50:]:
                        if ";" in line:
                            cmd = line.split(";", 1)[1].strip()
                            if cmd:
                                commands.append(
                                    {
                                        "command": cmd,
                                        "timestamp": zsh_history.stat().st_mtime,
                                        "source": "zsh",
                                        "directory": str(self.project_dir),
                                    },
                                )
            except (OSError, UnicodeDecodeError) as e:
                print(f"Zsh history error: {e}")

        # Get git history
        git_dir = self.project_dir / ".git"
        if git_dir.exists():
            try:
                # Get recent commits
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
                            },
                        )

                # Check git reflog
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
                                },
                            )
            except (
                subprocess.SubprocessError,
                subprocess.TimeoutExpired,
                OSError,
            ) as e:
                print(f"Git command error: {e}")

        return commands

    def get_recent_commands(self) -> List[Dict[str, Any]]:
        """Get recently executed commands."""

        def _compute_recent_commands():
            commands = self._get_shell_and_git_history()

            # Load cached command history
            if self.command_history_file.exists():
                try:
                    with open(self.command_history_file) as f:
                        history = json.load(f)
                        cutoff = time.time() - 3600
                        cached = [
                            entry
                            for entry in history
                            if entry.get("timestamp", 0) > cutoff
                        ]
                        commands.extend(cached)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Command history error: {e}")

            # Deduplicate and sort
            seen = set()
            unique_commands = []
            for cmd in sorted(commands, key=lambda x: x["timestamp"], reverse=True):
                cmd_key = f"{cmd['command']}:{cmd.get('directory', '')}"
                if cmd_key not in seen:
                    seen.add(cmd_key)
                    unique_commands.append(cmd)

            return unique_commands[:15]

        return self._get_cached_or_compute(
            "recent_commands",
            _compute_recent_commands,
            120,
        )

    def get_workflow_patterns(self) -> Dict[str, Any]:
        """Analyze workflow patterns from recent activity."""

        def _compute_patterns():
            files = self.get_recent_file_access()
            commands = self.get_recent_commands()

            # Detect languages
            extensions = defaultdict(int)
            for file_info in files:
                path = Path(file_info["path"])
                if path.suffix:
                    extensions[path.suffix.lower()] += 1

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
            for ext, count in sorted(
                extensions.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                if ext in language_map:
                    languages.append(language_map[ext])

            # Detect development phase
            command_text = " ".join(cmd["command"].lower() for cmd in commands)
            if any(
                word in command_text for word in ["test", "pytest", "jest", "npm test"]
            ):
                dev_phase = "testing"
            elif any(
                word in command_text
                for word in ["build", "compile", "make", "cargo build"]
            ):
                dev_phase = "building"
            elif any(
                word in command_text
                for word in ["deploy", "docker", "kubernetes", "helm"]
            ):
                dev_phase = "deployment"
            elif any(
                word in command_text for word in ["git add", "git commit", "git push"]
            ):
                dev_phase = "committing"
            elif any(word in command_text for word in ["debug", "gdb", "lldb", "pdb"]):
                dev_phase = "debugging"
            else:
                dev_phase = "development"

            # Extract tools
            tools = set()
            for cmd in commands:
                command = cmd["command"].lower()
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

            # Detect focus areas
            focus_areas = set()
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

            return {
                "primary_languages": languages[:3],
                "development_phase": dev_phase,
                "tools_used": list(tools),
                "focus_areas": list(focus_areas),
            }

        return self._get_cached_or_compute("workflow_patterns", _compute_patterns, 180)

    # ============================================================================
    # UNIFIED MONITORING METHODS
    # ============================================================================

    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status combining all monitoring data."""
        # Run monitoring tasks in parallel
        resources_task = asyncio.create_task(
            asyncio.to_thread(self.get_system_resources),
        )
        processes_task = asyncio.create_task(asyncio.to_thread(self.get_process_info))
        network_task = self.get_network_status()
        files_task = asyncio.create_task(
            asyncio.to_thread(self.get_file_system_activity),
        )
        test_results_task = asyncio.create_task(
            asyncio.to_thread(self.find_test_results),
        )
        ci_status_task = asyncio.create_task(
            asyncio.to_thread(lambda: self.get_ci_status() or {})
        )
        recent_files_task = asyncio.create_task(
            asyncio.to_thread(self.get_recent_file_access),
        )
        recent_commands_task = asyncio.create_task(
            asyncio.to_thread(self.get_recent_commands),
        )
        patterns_task = asyncio.create_task(
            asyncio.to_thread(self.get_workflow_patterns),
        )

        results = await asyncio.gather(
            resources_task,
            processes_task,
            network_task,
            files_task,
            test_results_task,
            ci_status_task,
            recent_files_task,  # type: ignore
            recent_commands_task,  # type: ignore
            patterns_task,
        )

        return {
            "runtime": {
                "resources": results[0],
                "processes": results[1],
                "network": results[2],
                "files": results[3],
            },
            "testing": {
                "results": results[4],
                "ci_status": results[5],
            },
            "context": {
                "recent_files": results[6],
                "recent_commands": results[7],
                "patterns": results[8],
            },
        }

    async def generate_monitoring_injection(self, prompt: str = "") -> str:
        """Generate consolidated monitoring injection for user prompt context."""
        try:
            status = await self.get_comprehensive_status()
            injection_parts = []

            # Runtime warnings
            resources = status["runtime"]["resources"]
            if resources["cpu"]["system_percent"] > 80:
                injection_parts.append(
                    f"⚠️ HIGH CPU: {resources['cpu']['system_percent']}%",
                )
            if resources["memory"]["system_percent"] > 85:
                injection_parts.append(
                    f"⚠️ HIGH MEMORY: {resources['memory']['system_percent']}%",
                )
            if resources["disk"]["usage_percent"] > 90:
                injection_parts.append(
                    f"⚠️ LOW DISK: {resources['disk']['usage_percent']}% used",
                )

            # Network issues
            network = status["runtime"]["network"]
            network_issues = []
            if not network["can_reach_github"]:
                network_issues.append("GitHub")
            if not network["can_reach_pypi"]:
                network_issues.append("PyPI")
            if not network["can_reach_npm"]:
                network_issues.append("NPM")
            if network_issues:
                injection_parts.append(f"⚠️ UNREACHABLE: {', '.join(network_issues)}")

            # Heavy processes
            processes = status["runtime"]["processes"]
            heavy_procs = [p for p in processes["relevant_processes"] if p["cpu"] > 50]
            if heavy_procs:
                injection_parts.append(
                    f"⚠️ HIGH CPU PROCESSES: {', '.join(p['name'] for p in heavy_procs)}",
                )

            # Test results
            test_results = status["testing"]["results"]
            for framework, results in test_results.items():
                if framework == "coverage":
                    continue

                if isinstance(results, dict) and "passed" in results:
                    total = (
                        results["passed"]
                        + results["failed"]
                        + results.get("skipped", 0)
                    )
                    status_emoji = "✅" if results["failed"] == 0 else "❌"
                    injection_parts.append(
                        f"{status_emoji} {framework.upper()}: {results['passed']}/{total} passed",
                    )

                    if results.get("failures"):
                        injection_parts.append("  Recent failures:")
                        for failure in results["failures"]:
                            test_name = (
                                failure["test"].split("::")[-1]
                                if "::" in failure["test"]
                                else failure["test"]
                            )
                            injection_parts.append(f"  - {test_name[:50]}")

            # Coverage summary
            coverage_data = test_results.get("coverage", {})
            for lang, cov in coverage_data.items():
                if "percentage" in cov:
                    emoji = (
                        "🟢"
                        if cov["percentage"] > 80
                        else "🟡"
                        if cov["percentage"] > 60
                        else "🔴"
                    )
                    injection_parts.append(
                        f"{emoji} {lang.capitalize()} coverage: {cov['percentage']:.1f}%",
                    )

            # Context information
            context = status["context"]
            patterns = context["patterns"]

            # Recent activity (if relevant)
            recent_files = context["recent_files"][:5]
            if recent_files:
                current_time = time.time()
                injection_parts.append("Recent files:")
                for file_info in recent_files:
                    try:
                        path = Path(file_info["path"])
                        time_ago = max(
                            0,
                            int((current_time - file_info["accessed"]) / 60),
                        )
                        try:
                            rel_path = path.relative_to(self.project_dir)
                            injection_parts.append(f"  {rel_path} ({time_ago}m ago)")
                        except ValueError:
                            injection_parts.append(f"  {path.name} ({time_ago}m ago)")
                    except (KeyError, OSError, ValueError):
                        continue

            # Development context
            if patterns["primary_languages"]:
                injection_parts.append(
                    f"Languages: {', '.join(patterns['primary_languages'])}",
                )

            if patterns["development_phase"] != "development":
                injection_parts.append(f"Phase: {patterns['development_phase']}")

            if patterns["focus_areas"]:
                injection_parts.append(f"Focus: {', '.join(patterns['focus_areas'])}")

            if injection_parts:
                return f"<system-monitor>\n{chr(10).join(injection_parts)}\n</system-monitor>\n"
            else:
                # Return minimal status if everything is normal
                return f"<system-monitor>System healthy (CPU: {resources['cpu']['system_percent']:.1f}%, MEM: {resources['memory']['system_percent']:.1f}%)</system-monitor>\n"

        except Exception as e:
            return f"<!-- System monitoring error: {str(e)} -->\n"


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================


async def get_runtime_monitoring_injection() -> str:
    """Backward compatibility for runtime monitoring."""
    monitor = SystemMonitor()
    try:
        resources = monitor.get_system_resources()
        processes = monitor.get_process_info()
        network = await monitor.get_network_status()
        files = monitor.get_file_system_activity()

        injection_parts = []

        # Resource warnings
        if resources["cpu"]["system_percent"] > 80:
            injection_parts.append(f"⚠️ HIGH CPU: {resources['cpu']['system_percent']}%")
        if resources["memory"]["system_percent"] > 85:
            injection_parts.append(
                f"⚠️ HIGH MEMORY: {resources['memory']['system_percent']}%",
            )
        if resources["disk"]["usage_percent"] > 90:
            injection_parts.append(
                f"⚠️ LOW DISK: {resources['disk']['usage_percent']}% used",
            )

        # Network issues
        network_issues = []
        if not network["can_reach_github"]:
            network_issues.append("GitHub")
        if not network["can_reach_pypi"]:
            network_issues.append("PyPI")
        if not network["can_reach_npm"]:
            network_issues.append("NPM")
        if network_issues:
            injection_parts.append(f"⚠️ UNREACHABLE: {', '.join(network_issues)}")

        # Heavy processes
        heavy_procs = [p for p in processes["relevant_processes"] if p["cpu"] > 50]
        if heavy_procs:
            injection_parts.append(
                f"⚠️ HIGH CPU PROCESSES: {', '.join(p['name'] for p in heavy_procs)}",
            )

        # Recently modified files
        if files["recently_modified"]:
            recent = files["recently_modified"][:3]
            injection_parts.append(
                f"Recent activity: {', '.join(f['path'] for f in recent)}",
            )

        if injection_parts:
            return f"<runtime-monitoring>\n{chr(10).join(injection_parts)}\n</runtime-monitoring>\n"
        else:
            return f"<runtime-monitoring>System resources normal (CPU: {resources['cpu']['system_percent']:.1f}%, MEM: {resources['memory']['system_percent']:.1f}%)</runtime-monitoring>\n"

    except Exception as e:
        return f"<!-- Runtime monitoring error: {str(e)} -->\n"


async def get_test_status_injection(prompt: str, project_dir: str) -> str:
    """Backward compatibility for test status injection."""
    monitor = SystemMonitor(project_dir)

    try:
        test_results = monitor.find_test_results()
        ci_status = monitor.get_ci_status()

        if not test_results and not ci_status:
            return ""

        injection_parts = []

        # Test results summary
        for framework, results in test_results.items():
            if framework == "coverage":
                continue

            if isinstance(results, dict) and "passed" in results:
                total = (
                    results["passed"] + results["failed"] + results.get("skipped", 0)
                )
                status = "✅" if results["failed"] == 0 else "❌"
                injection_parts.append(
                    f"{status} {framework.upper()}: {results['passed']}/{total} passed",
                )

                # Add failure details
                if results.get("failures"):
                    injection_parts.append("  Recent failures:")
                    for failure in results["failures"]:
                        test_name = (
                            failure["test"].split("::")[-1]
                            if "::" in failure["test"]
                            else failure["test"]
                        )
                        injection_parts.append(f"  - {test_name[:50]}")

        # Coverage summary
        coverage_data = test_results.get("coverage", {})
        for lang, cov in coverage_data.items():
            if "percentage" in cov:
                emoji = (
                    "🟢"
                    if cov["percentage"] > 80
                    else "🟡"
                    if cov["percentage"] > 60
                    else "🔴"
                )
                injection_parts.append(
                    f"{emoji} {lang.capitalize()} coverage: {cov['percentage']:.1f}%",
                )

                # Low coverage files
                if cov.get("uncovered_files"):
                    injection_parts.append("  Low coverage files:")
                    for file_info in cov["uncovered_files"][:3]:
                        filename = Path(file_info["file"]).name
                        injection_parts.append(
                            f"  - {filename}: {file_info['coverage']:.0f}%",
                        )

        # CI status
        if ci_status:
            injection_parts.append(f"CI/CD: {', '.join(ci_status.keys())}")

        if injection_parts:
            # Check if tests mentioned in prompt
            test_keywords = [
                "test",
                "coverage",
                "pytest",
                "jest",
                "unit",
                "integration",
            ]
            is_test_related = any(
                keyword in prompt.lower() for keyword in test_keywords
            )

            if is_test_related or any(
                "❌" in part or "🔴" in part for part in injection_parts
            ):
                return (
                    f"<test-status>\n{chr(10).join(injection_parts)}\n</test-status>\n"
                )
            else:
                return "<test-status>Tests passing, coverage healthy</test-status>\n"

        return ""

    except Exception as e:
        return f"<!-- Test status error: {str(e)} -->\n"


async def get_context_history_injection(prompt: str, project_dir: str) -> str:
    """Backward compatibility for context history injection."""
    monitor = SystemMonitor(project_dir)

    try:
        recent_files = monitor.get_recent_file_access()[:10]
        recent_commands = monitor.get_recent_commands()[:8]
        patterns = monitor.get_workflow_patterns()

        if not recent_files and not recent_commands:
            return ""

        injection_parts = []

        # Recent files
        if recent_files:
            injection_parts.append("Recent files:")
            current_time = time.time()

            for file_info in recent_files[:5]:
                try:
                    if "path" not in file_info or "accessed" not in file_info:
                        continue

                    path = Path(file_info["path"])
                    time_ago = max(0, int((current_time - file_info["accessed"]) / 60))

                    try:
                        rel_path = path.relative_to(monitor.project_dir)
                        injection_parts.append(f"  {rel_path} ({time_ago}m ago)")
                    except ValueError:
                        injection_parts.append(f"  {path.name} ({time_ago}m ago)")

                except (KeyError, OSError, ValueError):
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
                f"Languages: {', '.join(patterns['primary_languages'])}",
            )

        if patterns["development_phase"] != "development":
            injection_parts.append(f"Phase: {patterns['development_phase']}")

        if patterns["focus_areas"]:
            injection_parts.append(f"Focus: {', '.join(patterns['focus_areas'])}")

        if injection_parts:
            return f"<context-history>\n{chr(10).join(injection_parts)}\n</context-history>\n"
        else:
            return ""

    except Exception as e:
        return f"<!-- Context history error: {str(e)} -->\n"


# Main function for unified system monitoring
async def get_system_monitoring_injection(
    prompt: str = "",
    project_dir: Optional[str] = None,
) -> str:
    """Main entry point for unified system monitoring injection."""
    monitor = SystemMonitor(project_dir)
    return await monitor.generate_monitoring_injection(prompt)
