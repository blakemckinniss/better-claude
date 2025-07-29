"""Module for injecting suffix instructions into user prompts."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class EnhancedTaskClassifier:
    """Enhanced classifier using weighted patterns inspired by smart_filter.py."""

    def __init__(self):
        # Task patterns with base weights and snippet associations
        self.task_patterns = {
            # High complexity tasks (0.7-1.0)
            "architecture": {
                "patterns": [
                    (r"\b(architect|design|system.?design|pattern)\b", 0.9),
                    (r"\b(scale|scalab|distributed|microservice)\b", 0.8),
                    (r"\b(integration|pipeline|workflow|orchestrat)\b", 0.7),
                ],
                "snippets": ["delegation_matrix", "performance_rules"],
            },
            "debugging": {
                "patterns": [
                    (r"\b(debug|troubleshoot|diagnose|investigate)\b", 0.8),
                    (r"\b(error|bug|issue|problem|crash|fail)\b", 0.7),
                    (r"\b(trace|stack.?trace|exception|traceback)\b", 0.7),
                ],
                "snippets": ["anti_patterns", "performance_rules"],
            },
            "implementation": {
                "patterns": [
                    (r"\b(implement|build|create|develop)\b", 0.8),
                    (r"\b(feature|function|class|module|component)\b", 0.6),
                    (r"\b(add|new|enhance|extend)\b", 0.5),
                ],
                "snippets": ["modern_tools", "code_rules", "feature_guidelines"],
            },
            # Medium complexity tasks (0.4-0.7)
            "optimization": {
                "patterns": [
                    (r"\b(optimiz|performance|speed|fast)\b", 0.7),
                    (r"\b(efficient|improve|enhance|better)\b", 0.5),
                    (r"\b(refactor|reorganiz|restructur)\b", 0.6),
                ],
                "snippets": ["performance_rules", "anti_patterns"],
            },
            "security": {
                "patterns": [
                    (r"\b(security|vulnerabil|exploit|threat)\b", 0.8),
                    (r"\b(auth[eonz]|permission|access.?control)\b", 0.7),
                    (r"\b(encrypt|decrypt|hash|token|credential)\b", 0.6),
                ],
                "snippets": ["security_rules"],
            },
            "testing": {
                "patterns": [
                    (r"\b(test|unit.?test|pytest|coverage)\b", 0.6),
                    (r"\b(mock|fixture|assertion|validate)\b", 0.5),
                    (r"\b(e2e|end.?to.?end|integration)\b", 0.6),
                ],
                "snippets": ["code_rules"],
            },
            # Low complexity tasks (0.1-0.4)
            "documentation": {
                "patterns": [
                    (r"\b(document|explain|describe|comment)\b", 0.4),
                    (r"\b(readme|tutorial|guide|manual)\b", 0.3),
                    (r"\b(api.?doc|docstring|annotation)\b", 0.4),
                ],
                "snippets": [],
            },
        }

        # Complexity modifiers that affect all tasks
        self.complexity_modifiers = {
            "multiple": (r"\b(multiple|several|many|all|entire)\b", 0.15),
            "complex": (r"\b(complex|complicated|difficult|advanced)\b", 0.2),
            "conditional": (r"\b(if|when|unless|except|depend)\b", 0.1),
            "comparison": (r"\b(versus|vs|compare|better|worse)\b", 0.15),
            "uncertainty": (r"\b(might|maybe|perhaps|possibly|could)\b", 0.1),
            "planning": (r"\b(plan|strategy|approach|architect)\b", 0.15),
        }

        # Keywords that trigger specific snippets
        self.snippet_triggers = {
            "hooks_system": r"\b(hook|hooks|event|trigger)\b",
            "parallel_execution": r"\b(parallel|concurrent|async|simultaneous)\b",
            "modern_tools": r"\b(grep|find|cat|sed|awk)\b",  # Triggers modern tool reminder
        }

    def analyze(self, prompt: str) -> Tuple[Dict[str, float], List[str], float]:
        """Analyze prompt and return task scores, relevant snippets, and complexity.

        Returns:
            Tuple of (task_scores, relevant_snippets, total_complexity)
        """
        prompt_lower = prompt.lower()
        task_scores = {}
        relevant_snippets = set()
        total_score = 0.0

        # Analyze task patterns
        for task_name, task_info in self.task_patterns.items():
            task_score = 0.0
            for pattern, weight in task_info["patterns"]:
                if re.search(pattern, prompt_lower):
                    task_score = max(task_score, weight)

            if task_score > 0:
                task_scores[task_name] = task_score
                total_score += task_score
                # Add associated snippets
                relevant_snippets.update(task_info["snippets"])

        # Apply complexity modifiers
        modifier_score = 0.0
        for modifier_name, (pattern, weight) in self.complexity_modifiers.items():
            if re.search(pattern, prompt_lower):
                modifier_score += weight

        # Check snippet triggers
        for snippet_name, pattern in self.snippet_triggers.items():
            if re.search(pattern, prompt_lower):
                relevant_snippets.add(snippet_name)

        # Length-based adjustment
        word_count = len(prompt.split())
        length_score = min(word_count / 100, 0.3)  # Max 0.3 from length

        # Calculate total complexity
        total_complexity = min((total_score + modifier_score + length_score) / 2, 1.0)

        return task_scores, list(relevant_snippets), total_complexity

    @classmethod
    def classify(cls, prompt: str) -> List[str]:
        """Backward compatible method that returns task categories."""
        classifier = cls()
        task_scores, _, _ = classifier.analyze(prompt)
        # Return tasks with score > 0.3
        return [task for task, score in task_scores.items() if score > 0.3] or [
            "general",
        ]


def get_project_conventions() -> Dict[str, str]:
    """Load project-specific conventions from CLAUDE.md or settings."""
    conventions = {
        "tools": "Use rg instead of grep, fd instead of find, bat instead of cat",
        "parallel": "Execute independent operations in parallel using multiple tool calls",
        "testing": "Run tests with appropriate framework before completing tasks",
        "commits": "Never commit unless explicitly requested",
    }

    # Try to load additional conventions from CLAUDE.md
    claude_md_path = Path("/home/devcontainers/better-claude/CLAUDE.md")
    if claude_md_path.exists():
        # Extract key conventions (simplified for now)
        conventions["style"] = "Follow existing code conventions and patterns"

    return conventions


class ClaudeMdSnippets:
    """Extract and cache relevant snippets from CLAUDE.md."""

    # Cache for parsed snippets
    _snippets_cache = None
    _cache_path = Path(
        "/home/devcontainers/better-claude/.claude/hooks/claude_md_cache.json",
    )

    @classmethod
    def _parse_claude_md(cls) -> Dict[str, str]:
        """Parse CLAUDE.md into categorized snippets."""
        claude_md_path = Path("/home/devcontainers/better-claude/CLAUDE.md")
        if not claude_md_path.exists():
            return {}

        try:
            content = claude_md_path.read_text()
            snippets = {}

            # Extract Modern Tools section
            modern_tools_match = re.search(
                r"### 1\. MODERN TOOLS ONLY.*?```bash(.*?)```",
                content,
                re.DOTALL | re.MULTILINE,
            )
            if modern_tools_match:
                snippets["modern_tools"] = f"```bash{modern_tools_match.group(1)}```"

            # Extract Parallel By Default section
            parallel_match = re.search(
                r"### 2\. PARALLEL BY DEFAULT(.*?)(?=###|\Z)",
                content,
                re.DOTALL,
            )
            if parallel_match:
                snippets["parallel_execution"] = parallel_match.group(1).strip()

            # Extract Zen Delegation Matrix
            delegation_match = re.search(
                r"### 3\. ZEN DELEGATION MATRIX.*?(\|.*?\|.*?\n)+",
                content,
                re.DOTALL,
            )
            if delegation_match:
                snippets["delegation_matrix"] = delegation_match.group(0).strip()

            # Extract Performance Rules
            perf_rules_match = re.search(
                r"## 🚀 PERFORMANCE RULES(.*?)(?=##|\Z)",
                content,
                re.DOTALL,
            )
            if perf_rules_match:
                snippets["performance_rules"] = perf_rules_match.group(1).strip()

            # Extract Anti-patterns
            anti_patterns_match = re.search(
                r"## ❌ ANTI-PATTERNS(.*?)(?=##|\Z)",
                content,
                re.DOTALL,
            )
            if anti_patterns_match:
                snippets["anti_patterns"] = anti_patterns_match.group(1).strip()

            # Extract Code Rules
            code_rules_match = re.search(
                r"### Code Rules(.*?)(?=###|\Z)",
                content,
                re.DOTALL,
            )
            if code_rules_match:
                snippets["code_rules"] = code_rules_match.group(1).strip()

            # Extract Security Rules
            security_rules_match = re.search(
                r"### Security Rules(.*?)(?=###|\Z)",
                content,
                re.DOTALL,
            )
            if security_rules_match:
                snippets["security_rules"] = security_rules_match.group(1).strip()

            # Extract Hooks System basics
            hooks_match = re.search(
                r"## 🎣 HOOKS SYSTEM.*?### Critical Events.*?(\|.*?\|.*?\n)+",
                content,
                re.DOTALL,
            )
            if hooks_match:
                snippets["hooks_system"] = hooks_match.group(0).strip()

            # Extract Feature Implementation Guidelines
            feature_impl_match = re.search(
                r"### Feature Implementation Guidelines(.*?)(?=###|##|\Z)",
                content,
                re.DOTALL,
            )
            if feature_impl_match:
                snippets["feature_guidelines"] = feature_impl_match.group(1).strip()

            # Cache the snippets
            cls._cache_path.parent.mkdir(parents=True, exist_ok=True)
            cls._cache_path.write_text(json.dumps(snippets, indent=2))

            return snippets

        except Exception as e:
            # Return empty dict on any error
            print(f"Error parsing CLAUDE.md: {e}")
            import traceback

            traceback.print_exc()
            return {}

    @classmethod
    def get_snippets(cls) -> Dict[str, str]:
        """Get cached snippets or parse if needed."""
        if cls._snippets_cache is None:
            # Try to load from cache first
            if cls._cache_path.exists():
                try:
                    cls._snippets_cache = json.loads(cls._cache_path.read_text())
                except Exception:
                    cls._snippets_cache = cls._parse_claude_md()
            else:
                cls._snippets_cache = cls._parse_claude_md()

        return cls._snippets_cache

    @classmethod
    def get_relevant_snippets_enhanced(
        cls,
        snippet_suggestions: List[str],
        complexity_score: float,
    ) -> str:
        """Get snippets based on enhanced classifier suggestions.

        Args:
            snippet_suggestions: List of snippet names from the enhanced classifier
            complexity_score: Overall complexity score

        Returns:
            str: Formatted snippets for injection
        """
        snippets = cls.get_snippets()
        if not snippets:
            return ""

        relevant = []

        # Map snippet suggestions to actual snippets
        snippet_mapping = {
            "modern_tools": ("modern_tools", "<claude-md-tools>", "</claude-md-tools>"),
            "parallel_execution": (
                "parallel_execution",
                "<claude-md-parallel>",
                "</claude-md-parallel>",
            ),
            "delegation_matrix": (
                "delegation_matrix",
                "<claude-md-delegation>",
                "</claude-md-delegation>",
            ),
            "performance_rules": (
                "performance_rules",
                "<claude-md-performance>",
                "</claude-md-performance>",
            ),
            "anti_patterns": (
                "anti_patterns",
                "<claude-md-antipatterns>",
                "</claude-md-antipatterns>",
            ),
            "code_rules": (
                "code_rules",
                "<claude-md-coderules>",
                "</claude-md-coderules>",
            ),
            "security_rules": (
                "security_rules",
                "<claude-md-security>",
                "</claude-md-security>",
            ),
            "hooks_system": ("hooks_system", "<claude-md-hooks>", "</claude-md-hooks>"),
            "feature_guidelines": (
                "feature_guidelines",
                "<claude-md-features>",
                "</claude-md-features>",
            ),
        }

        # Add snippets based on suggestions
        for suggestion in snippet_suggestions:
            if suggestion in snippet_mapping and suggestion in snippets:
                snippet_key, open_tag, close_tag = snippet_mapping[suggestion]
                relevant.append(f"{open_tag}\n{snippets[snippet_key]}\n{close_tag}")

        # Add complexity-based snippets that weren't explicitly suggested
        if (
            complexity_score > 0.5
            and "delegation_matrix" not in snippet_suggestions
            and "delegation_matrix" in snippets
        ):
            relevant.append(
                f"<claude-md-delegation>\n{snippets['delegation_matrix']}\n</claude-md-delegation>",
            )

        if (
            complexity_score > 0.35
            and "parallel_execution" not in snippet_suggestions
            and "parallel_execution" in snippets
        ):
            relevant.append(
                f"<claude-md-parallel>\n{snippets['parallel_execution']}\n</claude-md-parallel>",
            )

        return "\n".join(relevant) if relevant else ""


def get_performance_metrics() -> str:
    """Generate performance tracking requirements."""
    return (
        "\n<performance-awareness>"
        "Consider: Token usage efficiency | Parallel execution opportunities | "
        "Resource consumption | Tool call optimization"
        "</performance-awareness>"
    )


def get_error_recovery_suffix() -> str:
    """Generate error recovery pattern suggestions."""
    return (
        "\n<error-recovery>"
        "If errors occur: Include rollback steps | Suggest debug commands | "
        "Provide alternative approaches | Note cleanup requirements"
        "</error-recovery>"
    )


def get_agent_recommendations(task_categories: List[str]) -> str:
    """Suggest relevant agents based on task type."""
    agent_map = {
        "debugging": "debugger",
        "performance": "performance-optimizer",
        "security": "security-auditor",
        "architecture": "api-architect",
        "documentation": "code-documenter",
        "testing": "test-strategist",
    }

    recommendations = []
    for category in task_categories:
        if category in agent_map:
            recommendations.append(f"{agent_map[category]} agent for {category} tasks")

    if recommendations:
        return (
            f"\n<agent-suggestions>"
            f"Consider using: {', '.join(recommendations)}"
            f"</agent-suggestions>"
        )
    return ""


def get_progress_tracking_suffix() -> str:
    """Generate progress tracking requirements."""
    return (
        "\n<progress-tracking>"
        "TodoWrite updates: Mark completed tasks | Update progress | "
        "Add discovered subtasks | Estimate remaining work"
        "</progress-tracking>"
    )


def get_task_specific_suffix(task_categories: List[str]) -> str:
    """Generate task-specific requirements based on categories."""
    suffixes = []

    if "coding" in task_categories:
        suffixes.append(
            "Code quality: Check linting | Consider tests | Follow patterns",
        )

    if "debugging" in task_categories:
        suffixes.append(
            "Debug info: Include error context | Log locations | Stack traces",
        )

    if "architecture" in task_categories:
        suffixes.append(
            "Architecture: Consider scalability | Design patterns | Future growth",
        )

    if "documentation" in task_categories:
        suffixes.append(
            "Docs: Include examples | Clear explanations | Update references",
        )

    if "testing" in task_categories:
        suffixes.append("Testing: Edge cases | Coverage goals | Integration points")

    if "performance" in task_categories:
        suffixes.append(
            "Performance: Measure baselines | Identify bottlenecks | Profile results",
        )

    if "security" in task_categories:
        suffixes.append("Security: Validate inputs | Check permissions | Audit logs")

    if suffixes:
        return f"\n<task-specific>\n{' | '.join(suffixes)}\n</task-specific>"
    return ""


@lru_cache(maxsize=256)
def analyze_prompt_enhanced(
    user_prompt: str,
) -> Tuple[bool, float, List[str], List[str]]:
    """Enhanced prompt analysis using the new classifier.

    Returns:
        Tuple of (should_apply_enhanced, complexity_score, task_categories, relevant_snippets)
    """
    classifier = EnhancedTaskClassifier()
    task_scores, relevant_snippets, complexity_score = classifier.analyze(user_prompt)

    # Get task categories for backward compatibility
    task_categories = [task for task, score in task_scores.items() if score > 0.3]

    # Apply enhanced suffix for complexity > 0.2
    should_apply = complexity_score > 0.2

    return should_apply, complexity_score, task_categories, relevant_snippets


def get_suffix(user_prompt: Optional[str] = None) -> str:
    """Get the suffix to inject as additional context.

    The core "3 Next Steps" requirement is ALWAYS included.
    Additional context-aware suffixes are added based on the prompt.

    Args:
        user_prompt: Optional user prompt for context-aware suffix generation

    Returns:
        str: The suffix text to add as context
    """
    # Core requirement - ALWAYS included
    core_suffix = (
        "\n<response-requirements>"
        "ALWAYS end your response with a 'Next Steps' section containing exactly 3 actionable suggestions: "
        "1. The most logical immediate next action based on what was just completed "
        "2. A proactive improvement or optimization that could enhance the current work "
        "3. A forward-thinking suggestion that anticipates future needs or potential issues"
        "IMPORTANT: Create agents whenever necessary to handle complex tasks, perform all tasks in parallel if it makes sense, and consult with Zen Gemini early and often."
        "</response-requirements>"
    )

    # If no prompt provided, return core suffix only
    if not user_prompt:
        return core_suffix

    # Analyze prompt using enhanced classifier
    apply_enhanced, complexity_score, task_categories, snippet_suggestions = (
        analyze_prompt_enhanced(user_prompt)
    )

    # Start with core suffix
    full_suffix = core_suffix

    if apply_enhanced:
        # Add task-specific requirements
        task_suffix = get_task_specific_suffix(task_categories)
        if task_suffix:
            full_suffix += task_suffix

        # Add performance metrics for moderately complex tasks
        if complexity_score > 0.35:
            full_suffix += get_performance_metrics()

        # Add error recovery for debugging/complex tasks
        if "debugging" in task_categories or complexity_score > 0.5:
            full_suffix += get_error_recovery_suffix()

        # Add agent recommendations
        agent_suffix = get_agent_recommendations(task_categories)
        if agent_suffix:
            full_suffix += agent_suffix

        # Add progress tracking for multi-step tasks
        word_count = len(user_prompt.split())
        if complexity_score > 0.4 or word_count > 25:
            full_suffix += get_progress_tracking_suffix()

        # Add project conventions reminder for coding tasks
        if "coding" in task_categories:
            conventions = get_project_conventions()
            if conventions:
                conv_list = " | ".join([f"{k}: {v}" for k, v in conventions.items()])
                full_suffix += (
                    f"\n<project-conventions>\n{conv_list}\n</project-conventions>"
                )

        # Add relevant CLAUDE.md snippets using enhanced suggestions
        claude_md_snippets = ClaudeMdSnippets.get_relevant_snippets_enhanced(
            snippet_suggestions,
            complexity_score,
        )
        if claude_md_snippets:
            full_suffix += f"\n{claude_md_snippets}"

    # Add complexity metadata
    if complexity_score > 0:
        full_suffix += f"\n<!-- Complexity: {complexity_score:.2f} -->"

    return full_suffix
