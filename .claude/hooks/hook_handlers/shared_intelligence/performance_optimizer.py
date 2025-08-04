#!/usr/bin/env python3
"""Performance Optimizer for Hook System.

Identifies performance optimization opportunities in tool usage.
"""

from typing import Any, Dict, List, Tuple


def _is_io_intensive_operation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if operation is I/O intensive."""
    # Multiple file operations
    if tool_name in ["Read", "Write", "Edit"]:
        return True

    # Large file operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        io_patterns = ["find", "grep", "cat", "head", "tail", "wc"]
        return any(pattern in command for pattern in io_patterns)

    return False


def _get_io_optimization(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get I/O optimization recommendation."""
    recent_ops = context.get("recent_operations", [])
    
    # Batch file reading optimization
    if tool_name == "Read":
        recent_reads = [op for op in recent_ops if op.get("tool_name") == "Read"]
        if len(recent_reads) >= 1:  # Include current operation
            return {
                "tool": "mcp__filesystem__read_multiple_files",
                "reason": "Batch file reading reduces I/O syscalls",
                "performance_gain": "60-80% faster than sequential reads",
                "command": "Collect file paths and read in single batch operation",
            }

    # Efficient search operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if "find" in command:
            return {
                "command": command.replace("find", "fd"),
                "reason": "fd is significantly faster than find",
                "performance_gain": "3-10x faster file discovery",
            }
        
        if "grep" in command:
            return {
                "command": command.replace("grep", "rg"),
                "reason": "ripgrep is much faster than grep",
                "performance_gain": "5-20x faster text search",
            }

    return {}


def _is_cpu_intensive_operation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if operation is CPU intensive."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        cpu_patterns = ["sort", "uniq", "awk", "sed", "tr", "cut"]
        return any(pattern in command for pattern in cpu_patterns)

    # Large text processing
    if tool_name in ["Edit", "MultiEdit"]:
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        return len(old_string) > 1000 or len(new_string) > 1000

    return False


def _convert_to_parallel(parts: List[str]) -> str:
    """Convert sequential commands to parallel execution."""
    if len(parts) <= 1:
        return " && ".join(parts)
    
    # Create background processes for all but last command
    parallel_parts = [f"({part.strip()}) &" for part in parts[:-1]]
    parallel_parts.append(parts[-1].strip())
    parallel_parts.append("wait")
    
    return " ".join(parallel_parts)


def _get_cpu_optimization(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Get CPU optimization recommendation."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Parallel processing suggestions
        if " && " in command:
            parts = command.split(" && ")
            if len(parts) <= 3:
                return {
                    "command": _convert_to_parallel(parts),
                    "reason": "Parallel execution utilizes multiple CPU cores",
                    "performance_gain": "50-200% faster with parallel processing",
                }

    return {}


def _is_memory_intensive_operation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if operation is memory intensive."""
    if tool_name in ["Read", "Write"]:
        # Check for large content
        content = tool_input.get("content", "")
        if len(content) > 100000:  # 100KB+
            return True

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        memory_patterns = ["sort", "uniq -c", "wc", "grep -r"]
        return any(pattern in command for pattern in memory_patterns)

    return False


def _get_memory_optimization(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Get memory optimization recommendation."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Streaming operations
        if "sort" in command and "-n" not in command:
            return {
                "command": command.replace("sort", "sort -S 50M"),
                "reason": "Limit sort memory usage for better performance",
                "performance_gain": "Prevents memory thrashing on large datasets",
            }

    # Large file operations
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            return {
                "tool": "mcp__filesystem__read_text_file",
                "reason": "Use streaming read for large files",
                "performance_gain": "Reduces memory footprint by 80-90%",
                "command": f"Use head/tail parameters to read file in chunks: {file_path}",
            }

    return {}


def _is_network_operation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if operation involves network access."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        network_patterns = ["curl", "wget", "git fetch", "git pull", "npm install"]
        return any(pattern in command for pattern in network_patterns)

    # MCP operations might involve network
    if tool_name.startswith("mcp__"):
        return True

    return False


def _get_network_optimization(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get network optimization recommendation."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Git operations
        if "git pull" in command:
            return {
                "command": "git fetch && git merge --ff-only",
                "reason": "Fetch first to check for conflicts",
                "performance_gain": "Avoids unnecessary merge commits",
            }
        
        # Package management
        if "npm install" in command:
            return {
                "command": f"{command} --prefer-offline",
                "reason": "Use local cache when possible",
                "performance_gain": "50-90% faster with cached packages",
            }

    return {}


def check_performance_optimization(
    tool_name: str,
    tool_input: Dict[str, Any], 
    context: Dict[str, Any],
) -> Tuple[bool, str, List[str], Dict[str, Any]]:
    """Check for performance optimization opportunities.

    Args:
        tool_name: Name of the tool being used
        tool_input: Input parameters for the tool
        context: Session and operation context

    Returns:
        Tuple of (should_optimize, reason, warnings, optimization_action)
    """
    warnings: List[str] = []
    optimization_action: Dict[str, Any] = {}

    # Check for I/O intensive operations that could be optimized
    if _is_io_intensive_operation(tool_name, tool_input):
        optimization = _get_io_optimization(tool_name, tool_input, context)
        if optimization:
            return (
                True,
                "I/O intensive operation detected - optimization available",
                warnings,
                optimization,
            )

    # Check for CPU intensive operations
    if _is_cpu_intensive_operation(tool_name, tool_input):
        optimization = _get_cpu_optimization(tool_name, tool_input)
        if optimization:
            warnings.append("🚀 CPU optimization available")
            optimization_action = optimization

    # Check for memory intensive operations
    if _is_memory_intensive_operation(tool_name, tool_input):
        optimization = _get_memory_optimization(tool_name, tool_input)
        if optimization:
            warnings.append("💾 Memory optimization available")
            optimization_action = optimization

    # Check for network operations that could be cached
    if _is_network_operation(tool_name, tool_input):
        optimization = _get_network_optimization(tool_name, tool_input, context)
        if optimization:
            warnings.append("🌐 Network optimization available")
            optimization_action = optimization

    return False, "", warnings, optimization_action
