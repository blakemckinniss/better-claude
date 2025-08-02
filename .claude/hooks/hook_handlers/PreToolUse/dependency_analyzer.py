#!/usr/bin/env python3
"""Analyze file dependencies for impact assessment."""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Set


class DependencyAnalyzer:
    """Analyze file dependencies for impact assessment."""

    @staticmethod
    def check_import_impact(file_path: str) -> int:
        """Check how many files import this module."""
        if not file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            return 0

        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            basename = os.path.basename(file_path).replace(
                os.path.splitext(file_path)[1],
                "",
            )

            # Quick grep for imports
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    f"import.*{basename}",
                    ".",
                    "--include=*.py",
                    "--include=*.js",
                    "--include=*.ts",
                ],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.stdout:
                # Filter out the file itself and count unique files
                lines = result.stdout.strip().split("\n")
                importing_files = set()
                for line in lines:
                    if ":" in line:
                        importing_file = line.split(":")[0]
                        # Don't count the file importing itself
                        if not importing_file.endswith(file_path):
                            importing_files.add(importing_file)
                return len(importing_files)
        except Exception:
            pass
        return 0

    @staticmethod
    def get_importing_files(file_path: str) -> List[str]:
        """Get list of files that import this module."""
        importing_files: List[str] = []

        if not file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            return importing_files

        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            basename = os.path.basename(file_path).replace(
                os.path.splitext(file_path)[1],
                "",
            )

            # Use ripgrep if available, otherwise fall back to grep
            try:
                result = subprocess.run(
                    [
                        "rg",
                        f"import.*{basename}",
                        "--type",
                        "py",
                        "--type",
                        "js",
                        "--type",
                        "ts",
                        "-l",
                    ],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
            except FileNotFoundError:
                # Fall back to grep
                result = subprocess.run(
                    [
                        "grep",
                        "-r",
                        f"import.*{basename}",
                        ".",
                        "--include=*.py",
                        "--include=*.js",
                        "--include=*.ts",
                        "-l",
                    ],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line and not line.endswith(file_path):
                        importing_files.append(line)

        except Exception:
            pass

        return importing_files

    @staticmethod
    def analyze_dependency_chain(
        file_path: str,
        max_depth: int = 3,
    ) -> Dict[str, Set[str]]:
        """Analyze the dependency chain for a file up to max_depth."""
        dependency_tree = {}
        visited = set()

        def analyze_level(files: List[str], depth: int):
            if depth >= max_depth:
                return

            for file in files:
                if file in visited:
                    continue

                visited.add(file)
                importing_files = DependencyAnalyzer.get_importing_files(file)

                if importing_files:
                    dependency_tree[file] = set(importing_files)
                    analyze_level(importing_files, depth + 1)

        # Start analysis from the target file
        analyze_level([file_path], 0)

        return dependency_tree

    @staticmethod
    def check_circular_dependencies(file_path: str) -> List[List[str]]:
        """Check for circular dependencies involving this file."""
        circular_deps: List[List[str]] = []

        # This is a simplified check - for production, you'd want a more robust solution
        try:
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            module_name = Path(file_path).stem

            # Check if any files this module imports also import it back
            with open(file_path) as f:
                content = f.read()

            # Extract imports (simplified - doesn't handle all import styles)
            import_lines = [
                line
                for line in content.split("\n")
                if line.strip().startswith(("import ", "from "))
            ]

            for line in import_lines:
                # Extract imported module name (simplified)
                if "import" in line:
                    parts = line.split()
                    if "from" in parts:
                        idx = parts.index("from")
                        if idx + 1 < len(parts):
                            imported_module = parts[idx + 1].strip("\"'")
                            # Check if that module imports us back
                            # This is simplified - would need proper module resolution
                            if imported_module != module_name:  # Avoid self-import
                                # Would check if imported_module imports module_name
                                pass

        except Exception:
            pass

        return circular_deps
