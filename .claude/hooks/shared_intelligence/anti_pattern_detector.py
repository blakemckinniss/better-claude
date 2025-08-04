#!/usr/bin/env python3
"""Advanced anti-pattern detection for destructive workflows.

This module extends the basic pattern detector with sophisticated analysis
of workflow patterns that indicate inefficient or destructive usage patterns.

Security Features:
- Pattern-based workflow analysis
- Sequential operation detection
- Resource usage monitoring
- Performance degradation prevention
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from .config import get_config


class AntiPatternDetector:
    """Advanced anti-pattern detection for workflow optimization."""

    # Workflow anti-patterns with severity levels
    WORKFLOW_PATTERNS = {
        "sequential_file_reads": {
            "threshold": 3,  # 3+ sequential reads trigger warning
            "window": 30,    # Within 30 seconds
            "severity": "high",
            "block": True,
            "message": "❌ ANTI-PATTERN: Sequential file reads detected - use batch operations",
            "suggestion": "Use mcp__filesystem__read_multiple_files or parallel processing",
            "alternative": {
                "tool": "mcp__filesystem__read_multiple_files",
                "reason": "Batch file reading is 10-50x more efficient",
            },
        },
        "read_for_search": {
            "patterns": [
                r"Read.*\.py.*search",
                r"Read.*grep",
                r"Read.*find",
            ],
            "severity": "medium",
            "block": True,
            "message": "❌ ANTI-PATTERN: Using Read for search operations",
            "suggestion": "Use ripgrep, grep, or search-specific tools",
            "alternative": {
                "tool": "Bash",
                "command_template": "rg --line-number --context 2 '{pattern}' '{file}'",
                "reason": "Search tools are 100x faster than reading entire files",
            },
        },
        "large_file_operations": {
            "threshold": 1000000,  # 1MB
            "severity": "medium",
            "block": False,
            "message": "⚠️ PERFORMANCE: Large file operation detected",
            "suggestion": "Consider streaming or chunked processing",
        },
        "destructive_batch_operations": {
            "patterns": [
                r"rm.*-rf.*\*",
                r"find.*-delete",
                r"Write.*overwrite.*multiple",
            ],
            "severity": "critical",
            "block": True,
            "message": "🚨 CRITICAL: Destructive batch operation detected",
            "suggestion": "Use targeted operations instead of bulk destructive commands",
        },
        "inefficient_loops": {
            "threshold": 5,  # 5+ similar operations
            "window": 60,    # Within 1 minute
            "severity": "medium",
            "block": False,
            "message": "⚠️ ANTI-PATTERN: Repetitive operations detected",
            "suggestion": "Consider batch processing or loop optimization",
        },
        "context_switching": {
            "threshold": 10,  # 10+ different tools rapidly
            "window": 120,    # Within 2 minutes
            "severity": "low",
            "block": False,
            "message": "💡 EFFICIENCY: Frequent context switching detected",
            "suggestion": "Group similar operations together for better performance",
        },
    }

    def __init__(self):
        """Initialize the anti-pattern detector."""
        self.config = get_config()
        self.operation_history: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _check_sequential_reads(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for sequential file read anti-pattern."""
        if tool_name != "Read":
            return False, "", [], None

        # Count recent Read operations
        current_time = time.time()
        window = config.get("window", 30)
        threshold = config.get("threshold", 3)
        
        recent_reads = [
            op for op in self.operation_history
            if (
                op.get("tool_name") == "Read" and 
                current_time - op.get("timestamp", 0) < window
            )
        ]

        if len(recent_reads) >= threshold:
            alternative = config.get("alternative", {})
            return (
                True,
                str(config.get("message", "Sequential reads detected")),
                [],
                alternative if alternative else None,
            )

        # Warning at threshold - 1
        if len(recent_reads) == threshold - 1:
            return (
                False,
                "",
                [f"⚠️ {len(recent_reads)} sequential reads detected - consider batch operations"],
                None,
            )

        return False, "", [], None

    def _looks_like_search_operation(
        self,
        file_path: str,
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Determine if this looks like a search operation."""
        # Check for common search file types
        search_file_types = [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".txt", ".md"]
        if any(file_path.endswith(ext) for ext in search_file_types):
            # If it's a code file and we have context suggesting search, likely search
            if context:
                return True

        return False

    def _check_read_for_search(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check if Read is being used for search operations."""
        if tool_name != "Read":
            return False, "", [], None

        # Check if context suggests this is a search operation
        search_indicators = [
            "search", "find", "grep", "locate", "pattern", "contains",
            "match", "filter", "query", "lookup",
        ]

        context_suggests_search = False
        if context:
            context_str = str(context).lower()
            context_suggests_search = any(indicator in context_str for indicator in search_indicators)

        # Check file path for search-like patterns
        file_path = tool_input.get("file_path", "")
        if context_suggests_search or self._looks_like_search_operation(file_path, context):
            alternative = config.get("alternative", {})
            
            # Customize the command template if available
            if "command_template" in alternative:
                template = alternative["command_template"]
                alternative["command"] = template.format(
                    pattern="SEARCH_PATTERN",  # Placeholder
                    file=file_path,
                )
            
            return (
                True,
                str(config.get("message", "Read for search detected")),
                [],
                alternative if alternative else None,
            )

        return False, "", [], None

    def _check_large_file_operations(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for large file operations."""
        if tool_name not in ["Read", "Write", "Edit"]:
            return False, "", [], None

        file_path = tool_input.get("file_path", "")
        if not file_path:
            return False, "", [], None

        try:
            import os
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                threshold = config.get("threshold", 1000000)
                
                if isinstance(threshold, int) and file_size > threshold:
                    message = str(config.get("message", "Large file operation"))
                    suggestion = str(config.get("suggestion", "Consider optimization"))
                    
                    return (
                        False,  # Don't block, just warn
                        "",
                        [f"{message} ({file_size:,} bytes) - {suggestion}"],
                        None,
                    )
        except Exception:
            pass

        return False, "", [], None

    def _check_destructive_operations(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for destructive batch operations."""
        if tool_name != "Bash":
            return False, "", [], None

        command = tool_input.get("command", "")
        patterns = config.get("patterns", [])

        import re
        for pattern in patterns:
            if re.search(pattern, command):
                return (
                    True,
                    str(config.get("message", "Destructive operation detected")),
                    [],
                    None,
                )

        return False, "", [], None

    def _check_inefficient_loops(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for inefficient repetitive operations."""
        current_time = time.time()
        window = config.get("window", 60)
        threshold = config.get("threshold", 5)

        # Find similar recent operations
        recent_similar = [
            op for op in self.operation_history
            if (
                op.get("tool_name") == tool_name and
                current_time - op.get("timestamp", 0) < window
            )
        ]

        if len(recent_similar) >= threshold:
            return (
                False,  # Don't block, just warn
                "",
                [str(config.get("message", "Repetitive operations detected"))],
                None,
            )

        return False, "", [], None

    def _check_context_switching(
        self,
        config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for excessive context switching between tools."""
        current_time = time.time()
        window = config.get("window", 120)
        threshold = config.get("threshold", 10)

        # Count unique tools in recent history
        recent_ops = [
            op for op in self.operation_history
            if current_time - op.get("timestamp", 0) < window
        ]

        unique_tools = {op.get("tool_name") for op in recent_ops}
        
        if len(unique_tools) >= threshold:
            return (
                False,  # Don't block, just suggest
                "",
                [str(config.get("message", "Context switching detected"))],
                None,
            )

        return False, "", [], None

    def _check_pattern(
        self,
        pattern_name: str,
        pattern_config: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check a specific anti-pattern."""
        warnings: List[str] = []

        if pattern_name == "sequential_file_reads":
            return self._check_sequential_reads(pattern_config, tool_name, tool_input)
        
        elif pattern_name == "read_for_search":
            return self._check_read_for_search(pattern_config, tool_name, tool_input, context)
        
        elif pattern_name == "large_file_operations":
            return self._check_large_file_operations(pattern_config, tool_name, tool_input)
        
        elif pattern_name == "destructive_batch_operations":
            return self._check_destructive_operations(pattern_config, tool_name, tool_input)
        
        elif pattern_name == "inefficient_loops":
            return self._check_inefficient_loops(pattern_config, tool_name, tool_input)
        
        elif pattern_name == "context_switching":
            return self._check_context_switching(pattern_config, tool_name, tool_input)

        return False, "", warnings, None

    def _record_operation(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Record operation for pattern analysis."""
        self.operation_history.append({
            "timestamp": time.time(),
            "tool_name": tool_name,
            "tool_input": tool_input,
        })

        # Keep only recent history (last 10 minutes)
        cutoff_time = time.time() - 600
        self.operation_history = [
            op for op in self.operation_history
            if op.get("timestamp", 0) > cutoff_time
        ]

    def analyze_workflow(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Analyze workflow for anti-patterns.

        Args:
            tool_name: Current tool being requested
            tool_input: Tool input parameters
            context: Optional workflow context

        Returns:
            (should_block, reason, warnings, alternative_action)
        """
        try:
            # Record this operation
            self._record_operation(tool_name, tool_input)

            warnings = []
            
            # Check each anti-pattern
            for pattern_name, pattern_config in self.WORKFLOW_PATTERNS.items():
                result = self._check_pattern(pattern_name, pattern_config, tool_name, tool_input, context)
                
                if result[0]:  # Pattern detected and should block
                    return result
                elif result[2]:  # Warnings generated
                    warnings.extend(result[2])

            return False, "", warnings, None

        except Exception as e:
            # Fail-secure: allow operation if analysis fails
            return False, f"Anti-pattern analysis error (operation allowed): {str(e)}", [], None

    def get_statistics(self) -> Dict[str, Any]:
        """Get anti-pattern detection statistics."""
        current_time = time.time()
        
        # Statistics for last hour
        hour_ago = current_time - 3600
        recent_ops = [
            op for op in self.operation_history
            if op.get("timestamp", 0) > hour_ago
        ]

        tool_counts: Dict[str, int] = {}
        for op in recent_ops:
            tool_name = op.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        return {
            "total_operations": len(recent_ops),
            "tool_distribution": tool_counts,
            "patterns_detected": len(self.pattern_cache),
            "most_common_tool": max(tool_counts.items(), key=lambda x: x[1])[0] if tool_counts else None,
        }


# Global detector instance
_detector: Optional[AntiPatternDetector] = None


def get_detector() -> AntiPatternDetector:
    """Get the global anti-pattern detector instance."""
    global _detector
    if _detector is None:
        _detector = AntiPatternDetector()
    return _detector


def analyze_workflow_patterns(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
    """Analyze workflow for anti-patterns.

    This is the main entry point for anti-pattern detection.

    Returns:
        (should_block, reason, warnings, alternative_action)
    """
    detector = get_detector()
    return detector.analyze_workflow(tool_name, tool_input, context)
