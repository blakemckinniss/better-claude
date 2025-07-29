"""Code smell detection for proactive quality warnings."""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeSmellDetector:
    """Detects common code smells and quality issues."""

    def __init__(self):
        # Thresholds for various metrics
        self.thresholds = {
            "max_function_length": 50,
            "max_function_complexity": 10,
            "max_parameters": 5,
            "max_file_length": 500,
            "max_class_methods": 20,
            "max_imports": 15,
            "min_docstring_length": 10,
            "duplicate_threshold": 0.8,  # 80% similarity
        }

        # Common code smell patterns
        self.smell_patterns = {
            "magic_numbers": r"\b(?<!\.)\d{2,}(?!\.)\b(?![a-zA-Z])",  # Numbers > 9 not in strings
            "todo_fixme": r"#\s*(TODO|FIXME|HACK|XXX|BUG)",
            "broad_except": r"except\s*(?:\(\s*\))?\s*:",
            "print_statements": r"^\s*print\s*\(",
            "long_lines": r"^.{120,}$",
            "multiple_returns": r"return\s+",
            "global_usage": r"\bglobal\s+\w+",
            "eval_usage": r"\b(eval|exec)\s*\(",
        }

    def _analyze_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze individual lines for smells."""
        line_smells = []

        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > self.thresholds["max_file_length"]:
                line_smells.append(
                    {
                        "line": i,
                        "type": "long_line",
                        "severity": "minor",
                        "message": f"Line too long ({len(line)} chars)",
                    }
                )

            # Check for patterns
            for smell_name, pattern in self.smell_patterns.items():
                if re.search(pattern, line):
                    severity = (
                        "major"
                        if smell_name in ["eval_usage", "broad_except"]
                        else "minor"
                    )
                    line_smells.append(
                        {
                            "line": i,
                            "type": smell_name,
                            "severity": severity,
                            "message": f"Found {smell_name.replace('_', ' ')}",
                        }
                    )

        return line_smells

    def _analyze_file_structure(
        self, tree: ast.AST, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze file-level structure issues."""
        file_smells = []

        # Count imports
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        if len(imports) > self.thresholds["max_imports"]:
            file_smells.append(
                {
                    "type": "too_many_imports",
                    "severity": "moderate",
                    "message": f"Too many imports ({len(imports)})",
                }
            )

        # Check file length
        if len(lines) > self.thresholds["max_file_length"]:
            file_smells.append(
                {
                    "type": "long_file",
                    "severity": "moderate",
                    "message": f"File too long ({len(lines)} lines)",
                }
            )

        # Check for module docstring
        if not ast.get_docstring(tree):
            file_smells.append(
                {
                    "type": "missing_module_docstring",
                    "severity": "minor",
                    "message": "Module lacks docstring",
                }
            )

        return file_smells

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _analyze_functions(
        self, tree: ast.AST, lines: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze function-level code smells."""
        function_smells = defaultdict(list)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name

                # Check function length
                func_lines = node.end_lineno - node.lineno + 1
                if func_lines > self.thresholds["max_function_length"]:
                    function_smells[func_name].append(
                        {
                            "type": "long_function",
                            "severity": "major",
                            "message": f"Function too long ({func_lines} lines)",
                            "line": node.lineno,
                        }
                    )

                # Check parameter count
                num_params = len(node.args.args) + len(node.args.kwonlyargs)
                if num_params > self.thresholds["max_parameters"]:
                    function_smells[func_name].append(
                        {
                            "type": "too_many_parameters",
                            "severity": "moderate",
                            "message": f"Too many parameters ({num_params})",
                            "line": node.lineno,
                        }
                    )

                # Check complexity
                complexity = self._calculate_complexity(node)
                if complexity > self.thresholds["max_function_complexity"]:
                    function_smells[func_name].append(
                        {
                            "type": "high_complexity",
                            "severity": "major",
                            "message": f"High cyclomatic complexity ({complexity})",
                            "line": node.lineno,
                        }
                    )

                # Check for docstring
                if not ast.get_docstring(node):
                    function_smells[func_name].append(
                        {
                            "type": "missing_docstring",
                            "severity": "minor",
                            "message": "Function lacks docstring",
                            "line": node.lineno,
                        }
                    )

                # Check for multiple returns
                returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                if len(returns) > 3:
                    function_smells[func_name].append(
                        {
                            "type": "multiple_returns",
                            "severity": "moderate",
                            "message": f"Multiple return statements ({len(returns)})",
                            "line": node.lineno,
                        }
                    )

        return dict(function_smells)

    def _analyze_classes(
        self, tree: ast.AST, lines: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze class-level code smells."""
        class_smells = defaultdict(list)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                # Count methods
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > self.thresholds["max_class_methods"]:
                    class_smells[class_name].append(
                        {
                            "type": "god_class",
                            "severity": "major",
                            "message": f"Too many methods ({len(methods)})",
                            "line": node.lineno,
                        }
                    )

                # Check for docstring
                if not ast.get_docstring(node):
                    class_smells[class_name].append(
                        {
                            "type": "missing_docstring",
                            "severity": "minor",
                            "message": "Class lacks docstring",
                            "line": node.lineno,
                        }
                    )

                # Check for class variables without type hints
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and item.annotation is None:
                        class_smells[class_name].append(
                            {
                                "type": "missing_type_annotation",
                                "severity": "minor",
                                "message": "Class variable lacks type annotation",
                                "line": item.lineno,
                            }
                        )

        return dict(class_smells)

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file for code smells."""
        smells = {
            "file_level": [],
            "function_level": defaultdict(list),
            "class_level": defaultdict(list),
            "line_level": [],
        }

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Line-level analysis
            smells["line_level"] = self._analyze_lines(lines)

            # AST-based analysis
            try:
                tree = ast.parse(content)
                smells["file_level"].extend(self._analyze_file_structure(tree, lines))
                smells["function_level"] = self._analyze_functions(tree, lines)
                smells["class_level"] = self._analyze_classes(tree, lines)
            except SyntaxError:
                smells["file_level"].append(
                    {
                        "type": "syntax_error",
                        "severity": "critical",
                        "message": "File contains syntax errors",
                    }
                )

        except Exception as e:
            smells["file_level"].append(
                {
                    "type": "read_error",
                    "severity": "critical",
                    "message": f"Could not analyze file: {str(e)}",
                }
            )

        return smells

    def get_smell_summary(self, smells: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of detected smells."""
        summary = {
            "total_smells": 0,
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "critical_issues": [],
        }

        # Count file-level smells
        for smell in smells["file_level"]:
            summary["total_smells"] += 1
            summary["by_severity"][smell["severity"]] += 1
            summary["by_type"][smell["type"]] += 1
            if smell["severity"] == "critical":
                summary["critical_issues"].append(smell)

        # Count function-level smells
        for func_smells in smells["function_level"].values():
            for smell in func_smells:
                summary["total_smells"] += 1
                summary["by_severity"][smell["severity"]] += 1
                summary["by_type"][smell["type"]] += 1
                if smell["severity"] == "critical":
                    summary["critical_issues"].append(smell)

        # Count class-level smells
        for class_smells in smells["class_level"].values():
            for smell in class_smells:
                summary["total_smells"] += 1
                summary["by_severity"][smell["severity"]] += 1
                summary["by_type"][smell["type"]] += 1
                if smell["severity"] == "critical":
                    summary["critical_issues"].append(smell)

        # Count line-level smells
        for smell in smells["line_level"]:
            summary["total_smells"] += 1
            summary["by_severity"][smell["severity"]] += 1
            summary["by_type"][smell["type"]] += 1

        return {
            "total_smells": summary["total_smells"],
            "by_severity": dict(summary["by_severity"]),
            "by_type": dict(summary["by_type"]),
            "critical_issues": summary["critical_issues"],
            "quality_score": max(
                0, 100 - (summary["total_smells"] * 2)
            ),  # Simple quality score
        }


def detect_smells_for_prompt(
    prompt: str, project_root: str = "."
) -> Optional[Dict[str, Any]]:
    """Detect code smells for files mentioned in the prompt."""
    # Extract file paths from prompt
    file_pattern = r'(?:^|[\s"\'])([\w/]+\.py)(?:$|[\s"\'])'
    mentioned_files = re.findall(file_pattern, prompt)

    if not mentioned_files:
        return None

    detector = CodeSmellDetector()
    all_smells = {}

    for file_path in mentioned_files:
        if Path(file_path).exists():
            smells = detector.analyze_file(file_path)
            summary = detector.get_smell_summary(smells)
            all_smells[file_path] = {
                "smells": smells,
                "summary": summary,
            }

    if not all_smells:
        return None

    # Generate overall summary
    total_smells = sum(data["summary"]["total_smells"] for data in all_smells.values())
    critical_count = sum(
        len(data["summary"]["critical_issues"]) for data in all_smells.values()
    )

    return {
        "files_analyzed": list(all_smells.keys()),
        "file_details": all_smells,
        "overall_summary": {
            "total_smells": total_smells,
            "critical_issues": critical_count,
            "files_with_issues": len(all_smells),
            "average_quality_score": (
                sum(data["summary"]["quality_score"] for data in all_smells.values())
                / len(all_smells)
                if all_smells
                else 0
            ),
        },
    }
