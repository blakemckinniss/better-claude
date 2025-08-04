#!/usr/bin/env python3
"""Performance-aware routing with circuit breakers and optimization.

This module provides performance monitoring and optimization routing
to prevent resource exhaustion and guide toward efficient operations.

Features:
- Circuit breakers for expensive operations
- Performance monitoring and metrics
- Resource usage tracking
- Optimization recommendations
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from .config import get_config


class PerformanceOptimizer:
    """Performance-aware routing and circuit breaker system."""

    # Performance thresholds and limits
    PERFORMANCE_LIMITS = {
        "max_file_size": 5_000_000,      # 5MB max file size
        "max_operations_per_minute": 30,  # Rate limiting
        "max_concurrent_reads": 10,       # Concurrent read limit
        "max_memory_usage": 100_000_000,  # 100MB memory limit
        "response_time_threshold": 2.0,   # 2s response time warning
    }

    # Circuit breaker states
    CIRCUIT_STATES = {
        "CLOSED": "normal_operation",
        "OPEN": "blocking_requests", 
        "HALF_OPEN": "testing_recovery",
    }

    def __init__(self):
        """Initialize the performance optimizer."""
        self.config = get_config()
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        self.operation_counts: Dict[str, int] = {}
        self.last_reset_time = time.time()

    def _get_alternative_for_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get alternative action when circuit breaker is active."""
        alternatives = {
            "Read": {
                "tool": "Bash",
                "command": "echo 'Read operations temporarily blocked - use search tools like rg instead'",
                "reason": "Circuit breaker active for Read operations",
            },
            "Write": {
                "tool": "mcp__filesystem__edit_file",
                "reason": "Use targeted edits instead of full writes",
            },
            "Bash": {
                "suggestion": "Wait for circuit breaker to reset or use alternative tools",
                "reason": "Bash operations temporarily limited",
            },
        }
        
        return alternatives.get(tool_name)

    def _check_circuit_breakers(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check and manage circuit breakers."""
        breaker_key = f"{tool_name}_breaker"
        
        # Initialize circuit breaker if not exists
        if breaker_key not in self.circuit_breakers:
            self.circuit_breakers[breaker_key] = {
                "state": "CLOSED",
                "failure_count": 0,
                "last_failure_time": 0,
                "success_count": 0,
                "next_attempt_time": 0,
            }
        
        breaker = self.circuit_breakers[breaker_key]
        current_time = time.time()
        
        # Check circuit breaker state
        if breaker["state"] == "OPEN":
            # Check if we should try half-open
            if current_time >= breaker["next_attempt_time"]:
                breaker["state"] = "HALF_OPEN"
                breaker["success_count"] = 0
            else:
                # Circuit breaker still open
                return (
                    True,
                    f"🔌 CIRCUIT BREAKER: {tool_name} operations temporarily blocked due to failures",
                    [],
                    self._get_alternative_for_tool(tool_name, tool_input),
                )
        
        # File size circuit breaker
        if tool_name in ["Read", "Write", "Edit"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                try:
                    import os
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        max_size = self.PERFORMANCE_LIMITS["max_file_size"]
                        
                        if file_size > max_size:
                            return (
                                True,
                                f"🔌 CIRCUIT BREAKER: File too large ({file_size:,} bytes > {max_size:,})",
                                [],
                                {
                                    "tool": "Bash",
                                    "command": f"head -n 50 '{file_path}' | bat",
                                    "reason": "Stream first 50 lines instead of loading entire large file",
                                },
                            )
                except Exception:
                    pass
        
        return False, "", [], None

    def _check_rate_limits(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check rate limiting constraints."""
        current_time = time.time()
        
        # Reset counters every minute
        if current_time - self.last_reset_time > 60:
            self.operation_counts.clear()
            self.last_reset_time = current_time
        
        # Count operations
        count_key = f"{tool_name}_count"
        current_count = self.operation_counts.get(count_key, 0)
        max_ops = self.PERFORMANCE_LIMITS["max_operations_per_minute"]
        
        if current_count >= max_ops:
            return (
                True,
                f"⚡ RATE LIMIT: {tool_name} operations limited ({current_count}/{max_ops} per minute)",
                [],
                {
                    "suggestion": "Wait a moment before retrying or use batch operations",
                    "retry_after": 60 - (current_time - self.last_reset_time),
                },
            )
        
        # Increment counter
        self.operation_counts[count_key] = current_count + 1
        
        # Warning at 80% capacity
        if current_count >= max_ops * 0.8:
            return (
                False,
                "",
                [f"⚡ Rate limit warning: {current_count}/{max_ops} operations this minute"],
                None,
            )
        
        return False, "", [], None

    def _check_resource_constraints(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check resource usage constraints."""
        warnings: List[str] = []
        
        # Memory usage check (simplified)
        try:
            import psutil  # type: ignore
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > 90:
                warnings.append("🧠 High memory usage detected - consider lighter operations")
            elif memory_percent > 80:
                warnings.append("🧠 Memory usage elevated - monitor resource usage")
                
        except ImportError:
            # psutil not available, skip memory check
            pass
        except Exception:
            # Error getting memory info, skip
            pass
        
        # Concurrent operations check
        if tool_name == "Read":
            concurrent_reads = self.operation_counts.get("concurrent_reads", 0)
            max_concurrent = self.PERFORMANCE_LIMITS["max_concurrent_reads"]
            
            if concurrent_reads >= max_concurrent:
                return (
                    True,
                    f"🔄 CONCURRENCY LIMIT: Too many concurrent reads ({concurrent_reads}/{max_concurrent})",
                    [],
                    {
                        "tool": "mcp__filesystem__read_multiple_files",
                        "reason": "Use batch reading instead of concurrent individual reads",
                    },
                )
        
        return False, "", warnings, None

    def _optimize_bash_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Optimize bash commands for better performance."""
        optimizations = {
            "grep": {
                "alternative": "rg",
                "reason": "ripgrep is 10-100x faster than grep",
                "command_template": lambda cmd: cmd.replace("grep", "rg"),
            },
            "find": {
                "alternative": "fd",
                "reason": "fd is faster and simpler than find",
                "command_template": lambda cmd: cmd.replace("find", "fd"),
            },
            "cat": {
                "alternative": "bat",
                "reason": "bat provides syntax highlighting and better output",
                "command_template": lambda cmd: cmd.replace("cat", "bat"),
            },
            "ls -la": {
                "alternative": "lsd -la",
                "reason": "lsd provides better formatting and icons",
                "command_template": lambda cmd: cmd.replace("ls -la", "lsd -la"),
            },
        }
        
        for old_cmd, opt in optimizations.items():
            if old_cmd in command:
                template_func = opt["command_template"]
                if callable(template_func):
                    optimized_command = template_func(command)
                else:
                    optimized_command = command
                
                return {
                    "tool": "Bash",
                    "command": optimized_command,
                    "reason": opt["reason"],
                    "original_command": command,
                }
        
        return None

    def _optimize_file_operation(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Optimize file operations for better performance."""
        # Batch read optimization
        if tool_name == "Read" and context:
            file_count = context.get("file_count", 1)
            if isinstance(file_count, int) and file_count > 1:
                return {
                    "tool": "mcp__filesystem__read_multiple_files",
                    "reason": f"Batch read {file_count} files instead of sequential reads",
                    "performance_gain": "5-10x faster than sequential reads",
                }
        
        # Large file streaming optimization
        file_path = tool_input.get("file_path", "")
        if file_path and tool_name == "Read":
            try:
                import os
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    if file_size > 1_000_000:  # 1MB
                        return {
                            "tool": "Bash",
                            "command": f"head -n 100 '{file_path}' | bat",
                            "reason": f"Stream first 100 lines of large file ({file_size:,} bytes)",
                            "performance_gain": "Instant response vs full file load",
                        }
            except Exception:
                pass
        
        return None

    def _check_optimizations(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check for performance optimization opportunities."""
        warnings: List[str] = []
        
        # Bash command optimizations
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            optimization = self._optimize_bash_command(command)
            if optimization:
                return (
                    True,
                    f"⚡ PERFORMANCE OPTIMIZATION: {optimization['reason']}",
                    [],
                    optimization,
                )
        
        # File operation optimizations  
        elif tool_name in ["Read", "Write", "Edit"]:
            file_optimization = self._optimize_file_operation(tool_name, tool_input, context)
            if file_optimization:
                return (
                    True,
                    f"⚡ FILE OPTIMIZATION: {file_optimization['reason']}",
                    [],
                    file_optimization,
                )
        
        return False, "", warnings, None

    def _update_metrics(self, tool_name: str) -> None:
        """Update internal metrics tracking."""
        # Track concurrent operations
        if tool_name == "Read":
            concurrent_key = "concurrent_reads"
            current = self.operation_counts.get(concurrent_key, 0)
            self.operation_counts[concurrent_key] = current + 1
        
        # Clean up old concurrent counters periodically
        current_time = time.time()
        if not hasattr(self, '_last_cleanup'):
            self._last_cleanup = current_time
        elif current_time - self._last_cleanup > 30:
            # Reset concurrent counters every 30 seconds
            for key in list(self.operation_counts.keys()):
                if key.startswith("concurrent_"):
                    self.operation_counts[key] = max(0, self.operation_counts[key] - 1)
            self._last_cleanup = current_time

    def check_performance_constraints(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """Check performance constraints and apply optimizations.

        Args:
            tool_name: Tool being requested
            tool_input: Tool input parameters
            context: Optional context information

        Returns:
            (should_optimize, reason, warnings, optimization_action)
        """
        try:
            warnings: List[str] = []
            
            # Update metrics
            self._update_metrics(tool_name)
            
            # Check circuit breakers
            circuit_result = self._check_circuit_breakers(tool_name, tool_input)
            if circuit_result[0]:  # Circuit breaker active
                return circuit_result
            
            # Check rate limits
            rate_result = self._check_rate_limits(tool_name, tool_input)
            if rate_result[0]:  # Rate limit exceeded
                return rate_result
            
            # Check resource constraints
            resource_result = self._check_resource_constraints(tool_name, tool_input)
            if resource_result[2]:  # Warnings generated
                warnings.extend(resource_result[2])
            
            # Check for optimization opportunities
            optimization_result = self._check_optimizations(tool_name, tool_input, context)
            if optimization_result[3]:  # Optimization available
                return optimization_result
            
            return False, "", warnings, None
            
        except Exception as e:
            # Fail-secure: allow operation if performance check fails
            return False, f"Performance check error (operation allowed): {str(e)}", [], None

    def record_operation_result(self, tool_name: str, success: bool, response_time: float) -> None:
        """Record operation result for circuit breaker and metrics."""
        breaker_key = f"{tool_name}_breaker"
        
        if breaker_key not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[breaker_key]
        current_time = time.time()
        
        if success:
            # Reset failure count on success
            breaker["failure_count"] = 0
            breaker["success_count"] += 1
            
            # Close circuit breaker if in half-open state with enough successes
            if breaker["state"] == "HALF_OPEN" and breaker["success_count"] >= 3:
                breaker["state"] = "CLOSED"
                breaker["success_count"] = 0
                
        else:
            # Increment failure count
            breaker["failure_count"] += 1
            breaker["last_failure_time"] = current_time
            
            # Open circuit breaker if too many failures
            if breaker["failure_count"] >= 5:
                breaker["state"] = "OPEN"
                breaker["next_attempt_time"] = current_time + 60  # 1 minute timeout
        
        # Record performance metrics
        if tool_name not in self.performance_metrics:
            self.performance_metrics[tool_name] = []
        
        metrics = self.performance_metrics[tool_name]
        metrics.append(response_time)
        
        # Keep only recent metrics (last 100 operations)
        if len(metrics) > 100:
            metrics.pop(0)

    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics."""
        health = {"status": "unknown"}
        
        try:
            import psutil  # type: ignore
            health.update({
                "status": "healthy",
                "memory_percent": psutil.virtual_memory().percent,
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "disk_usage": psutil.disk_usage('/').percent,
            })
            
            # Determine overall health status
            memory_pct = health["memory_percent"]
            cpu_pct = health["cpu_percent"]
            
            if isinstance(memory_pct, (int, float)) and isinstance(cpu_pct, (int, float)):
                if memory_pct > 90 or cpu_pct > 95:
                    health["status"] = "critical"
                elif memory_pct > 80 or cpu_pct > 85:
                    health["status"] = "warning"
                else:
                    health["status"] = "healthy"
                
        except ImportError:
            health["status"] = "monitoring_unavailable"
        except Exception as e:
            health["status"] = f"error: {str(e)}"
        
        return health

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics and metrics."""
        stats = {
            "circuit_breakers": {},
            "operation_counts": self.operation_counts.copy(),
            "performance_metrics": {},
            "system_health": self._get_system_health(),
        }
        
        # Circuit breaker states
        for breaker_name, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][breaker_name] = {
                "state": breaker["state"],
                "failure_count": breaker["failure_count"],
                "success_count": breaker["success_count"],
            }
        
        # Performance metrics summary
        for tool_name, metrics in self.performance_metrics.items():
            if metrics:
                stats["performance_metrics"][tool_name] = {
                    "avg_response_time": sum(metrics) / len(metrics),
                    "max_response_time": max(metrics),
                    "min_response_time": min(metrics),
                    "operation_count": len(metrics),
                }
        
        return stats


# Global optimizer instance
_optimizer: Optional[PerformanceOptimizer] = None


def get_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer


def check_performance_optimization(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
    """Check for performance optimization opportunities.

    This is the main entry point for performance optimization.

    Returns:
        (should_optimize, reason, warnings, optimization_action)
    """
    optimizer = get_optimizer()
    return optimizer.check_performance_constraints(tool_name, tool_input, context)
