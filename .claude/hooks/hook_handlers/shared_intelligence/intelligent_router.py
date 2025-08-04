#!/usr/bin/env python3
"""Intelligent Router for Hook System.

Analyzes tool usage patterns and provides routing recommendations for more efficient
operations.
"""

from typing import Any, Dict, List, Optional, Tuple


def _is_single_file_read(tool_input: Dict[str, Any]) -> bool:
    """Check if this is a single file read operation."""
    return "file_path" in tool_input and isinstance(tool_input["file_path"], str)


def _could_benefit_from_batch_read(
    tool_input: Dict[str, Any], context: Dict[str, Any],
) -> bool:
    """Check if operation could benefit from batch reading."""
    # This would check recent operations to see if multiple reads are happening
    recent_ops = context.get("recent_operations", [])
    recent_reads = [op for op in recent_ops if op.get("tool_name") == "Read"]
    return len(recent_reads) >= 2


def _is_sequential_command(tool_input: Dict[str, Any]) -> bool:
    """Check if bash command contains sequential operations."""
    command = tool_input.get("command", "")
    # Look for sequential operators
    return any(sep in command for sep in [" && ", " ; ", " || "])


def _get_parallel_alternative(tool_input: Dict[str, Any]) -> Optional[str]:
    """Get parallel alternative for sequential command."""
    command = tool_input.get("command", "")

    # Simple parallel conversions
    if " && " in command:
        parts = command.split(" && ")
        if len(parts) <= 3 and all(len(part.strip()) < 100 for part in parts):
            # Convert to background processes
            bg_parts = [f"({part.strip()}) &" for part in parts[:-1]]
            bg_parts.append(parts[-1].strip())
            bg_parts.append("wait")
            return " ".join(bg_parts)

    return None


def _should_use_ripgrep(tool_input: Dict[str, Any]) -> bool:
    """Check if ripgrep would be better than standard grep."""
    pattern = tool_input.get("pattern", "")
    # For complex patterns or large searches, ripgrep is better
    return len(pattern) > 10 or any(
        char in pattern for char in [".*", "+", "?", "[", "]"]
    )


def _convert_to_ripgrep(tool_input: Dict[str, Any]) -> str:
    """Convert Grep tool input to ripgrep command."""
    pattern = tool_input.get("pattern", "")
    path = tool_input.get("path", ".")
    glob = tool_input.get("glob", "")

    cmd = f"rg '{pattern}'"
    if glob:
        cmd += f" --glob '{glob}'"
    if path != ".":
        cmd += f" {path}"

    return cmd


def _is_complex_edit(tool_input: Dict[str, Any]) -> bool:
    """Check if edit operation is complex enough to delegate."""
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")

    # Large edits
    if len(old_string) > 500 or len(new_string) > 500:
        return True

    # Multiple line changes
    if old_string.count("\n") > 10 or new_string.count("\n") > 10:
        return True

    return False


def _should_delegate_to_agent(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> bool:
    """Check if operation should be delegated to a specialized agent."""
    # Check for complex multi-step operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Complex git operations
        if command.startswith("git") and len(command.split()) > 3:
            return True
        # Complex build/deploy commands
        if any(
            keyword in command
            for keyword in ["docker", "npm run", "cargo build", "python setup.py"]
        ):
            return True

    # Complex file operations
    if tool_name in ["MultiEdit", "Edit"] and _is_complex_edit(tool_input):
        return True

    # Multiple tool sequence detection
    recent_ops = context.get("recent_operations", [])
    if len(recent_ops) >= 3:
        return True

    return False


def _get_delegation_recommendation(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get specific delegation recommendation."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command.startswith("git"):
            return {
                "tool": "mcp__zen__chat",
                "reason": "Complex git operations benefit from specialized analysis",
                "command": f"Analyze and execute git workflow: {command}",
            }

    if tool_name in ["MultiEdit", "Edit"]:
        return {
            "tool": "mcp__zen__refactor",
            "reason": "Complex code changes benefit from systematic refactoring approach",
            "command": "Use refactoring agent for structured code changes",
        }

    return {
        "tool": "mcp__zen__chat",
        "reason": "Multi-step operation benefits from agent planning",
        "command": "Delegate complex operation to specialized agent",
    }


def analyze_tool_for_routing(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Dict[str, Any],
) -> Tuple[bool, str, List[str], Dict[str, Any]]:
    """Analyze tool usage for intelligent routing opportunities.

    Args:
        tool_name: Name of the tool being used
        tool_input: Input parameters for the tool
        context: Session and operation context

    Returns:
        Tuple of (should_redirect, reason, warnings, alternative_action)
    """
    warnings: List[str] = []
    alternative_action: Dict[str, Any] = {}

    # Check for batch operation opportunities
    if tool_name == "Read" and _is_single_file_read(tool_input):
        # Check if multiple reads could be batched
        if _could_benefit_from_batch_read(tool_input, context):
            return (
                True,
                "Multiple file reads detected - batch operations are more efficient",
                warnings,
                {
                    "tool": "mcp__filesystem__read_multiple_files",
                    "reason": "Batch reading reduces I/O overhead by 60-80%",
                    "command": "Use read_multiple_files with array of paths",
                },
            )

    # Check for parallel operation opportunities
    if tool_name == "Bash" and _is_sequential_command(tool_input):
        parallel_cmd = _get_parallel_alternative(tool_input)
        if parallel_cmd:
            return (
                True,
                "Sequential operations detected - parallel execution available",
                warnings,
                {
                    "command": parallel_cmd,
                    "reason": "Parallel execution can reduce time by 50-90%",
                },
            )

    # Check for more efficient tool alternatives
    if tool_name == "Grep" and _should_use_ripgrep(tool_input):
        return (
            True,
            "Standard grep detected - ripgrep is significantly faster",
            warnings,
            {
                "tool": "Bash",
                "command": _convert_to_ripgrep(tool_input),
                "reason": "ripgrep is 3-10x faster than standard grep",
            },
        )

    # Check for task delegation opportunities
    if _should_delegate_to_agent(tool_name, tool_input, context):
        delegation_info = _get_delegation_recommendation(tool_name, tool_input, context)
        if delegation_info:
            return (
                True,
                f"Complex {tool_name} operation - consider delegating to specialized agent",
                warnings,
                delegation_info,
            )

    return False, "", warnings, alternative_action
