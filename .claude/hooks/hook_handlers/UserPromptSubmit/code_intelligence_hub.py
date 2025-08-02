"""Code Intelligence Hub - Unified AST analysis and LSP diagnostics module.

This module consolidates tree-sitter AST analysis and Language Server Protocol
diagnostics to provide comprehensive code intelligence for enhanced development workflow.
"""

import asyncio
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import graceful fallbacks
try:
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


class CodeIntelligenceHub:
    """Unified code intelligence analyzer combining AST analysis and diagnostics."""

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.project_name = self.project_dir.name

        # Diagnostics storage
        self.diagnostics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._diagnostic_cache: Dict[str, Any] = {}

        # Tree-sitter configurations
        self.query_templates = {
            "find_functions": {
                "python": "(function_definition name: (identifier) @name) @func",
                "javascript": "(function_declaration name: (identifier) @name) @func",
                "typescript": "[(function_declaration name: (identifier) @name) (method_definition key: (property_identifier) @name)] @func",
                "go": "(function_declaration name: (identifier) @name) @func",
                "rust": "(function_item name: (identifier) @name) @func",
            },
            "find_classes": {
                "python": "(class_definition name: (identifier) @name) @class",
                "javascript": "(class_declaration name: (identifier) @name) @class",
                "typescript": "(class_declaration name: (identifier) @name) @class",
                "java": "(class_declaration name: (identifier) @name) @class",
                "rust": "(struct_item name: (type_identifier) @name) @struct",
            },
            "find_imports": {
                "python": "[(import_statement) (import_from_statement)] @import",
                "javascript": "[(import_statement) (export_statement)] @import",
                "go": "(import_declaration) @import",
                "rust": "(use_declaration) @import",
            },
            "find_error_handling": {
                "python": "(try_statement) @try",
                "javascript": "(try_statement) @try",
                "go": '(if_statement condition: (binary_expression left: (identifier) @err (#eq? @err "err"))) @error_check',
                "rust": "(match_expression) @match",
            },
            "find_tests": {
                "python": '(function_definition name: (identifier) @name (#match? @name "^test")) @test',
                "javascript": '(call_expression function: (identifier) @func (#match? @func "^(test|it|describe)")) @test',
                "go": '(function_declaration name: (identifier) @name (#match? @name "^Test")) @test',
                "rust": '(attribute_item (meta_item (identifier) @attr (#eq? @attr "test"))) @test_attr',
            },
            "find_todos": {
                "all": '(comment) @comment (#match? @comment "(TODO|FIXME|XXX|HACK|BUG)")',
            },
            "find_long_functions": {
                "all": '(function_definition body: (block) @body (#match? @body ".{500,}")) @long_func',
            },
            "find_nested_conditions": {
                "all": "(if_statement condition: (if_statement)) @nested",
            },
            "find_complexity": {
                "python": "[(if_statement) (for_statement) (while_statement) (try_statement)] @complexity",
                "javascript": "[(if_statement) (for_statement) (while_statement) (try_statement)] @complexity",
                "go": "[(if_statement) (for_statement) (range_clause)] @complexity",
                "rust": "[(if_expression) (loop_expression) (for_expression) (match_expression)] @complexity",
            },
        }

        # Intent patterns for code analysis
        self.intent_patterns = {
            "refactor": {
                "patterns": [
                    r"refactor",
                    r"improve",
                    r"clean",
                    r"optimize",
                    r"restructure",
                    r"simplify",
                ],
                "suggested_queries": [
                    "find_long_functions",
                    "find_nested_conditions",
                    "find_todos",
                    "find_complexity",
                ],
                "tools": [
                    "find_similar_code",
                    "analyze_complexity",
                    "get_symbols_overview",
                ],
                "diagnostics_focus": ["complexity", "duplication", "maintainability"],
            },
            "debug": {
                "patterns": [
                    r"debug",
                    r"bug",
                    r"error",
                    r"issue",
                    r"problem",
                    r"fix",
                    r"broken",
                    r"failing",
                ],
                "suggested_queries": [
                    "find_error_handling",
                    "find_functions",
                    "find_tests",
                ],
                "tools": [
                    "find_symbol",
                    "find_referencing_symbols",
                    "get_dependencies",
                ],
                "diagnostics_focus": ["error", "type_error", "runtime_error"],
            },
            "implement": {
                "patterns": [
                    r"implement",
                    r"add",
                    r"create",
                    r"build",
                    r"feature",
                    r"new",
                    r"develop",
                ],
                "suggested_queries": ["find_classes", "find_functions", "find_imports"],
                "tools": [
                    "get_symbols_overview",
                    "find_similar_code",
                    "get_file_contents",
                ],
                "diagnostics_focus": ["missing_implementation", "incomplete"],
            },
            "analyze": {
                "patterns": [
                    r"analyze",
                    r"understand",
                    r"explain",
                    r"how does",
                    r"what does",
                    r"explore",
                ],
                "suggested_queries": [
                    "find_functions",
                    "find_classes",
                    "find_imports",
                    "find_complexity",
                ],
                "tools": ["get_ast", "get_symbols_overview", "analyze_complexity"],
                "diagnostics_focus": ["all"],
            },
            "test": {
                "patterns": [
                    r"test",
                    r"coverage",
                    r"unit test",
                    r"integration test",
                    r"e2e",
                    r"pytest",
                    r"jest",
                ],
                "suggested_queries": ["find_tests", "find_functions", "find_classes"],
                "tools": [
                    "find_symbol",
                    "find_referencing_symbols",
                    "analyze_complexity",
                ],
                "diagnostics_focus": ["test_failure", "coverage", "assertion"],
            },
            "type_check": {
                "patterns": [
                    r"type",
                    r"typing",
                    r"annotation",
                    r"mypy",
                    r"pyright",
                    r"typescript",
                ],
                "suggested_queries": ["find_functions", "find_classes"],
                "tools": ["get_ast", "find_symbol"],
                "diagnostics_focus": ["type_error", "type_annotation"],
            },
            "lint": {
                "patterns": [
                    r"lint",
                    r"format",
                    r"style",
                    r"clean",
                    r"ruff",
                    r"eslint",
                    r"clippy",
                ],
                "suggested_queries": ["find_todos", "find_complexity"],
                "tools": ["analyze_complexity"],
                "diagnostics_focus": ["style", "lint", "formatting"],
            },
        }

        # Language detection patterns
        self.language_patterns = {
            "python": r"\.py\b|python|def\s|class\s|import\s|from\s.*import|__init__|self\.|pip|pytest|mypy|ruff",
            "javascript": r"\.js\b|javascript|function\s|const\s|let\s|var\s|=>\s|npm|node|react|eslint",
            "typescript": r"\.ts\b|typescript|interface\s|type\s|:\s*\w+\s*=|enum\s|namespace|tsc",
            "go": r"\.go\b|golang|func\s|package\s|import\s\(|go\s+mod|gofmt",
            "rust": r"\.rs\b|rust|fn\s|struct\s|impl\s|cargo|clippy|rustfmt",
            "java": r"\.java\b|java|public\s+class|package\s|import\s+java",
            "cpp": r"\.(cpp|cc|cxx)\b|c\+\+|#include|namespace\s|std::",
            "c": r"\.c\b|#include|stdio\.h|malloc|printf",
        }

    async def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Comprehensive prompt analysis combining AST and diagnostics insights."""
        # Basic analysis
        intent, confidence = self.detect_intent(prompt)
        languages = self.detect_languages(prompt)
        files = self.extract_file_paths(prompt)
        symbols = self.extract_symbols(prompt)

        # Collect diagnostics asynchronously
        diagnostics_task = self.collect_relevant_diagnostics(prompt)

        # Generate AST recommendations
        ast_analysis = self.generate_ast_analysis(
            intent,
            languages,
            files,
            symbols,
            confidence,
        )

        # Wait for diagnostics
        try:
            diagnostics_analysis = await asyncio.wait_for(
                diagnostics_task,
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            diagnostics_analysis = {
                "summary": "Diagnostics collection timed out",
                "details": {},
            }

        return {
            "intent": intent,
            "confidence": confidence,
            "languages": languages,
            "files": files,
            "symbols": symbols,
            "ast_analysis": ast_analysis,
            "diagnostics": diagnostics_analysis,
            "recommendations": self.generate_unified_recommendations(
                intent,
                languages,
                files,
                symbols,
                ast_analysis,
                diagnostics_analysis,
            ),
        }

    def detect_intent(self, prompt: str) -> Tuple[str, float]:
        """Detect the primary development intent from the prompt."""
        prompt_lower = prompt.lower()
        intent_scores = {}

        for intent, config in self.intent_patterns.items():
            score = 0
            for pattern in config["patterns"]:
                matches = len(re.findall(pattern, prompt_lower))
                score += matches

            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return "analyze", 0.5  # Default intent

        # Get highest scoring intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        confidence = (
            best_intent[1] / sum(intent_scores.values())
            if sum(intent_scores.values()) > 0
            else 0
        )

        return best_intent[0], min(confidence, 1.0)

    def detect_languages(self, prompt: str) -> List[str]:
        """Detect programming languages mentioned in the prompt."""
        detected = []

        for lang, pattern in self.language_patterns.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                detected.append(lang)

        # Default to Python if no language detected and we're in a Python project
        if not detected:
            if (self.project_dir / "pyproject.toml").exists() or (
                self.project_dir / "requirements.txt"
            ).exists():
                detected = ["python"]
            else:
                detected = ["python"]  # Conservative default

        return detected

    def extract_file_paths(self, prompt: str) -> List[str]:
        """Extract file paths mentioned in the prompt."""
        patterns = [
            r'(?:^|[\s"\'])([\w\-/\.]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|hpp))(?:$|[\s"\'])',
            r"(?:file|path):\s*([^\s]+)",
            r"in\s+([^\s]+\.(?:py|js|ts|go|rs|java|cpp|c|h))",
            r"`([^`]+\.(?:py|js|ts|go|rs|java|cpp|c|h))`",
        ]

        files = []
        for pattern in patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            files.extend(matches)

        return list(set(files))  # Remove duplicates

    def extract_symbols(self, prompt: str) -> List[Tuple[str, str]]:
        """Extract function/class names mentioned in the prompt."""
        symbols = []

        # Function patterns
        func_patterns = [
            r"function\s+(\w+)",
            r"def\s+(\w+)",
            r"func\s+(\w+)",
            r"fn\s+(\w+)",
            r"method\s+(\w+)",
            r"(\w+)\s*\(\s*\)\s*[{:]",
            r"(\w+)\s+function",
            r"the\s+(\w+)\s+function",
            r"`(\w+)\(`",  # Markdown code references
        ]

        for pattern in func_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if len(match) > 2 and match.isidentifier():  # Valid identifier
                    symbols.append((match, "function"))

        # Class patterns
        class_patterns = [
            r"class\s+(\w+)",
            r"type\s+(\w+)",
            r"struct\s+(\w+)",
            r"interface\s+(\w+)",
            r"enum\s+(\w+)",
            r"the\s+(\w+)\s+class",
            r"`(\w+)`(?:\s+class)?",
        ]

        for pattern in class_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if len(match) > 2 and match.isidentifier():
                    symbols.append((match, "class"))

        # Remove duplicates while preserving order
        seen = set()
        unique_symbols = []
        for symbol, symbol_type in symbols:
            key = (symbol.lower(), symbol_type)
            if key not in seen:
                seen.add(key)
                unique_symbols.append((symbol, symbol_type))

        return unique_symbols

    def generate_ast_analysis(
        self,
        intent: str,
        languages: List[str],
        files: List[str],
        symbols: List[Tuple[str, str]],
        confidence: float,
    ) -> Dict[str, Any]:
        """Generate AST-based analysis recommendations."""
        self.intent_patterns.get(intent, {})

        analysis = {
            "tree_sitter_available": HAS_TREE_SITTER,
            "suggested_queries": self.generate_queries(intent, languages),
            "tool_recommendations": self.generate_tool_recommendations(
                intent,
                languages,
                files,
                symbols,
            ),
            "workflow": self.generate_workflow_suggestion(intent, confidence),
            "complexity_hints": self.get_complexity_hints(
                prompt_text=" ".join([intent] + languages),
            ),
        }

        return analysis

    def generate_queries(self, intent: str, languages: List[str]) -> Dict[str, str]:
        """Generate tree-sitter queries based on intent and languages."""
        intent_config = self.intent_patterns.get(intent, {})
        suggested_queries = intent_config.get("suggested_queries", [])

        queries = {}

        for query_type in suggested_queries:
            if query_type in self.query_templates:
                query_config = self.query_templates[query_type]

                # Get queries for detected languages
                for lang in languages:
                    if lang in query_config:
                        query = query_config[lang]
                        queries[f"{lang}_{query_type}"] = query
                    elif "all" in query_config:
                        query = query_config["all"]
                        queries[f"{lang}_{query_type}"] = query

        return queries

    def generate_tool_recommendations(
        self,
        intent: str,
        languages: List[str],
        files: List[str],
        symbols: List[Tuple[str, str]],
    ) -> List[str]:
        """Generate specific tree-sitter tool recommendations."""
        recommendations = []
        intent_config = self.intent_patterns.get(intent, {})
        suggested_tools = intent_config.get("tools", [])

        # Tool-specific recommendations
        if "find_symbol" in suggested_tools and symbols:
            for symbol_name, symbol_type in symbols[:3]:  # Limit to first 3
                recommendations.append(
                    f'mcp__tree_sitter__find_symbol(name_path="{symbol_name}", '
                    f"include_body=True, depth=1)",
                )

        if "get_symbols_overview" in suggested_tools:
            if files:
                for file_path in files[:2]:  # Limit to first 2 files
                    recommendations.append(
                        f'mcp__tree_sitter__get_symbols_overview(relative_path="{file_path}")',
                    )
            else:
                recommendations.append(
                    'mcp__tree_sitter__get_symbols_overview(relative_path=".")',
                )

        if "analyze_complexity" in suggested_tools:
            recommendations.append(
                f'mcp__tree_sitter__analyze_complexity(project="{self.project_name}", file_path=<target_file>)',
            )

        if "find_similar_code" in suggested_tools:
            recommendations.append(
                f'mcp__tree_sitter__find_similar_code(project="{self.project_name}", snippet=<code_snippet>, threshold=0.7)',
            )

        if "get_ast" in suggested_tools:
            recommendations.append(
                f'mcp__tree_sitter__get_ast(project="{self.project_name}", path=<file_path>, max_depth=3)',
            )

        return recommendations

    def generate_workflow_suggestion(self, intent: str, confidence: float) -> str:
        """Generate a suggested workflow based on intent."""
        workflows = {
            "refactor": """1. Use get_symbols_overview to understand file structure
2. Run find_long_functions and find_complexity queries
3. Use analyze_complexity for detailed metrics
4. Apply find_similar_code to detect duplication
5. Check LSP diagnostics for style/lint issues
6. Use find_referencing_symbols before making changes""",
            "debug": """1. Check LSP diagnostics for immediate errors
2. Use find_symbol to locate the problematic function
3. Run find_referencing_symbols to trace usage
4. Check get_dependencies for import issues
5. Use get_ast to examine code structure
6. Search for error handling patterns nearby""",
            "implement": """1. Check LSP diagnostics for type/compilation errors
2. Use get_symbols_overview on related files
3. Find similar implementations with find_similar_code
4. Check existing patterns with run_query
5. Use find_symbol to navigate to insertion points
6. Verify integration with find_referencing_symbols""",
            "analyze": """1. Start with get_symbols_overview for file structure
2. Use get_ast for detailed structural analysis
3. Run analyze_complexity on key functions
4. Check LSP diagnostics for code quality insights
5. Use run_query for specific pattern searches
6. Check get_dependencies for relationships""",
            "test": """1. Use find_tests query to locate existing tests
2. Find functions to test with find_functions query
3. Check complexity with analyze_complexity
4. Use find_referencing_symbols for test coverage
5. Check LSP diagnostics for test failures
6. Search for untested edge cases""",
            "type_check": """1. Check LSP diagnostics for type errors (mypy/pyright)
2. Use find_symbol to locate type annotations
3. Run find_functions to identify untyped functions
4. Use get_ast to examine type usage patterns
5. Check find_imports for typing module usage""",
            "lint": """1. Check LSP diagnostics for linting issues
2. Use find_todos to locate technical debt
3. Run find_complexity to identify complex code
4. Use analyze_complexity for detailed metrics
5. Apply automated fixes where possible""",
        }

        if intent in workflows and confidence > 0.6:
            return workflows[intent]
        return ""

    def get_complexity_hints(self, prompt_text: str) -> List[str]:
        """Generate contextual hints for complexity management."""
        hints = []

        if re.search(
            r"complex|complicated|hard to understand|difficult",
            prompt_text,
            re.IGNORECASE,
        ):
            hints.append("Consider cyclomatic complexity analysis with tree-sitter")
            hints.append("Look for deeply nested conditions and long functions")

        if re.search(r"performance|slow|optimize", prompt_text, re.IGNORECASE):
            hints.append("Check for algorithmic complexity patterns")
            hints.append("Identify potential bottlenecks with AST analysis")

        if re.search(
            r"maintain|maintainability|technical debt",
            prompt_text,
            re.IGNORECASE,
        ):
            hints.append("Use duplicate code detection")
            hints.append("Analyze function length and parameter counts")

        return hints

    async def _collect_mypy_diagnostics(self):
        """Collect mypy type checking errors."""
        try:
            process = await asyncio.create_subprocess_exec(
                "mypy",
                "--no-error-summary",
                "--show-column-numbers",
                "--show-error-codes",
                ".",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)

            if stdout:
                for line in stdout.decode().splitlines():
                    match = re.match(
                        r"^(.+?):(\d+):(\d+): (\w+): (.+?)(?:\s+\[(.+?)\])?$",
                        line,
                    )
                    if match:
                        file_path, line_num, col, severity, message, code = (
                            match.groups()
                        )
                        self.diagnostics["mypy"].append(
                            {
                                "file": file_path,
                                "line": int(line_num),
                                "column": int(col),
                                "severity": severity,
                                "message": message,
                                "code": code or "unknown",
                                "source": "mypy",
                            },
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def _collect_ruff_diagnostics(self):
        """Collect ruff linting errors."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--output-format=json",
                ".",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)

            if stdout:
                try:
                    issues = json.loads(stdout.decode())
                    for issue in issues:
                        self.diagnostics["ruff"].append(
                            {
                                "file": issue.get("filename", ""),
                                "line": issue.get("location", {}).get("row", 0),
                                "column": issue.get("location", {}).get("column", 0),
                                "severity": "error" if issue.get("fix") else "warning",
                                "message": issue.get("message", ""),
                                "code": issue.get("code", "unknown"),
                                "source": "ruff",
                            },
                        )
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def _collect_pyright_diagnostics(self):
        """Collect Pyright/Pylance diagnostics."""
        try:
            process = await asyncio.create_subprocess_exec(
                "pyright",
                "--outputjson",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=8)

            if stdout:
                try:
                    data = json.loads(stdout.decode())
                    for diag in data.get("generalDiagnostics", []):
                        self.diagnostics["pyright"].append(
                            {
                                "file": diag.get("file", ""),
                                "line": diag.get("range", {})
                                .get("start", {})
                                .get("line", 0)
                                + 1,
                                "column": diag.get("range", {})
                                .get("start", {})
                                .get("character", 0)
                                + 1,
                                "severity": diag.get("severity", "error"),
                                "message": diag.get("message", ""),
                                "code": diag.get("rule", "unknown"),
                                "source": "pyright",
                            },
                        )
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def _collect_typescript_diagnostics(self):
        """Collect TypeScript compiler diagnostics."""
        tsconfig = self.project_dir / "tsconfig.json"
        if not tsconfig.exists():
            return

        try:
            process = await asyncio.create_subprocess_exec(
                "tsc",
                "--noEmit",
                "--pretty",
                "false",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

            output = stdout.decode() if stdout else stderr.decode()
            if output:
                for line in output.splitlines():
                    match = re.match(
                        r"^(.+?)\((\d+),(\d+)\): (\w+) (TS\d+): (.+)$",
                        line,
                    )
                    if match:
                        file_path, line_num, col, severity, code, message = (
                            match.groups()
                        )
                        self.diagnostics["typescript"].append(
                            {
                                "file": file_path,
                                "line": int(line_num),
                                "column": int(col),
                                "severity": severity.lower(),
                                "message": message,
                                "code": code,
                                "source": "tsc",
                            },
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def _collect_eslint_diagnostics(self):
        """Collect ESLint diagnostics."""
        eslintrc_files = list(self.project_dir.glob(".eslintrc*"))
        package_json = self.project_dir / "package.json"

        if not (eslintrc_files or package_json.exists()):
            return

        try:
            process = await asyncio.create_subprocess_exec(
                "npx",
                "eslint",
                ".",
                "--format=json",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

            if stdout:
                try:
                    files = json.loads(stdout.decode())
                    for file_data in files:
                        for msg in file_data.get("messages", []):
                            self.diagnostics["eslint"].append(
                                {
                                    "file": file_data.get("filePath", ""),
                                    "line": msg.get("line", 0),
                                    "column": msg.get("column", 0),
                                    "severity": (
                                        "error"
                                        if msg.get("severity", 0) == 2
                                        else "warning"
                                    ),
                                    "message": msg.get("message", ""),
                                    "code": msg.get("ruleId", "unknown"),
                                    "source": "eslint",
                                },
                            )
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def _collect_rust_diagnostics(self):
        """Collect Rust compiler/clippy diagnostics."""
        cargo_toml = self.project_dir / "Cargo.toml"
        if not cargo_toml.exists():
            return

        try:
            process = await asyncio.create_subprocess_exec(
                "cargo",
                "clippy",
                "--message-format=json",
                "--no-deps",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)

            if stdout:
                for line in stdout.decode().splitlines():
                    try:
                        msg = json.loads(line)
                        if msg.get("reason") == "compiler-message":
                            message = msg.get("message", {})
                            for span in message.get("spans", []):
                                if span.get("is_primary"):
                                    self.diagnostics["rust"].append(
                                        {
                                            "file": span.get("file_name", ""),
                                            "line": span.get("line_start", 0),
                                            "column": span.get("column_start", 0),
                                            "severity": message.get("level", "warning"),
                                            "message": message.get("message", ""),
                                            "code": message.get("code", {}).get(
                                                "code",
                                                "unknown",
                                            ),
                                            "source": "clippy",
                                        },
                                    )
                    except json.JSONDecodeError:
                        pass
        except (subprocess.TimeoutExpired, FileNotFoundError, asyncio.TimeoutError):
            pass

    async def collect_relevant_diagnostics(self, prompt: str) -> Dict[str, Any]:
        """Collect and filter diagnostics relevant to the prompt."""
        try:
            # Run diagnostic collectors in parallel
            collectors = [
                self._collect_mypy_diagnostics(),
                self._collect_ruff_diagnostics(),
                self._collect_pyright_diagnostics(),
                self._collect_typescript_diagnostics(),
                self._collect_eslint_diagnostics(),
                self._collect_rust_diagnostics(),
            ]

            await asyncio.gather(*collectors, return_exceptions=True)

            # Filter diagnostics based on prompt
            filtered = self.filter_diagnostics_for_prompt(prompt)

            # Generate summary
            summary = self.generate_diagnostics_summary(filtered)

            return {
                "summary": summary,
                "details": filtered,
                "total_issues": sum(len(diags) for diags in filtered.values()),
            }

        except Exception as e:
            return {
                "summary": f"Diagnostics collection error: {str(e)}",
                "details": {},
                "total_issues": 0,
            }

    def filter_diagnostics_for_prompt(
        self,
        prompt: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Filter diagnostics relevant to the user's prompt."""
        # Extract file paths mentioned in prompt
        mentioned_files = set(self.extract_file_paths(prompt))

        # Keywords that suggest interest in diagnostics
        diagnostic_keywords = [
            "error",
            "warning",
            "type",
            "lint",
            "fix",
            "issue",
            "problem",
            "diagnostic",
        ]
        wants_diagnostics = any(
            keyword in prompt.lower() for keyword in diagnostic_keywords
        )

        filtered = defaultdict(list)

        for source, diags in self.diagnostics.items():
            for diag in diags:
                file_path = Path(diag["file"])

                # Include if file is mentioned
                if mentioned_files:
                    for mentioned in mentioned_files:
                        if mentioned in str(file_path) or file_path.name == mentioned:
                            filtered[source].append(diag)
                            break
                # Include critical errors when diagnostics are wanted
                elif wants_diagnostics and diag["severity"] in ["error", "critical"]:
                    filtered[source].append(diag)

        return dict(filtered)

    def generate_diagnostics_summary(
        self,
        filtered_diagnostics: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Generate a summary of diagnostics."""
        if not filtered_diagnostics:
            total_count = sum(len(diags) for diags in self.diagnostics.values())
            if total_count > 0:
                error_count = sum(
                    1
                    for diags in self.diagnostics.values()
                    for d in diags
                    if d["severity"] == "error"
                )
                warning_count = total_count - error_count
                return (
                    f"🔴 {error_count} errors, {warning_count} warnings across codebase"
                )
            return "No diagnostics found"

        error_count = sum(
            1
            for diags in filtered_diagnostics.values()
            for d in diags
            if d["severity"] == "error"
        )
        warning_count = (
            sum(len(diags) for diags in filtered_diagnostics.values()) - error_count
        )

        return f"Found {error_count} errors, {warning_count} warnings in relevant files"

    def generate_unified_recommendations(
        self,
        intent: str,
        languages: List[str],
        files: List[str],
        symbols: List[Tuple[str, str]],
        ast_analysis: Dict[str, Any],
        diagnostics: Dict[str, Any],
    ) -> List[str]:
        """Generate unified recommendations combining AST and diagnostics insights."""
        recommendations = []

        # Priority recommendations based on diagnostics
        if diagnostics.get("total_issues", 0) > 0:
            recommendations.append(
                "🔴 Address diagnostics issues first - they may block other analysis",
            )

        # AST-based recommendations
        if ast_analysis.get("tool_recommendations"):
            recommendations.extend(ast_analysis["tool_recommendations"][:3])  # Top 3

        # Workflow-based recommendations
        if ast_analysis.get("workflow"):
            recommendations.append(f"📋 Suggested workflow for {intent}:")
            workflow_steps = ast_analysis["workflow"].split("\n")
            recommendations.extend(workflow_steps[:3])  # First 3 steps

        # Language-specific recommendations
        if "python" in languages and diagnostics.get("total_issues", 0) > 0:
            recommendations.append(
                "🐍 Run `ruff check --fix .` and `mypy .` for Python code quality",
            )

        if "typescript" in languages or "javascript" in languages:
            recommendations.append(
                "📘 Use TypeScript compiler and ESLint for comprehensive analysis",
            )

        return recommendations[:8]  # Limit to 8 recommendations


# Main interface functions
async def create_code_intelligence_injection(
    prompt: str,
    project_dir: Optional[str] = None,
) -> str:
    """Create comprehensive code intelligence injection."""
    hub = CodeIntelligenceHub(project_dir)

    try:
        analysis = await hub.analyze_prompt(prompt)

        # Build injection
        injection_parts = []

        # Header with intent and confidence
        injection_parts.append(
            f"<code-intelligence>\n"
            f"Intent: {analysis['intent']} (confidence: {analysis['confidence']:.2f})\n"
            f"Languages: {', '.join(analysis['languages'])}\n",
        )

        # File and symbol context
        if analysis["files"]:
            injection_parts.append(f"Files: {', '.join(analysis['files'])}")
        if analysis["symbols"]:
            symbol_list = ", ".join(
                f"{name} ({type_})" for name, type_ in analysis["symbols"][:5]
            )
            injection_parts.append(f"Symbols: {symbol_list}")

        injection_parts.append("</code-intelligence>")

        # Diagnostics summary
        if analysis["diagnostics"]["total_issues"] > 0:
            injection_parts.append(
                f"\n<diagnostics-summary>\n"
                f"{analysis['diagnostics']['summary']}\n"
                f"</diagnostics-summary>",
            )

        # AST tools and queries
        if analysis["ast_analysis"]["tool_recommendations"]:
            tools = "\n".join(
                f"- {tool}"
                for tool in analysis["ast_analysis"]["tool_recommendations"][:5]
            )
            injection_parts.append(
                f"\n<ast-tools>\nRecommended tree-sitter tools:\n{tools}\n</ast-tools>",
            )

        # Unified recommendations
        if analysis["recommendations"]:
            recs = "\n".join(f"- {rec}" for rec in analysis["recommendations"][:6])
            injection_parts.append(
                f"\n<recommendations>\n{recs}\n</recommendations>",
            )

        return f"{'\n'.join(injection_parts)}\n"

    except Exception as e:
        return f"<!-- Code intelligence error: {str(e)} -->\n"


# Backward compatibility functions
def create_tree_sitter_injection(prompt: str) -> str:
    """Backward compatibility for tree_sitter_injection."""
    try:
        import asyncio

        return asyncio.run(create_code_intelligence_injection(prompt))
    except Exception:
        # Fallback to basic analysis
        hub = CodeIntelligenceHub()
        intent, confidence = hub.detect_intent(prompt)
        languages = hub.detect_languages(prompt)
        files = hub.extract_file_paths(prompt)
        symbols = hub.extract_symbols(prompt)

        injection_parts = [
            f"<tree-sitter-analysis>\n"
            f"Intent: {intent} (confidence: {confidence:.2f})\n"
            f"Languages: {', '.join(languages)}\n",
        ]

        if files:
            injection_parts.append(f"Files mentioned: {', '.join(files)}")
        if symbols:
            symbol_list = ", ".join(f"{name} ({type_})" for name, type_ in symbols[:5])
            injection_parts.append(f"Symbols mentioned: {symbol_list}")

        injection_parts.append("</tree-sitter-analysis>")

        return f"{'\n'.join(injection_parts)}\n"


async def get_lsp_diagnostics_injection(prompt: str, project_dir: str) -> str:
    """Backward compatibility for lsp_diagnostics_injection."""
    hub = CodeIntelligenceHub(project_dir)
    diagnostics = await hub.collect_relevant_diagnostics(prompt)

    if diagnostics["total_issues"] == 0:
        return ""

    return f"<lsp-diagnostics>\n{diagnostics['summary']}\n</lsp-diagnostics>\n"


# Additional backward compatibility aliases
def create_tree_sitter_enhanced_injection(prompt: str) -> str:
    """Alias for create_tree_sitter_injection."""
    return create_tree_sitter_injection(prompt)


def get_tree_sitter_hints(prompt: str) -> str:
    """Generate contextual hints for tree-sitter usage."""
    hints = []

    if re.search(r"structure|organization|architecture|layout", prompt, re.IGNORECASE):
        hints.append(
            "💡 Tree-sitter can map entire codebases:\n"
            "   - get_symbols_overview: File structure view\n"
            "   - analyze_project: Full project analysis\n"
            "   - get_ast: Deep structural insights",
        )

    if re.search(r"performance|slow|optimize|complexity", prompt, re.IGNORECASE):
        hints.append(
            "⚡ Tree-sitter complexity analysis:\n"
            "   - analyze_complexity: Beyond cyclomatic\n"
            "   - find_long_functions: Identify hotspots\n"
            "   - find_similar_code: Detect duplication",
        )

    return f"{'\n\n'.join(hints)}\n" if hints else ""


def get_ast_navigation_hints(prompt: str) -> str:
    """Alias for get_tree_sitter_hints."""
    return get_tree_sitter_hints(prompt)
