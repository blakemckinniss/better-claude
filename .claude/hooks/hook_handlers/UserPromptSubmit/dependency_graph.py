"""Dependency graph analysis for understanding change impact radius."""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class DependencyGraphAnalyzer:
    """Analyzes code dependencies to understand impact of changes."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.import_cache: Dict[str, List[str]] = {}

    def analyze_file_imports(self, file_path: str) -> List[str]:
        """Extract imports from a Python file."""
        if file_path in self.import_cache:
            return self.import_cache[file_path]

        imports = []
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        if module:
                            imports.append(f"{module}.{alias.name}")
                        else:
                            imports.append(alias.name)

        except Exception:
            # Fallback to regex if AST parsing fails
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Simple import patterns
                import_pattern = r"(?:from\s+(\S+)\s+)?import\s+([^#\n]+)"
                for match in re.finditer(import_pattern, content):
                    from_module = match.group(1)
                    import_items = match.group(2)

                    if from_module:
                        imports.append(from_module)

                    # Handle multiple imports
                    for item in import_items.split(","):
                        item = item.strip().split(" as ")[0]
                        if item and item != "*":
                            imports.append(item)

            except Exception:
                pass

        self.import_cache[file_path] = imports
        return imports

    def build_dependency_graph(self, target_files: Optional[List[str]] = None):
        """Build dependency graph for Python files."""
        if target_files:
            files_to_analyze = target_files
        else:
            # Find all Python files
            files_to_analyze = []
            for root, _, files in os.walk(self.project_root):
                for file in files:
                    if file.endswith(".py"):
                        files_to_analyze.append(os.path.join(root, file))

        for file_path in files_to_analyze:
            rel_path = os.path.relpath(file_path, self.project_root)
            imports = self.analyze_file_imports(file_path)

            # Convert imports to file paths
            for imp in imports:
                # Try to resolve import to local file
                possible_paths = [
                    f"{imp.replace('.', '/')}.py",
                    f"{imp.replace('.', '/')}/__init__.py",
                    f"{imp.split('.')[0]}.py",
                ]

                for possible_path in possible_paths:
                    full_path = self.project_root / possible_path
                    if full_path.exists():
                        dep_rel_path = os.path.relpath(full_path, self.project_root)
                        self.dependency_graph[rel_path].add(dep_rel_path)
                        self.reverse_graph[dep_rel_path].add(rel_path)
                        break

    def _find_critical_paths(
        self, changed_file: str, impacted_files: Set[Tuple[str, int]]
    ) -> List[str]:
        """Identify critical files in the impact chain."""
        critical = []

        # Files that appear in many dependency chains are critical
        impact_count = defaultdict(int)
        for file, _ in impacted_files:
            impact_count[file] += len(self.reverse_graph.get(file, []))

        # Top 5 most impacted files
        sorted_impacts = sorted(impact_count.items(), key=lambda x: x[1], reverse=True)
        critical = [file for file, _ in sorted_impacts[:5] if file != changed_file]

        return critical

    def get_impact_radius(self, file_path: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get files that would be impacted by changes to the given file."""
        rel_path = os.path.relpath(file_path, self.project_root)

        # Direct dependencies (files that import this file)
        direct_deps = self.reverse_graph.get(rel_path, set())

        # Transitive dependencies
        all_impacted = set()
        to_check = [(dep, 1) for dep in direct_deps]
        checked = {rel_path}

        while to_check:
            current_file, depth = to_check.pop(0)
            if current_file in checked or depth > max_depth:
                continue

            checked.add(current_file)
            all_impacted.add((current_file, depth))

            # Add dependencies of this file
            for dep in self.reverse_graph.get(current_file, []):
                if dep not in checked:
                    to_check.append((dep, depth + 1))

        # Categorize by depth
        impact_by_depth = defaultdict(list)
        for file, depth in all_impacted:
            impact_by_depth[depth].append(file)

        return {
            "direct_dependencies": list(direct_deps),
            "total_impacted": len(all_impacted),
            "impact_by_depth": dict(impact_by_depth),
            "critical_paths": self._find_critical_paths(rel_path, all_impacted),
        }

    def get_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """Get what files this file depends on."""
        rel_path = os.path.relpath(file_path, self.project_root)

        return {
            "imports": list(self.dependency_graph.get(rel_path, [])),
            "imported_by": list(self.reverse_graph.get(rel_path, [])),
            "dependency_count": len(self.dependency_graph.get(rel_path, [])),
            "usage_count": len(self.reverse_graph.get(rel_path, [])),
        }


def analyze_dependencies_for_prompt(
    prompt: str, project_root: str = "."
) -> Optional[Dict[str, Any]]:
    """Analyze dependencies for files mentioned in the prompt."""
    # Extract file paths from prompt
    file_pattern = r'(?:^|[\s"\'])([\w/]+\.py)(?:$|[\s"\'])'
    mentioned_files = re.findall(file_pattern, prompt)

    if not mentioned_files:
        return None

    analyzer = DependencyGraphAnalyzer(project_root)

    # Build graph for mentioned files and their dependencies
    files_to_analyze = set(mentioned_files)
    for file in mentioned_files:
        if os.path.exists(file):
            # Add files that import or are imported by this file
            imports = analyzer.analyze_file_imports(file)
            files_to_analyze.update(imports)

    analyzer.build_dependency_graph(list(files_to_analyze))

    # Analyze impact for each mentioned file
    impact_analysis = {}
    for file in mentioned_files:
        if os.path.exists(file):
            impact_analysis[file] = analyzer.get_impact_radius(file)

    return {
        "mentioned_files": mentioned_files,
        "impact_analysis": impact_analysis,
        "total_files_affected": sum(
            analysis["total_impacted"] for analysis in impact_analysis.values()
        ),
    }
