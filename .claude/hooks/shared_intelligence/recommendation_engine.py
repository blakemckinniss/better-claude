#!/usr/bin/env python3
"""Recommendation engine for proactive tool suggestions.

This module provides intelligent recommendations for better tool choices
and workflow optimizations based on usage patterns and best practices.

Features:
- Proactive tool recommendations
- Usage pattern analysis
- Best practice suggestions
- Learning from user behavior
"""

import time
from typing import Any, Dict, List, Optional

from .config import get_config


class RecommendationEngine:
    """Intelligent recommendation system for tool optimization."""

    # Best practice recommendations
    RECOMMENDATIONS = {
        "modern_cli_tools": {
            "grep -> rg": {
                "reason": "ripgrep is 10-100x faster with better defaults",
                "example": "rg 'pattern' instead of grep 'pattern'",
                "performance_gain": "10-100x",
                "learn_more": "https://github.com/BurntSushi/ripgrep",
            },
            "find -> fd": {
                "reason": "fd is simpler and faster with intuitive syntax",
                "example": "fd 'filename' instead of find . -name 'filename'",
                "performance_gain": "3-10x",
                "learn_more": "https://github.com/sharkdp/fd",
            },
            "cat -> bat": {
                "reason": "bat provides syntax highlighting and line numbers",
                "example": "bat file.py instead of cat file.py",
                "performance_gain": "Better readability",
                "learn_more": "https://github.com/sharkdp/bat",
            },
            "ls -> lsd": {
                "reason": "lsd provides better formatting and icons",
                "example": "lsd -la instead of ls -la",
                "performance_gain": "Better visualization",
                "learn_more": "https://github.com/Peltoche/lsd",
            },
            "du -> dust": {
                "reason": "dust provides better disk usage visualization",
                "example": "dust instead of du -h",
                "performance_gain": "Better insights",
                "learn_more": "https://github.com/bootandy/dust",
            },
        },
        "workflow_patterns": {
            "batch_operations": {
                "trigger": "multiple_sequential_operations",
                "recommendation": "Use batch operations instead of sequential ones",
                "examples": [
                    "mcp__filesystem__read_multiple_files for multiple reads",
                    "Parallel Bash commands with &&",
                    "MultiEdit for multiple file changes",
                ],
                "benefit": "5-50x performance improvement",
            },
            "streaming_operations": {
                "trigger": "large_file_operations",
                "recommendation": "Use streaming operations for large files",
                "examples": [
                    "head -n 100 file.txt | bat for previewing large files",
                    "sed -n '100,200p' file.txt for specific line ranges",
                    "rg 'pattern' file.txt for searching large files",
                ],
                "benefit": "Instant response vs waiting for full file load",
            },
            "targeted_edits": {
                "trigger": "full_file_rewrites",
                "recommendation": "Use targeted edits instead of full rewrites",
                "examples": [
                    "Edit tool for specific changes",
                    "MultiEdit for multiple targeted changes",
                    "sed for simple text replacements",
                ],
                "benefit": "Safer and more precise changes",
            },
        },
        "mcp_tools": {
            "filesystem_operations": {
                "recommendation": "Use MCP filesystem tools for better error handling",
                "examples": [
                    "mcp__filesystem__read_text_file instead of Read",
                    "mcp__filesystem__write_file instead of Write",
                    "mcp__filesystem__edit_file instead of Edit",
                ],
                "benefits": [
                    "Better error handling and validation",
                    "Consistent API across operations",
                    "Built-in safety checks",
                ],
            },
        },
    }

    # Learning patterns from user behavior
    USAGE_PATTERNS: Dict[str, Dict[str, Any]] = {
        "frequent_tools": {},
        "common_workflows": {},
        "optimization_acceptance": {},
        "performance_improvements": {},
    }

    def __init__(self):
        """Initialize the recommendation engine."""
        self.config = get_config()
        self.usage_history: List[Dict[str, Any]] = []
        self.recommendation_cache: Dict[str, Dict[str, Any]] = {}
        self.user_preferences: Dict[str, Any] = {}

    def _get_cli_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get modern CLI tool recommendations."""
        recommendations: List[Dict[str, Any]] = []
        
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            
            modern_cli_tools = self.RECOMMENDATIONS["modern_cli_tools"]
            if isinstance(modern_cli_tools, dict):
                for old_new, details in modern_cli_tools.items():
                    if isinstance(details, dict):
                        old_tool = old_new.split(" -> ")[0]
                        new_tool = old_new.split(" -> ")[1]
                        
                        if old_tool in command and new_tool not in command:
                            recommendations.append({
                                "type": "modern_cli",
                                "severity": "suggestion",
                                "title": f"Consider using {new_tool} instead of {old_tool}",
                                "reason": details.get("reason", "Performance improvement"),
                                "example": details.get("example", "See documentation"),
                                "performance_gain": details.get("performance_gain", "Better performance"),
                                "learn_more": details.get("learn_more"),
                                "original_command": command,
                                "suggested_command": command.replace(old_tool, new_tool),
                            })
        
        return recommendations

    def _get_recent_operations(self, tool_name: str, window: int) -> List[Dict[str, Any]]:
        """Get recent operations for a specific tool."""
        current_time = time.time()
        return [
            op for op in self.usage_history
            if (
                op.get("tool_name") == tool_name and
                current_time - op.get("timestamp", 0) < window
            )
        ]

    def _detect_sequential_pattern(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Detect if user is performing sequential operations."""
        if not context:
            return False
        
        # Check for multiple file operations
        recent_ops = self._get_recent_operations(tool_name, 60)  # Last minute
        return len(recent_ops) > 2

    def _detect_large_file_pattern(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> bool:
        """Detect operations on large files."""
        if tool_name not in ["Read", "Write", "Edit"]:
            return False
        
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return False
        
        try:
            import os
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return file_size > 1_000_000  # 1MB
        except Exception:
            pass
        
        return False

    def _detect_full_rewrite_pattern(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> bool:
        """Detect full file rewrite operations."""
        if tool_name != "Write":
            return False
        
        content = tool_input.get("content", "")
        file_path = tool_input.get("file_path", "")
        
        if not content or not file_path:
            return False
        
        try:
            import os
            if os.path.exists(file_path):
                with open(file_path, encoding='utf-8') as f:
                    current_content = f.read()
                
                # If new content is significantly different, it's likely a rewrite
                return len(content) > len(current_content) * 0.5
        except Exception:
            pass
        
        return False

    def _get_workflow_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get workflow pattern recommendations."""
        recommendations: List[Dict[str, Any]] = []
        
        # Batch operations recommendation
        if self._detect_sequential_pattern(tool_name, context):
            workflow_patterns = self.RECOMMENDATIONS["workflow_patterns"]
            if isinstance(workflow_patterns, dict):
                batch_rec = workflow_patterns.get("batch_operations", {})
                if isinstance(batch_rec, dict):
                    recommendations.append({
                        "type": "workflow_optimization",
                        "severity": "suggestion",
                        "title": "Consider batch operations for better performance",
                        "reason": batch_rec.get("recommendation", "Batch operations improve performance"),
                        "examples": batch_rec.get("examples", []),
                        "benefit": batch_rec.get("benefit", "Better performance"),
                        "trigger": "Sequential operations detected",
                    })
        
        # Streaming operations recommendation
        if self._detect_large_file_pattern(tool_name, tool_input):
            workflow_patterns = self.RECOMMENDATIONS["workflow_patterns"]
            if isinstance(workflow_patterns, dict):
                streaming_rec = workflow_patterns.get("streaming_operations", {})
                if isinstance(streaming_rec, dict):
                    recommendations.append({
                        "type": "workflow_optimization",
                        "severity": "suggestion",
                        "title": "Consider streaming operations for large files",
                        "reason": streaming_rec.get("recommendation", "Streaming improves performance"),
                        "examples": streaming_rec.get("examples", []),
                        "benefit": streaming_rec.get("benefit", "Better performance"),
                        "trigger": "Large file operation detected",
                    })
        
        # Targeted edits recommendation
        if self._detect_full_rewrite_pattern(tool_name, tool_input):
            workflow_patterns = self.RECOMMENDATIONS["workflow_patterns"]
            if isinstance(workflow_patterns, dict):
                targeted_rec = workflow_patterns.get("targeted_edits", {})
                if isinstance(targeted_rec, dict):
                    recommendations.append({
                        "type": "workflow_optimization",
                        "severity": "suggestion",
                        "title": "Consider targeted edits instead of full rewrites",
                        "reason": targeted_rec.get("recommendation", "Targeted edits are safer"),
                        "examples": targeted_rec.get("examples", []),
                        "benefit": targeted_rec.get("benefit", "Safer changes"),
                        "trigger": "Full file rewrite detected",
                    })
        
        return recommendations

    def _get_mcp_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get MCP tool recommendations."""
        recommendations: List[Dict[str, Any]] = []
        
        # Recommend MCP filesystem tools
        if tool_name in ["Read", "Write", "Edit"]:
            mcp_tools = self.RECOMMENDATIONS["mcp_tools"]
            if isinstance(mcp_tools, dict):
                mcp_rec = mcp_tools.get("filesystem_operations", {})
                if isinstance(mcp_rec, dict):
                    mcp_tool_map = {
                        "Read": "mcp__filesystem__read_text_file",
                        "Write": "mcp__filesystem__write_file",
                        "Edit": "mcp__filesystem__edit_file",
                    }
                    
                    recommended_tool = mcp_tool_map.get(tool_name)
                    if recommended_tool:
                        recommendations.append({
                            "type": "mcp_tool",
                            "severity": "info",
                            "title": f"Consider using {recommended_tool}",
                            "reason": mcp_rec.get("recommendation", "Better error handling"),
                            "benefits": mcp_rec.get("benefits", []),
                            "current_tool": tool_name,
                            "recommended_tool": recommended_tool,
                        })
        
        return recommendations

    def _get_recent_tool_usage(self, window: int = 300) -> Dict[str, int]:
        """Get recent tool usage counts."""
        current_time = time.time()
        recent_ops = [
            op for op in self.usage_history
            if current_time - op.get("timestamp", 0) < window
        ]
        
        tool_counts: Dict[str, int] = {}
        for op in recent_ops:
            tool_name = op.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        return tool_counts

    def _detect_complex_task_pattern(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Detect complex tasks that would benefit from agents."""
        # Check for multiple different tools in short timeframe
        recent_tools = self._get_recent_tool_usage(300)  # Last 5 minutes
        
        # Complex task indicators
        complexity_indicators = [
            len(recent_tools) > 4,  # Using many different tools
            any("search" in str(context).lower() for _ in [1] if context),  # Search operations
            any("analyze" in str(context).lower() for _ in [1] if context),  # Analysis tasks
            tool_name in ["Bash"] and context and len(str(context)) > 200,  # Complex commands
        ]
        
        return any(complexity_indicators)

    def _get_contextual_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get contextual recommendations based on usage patterns."""
        recommendations: List[Dict[str, Any]] = []
        
        # Analyze recent usage patterns
        recent_tools = self._get_recent_tool_usage()
        
        # Recommend consolidation if using many different tools
        if len(recent_tools) > 5:
            recommendations.append({
                "type": "workflow_efficiency",
                "severity": "info",
                "title": "Consider consolidating tool usage",
                "reason": f"Using {len(recent_tools)} different tools recently",
                "suggestion": "Group similar operations together for better efficiency",
                "tools_used": list(recent_tools.keys()),
            })
        
        # Recommend agents for complex tasks
        if self._detect_complex_task_pattern(tool_name, context):
            recommendations.append({
                "type": "agent_suggestion",
                "severity": "suggestion",
                "title": "Consider using specialized agents",
                "reason": "Complex task detected - agents can provide better guidance",
                "examples": [
                    "Use zen agents for complex analysis",
                    "Use Task tool for multi-step operations",
                    "Use specialized search agents for code exploration",
                ],
                "benefit": "Expert guidance and optimized workflows",
            })
        
        return recommendations

    def _filter_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        tool_name: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Filter and prioritize recommendations."""
        # Remove duplicates
        seen_titles = set()
        filtered = []
        
        for rec in recommendations:
            title = rec.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                filtered.append(rec)
        
        # Sort by severity and relevance
        severity_order = {"critical": 0, "high": 1, "medium": 2, "suggestion": 3, "info": 4}
        filtered.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 5))
        
        # Limit to top 3 recommendations to avoid overwhelming user
        return filtered[:3]

    def _record_usage(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Record usage for learning patterns."""
        self.usage_history.append({
            "timestamp": time.time(),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "context": context,
        })
        
        # Keep only recent history (last hour)
        cutoff_time = time.time() - 3600
        self.usage_history = [
            op for op in self.usage_history
            if op.get("timestamp", 0) > cutoff_time
        ]

    def get_recommendations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get recommendations for better tool usage.

        Args:
            tool_name: Current tool being requested
            tool_input: Tool input parameters
            context: Optional context information

        Returns:
            List of recommendations with reasons and examples
        """
        try:
            recommendations: List[Dict[str, Any]] = []
            
            # Record usage for learning
            self._record_usage(tool_name, tool_input, context)
            
            # Get modern CLI tool recommendations
            cli_recs = self._get_cli_recommendations(tool_name, tool_input)
            recommendations.extend(cli_recs)
            
            # Get workflow pattern recommendations
            workflow_recs = self._get_workflow_recommendations(tool_name, tool_input, context)
            recommendations.extend(workflow_recs)
            
            # Get MCP tool recommendations
            mcp_recs = self._get_mcp_recommendations(tool_name, tool_input)
            recommendations.extend(mcp_recs)
            
            # Get contextual recommendations
            contextual_recs = self._get_contextual_recommendations(tool_name, tool_input, context)
            recommendations.extend(contextual_recs)
            
            # Filter and prioritize recommendations
            filtered_recs = self._filter_recommendations(recommendations, tool_name, context)
            
            return filtered_recs
            
        except Exception as e:
            # Don't fail the operation if recommendations fail
            return [{
                "type": "error",
                "message": f"Recommendation error: {str(e)}",
                "severity": "info",
            }]

    def _count_optimization_opportunities(self) -> int:
        """Count potential optimization opportunities from recent usage."""
        opportunities = 0
        
        # Count sequential operations
        for tool_name in ["Read", "Write", "Edit"]:
            recent_ops = self._get_recent_operations(tool_name, 300)
            if len(recent_ops) > 2:
                opportunities += 1
        
        # Count legacy command usage
        bash_ops = self._get_recent_operations("Bash", 300)
        for op in bash_ops:
            command = op.get("tool_input", {}).get("command", "")
            if any(old_cmd in command for old_cmd in ["grep", "find", "cat"]):
                opportunities += 1
        
        return opportunities

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics and learning insights."""
        tool_usage = self._get_recent_tool_usage(3600)  # Last hour
        
        return {
            "total_operations": len(self.usage_history),
            "tool_distribution": tool_usage,
            "most_used_tool": max(tool_usage.items(), key=lambda x: x[1])[0] if tool_usage else None,
            "recommendations_generated": len(self.recommendation_cache),
            "optimization_opportunities": self._count_optimization_opportunities(),
        }


# Global recommendation engine instance
_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get the global recommendation engine instance."""
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine


def get_tool_recommendations(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Get recommendations for better tool usage.

    This is the main entry point for the recommendation system.

    Returns:
        List of recommendations with reasons and examples
    """
    engine = get_recommendation_engine()
    return engine.get_recommendations(tool_name, tool_input, context)
