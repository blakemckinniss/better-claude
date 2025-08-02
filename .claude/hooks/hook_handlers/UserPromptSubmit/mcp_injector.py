#!/usr/bin/env python3
"""MCP (Model Context Protocol) injector for intelligent tool recommendations.

This module analyzes user prompts to recommend the 3 most relevant MCP tools
from the available set, providing contextual examples and usage guidance.
"""

import re
from typing import Dict, List, Tuple


class MCPInjector:
    """Analyzes prompts and recommends the most relevant MCP tools."""
    
    def __init__(self):
        # Define MCP tools with their characteristics and use cases
        self.mcp_tools = {
            "zen": {
                "name": "ZEN (mcp__zen__)",
                "description": "Strategic AI co-pilot for complex tasks",
                "tools": ["chat", "thinkdeep", "debug", "analyze", "consensus", "refactor", "secaudit"],
                "use_cases": [
                    "complex problem solving",
                    "architecture decisions", 
                    "debugging difficult issues",
                    "strategic planning",
                    "code analysis",
                    "multi-perspective evaluation"
                ],
                "example": "mcp__zen__chat(prompt='How should I approach implementing this feature?', model='anthropic/claude-opus-4', use_websearch=True)"
            },
            "filesystem": {
                "name": "Filesystem (mcp__filesystem__)",
                "description": "General file & directory operations",
                "tools": ["read_file", "write_file", "edit_file", "list_directory", "search_files"],
                "use_cases": [
                    "reading files",
                    "creating files",
                    "editing text files",
                    "exploring directories",
                    "searching file patterns",
                    "general file operations"
                ],
                "example": "mcp__filesystem__read_multiple_files(paths=['file1.py', 'file2.py', 'file3.py'])"
            },
            "tavily": {
                "name": "Tavily (mcp__tavily-remote__)",
                "description": "Web search & content extraction",
                "tools": ["tavily_search", "tavily_extract", "tavily_crawl"],
                "use_cases": [
                    "searching documentation",
                    "finding latest information",
                    "extracting web content",
                    "researching libraries",
                    "checking best practices",
                    "finding solutions online"
                ],
                "example": "mcp__tavily-remote__tavily_search(query='React hooks best practices 2025', max_results=5)"
            },
            "tree_sitter": {
                "name": "Tree-sitter (mcp__tree_sitter__)",
                "description": "Advanced code parsing & AST analysis",
                "tools": ["get_ast", "run_query", "analyze_complexity", "find_similar_code"],
                "use_cases": [
                    "code structure analysis",
                    "finding patterns",
                    "complexity analysis",
                    "duplicate detection",
                    "AST manipulation",
                    "cross-language analysis"
                ],
                "example": "mcp__tree_sitter__analyze_complexity(project='better-claude', file_path='src/main.py')"
            },
            "github": {
                "name": "GitHub (mcp__github__)",
                "description": "GitHub repository operations",
                "tools": ["create_pull_request", "list_issues", "get_pull_request", "search_code"],
                "use_cases": [
                    "creating PRs",
                    "managing issues",
                    "code reviews",
                    "searching repositories",
                    "GitHub automation",
                    "repository management"
                ],
                "example": "mcp__github__create_issue(owner='user', repo='project', title='Bug: Error in login', body='Details...')"
            },
            "playwright": {
                "name": "Playwright (mcp__playwright__)",
                "description": "Browser automation & testing",
                "tools": ["browser_navigate", "browser_click", "browser_snapshot", "browser_type"],
                "use_cases": [
                    "web scraping",
                    "UI testing",
                    "browser automation",
                    "taking screenshots",
                    "form filling",
                    "web interaction"
                ],
                "example": "mcp__playwright__browser_navigate(url='https://example.com')"
            },
            "shadcn": {
                "name": "shadcn/ui (mcp__shadcn-ui__)",
                "description": "React component library",
                "tools": ["get_component", "list_components", "get_component_demo"],
                "use_cases": [
                    "React UI development",
                    "component implementation",
                    "UI patterns",
                    "design system",
                    "React components",
                    "frontend development"
                ],
                "example": "mcp__shadcn-ui__get_component(componentName='button')"
            },
            "memory": {
                "name": "Memory (mcp__better-claude-memory__)",
                "description": "Knowledge graph for code relationships",
                "tools": ["create_entities", "search_similar", "get_implementation"],
                "use_cases": [
                    "tracking code relationships",
                    "semantic search",
                    "knowledge management",
                    "code discovery",
                    "relationship mapping",
                    "context preservation"
                ],
                "example": "mcp__better-claude-memory__search_similar(query='authentication logic', limit=10)"
            },
            "context7": {
                "name": "Context7 (mcp__context7__)",
                "description": "Library documentation retrieval",
                "tools": ["resolve-library-id", "get-library-docs"],
                "use_cases": [
                    "finding library docs",
                    "API documentation",
                    "framework reference",
                    "library research",
                    "documentation lookup",
                    "code examples"
                ],
                "example": "mcp__context7__get-library-docs(context7CompatibleLibraryID='/react/react', topic='hooks')"
            }
        }
        
        # Intent patterns for different types of tasks
        self.intent_patterns = {
            "coding": {
                "patterns": [r"implement", r"code", r"function", r"class", r"method", r"develop", r"program", r"write.*code"],
                "primary_tools": ["filesystem", "zen"],
                "secondary_tools": ["tree_sitter", "memory"]
            },
            "debugging": {
                "patterns": [r"debug", r"error", r"bug", r"fix", r"issue", r"problem", r"broken", r"fail", r"exception"],
                "primary_tools": ["zen", "tree_sitter"],
                "secondary_tools": ["filesystem", "memory"]
            },
            "analysis": {
                "patterns": [r"analyze", r"understand", r"explain", r"how does", r"what does", r"explore", r"investigate"],
                "primary_tools": ["zen", "tree_sitter"],
                "secondary_tools": ["filesystem", "memory"]
            },
            "refactoring": {
                "patterns": [r"refactor", r"improve", r"clean", r"optimize", r"restructure", r"simplify", r"organize"],
                "primary_tools": ["zen", "tree_sitter"],
                "secondary_tools": ["filesystem"]
            },
            "file_operations": {
                "patterns": [r"read", r"write", r"create.*file", r"edit", r"modify", r"delete", r"list.*files", r"search.*files"],
                "primary_tools": ["filesystem"],
                "secondary_tools": ["tree_sitter"]
            },
            "web_search": {
                "patterns": [r"search", r"find.*online", r"documentation", r"latest", r"how to", r"tutorial", r"example", r"best practice"],
                "primary_tools": ["tavily", "context7", "zen"],
                "secondary_tools": ["filesystem"]
            },
            "github_ops": {
                "patterns": [r"pull request", r"PR", r"issue", r"github", r"repository", r"commit", r"merge", r"branch"],
                "primary_tools": ["github", "filesystem", "zen"],
                "secondary_tools": ["filesystem"]
            },
            "ui_development": {
                "patterns": [r"UI", r"component", r"frontend", r"React", r"interface", r"design", r"layout", r"styling"],
                "primary_tools": ["shadcn", "filesystem", "zen"],
                "secondary_tools": ["playwright", "tavily"]
            },
            "testing": {
                "patterns": [r"test", r"automate", r"browser", r"UI test", r"e2e", r"integration test", r"screenshot"],
                "primary_tools": ["playwright", "zen", "filesystem"],
                "secondary_tools": ["tree_sitter"]
            },
            "complex_task": {
                "patterns": [r"complex", r"difficult", r"strategy", r"plan", r"architecture", r"decision", r"approach"],
                "primary_tools": ["zen", "tree_sitter", "memory"],
                "secondary_tools": ["tavily", "filesystem"]
            }
        }
    
    def detect_languages(self, prompt: str) -> List[str]:
        """Detect programming languages mentioned in the prompt."""
        languages = []
        
        language_patterns = {
            "python": r"python|\.py\b|django|flask|fastapi",
            "javascript": r"javascript|\.js\b|node|react|vue|angular",
            "typescript": r"typescript|\.ts\b|\.tsx\b",
            "java": r"java\b|\.java\b|spring|maven",
            "go": r"golang|\.go\b|go\s+",
            "rust": r"rust|\.rs\b|cargo",
            "cpp": r"c\+\+|\.cpp\b|\.cc\b|\.cxx\b"
        }
        
        prompt_lower = prompt.lower()
        for lang, pattern in language_patterns.items():
            if re.search(pattern, prompt_lower):
                languages.append(lang)
        
        return languages
    
    def calculate_intent_score(self, prompt: str, patterns: List[str]) -> float:
        """Calculate how well a prompt matches intent patterns."""
        prompt_lower = prompt.lower()
        score = 0.0
        
        for pattern in patterns:
            matches = len(re.findall(pattern, prompt_lower))
            score += matches * 2.0  # Weight each match
            
            # Bonus for exact word matches
            if re.search(r'\b' + pattern + r'\b', prompt_lower):
                score += 1.0
        
        return score
    
    def detect_intents(self, prompt: str) -> List[Tuple[str, float]]:
        """Detect intents from the prompt and return sorted by score."""
        intents = []
        
        for intent_name, config in self.intent_patterns.items():
            score = self.calculate_intent_score(prompt, config["patterns"])
            if score > 0:
                intents.append((intent_name, score))
        
        # Sort by score descending
        intents.sort(key=lambda x: x[1], reverse=True)
        return intents
    
    def score_tool_relevance(self, tool_name: str, intents: List[Tuple[str, float]], 
                           languages: List[str], prompt: str) -> float:
        """Score how relevant a tool is for the given context."""
        score = 0.0
        
        # Score based on intent matches
        for intent_name, intent_score in intents:
            intent_config = self.intent_patterns.get(intent_name, {})
            
            # Primary tools get higher scores
            if tool_name in intent_config.get("primary_tools", []):
                score += intent_score * 3.0
            # Secondary tools get lower scores
            elif tool_name in intent_config.get("secondary_tools", []):
                score += intent_score * 1.5
        
        # Language-specific bonuses
        if tool_name == "filesystem" and "python" in languages:
            score += 5.0  # Strong Python specialization
        elif tool_name == "tree_sitter" and languages:
            score += 3.0  # Works with multiple languages
        
        # Context-specific bonuses
        tool_info = self.mcp_tools.get(tool_name, {})
        for use_case in tool_info.get("use_cases", []):
            if any(word in prompt.lower() for word in use_case.split()):
                score += 1.0
        
        return score
    
    def get_tool_recommendations(self, prompt: str, max_tools: int = 3) -> List[Dict]:
        """Get the most relevant MCP tools for the prompt."""
        # Detect context
        intents = self.detect_intents(prompt)
        languages = self.detect_languages(prompt)
        
        # Score all tools
        tool_scores = []
        for tool_name, tool_info in self.mcp_tools.items():
            score = self.score_tool_relevance(tool_name, intents, languages, prompt)
            if score > 0:
                tool_scores.append({
                    "name": tool_name,
                    "info": tool_info,
                    "score": score
                })
        
        # Sort by score and get top tools
        tool_scores.sort(key=lambda x: x["score"], reverse=True)
        recommendations = tool_scores[:max_tools]
        
        # Add contextual reasons
        for rec in recommendations:
            rec["reason"] = self.generate_reason(rec["name"], intents, languages, prompt)
        
        return recommendations
    
    def generate_reason(self, tool_name: str, intents: List[Tuple[str, float]], 
                       languages: List[str], prompt: str) -> str:
        """Generate a contextual reason for recommending a tool."""
        reasons = []
        
        # Intent-based reasons
        if intents:
            top_intent = intents[0][0]
            intent_reasons = {
                "coding": "for code implementation and development",
                "debugging": "for systematic debugging and root cause analysis",
                "analysis": "for deep code analysis and understanding",
                "refactoring": "for code improvement and restructuring",
                "file_operations": "for file manipulation and management",
                "web_search": "for finding documentation and solutions",
                "github_ops": "for GitHub repository operations",
                "ui_development": "for UI component development",
                "testing": "for automated testing and validation",
                "complex_task": "for strategic planning and complex problem solving"
            }
            if top_intent in intent_reasons:
                reasons.append(intent_reasons[top_intent])
        
        # Tool-specific reasons
        tool_reasons = {
            "zen": "Expert AI analysis and strategic guidance",
            "filesystem": "Efficient file and directory operations",
            "tavily": "Real-time web search and documentation",
            "tree_sitter": "Advanced AST analysis and pattern detection",
            "github": "GitHub integration and automation",
            "playwright": "Browser automation and UI testing",
            "shadcn": "Modern React component implementation",
            "memory": "Semantic code search and relationship tracking",
            "context7": "Comprehensive library documentation"
        }
        
        if tool_name in tool_reasons:
            return tool_reasons[tool_name]
        
        return "Relevant for your current task"
    
    def generate_injection(self, prompt: str) -> str:
        """Generate the MCP tool recommendation injection."""
        recommendations = self.get_tool_recommendations(prompt, max_tools=3)
        
        if not recommendations:
            return ""
        
        lines = ["<mcp-recommendations>"]
        lines.append("🛠️ **Recommended MCP Tools**")
        lines.append("")
        
        for i, rec in enumerate(recommendations, 1):
            tool_info = rec["info"]
            reason = rec["reason"]
            
            lines.append(f"{i}. **{tool_info['name']}**")
            lines.append(f"   {tool_info['description']}")
            lines.append(f"   *{reason}*")
            lines.append("   ```python")
            lines.append(f"   {tool_info['example']}")
            lines.append("   ```")
            lines.append("")
        
        # Add usage tips based on detected intent
        intents = self.detect_intents(prompt)
        if intents and intents[0][1] > 2.0:  # Strong intent detected
            lines.append("💡 **Quick Tips:**")
            top_intent = intents[0][0]
            
            tips = {
                "debugging": "• Use ZEN's debug tool for systematic investigation\n",
                "analysis": "• Begin with Tree-sitter for structural analysis\n• Follow up with ZEN for strategic insights",
                "web_search": "• Use Tavily for current information\n• Context7 for specific library documentation",
                "complex_task": "• Always start with ZEN for strategic planning\n• Break down into subtasks using specialized tools"
            }
            
            if top_intent in tips:
                lines.append(tips[top_intent])
        
        lines.append("</mcp-recommendations>")
        
        return "\n".join(lines)


def get_mcp_injection(prompt: str) -> str:
    """Main entry point for MCP tool recommendations."""
    injector = MCPInjector()
    return injector.generate_injection(prompt)


# Testing
if __name__ == "__main__":
    test_prompts = [
        "Debug this Python function that's throwing a NullPointerException",
        "Create a new React component for user authentication",
        "Search for the latest React hooks best practices",
        "Analyze the complexity of our authentication module",
        "Create a pull request for the bug fix"
    ]
    
    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        print("-" * 50)
        print(get_mcp_injection(prompt))