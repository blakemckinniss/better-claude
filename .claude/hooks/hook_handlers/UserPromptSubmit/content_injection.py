"""Module for injecting performance and efficiency instructions into user prompts."""

import re
from typing import Any, Dict, Optional

try:
    from .code_smell_detector import detect_smells_for_prompt
    from .dependency_graph import analyze_dependencies_for_prompt
except ImportError:
    # Fallback if modules aren't available yet
    analyze_dependencies_for_prompt = None
    detect_smells_for_prompt = None


class SmartContentInjector:
    """Intelligent content injection based on detected operations."""

    def __init__(self):
        # Patterns that indicate file operations
        self.file_patterns = {
            "multi_read": r"\b(all|multiple|several|each|every)\s+\w*\s*(files?|documents?|modules?)\b",
            "batch_edit": r"\b(update|modify|change|refactor|edit)\s+\w*\s*(all|multiple|several|files?)\b",
            "search_ops": r"\b(search|find|grep|look for|locate)\s+\w*\s*(in|across|through)\b",
            "analysis": r"\b(analyze|review|check|examine|inspect)\s+\w*\s*(code|files?|modules?|functions?)\b",
        }

        # Patterns that indicate parallelizable tasks
        self.parallel_patterns = {
            "independent_tasks": r"\b(and also|additionally|separately|meanwhile|at the same time)\b",
            "multiple_actions": r"\b(then|after that|next|following that|subsequently)\b.*\b(also|and|plus)\b",
            "enumerated_tasks": r"(\d+[\.\)]\s+\w+.*\n)+",  # Numbered lists
            "test_and_X": r"\b(test|tests?)\s+and\s+(document|implement|refactor|analyze)\b",
        }

        # Task-specific optimizations
        self.task_optimizations = {
            "testing": {
                "pattern": r"\b(test|tests?|testing|unit test|integration test)\b",
                "directive": "For test generation: Use Task tool with subagent_type='general-purpose' to generate tests in parallel with other work",
            },
            "documentation": {
                "pattern": r"\b(document|documentation|docs|readme|comments?)\b",
                "directive": "For documentation: Spawn a documentation subagent while continuing with implementation",
            },
            "refactoring": {
                "pattern": r"\b(refactor|restructure|reorganize|clean up|improve)\b",
                "directive": "For refactoring: Batch all file edits in a single message with multiple Edit tool calls",
            },
            "debugging": {
                "pattern": r"\b(debug|fix|troubleshoot|diagnose|investigate)\b",
                "directive": "For debugging: Use parallel Read operations to gather all relevant files before analysis",
            },
        }

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt for optimization opportunities."""
        prompt_lower = prompt.lower()

        # Check for file operations
        file_ops = []
        for op_type, pattern in self.file_patterns.items():
            if re.search(pattern, prompt_lower):
                file_ops.append(op_type)

        # Check for parallelizable tasks
        parallel_ops = []
        for op_type, pattern in self.parallel_patterns.items():
            if re.search(pattern, prompt_lower, re.MULTILINE):
                parallel_ops.append(op_type)

        # Check for specific task types
        task_types = []
        applicable_directives = []
        for task_name, task_info in self.task_optimizations.items():
            if re.search(task_info["pattern"], prompt_lower):
                task_types.append(task_name)
                applicable_directives.append(task_info["directive"])

        # Analyze dependencies if available
        dependency_analysis = None
        if analyze_dependencies_for_prompt:
            dependency_analysis = analyze_dependencies_for_prompt(prompt)

        # Detect code smells if available
        code_smell_analysis = None
        if detect_smells_for_prompt:
            code_smell_analysis = detect_smells_for_prompt(prompt)

        return {
            "has_file_ops": len(file_ops) > 0,
            "has_parallel_potential": len(parallel_ops) > 0,
            "file_operations": file_ops,
            "parallel_operations": parallel_ops,
            "task_types": task_types,
            "specific_directives": applicable_directives,
            "dependency_analysis": dependency_analysis,
            "code_smell_analysis": code_smell_analysis,
        }

    def generate_injection(self, analysis: Dict[str, Any]) -> str:
        """Generate appropriate performance directives based on analysis."""
        sections = []

        # Performance optimizations
        perf_directives = []
        if analysis["has_file_ops"]:
            if "multi_read" in analysis["file_operations"]:
                perf_directives.append(
                    "file_batch_read: 'Send ONE message with multiple Read tool calls for all files'",
                )
            if "batch_edit" in analysis["file_operations"]:
                perf_directives.append(
                    "file_batch_edit: 'Use MultiEdit tool or batch Edit calls in single message'",
                )
            if "search_ops" in analysis["file_operations"]:
                perf_directives.append(
                    "file_search: 'Use Grep/Glob tools with appropriate patterns, batch results'",
                )

        if analysis["has_parallel_potential"]:
            perf_directives.append(
                "parallel_execution: 'Identify independent tasks and spawn subagents using Task tool'",
            )
            if "test_and_X" in analysis["parallel_operations"]:
                perf_directives.append(
                    "test_parallel: 'Create test subagent while implementing main functionality'",
                )

        if analysis["specific_directives"]:
            for i, directive in enumerate(analysis["specific_directives"], 1):
                perf_directives.append(f"optimization_{i}: '{directive}'")

        if perf_directives:
            sections.append(
                "PERFORMANCE_OPTIMIZATIONS: {"
                + ", ".join(perf_directives)
                + ", priority: 'Maximize parallelism and minimize sequential operations'}",
            )

        # Dependency impact analysis
        if analysis.get("dependency_analysis"):
            dep_analysis = analysis["dependency_analysis"]
            dep_warnings = []

            for file, impact in dep_analysis.get("impact_analysis", {}).items():
                if impact["total_impacted"] > 0:
                    dep_warnings.append(
                        f"'{file}': {impact['total_impacted']} files depend on this",
                    )
                    if impact["critical_paths"]:
                        dep_warnings.append(
                            f"critical_paths: {impact['critical_paths'][:3]}",
                        )

            if dep_warnings:
                sections.append(
                    "DEPENDENCY_IMPACT: {"
                    + ", ".join(dep_warnings)
                    + ", warning: 'Changes will cascade to dependent files'}",
                )

        # Code quality warnings
        if analysis.get("code_smell_analysis"):
            smell_analysis = analysis["code_smell_analysis"]
            quality_warnings = []

            overall = smell_analysis.get("overall_summary", {})
            if overall.get("critical_issues", 0) > 0:
                quality_warnings.append(
                    f"CRITICAL: {overall['critical_issues']} critical issues found",
                )

            if overall.get("average_quality_score", 100) < 70:
                quality_warnings.append(
                    f"quality_score: {overall['average_quality_score']:.0f}/100",
                )

            # Highlight specific issues
            for file, details in smell_analysis.get("file_details", {}).items():
                summary = details["summary"]
                if summary["total_smells"] > 5:
                    top_issues = sorted(
                        summary["by_type"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3]
                    quality_warnings.append(
                        f"'{file}': {', '.join([f'{k}({v})' for k, v in top_issues])}",
                    )

            if quality_warnings:
                sections.append(
                    "CODE_QUALITY_WARNINGS: {"
                    + ", ".join(quality_warnings)
                    + ", recommendation: 'Consider refactoring before adding new features'}",
                )

        if not sections:
            return ""

        # Build the complete injection
        return f"<system-instruction>{' '.join(sections)}</system-instruction> "


# Global instance
_injector_instance = None


def get_content_injector() -> SmartContentInjector:
    """Get or create the global injector instance."""
    global _injector_instance
    if _injector_instance is None:
        _injector_instance = SmartContentInjector()
    return _injector_instance


def get_content_injection(user_prompt: Optional[str] = None) -> str:
    """Get performance optimization instructions based on prompt analysis.

    Args:
        user_prompt: The user's prompt to analyze

    Returns:
        str: Context-aware performance instructions or empty string
    """
    if not user_prompt:
        # Return generic instructions if no prompt provided
        return (
            "<system-instruction>"
            "PERFORMANCE_DIRECTIVES: {"
            "file_operations: 'ALWAYS batch Read/Write/Edit operations - use single message with multiple tool calls for parallel execution', "
            "subagent_usage: 'When independent tasks exist, spawn subagents using Task tool to process in parallel', "
            "examples: ["
            "'For multiple file reads: Send ONE message with multiple Read tool calls', "
            "'For refactoring multiple files: Use Task tool with subagent_type=\"general-purpose\" for parallel processing', "
            "'For testing + documentation: Create separate subagents to handle simultaneously'"
            "]"
            "}"
            "</system-instruction> "
        )

    injector = get_content_injector()
    analysis = injector.analyze_prompt(user_prompt)

    # Generate smart injection based on analysis
    injection = injector.generate_injection(analysis)

    # If no specific optimizations found, return minimal guidance
    if not injection:
        return ""

    return injection
