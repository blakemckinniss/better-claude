"""Agent Injector Module.

This module analyzes user prompts to detect intent and recommends relevant agents based
on keyword matching and patterns. It loads agent metadata from .claude/agents/*.md files
and provides intelligent agent recommendations as context injection.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AgentInjector:
    """Analyzes user prompts and recommends relevant agents based on intent
    detection."""

    def __init__(self, agents_dir: str = ".claude/agents"):
        # Try to find the agents directory relative to current directory or project root
        agents_path = Path(agents_dir)
        if not agents_path.exists():
            # Try from current file's perspective (hook handlers are in .claude/hooks/hook_handlers)
            agents_path = Path(__file__).parent.parent.parent / "agents"
            if not agents_path.exists():
                # Try from project root
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
                agents_path = Path(project_dir) / ".claude" / "agents"

        self.agents_dir = agents_path
        self._agent_cache: Optional[Dict[str, Dict]] = None
        self._pattern_cache: Optional[Dict[str, List[str]]] = None

        # Define intent patterns with associated keywords
        self.intent_patterns = {
            "refactoring": {
                "keywords": [
                    "clean up",
                    "improve",
                    "refactor",
                    "simplify",
                    "organize",
                    "restructure",
                    "reduce duplication",
                    "code smell",
                    "messy code",
                    "hard to understand",
                    "complex logic",
                    "better structure",
                ],
                "agent": "code-refactorer",
            },
            "security": {
                "keywords": [
                    "security",
                    "audit",
                    "vulnerability",
                    "secure",
                    "CVE",
                    "authentication",
                    "authorization",
                    "injection",
                    "XSS",
                    "CSRF",
                    "penetration test",
                    "security scan",
                    "exploit",
                    "breach",
                ],
                "agent": "security-auditor",
            },
            "testing": {
                "keywords": [
                    "test",
                    "coverage",
                    "unit test",
                    "e2e",
                    "testing strategy",
                    "test suite",
                    "integration test",
                    "mock",
                    "TDD",
                    "BDD",
                    "test cases",
                    "testing framework",
                    "jest",
                    "pytest",
                ],
                "agent": "test-strategist",
            },
            "database": {
                "keywords": [
                    "database",
                    "schema",
                    "query",
                    "migration",
                    "SQL",
                    "NoSQL",
                    "MongoDB",
                    "PostgreSQL",
                    "MySQL",
                    "Redis",
                    "data model",
                    "indexes",
                    "optimization",
                    "ORM",
                    "database design",
                ],
                "agent": "database-architect",
            },
            "performance": {
                "keywords": [
                    "slow",
                    "optimize",
                    "performance",
                    "speed up",
                    "bottleneck",
                    "profiling",
                    "benchmark",
                    "latency",
                    "throughput",
                    "memory leak",
                    "CPU usage",
                    "response time",
                    "scalability",
                    "caching",
                ],
                "agent": "performance-optimizer",
            },
            "api": {
                "keywords": [
                    "API",
                    "endpoint",
                    "REST",
                    "GraphQL",
                    "swagger",
                    "OpenAPI",
                    "microservice",
                    "webhook",
                    "rate limit",
                    "API design",
                    "API documentation",
                    "HTTP methods",
                    "status codes",
                ],
                "agent": "api-architect",
            },
            "devops": {
                "keywords": [
                    "CI/CD",
                    "deploy",
                    "docker",
                    "kubernetes",
                    "pipeline",
                    "containerize",
                    "DevOps",
                    "helm",
                    "terraform",
                    "ansible",
                    "GitHub Actions",
                    "Jenkins",
                    "AWS",
                    "cloud",
                    "infrastructure",
                ],
                "agent": "devops-engineer",
            },
            "documentation": {
                "keywords": [
                    "document",
                    "docs",
                    "README",
                    "explain",
                    "documentation",
                    "JSDoc",
                    "docstring",
                    "API docs",
                    "user guide",
                    "tutorial",
                    "code comments",
                    "inline docs",
                    "documentation generation",
                ],
                "agent": "code-documenter",
            },
            "dependencies": {
                "keywords": [
                    "update",
                    "upgrade",
                    "dependency",
                    "package",
                    "vulnerability",
                    "npm audit",
                    "outdated",
                    "security patch",
                    "version bump",
                    "package.json",
                    "requirements.txt",
                    "lock file",
                ],
                "agent": "dependency-upgrader",
            },
            "frontend": {
                "keywords": [
                    "UI",
                    "design",
                    "component",
                    "frontend",
                    "React",
                    "Vue",
                    "Angular",
                    "CSS",
                    "styling",
                    "responsive",
                    "user interface",
                    "layout",
                    "animation",
                    "accessibility",
                    "UX",
                ],
                "agent": "frontend-designer",
            },
            "content": {
                "keywords": [
                    "article",
                    "blog",
                    "write content",
                    "marketing",
                    "copy",
                    "content strategy",
                    "SEO",
                    "technical writing",
                    "blog post",
                    "documentation content",
                    "user manual",
                    "guide",
                ],
                "agent": "content-writer",
            },
            "migration": {
                "keywords": [
                    "migrate",
                    "upgrade",
                    "move from",
                    "transition",
                    "port",
                    "legacy system",
                    "modernize",
                    "replatform",
                    "version upgrade",
                    "framework migration",
                    "database migration",
                    "cloud migration",
                ],
                "agent": "migration-planner",
            },
            "tech_debt": {
                "keywords": [
                    "technical debt",
                    "code quality",
                    "legacy",
                    "outdated",
                    "deprecated",
                    "anti-pattern",
                    "code rot",
                    "maintenance burden",
                    "refactoring backlog",
                    "architecture debt",
                    "design debt",
                ],
                "agent": "tech-debt-analyzer",
            },
            "accessibility": {
                "keywords": [
                    "a11y",
                    "accessibility",
                    "WCAG",
                    "screen reader",
                    "ARIA",
                    "keyboard navigation",
                    "color contrast",
                    "alt text",
                    "accessible",
                    "disability",
                    "inclusive design",
                ],
                "agent": "accessibility-auditor",
            },
            "prd": {
                "keywords": [
                    "requirements",
                    "PRD",
                    "product document",
                    "specification",
                    "user stories",
                    "acceptance criteria",
                    "functional requirements",
                    "product spec",
                    "feature specification",
                    "scope document",
                ],
                "agent": "prd-writer",
            },
            "planning": {
                "keywords": [
                    "plan",
                    "roadmap",
                    "task list",
                    "project planning",
                    "milestone",
                    "timeline",
                    "sprint planning",
                    "backlog",
                    "project breakdown",
                    "work breakdown",
                    "task decomposition",
                ],
                "agent": "project-task-planner",
            },
        }

    @lru_cache(maxsize=1)
    def _load_agents(self) -> Dict[str, Dict]:
        """Load and cache agent metadata from .claude/agents/*.md files."""
        if self._agent_cache is not None:
            return self._agent_cache

        agents = {}

        if not self.agents_dir.exists():
            return agents

        for agent_file in self.agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text()

                # Extract frontmatter - more robust approach
                if content.startswith("---"):
                    # Find the second "---" that ends the frontmatter
                    second_dash_pos = content.find("---", 4)
                    if second_dash_pos != -1:
                        frontmatter_text = content[4:second_dash_pos].strip()

                        # Parse line by line for simple key-value pairs
                        # This avoids issues with complex multi-line YAML
                        metadata = {}
                        current_key = None
                        current_value = []

                        for line in frontmatter_text.split("\n"):
                            # Check if this is a new key
                            if ":" in line and not line.startswith(" "):
                                # Save previous key-value if exists
                                if current_key and current_value:
                                    metadata[current_key] = "\n".join(
                                        current_value,
                                    ).strip()

                                # Parse new key
                                key, value = line.split(":", 1)
                                current_key = key.strip()
                                current_value = [value.strip()] if value.strip() else []
                            elif current_key:
                                # Continue previous value
                                current_value.append(line)

                        # Save last key-value
                        if current_key and current_value:
                            metadata[current_key] = "\n".join(current_value).strip()

                        # Process metadata
                        if metadata.get("name"):
                            # Clean up description - remove quotes if present
                            description = metadata.get("description", "")
                            if description.startswith('"') and description.endswith(
                                '"',
                            ):
                                description = description[1:-1]

                            # Parse tools list
                            tools = []
                            tools_str = metadata.get("tools", "")
                            if tools_str:
                                # Simple comma-separated parsing
                                tools = [t.strip() for t in tools_str.split(",")]

                            agents[metadata["name"]] = {
                                "name": metadata.get("name"),
                                "description": description,
                                "tools": tools,
                                "file": str(agent_file),
                            }
            except Exception as e:
                # Log error for debugging but continue
                print(f"Error parsing {agent_file.name}: {e}")
                continue

        self._agent_cache = agents
        return agents

    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching."""
        return text.lower().strip()

    def _calculate_match_score(self, prompt: str, keywords: List[str]) -> float:
        """Calculate how well a prompt matches a set of keywords."""
        normalized_prompt = self._normalize_text(prompt)
        score = 0.0
        matched_keywords = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Exact match gets higher score
            if f" {keyword_lower} " in f" {normalized_prompt} ":
                score += 2.0
                matched_keywords += 1
            # Partial match gets lower score
            elif keyword_lower in normalized_prompt:
                score += 1.0
                matched_keywords += 1

        # Bonus for matching multiple different keywords
        if matched_keywords > 1:
            score *= 1 + matched_keywords * 0.1

        return score

    def _detect_intents(self, prompt: str) -> List[Tuple[str, float]]:
        """Detect intents from user prompt and return sorted by relevance score."""
        intents = []

        for intent_name, intent_data in self.intent_patterns.items():
            score = self._calculate_match_score(prompt, intent_data["keywords"])
            if score > 0:
                intents.append((intent_name, score))

        # Sort by score descending
        intents.sort(key=lambda x: x[1], reverse=True)

        return intents

    def _generate_reason(self, intent: str, prompt: str) -> str:
        """Generate a brief reason for recommending an agent."""
        reason_templates = {
            "refactoring": "Code improvement and restructuring detected",
            "security": "Security analysis or vulnerability assessment needed",
            "testing": "Testing strategy or test implementation required",
            "database": "Database-related work identified",
            "performance": "Performance optimization opportunity detected",
            "api": "API design or implementation task",
            "devops": "DevOps or infrastructure work needed",
            "documentation": "Documentation generation or improvement required",
            "dependencies": "Dependency management or updates needed",
            "frontend": "Frontend or UI development task",
            "content": "Content creation or writing task",
            "migration": "System or framework migration detected",
            "tech_debt": "Technical debt analysis or remediation needed",
            "accessibility": "Accessibility improvements required",
            "prd": "Product requirements or specification writing",
            "planning": "Project planning or task breakdown needed",
        }

        return reason_templates.get(intent, "Relevant expertise detected")

    def get_agent_recommendations(self, prompt: str, max_agents: int = 3) -> List[Dict]:
        """Get agent recommendations based on the user prompt."""
        agents = self._load_agents()
        intents = self._detect_intents(prompt)

        recommendations = []
        seen_agents = set()

        for intent_name, score in intents:
            if len(recommendations) >= max_agents:
                break

            agent_name = self.intent_patterns[intent_name]["agent"]

            # Skip if agent already recommended or doesn't exist
            if agent_name in seen_agents or agent_name not in agents:
                continue

            seen_agents.add(agent_name)

            # Generate reason based on matched intent
            reason = self._generate_reason(intent_name, prompt)

            recommendations.append(
                {
                    "agent": agent_name,
                    "score": score,
                    "reason": reason,
                    "intent": intent_name,
                },
            )

        return recommendations

    def get_agent_injection(self, user_prompt: str) -> str:
        """Get formatted agent recommendations as context injection."""
        recommendations = self.get_agent_recommendations(user_prompt)

        if not recommendations:
            return ""

        # Format the injection
        lines = ["## 🤖 Recommended Agents"]
        lines.append("")
        lines.append(
            "Based on your request, these specialized agents might be helpful:",
        )
        lines.append("")

        for i, rec in enumerate(recommendations, 1):
            agent_name = rec["agent"]
            reason = rec["reason"]
            lines.append(f"{i}. **{agent_name}** - {reason}")

        lines.append("")
        lines.append("To use an agent, you can ask me to delegate the task to them.")
        lines.append("")

        return "\n".join(lines)


def get_agent_injection(user_prompt: str) -> str:
    """Main entry point for getting agent recommendations."""
    injector = AgentInjector()
    return injector.get_agent_injection(user_prompt)
