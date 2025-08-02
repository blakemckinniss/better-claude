"""Unified Smart Advisor - consolidates zen, agent, content, and trigger injections."""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple


class UnifiedSmartAdvisor:
    """Consolidates zen_injection, agent_injector, content_injection, and
    trigger_injection into a single, efficient recommendation system."""

    def __init__(self):
        self.project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        if self.project_dir == "$CLAUDE_PROJECT_DIR" or not os.path.isdir(
            self.project_dir
        ):
            self.project_dir = os.getcwd()

        # Agent patterns from agent_injector.py
        self.intent_patterns = {
            "refactoring": {
                "keywords": [
                    "clean up",
                    "improve",
                    "refactor",
                    "simplify",
                    "organize",
                    "restructure",
                ],
                "agent": "code-refactorer",
                "zen_tool": "refactor",
            },
            "security": {
                "keywords": [
                    "security",
                    "audit",
                    "vulnerability",
                    "secure",
                    "CVE",
                    "authentication",
                ],
                "agent": "security-auditor",
                "zen_tool": "secaudit",
            },
            "testing": {
                "keywords": [
                    "test",
                    "coverage",
                    "unit test",
                    "e2e",
                    "testing strategy",
                ],
                "agent": "test-strategist",
                "zen_tool": "testgen",
            },
            "debugging": {
                "keywords": [
                    "debug",
                    "bug",
                    "error",
                    "issue",
                    "problem",
                    "broken",
                    "failing",
                ],
                "agent": "debugger",
                "zen_tool": "debug",
            },
            "performance": {
                "keywords": [
                    "slow",
                    "optimize",
                    "performance",
                    "speed up",
                    "bottleneck",
                ],
                "agent": "performance-optimizer",
                "zen_tool": "analyze",
            },
            "architecture": {
                "keywords": [
                    "architecture",
                    "design",
                    "system",
                    "microservice",
                    "pattern",
                ],
                "agent": "api-architect",
                "zen_tool": "thinkdeep",
            },
            "documentation": {
                "keywords": ["document", "docs", "readme", "explain", "documentation"],
                "agent": "code-documenter",
                "zen_tool": "docgen",
            },
            "database": {
                "keywords": ["database", "schema", "query", "migration", "SQL"],
                "agent": "database-architect",
                "zen_tool": "analyze",
            },
            "devops": {
                "keywords": ["CI/CD", "deploy", "docker", "kubernetes", "pipeline"],
                "agent": "devops-engineer",
                "zen_tool": "analyze",
            },
            "migration": {
                "keywords": ["migrate", "upgrade", "move from", "transition", "port"],
                "agent": "migration-planner",
                "zen_tool": "thinkdeep",
            },
        }

        # MCP tool patterns from trigger_injection.py (simplified)
        self.mcp_patterns = {
            "mcp__github__": {
                "keywords": [
                    "github",
                    "pull request",
                    "create pr",
                    "git commit",
                    "repository",
                ],
                "priority": 8,
            },
            "mcp__zen__": {
                "keywords": [
                    "analyze architecture",
                    "debug complex",
                    "root cause",
                    "brainstorm",
                ],
                "priority": 9,
            },
            "mcp__filesystem__": {
                "keywords": ["create file", "delete file", "list files", "find files"],
                "priority": 7,
            },
            "mcp__tavily-remote__": {
                "keywords": [
                    "search web",
                    "find documentation",
                    "latest docs",
                    "research",
                ],
                "priority": 8,
            },
            "mcp__playwright__": {
                "keywords": [
                    "browser automation",
                    "e2e test",
                    "ui test",
                    "click button",
                ],
                "priority": 7,
            },
        }

        # Performance optimization patterns from content_injection.py
        self.performance_patterns = {
            "multi_read": r"\b(all|multiple|several|each|every)\s+\w*\s*(files?|documents?|modules?)\b",
            "batch_edit": r"\b(update|modify|change|refactor|edit)\s+\w*\s*(all|multiple|several|files?)\b",
            "search_ops": r"\b(search|find|grep|look for|locate)\s+\w*\s*(in|across|through)\b",
            "parallel_tasks": r"\b(and also|additionally|separately|meanwhile|at the same time)\b",
        }

        # ZEN tool selection patterns from zen_injection.py
        self.zen_tool_patterns = {
            "thinkdeep": [
                r"\b(investigate|complex|deep|thorough|comprehensive|analyze deeply)\b"
            ],
            "debug": [
                r"\b(debug|bug|error|issue|problem|broken|failing|fix|troubleshoot)\b"
            ],
            "analyze": [r"\b(analyze|assessment|review|evaluate|examine|audit)\b"],
            "consensus": [
                r"\b(should I|which is better|compare|decide|choice|opinion)\b"
            ],
            "chat": [r"\b(help|how to|explain|guide|question|brainstorm|discuss)\b"],
        }

    @lru_cache(maxsize=100)
    def _get_available_agents(self) -> List[Tuple[str, str]]:
        """Get list of available agents from .claude/agents directory (cached)."""
        agents = []
        agents_dir = Path(self.project_dir) / ".claude" / "agents"

        if not agents_dir.exists():
            return agents

        for agent_file in agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text()
                name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
                desc_match = re.search(
                    r"^description:\s*(.+?)(?=\n(?:tools:|color:|Examples:|examples:))",
                    content,
                    re.MULTILINE | re.DOTALL,
                )

                if name_match and desc_match:
                    name = name_match.group(1).strip()
                    desc = f"{desc_match.group(1).strip().split('.')[0]}."
                    agents.append((name, desc))
            except Exception:
                continue

        return agents

    def _analyze_intent(self, prompt: str) -> List[Tuple[str, float, str, str]]:
        """Analyze prompt intent and return scored matches.

        Returns: List of (intent_name, score, agent, zen_tool)
        """
        prompt_lower = prompt.lower()
        matches = []

        for intent_name, intent_data in self.intent_patterns.items():
            score = 0.0
            matched_keywords = []

            for keyword in intent_data["keywords"]:
                if keyword.lower() in prompt_lower:
                    score += (
                        2.0 if f" {keyword.lower()} " in f" {prompt_lower} " else 1.0
                    )
                    matched_keywords.append(keyword)

            if score > 0:
                # Bonus for multiple keyword matches
                if len(matched_keywords) > 1:
                    score *= 1 + len(matched_keywords) * 0.1

                matches.append(
                    (
                        intent_name,
                        score,
                        intent_data["agent"],
                        intent_data["zen_tool"],
                    )
                )

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _analyze_mcp_triggers(self, prompt: str) -> List[Tuple[str, str, float]]:
        """Analyze prompt for MCP tool triggers.

        Returns: List of (tool_id, tool_name, score)
        """
        prompt_lower = prompt.lower()
        matches = []

        for tool_id, tool_data in self.mcp_patterns.items():
            score = 0.0

            for keyword in tool_data["keywords"]:
                if keyword.lower() in prompt_lower:
                    score += (
                        2.0 if f" {keyword.lower()} " in f" {prompt_lower} " else 1.0
                    )

            if score > 0:
                base_priority = tool_data["priority"]
                final_score = score * base_priority
                tool_name = tool_id.replace("mcp__", "").replace("__", " ").title()
                matches.append((tool_id, tool_name, final_score))

        return sorted(matches, key=lambda x: x[2], reverse=True)

    def _analyze_performance_needs(self, prompt: str) -> List[str]:
        """Analyze prompt for performance optimization opportunities."""
        directives = []

        for pattern_name, pattern in self.performance_patterns.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                if pattern_name == "multi_read":
                    directives.append("Use batch Read operations in single message")
                elif pattern_name == "batch_edit":
                    directives.append("Use MultiEdit or batch Edit calls")
                elif pattern_name == "search_ops":
                    directives.append("Use Grep/Glob tools with patterns")
                elif pattern_name == "parallel_tasks":
                    directives.append("Consider Task tool for parallel execution")

        return directives

    def _suggest_zen_tools(self, prompt: str) -> Tuple[str, List[str], str]:
        """Suggest ZEN tools based on prompt analysis.

        Returns: (primary_tool, secondary_tools, reasoning)
        """
        prompt_lower = prompt.lower()
        tool_scores = {}

        for tool, patterns in self.zen_tool_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, prompt_lower))
                score += matches
            if score > 0:
                tool_scores[tool] = score

        if not tool_scores:
            return "chat", [], "general_consultation"

        primary_tool = max(tool_scores.items(), key=lambda x: x[1])[0]
        secondary_tools = [
            tool
            for tool, score in tool_scores.items()
            if tool != primary_tool and score >= max(1, tool_scores[primary_tool] * 0.5)
        ][:2]

        reasoning = f"Primary: {primary_tool} (score: {tool_scores[primary_tool]})"
        if secondary_tools:
            reasoning += f", Secondary: {', '.join(secondary_tools)}"

        return primary_tool, secondary_tools, reasoning

    def generate_smart_recommendations(self, prompt: str) -> str:
        """Generate unified smart recommendations for the prompt."""
        if not prompt:
            return ""

        sections = []

        # 1. Intent Analysis & Agent Recommendations
        intent_matches = self._analyze_intent(prompt)[:3]  # Top 3
        if intent_matches:
            sections.append("## 🎯 Task Analysis & Agent Recommendations")
            for intent, score, agent, zen_tool in intent_matches:
                sections.append(
                    f"- **{intent.title()}** (score: {score:.1f}) → Use `{agent}` agent or `mcp__zen__{zen_tool}`"
                )

        # 2. ZEN Tool Recommendations
        primary_zen, secondary_zen, zen_reasoning = self._suggest_zen_tools(prompt)
        if primary_zen != "chat" or secondary_zen:
            sections.append("## 🧠 ZEN Strategic Analysis")
            zen_recommendation = f"PRIMARY: mcp__zen__{primary_zen}"
            if secondary_zen:
                zen_recommendation += f" | SECONDARY: {', '.join([f'mcp__zen__{tool}' for tool in secondary_zen])}"
            sections.append(f"- {zen_recommendation}")
            sections.append(f"- Reasoning: {zen_reasoning}")

        # 3. MCP Tool Triggers
        mcp_matches = self._analyze_mcp_triggers(prompt)[:3]  # Top 3
        if mcp_matches:
            sections.append("## 🛠️ MCP Tool Recommendations")
            for tool_id, tool_name, score in mcp_matches:
                if score > 30:  # Only show high-confidence matches
                    prefix = (
                        "🔴 CRITICAL"
                        if score > 70
                        else "🟡 IMPORTANT"
                        if score > 50
                        else "🟢 SUGGESTED"
                    )
                    sections.append(
                        f"- {prefix}: {tool_id} ({tool_name}) [score: {score:.0f}]"
                    )

        # 4. Performance Optimizations
        perf_directives = self._analyze_performance_needs(prompt)
        if perf_directives:
            sections.append("## ⚡ Performance Optimizations")
            for directive in perf_directives:
                sections.append(f"- {directive}")

        # 5. Available Agents Summary
        agents = self._get_available_agents()
        if agents and intent_matches:
            sections.append("## 📋 Available Specialist Agents")
            for name, desc in agents[:5]:  # Top 5
                sections.append(f"- **{name}**: {desc}")

        if not sections:
            return ""

        # Combine all sections
        output = "\n<smart-advisor-recommendations>\n"
        output += "\n".join(sections)
        output += "\n</smart-advisor-recommendations>\n"

        return output


# Global instance for performance
_advisor_instance = None


def get_unified_smart_advisor() -> UnifiedSmartAdvisor:
    """Get or create the global advisor instance."""
    global _advisor_instance
    if _advisor_instance is None:
        _advisor_instance = UnifiedSmartAdvisor()
    return _advisor_instance


def get_smart_recommendations(user_prompt: Optional[str] = None) -> str:
    """Main entry point for unified smart recommendations."""
    if not user_prompt:
        return ""

    advisor = get_unified_smart_advisor()
    return advisor.generate_smart_recommendations(user_prompt)


# Backward compatibility functions for existing imports
def get_zen_injection(user_prompt: Optional[str] = None) -> str:
    """Backward compatibility for zen_injection."""
    return get_smart_recommendations(user_prompt)


def get_agent_injection(user_prompt: Optional[str] = None) -> str:
    """Backward compatibility for agent_injector."""
    return get_smart_recommendations(user_prompt)


def get_content_injection(user_prompt: Optional[str] = None) -> str:
    """Backward compatibility for content_injection."""
    return get_smart_recommendations(user_prompt)


def get_trigger_injection(user_prompt: Optional[str] = None) -> str:
    """Backward compatibility for trigger_injection."""
    return get_smart_recommendations(user_prompt)
