#!/usr/bin/env python3
"""Intelligent command routing system for optimal Claude Code performance.

This module provides intelligent routing of tool requests to optimal alternatives,
preventing anti-patterns and guiding Claude toward efficient tool usage.

Security Architecture:
- Defense in depth with multiple validation layers
- Fail-secure behavior (allow operation if routing fails)
- Performance-aware circuit breakers
- Comprehensive logging and audit trails
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import get_config


class IntelligentRouter:
    """Core routing engine for intelligent tool optimization."""

    # Tool routing rules with security classifications
    TOOL_ROUTING_RULES: Dict[str, Dict[str, Any]] = {
        # File operations - redirect to batch/streaming alternatives
        "Read": {
            "alternatives": [
                {
                    "tool": "Bash",
                    "command_template": "rg --line-number '{pattern}' {file_path}",
                    "reason": "Use ripgrep for targeted content search - 10-100x faster than Read",
                    "conditions": ["file_size_large", "search_pattern_detected"],
                    "security_level": "safe",
                },
                {
                    "tool": "mcp__filesystem__read_multiple_files",
                    "reason": "Use batch read for multiple files - prevents sequential Read operations",
                    "conditions": ["multiple_files_context"],
                    "security_level": "safe",
                },
                {
                    "tool": "Bash",
                    "command_template": "sed -n '{start_line},{end_line}p' {file_path}",
                    "reason": "Use sed for reading specific line ranges - more efficient than full Read",
                    "conditions": ["line_range_context"],
                    "security_level": "safe",
                },
            ],
        },
        "Write": {
            "alternatives": [
                {
                    "tool": "mcp__filesystem__edit_file",
                    "reason": "Use targeted edits instead of full file rewrites - safer and more precise",
                    "conditions": ["partial_change_detected"],
                    "security_level": "safe",
                },
                {
                    "tool": "mcp__filesystem__write_file",
                    "reason": "Use MCP filesystem for better error handling and validation",
                    "conditions": ["always"],
                    "security_level": "safe",
                },
            ],
        },
        # Command operations - modern alternatives
        "Bash": {
            "command_improvements": {
                "grep": {
                    "alternative": "rg",
                    "template": "rg {args}",
                    "reason": "ripgrep is 10-100x faster than grep with better defaults",
                    "security_level": "safe",
                },
                "find": {
                    "alternative": "fd",
                    "template": "fd {args}",
                    "reason": "fd is simpler and faster than find with intuitive syntax",
                    "security_level": "safe",
                },
                "cat": {
                    "alternative": "bat",
                    "template": "bat {args}",
                    "reason": "bat provides syntax highlighting and better formatting",
                    "security_level": "safe",
                },
                "ls": {
                    "alternative": "lsd",
                    "template": "lsd {args}",
                    "reason": "lsd provides better formatting and icons",
                    "security_level": "safe",
                },
                "du": {
                    "alternative": "dust",
                    "template": "dust {args}",
                    "reason": "dust provides better visualization of disk usage",
                    "security_level": "safe",
                },
                "ps": {
                    "alternative": "procs",
                    "template": "procs {args}",
                    "reason": "procs provides modern process information with colors",
                    "security_level": "safe",
                },
            },
        },
    }

    # Anti-pattern detection rules
    ANTI_PATTERNS: Dict[str, Dict[str, Any]] = {
        "sequential_reads": {
            "pattern": "multiple_read_operations_detected",
            "severity": "high",
            "block": True,
            "message": "❌ ANTI-PATTERN: Sequential Read operations detected - use batch operations instead",
            "suggestion": "Use mcp__filesystem__read_multiple_files or parallel Bash commands",
        },
        "full_file_rewrite": {
            "pattern": "large_file_complete_replacement",
            "severity": "medium",
            "block": False,
            "message": "⚠️ ANTI-PATTERN: Full file rewrite detected - consider targeted edits",
            "suggestion": "Use Edit tool for specific changes or MultiEdit for multiple changes",
        },
        "inefficient_search": {
            "pattern": "read_for_content_search",
            "severity": "medium",
            "block": True,
            "message": "❌ ANTI-PATTERN: Using Read for content search - use search tools instead",
            "suggestion": "Use rg, grep, or search-specific tools for better performance",
        },
        "legacy_commands": {
            "pattern": "old_command_usage",
            "severity": "low",
            "block": False,
            "message": "💡 PERFORMANCE: Legacy command detected - modern alternatives available",
            "suggestion": "Consider using modern CLI tools for better performance",
        },
    }

    # Performance circuit breakers
    CIRCUIT_BREAKERS: Dict[str, Dict[str, Union[int, str]]] = {
        "large_file_read": {
            "threshold": 1000000,  # 1MB
            "action": "redirect",
            "target": "streaming_read",
        },
        "multiple_file_ops": {
            "threshold": 5,  # More than 5 files
            "action": "batch",
            "target": "batch_operations",
        },
        "expensive_operations": {
            "threshold": 10,  # Operations per minute
            "action": "throttle",
            "target": "rate_limit",
        },
    }

    def __init__(self):
        """Initialize the intelligent router."""
        self.config = get_config()
        self.operation_history = []
        self.circuit_breaker_state = {}

    def _validate_privilege_escalation(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Validate that routing to higher-privilege tools is safe."""
        # Only allow safe, read-only operations or well-validated writes
        if tool_name == "Read":
            # Read -> Bash is safe for search operations
            return True
        elif tool_name == "Write":
            # Write -> Edit is safe for targeted changes
            return True

        return False

    def _validate_tool_security(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Validate that routing doesn't introduce security vulnerabilities."""
        # Ensure we don't route to more privileged operations
        privileged_tools = ["Bash", "mcp__filesystem__write_file"]
        if tool_name not in privileged_tools and any(
            alt.get("tool") in privileged_tools
            for alt in self.TOOL_ROUTING_RULES.get(tool_name, {}).get("alternatives", [])
        ):
            # Additional validation needed for privilege escalation
            if not self._validate_privilege_escalation(tool_name, tool_input):
                return False

        return True

    def _check_circuit_breakers(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check performance circuit breakers."""
        warnings = []

        # Large file circuit breaker
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            try:
                import os
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    threshold = self.CIRCUIT_BREAKERS["large_file_read"]["threshold"]
                    if isinstance(threshold, int) and file_size > threshold:
                        return (
                            True,
                            "❌ CIRCUIT BREAKER: Large file read blocked - use streaming alternatives",
                            [],
                            {
                                "tool": "Bash",
                                "command": f"head -n 100 '{file_path}' | bat",
                                "reason": "Stream first 100 lines instead of loading entire file",
                            },
                        )
            except Exception:
                pass

        # Multiple operation circuit breaker
        recent_ops = [
            op for op in self.operation_history 
            if isinstance(op, dict) and time.time() - op.get("timestamp", 0) < 60
        ]
        threshold = self.CIRCUIT_BREAKERS["expensive_operations"]["threshold"]
        if isinstance(threshold, int) and len(recent_ops) > threshold:
            warnings.append("⚠️ High operation frequency detected - consider batch operations")

        return False, "", warnings, None

    def _looks_like_search_context(self, context: Optional[Dict[str, Any]]) -> bool:
        """Determine if the context suggests this is a search operation."""
        if not context:
            return False

        # Check for search-related keywords in context
        search_indicators = ["find", "search", "locate", "grep", "pattern", "contains"]
        if isinstance(context, dict):
            context_str = str(context).lower()
            return any(indicator in context_str for indicator in search_indicators)
        return False

    def _is_full_file_rewrite(self, file_path: str, new_content: str) -> bool:
        """Check if this is a full file rewrite vs targeted change."""
        try:
            import os
            if os.path.exists(file_path):
                with open(file_path, encoding="utf-8") as f:
                    current_content = f.read()

                # If content is completely different, it's a full rewrite
                if len(new_content) > len(current_content) * 0.8:
                    return True
        except Exception:
            pass

        return False

    def _detect_anti_patterns(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Detect and prevent anti-patterns."""
        warnings = []

        # Sequential reads anti-pattern
        if tool_name == "Read" and context:
            recent_reads = context.get("recent_reads", 0)
            if isinstance(recent_reads, int) and recent_reads > 2:
                return (
                    True,
                    str(self.ANTI_PATTERNS["sequential_reads"]["message"]),
                    [],
                    {
                        "tool": "mcp__filesystem__read_multiple_files",
                        "reason": str(self.ANTI_PATTERNS["sequential_reads"]["suggestion"]),
                    },
                )

        # Inefficient search anti-pattern
        if tool_name == "Read":
            # Check if this looks like a search operation
            file_path = tool_input.get("file_path", "")
            if self._looks_like_search_context(context):
                return (
                    True,
                    str(self.ANTI_PATTERNS["inefficient_search"]["message"]),
                    [],
                    {
                        "tool": "Bash",
                        "command": f"rg --line-number --context 3 'SEARCH_PATTERN' '{file_path}'",
                        "reason": str(self.ANTI_PATTERNS["inefficient_search"]["suggestion"]),
                    },
                )

        # Full file rewrite anti-pattern
        if tool_name == "Write":
            content = tool_input.get("content", "")
            file_path = tool_input.get("file_path", "")
            if self._is_full_file_rewrite(file_path, content):
                warnings.append(str(self.ANTI_PATTERNS["full_file_rewrite"]["message"]))

        return False, "", warnings, None

    def _conditions_met(
        self,
        conditions: List[str],
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if routing conditions are met."""
        if not conditions or "always" in conditions:
            return True

        for condition in conditions:
            if condition == "file_size_large":
                file_path = tool_input.get("file_path", "")
                try:
                    import os
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 100000:
                        return True
                except Exception:
                    pass

            elif condition == "multiple_files_context" and context:
                file_count = context.get("file_count", 1)
                if isinstance(file_count, int) and file_count > 1:
                    return True

            elif condition == "search_pattern_detected":
                if self._looks_like_search_context(context):
                    return True

            elif condition == "partial_change_detected":
                content = tool_input.get("content", "")
                if len(content) < 10000:  # Small changes suggest targeted edits
                    return True

        return False

    def _find_optimizations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Find optimization opportunities."""
        warnings = []

        # Tool-specific optimizations
        if tool_name in self.TOOL_ROUTING_RULES:
            rules = self.TOOL_ROUTING_RULES[tool_name]

            # Check alternatives
            alternatives = rules.get("alternatives")
            if isinstance(alternatives, list):
                for alt in alternatives:
                    if isinstance(alt, dict) and self._conditions_met(alt.get("conditions", []), tool_input, context):
                        if alt.get("security_level") == "safe":
                            return (
                                True,
                                f"💡 OPTIMIZATION: {alt.get('reason', 'Optimization available')}",
                                [],
                                alt,
                            )

            # Check command improvements for Bash
            if tool_name == "Bash":
                command = tool_input.get("command", "")
                improvements = rules.get("command_improvements")
                if isinstance(improvements, dict):
                    for old_cmd, improvement in improvements.items():
                        if isinstance(improvement, dict) and command.strip().startswith(old_cmd):
                            warnings.append(
                                f"💡 {improvement.get('reason', 'Improvement available')} - Consider: {improvement.get('template', 'Alternative available')}",
                            )

        return False, "", warnings, None

    def analyze_tool_request(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Analyze tool request for optimization opportunities.

        Args:
            tool_name: Name of the tool being requested
            tool_input: Input parameters for the tool
            context: Optional context about the current session

        Returns:
            (should_redirect, reason, warnings, alternative_action)
        """
        try:
            # Security validation - ensure we don't introduce vulnerabilities
            if not self._validate_tool_security(tool_name, tool_input):
                return False, "Security validation failed", [], None

            # Check circuit breakers first
            circuit_result = self._check_circuit_breakers(tool_name, tool_input)
            if circuit_result[0]:  # Circuit breaker triggered
                return circuit_result

            # Detect anti-patterns
            anti_pattern_result = self._detect_anti_patterns(tool_name, tool_input, context)
            if anti_pattern_result[0]:  # Anti-pattern detected and should block
                return anti_pattern_result

            # Look for optimization opportunities
            optimization_result = self._find_optimizations(tool_name, tool_input, context)
            if optimization_result[3]:  # Alternative action available
                return optimization_result

            # No routing needed
            return False, "", [], None

        except Exception as e:
            # Fail-secure: if routing fails, allow the original operation
            return False, f"Router error (operation allowed): {str(e)}", [], None

    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of routing decisions."""
        if not self.operation_history:
            return 1.0

        successful = sum(1 for op in self.operation_history if op.get("success", True))
        return successful / len(self.operation_history)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        return {
            "total_operations": len(self.operation_history),
            "recent_operations": len([
                op for op in self.operation_history
                if time.time() - op["timestamp"] < 300  # Last 5 minutes
            ]),
            "circuit_breaker_state": self.circuit_breaker_state,
            "routing_success_rate": self._calculate_success_rate(),
        }

    def log_operation(self, tool_name: str, result: str, routing_applied: bool = False):
        """Log operation for performance monitoring."""
        self.operation_history.append({
            "timestamp": time.time(),
            "tool_name": tool_name,
            "result": result,
            "routing_applied": routing_applied,
            "success": result != "error",
        })

        # Keep only recent history to prevent memory growth
        cutoff_time = time.time() - 3600  # 1 hour
        self.operation_history = [
            op for op in self.operation_history
            if op["timestamp"] > cutoff_time
        ]


# Global router instance (lazy initialization)
_router: Optional[IntelligentRouter] = None


def get_router() -> IntelligentRouter:
    """Get the global intelligent router instance."""
    global _router
    if _router is None:
        _router = IntelligentRouter()
    return _router


def analyze_tool_for_routing(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
    """Analyze tool request for intelligent routing.

    This is the main entry point for the routing system.

    Returns:
        (should_redirect, reason, warnings, alternative_action)
    """
    router = get_router()
    return router.analyze_tool_request(tool_name, tool_input, context)
