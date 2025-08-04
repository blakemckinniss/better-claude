#!/usr/bin/env python3
"""Recommendation Engine for Hook System.

Provides intelligent tool recommendations based on context and patterns.
"""

from typing import Any, Dict, List


def _has_recent_analysis(recent_ops: List[Dict[str, Any]]) -> bool:
    """Check if user has done recent analysis."""
    analysis_tools = ["Read", "Grep", "Glob", "mcp__filesystem__read_text_file"]
    return any(op.get("tool_name") in analysis_tools for op in recent_ops[-3:])


def _is_repetitive_pattern(tool_name: str, recent_ops: List[Dict[str, Any]]) -> bool:
    """Check if current tool usage shows repetitive pattern."""
    recent_same_tools = [op for op in recent_ops if op.get("tool_name") == tool_name]
    return len(recent_same_tools) >= 2


def _get_batch_tool(tool_name: str) -> str:
    """Get appropriate batch tool for given tool."""
    batch_mapping = {
        "Read": "mcp__filesystem__read_multiple_files",
        "Edit": "MultiEdit",
        "Write": "MultiEdit",
    }
    return batch_mapping.get(tool_name, tool_name)


def _is_complex_operation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if operation is complex enough to benefit from agent."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Complex bash commands
        complexity_indicators = ["|", "&&", "||", "for ", "while ", "if ", "$("]
        return any(indicator in command for indicator in complexity_indicators)
    
    if tool_name in ["Edit", "MultiEdit"]:
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        # Large or multi-line edits
        return (
            len(old_string) > 200 or len(new_string) > 200 or 
            old_string.count("\n") > 5 or new_string.count("\n") > 5
        )
    
    return False


def _has_recent_agent_use(recent_ops: List[Dict[str, Any]]) -> bool:
    """Check if user has recently used agents."""
    agent_tools = [
        "mcp__zen__chat", "mcp__zen__debug", "mcp__zen__refactor", 
        "mcp__zen__analyze", "mcp__zen__testgen",
    ]
    return any(op.get("tool_name") in agent_tools for op in recent_ops[-5:])


def _get_context_recommendations(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get recommendations based on session context."""
    recommendations = []
    recent_ops = context.get("recent_operations", [])

    # If user hasn't used analysis tools, recommend them
    if tool_name in ["Edit", "Write", "MultiEdit"] and not _has_recent_analysis(recent_ops):
        recommendations.append({
            "type": "context",
            "severity": "suggestion",
            "title": "Consider analyzing before editing",
            "reason": "Reading the file first helps understand structure and avoid errors",
            "suggested_tool": "Read",
            "suggested_action": f"Read {tool_input.get('file_path', 'the file')} to understand its structure",
            "priority": 8,
        })

    # If user is doing repetitive operations, suggest batching
    if _is_repetitive_pattern(tool_name, recent_ops):
        recommendations.append({
            "type": "efficiency",
            "severity": "suggestion", 
            "title": "Batch similar operations",
            "reason": "Multiple similar operations can often be combined for efficiency",
            "suggested_tool": _get_batch_tool(tool_name),
            "suggested_action": "Consider batching these operations together",
            "priority": 7,
        })

    # If complex operation without agent, suggest delegation
    if _is_complex_operation(tool_name, tool_input) and not _has_recent_agent_use(recent_ops):
        recommendations.append({
            "type": "delegation",
            "severity": "info",
            "title": "Consider using specialized agent",
            "reason": "Complex operations benefit from agent planning and execution",
            "suggested_tool": "mcp__zen__chat",
            "suggested_action": "Delegate complex operation to specialized agent for better results",
            "priority": 6,
        })

    return recommendations


def _get_tool_specific_recommendations(
    tool_name: str, tool_input: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get recommendations specific to the current tool."""
    recommendations = []

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Recommend modern CLI alternatives
        if "find" in command:
            recommendations.append({
                "type": "tool_upgrade",
                "severity": "suggestion",
                "title": "Use 'fd' instead of 'find'",
                "reason": "fd is faster and has better defaults than find",
                "suggested_tool": "Bash",
                "suggested_action": f"Replace 'find' with 'fd' in: {command}",
                "priority": 5,
            })

        if "grep" in command:
            recommendations.append({
                "type": "tool_upgrade", 
                "severity": "suggestion",
                "title": "Use 'rg' (ripgrep) instead of 'grep'",
                "reason": "ripgrep is significantly faster and has better output",
                "suggested_tool": "Bash",
                "suggested_action": f"Replace 'grep' with 'rg' in: {command}",
                "priority": 5,
            })

    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            # Suggest using Grep for finding specific content
            recommendations.append({
                "type": "efficiency",
                "severity": "info",
                "title": "Use Grep for searching within files",
                "reason": "If looking for specific content, Grep is more efficient than reading entire file",
                "suggested_tool": "Grep",
                "suggested_action": f"Use Grep to search for patterns in {file_path}",
                "priority": 4,
            })

    elif tool_name in ["Edit", "MultiEdit"]:
        # Suggest testing after edits
        recommendations.append({
            "type": "quality",
            "severity": "info", 
            "title": "Test changes after editing",
            "reason": "Testing ensures your changes work as expected",
            "suggested_tool": "Bash",
            "suggested_action": "Run relevant tests or validation commands",
            "priority": 6,
        })

    return recommendations


def _has_recent_git_activity(recent_ops: List[Dict[str, Any]]) -> bool:
    """Check if user has recent git activity."""
    for op in recent_ops[-5:]:
        if op.get("tool_name") == "Bash":
            command = op.get("tool_input", {}).get("command", "")
            if command.startswith("git "):
                return True
    return False


def _is_significant_change(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if this represents a significant change."""
    if tool_name in ["Edit", "MultiEdit"]:
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        
        # Consider it significant if it's a large change or adds new functionality
        return (
            len(old_string) > 300 or len(new_string) > 300 or
            "def " in new_string or "class " in new_string or
            "function " in new_string
        )
    
    if tool_name == "Write":
        content = tool_input.get("content", "")
        return len(content) > 500
    
    return False


def _get_workflow_recommendations(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get workflow improvement recommendations."""
    recommendations = []
    recent_ops = context.get("recent_operations", [])

    # Suggest using version control
    if tool_name in ["Edit", "Write", "MultiEdit"] and not _has_recent_git_activity(recent_ops):
        recommendations.append({
            "type": "best_practice",
            "severity": "info",
            "title": "Consider version control",
            "reason": "Git helps track changes and enables safe experimentation",
            "suggested_tool": "Bash",
            "suggested_action": "git add . && git commit -m 'descriptive message'",
            "priority": 3,
        })

    # Suggest documentation for complex changes
    if _is_significant_change(tool_name, tool_input):
        recommendations.append({
            "type": "documentation",
            "severity": "suggestion",
            "title": "Document significant changes",
            "reason": "Complex changes benefit from documentation for future reference",
            "suggested_tool": "Write",
            "suggested_action": "Add comments or update documentation explaining the changes",
            "priority": 4,
        })

    return recommendations


def _get_educational_recommendations(
    tool_name: str, tool_input: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get educational recommendations to improve user skills."""
    recommendations = []

    # Bash command education
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Complex pipe chains - suggest learning about each component
        if command.count("|") >= 2:
            recommendations.append({
                "type": "education",
                "severity": "info",
                "title": "Complex pipe chain detected",
                "reason": "Understanding each component helps debug and optimize",
                "suggested_tool": "mcp__zen__chat",
                "suggested_action": "Ask about bash pipe optimization and debugging techniques",
                "priority": 2,
            })

    # File operation patterns
    if tool_name in ["Edit", "MultiEdit"]:
        old_string = tool_input.get("old_string", "")
        if len(old_string) > 500:
            recommendations.append({
                "type": "education",
                "severity": "info",
                "title": "Large edit operation",
                "reason": "Large edits can be risky - consider incremental approaches",
                "suggested_tool": "mcp__zen__refactor",
                "suggested_action": "Learn about safe refactoring techniques for large changes",
                "priority": 3,
            })

    return recommendations


def _get_recommendation_priority(recommendation: Dict[str, Any]) -> int:
    """Calculate priority score for recommendation."""
    base_priority = recommendation.get("priority", 1)
    severity = recommendation.get("severity", "info")
    
    # Adjust based on severity
    severity_multipliers = {
        "critical": 2.0,
        "warning": 1.5,
        "suggestion": 1.2,
        "info": 1.0,
    }
    
    return int(base_priority * severity_multipliers.get(severity, 1.0))


def get_tool_recommendations(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get tool recommendations based on current usage and context.

    Args:
        tool_name: Name of the tool being used
        tool_input: Input parameters for the tool
        context: Session and operation context

    Returns:
        List of recommendation dictionaries
    """
    recommendations = []

    # Context-aware recommendations
    recommendations.extend(_get_context_recommendations(tool_name, tool_input, context))

    # Tool-specific recommendations
    recommendations.extend(_get_tool_specific_recommendations(tool_name, tool_input))

    # Workflow improvement recommendations
    recommendations.extend(_get_workflow_recommendations(tool_name, tool_input, context))

    # Educational recommendations
    recommendations.extend(_get_educational_recommendations(tool_name, tool_input))

    # Sort by priority and return top recommendations
    recommendations.sort(key=lambda x: _get_recommendation_priority(x), reverse=True)
    return recommendations[:5]  # Return top 5 recommendations
