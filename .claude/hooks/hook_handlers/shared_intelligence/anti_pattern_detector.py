#!/usr/bin/env python3
"""Anti-Pattern Detector for Hook System.

Detects common workflow anti-patterns and suggests improvements.
"""

from typing import Any, Dict, List, Tuple


def _has_technical_debt_filename(tool_input: Dict[str, Any]) -> bool:
    """Check if filename contains technical debt keywords."""
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return False

    debt_keywords = [
        "backup", "v2", "enhanced", "legacy", "old", "revised", "new", "copy",
        "temp", "tmp", "bak", "orig", "v3", "v4", "original", "renamed",
        "deprecated", "archived", "obsolete", "draft", "_old", "_new",
        "_backup", "_legacy", "_temp", "_copy",
    ]

    filename = file_path.lower()
    return any(keyword in filename for keyword in debt_keywords)


def _extract_debt_keyword(filename: str) -> str:
    """Extract the technical debt keyword from filename."""
    debt_keywords = [
        "backup", "v2", "enhanced", "legacy", "old", "revised", "new", "copy",
        "temp", "tmp", "bak", "orig", "v3", "v4", "original", "renamed",
        "deprecated", "archived", "obsolete", "draft", "_old", "_new",
        "_backup", "_legacy", "_temp", "_copy",
    ]

    filename_lower = filename.lower()
    for keyword in debt_keywords:
        if keyword in filename_lower:
            return keyword
    return "unknown"


def _is_repetitive_operation(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> bool:
    """Check if this is part of a repetitive operation pattern."""
    recent_ops = context.get("recent_operations", [])
    if len(recent_ops) < 2:
        return False

    # Count similar operations in recent history
    similar_ops = [
        op for op in recent_ops 
        if op.get("tool_name") == tool_name
    ]

    return len(similar_ops) >= 2


def _get_batch_alternative(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get batch operation alternative."""
    if tool_name == "Read":
        return {
            "tool": "mcp__filesystem__read_multiple_files",
            "reason": "Batch reading is more efficient than multiple single reads",
            "command": "Collect all file paths and read in single operation",
        }

    if tool_name == "Edit":
        return {
            "tool": "MultiEdit",
            "reason": "Multiple edits to same file should be batched",
            "command": "Use MultiEdit to apply all changes in single operation",
        }

    return {}


def _has_inefficient_command_pattern(tool_input: Dict[str, Any]) -> bool:
    """Check for inefficient bash command patterns."""
    command = tool_input.get("command", "")
    
    # Check for inefficient patterns
    inefficient_patterns = [
        "find . -name",  # Should use fd
        "grep -r",       # Should use rg (ripgrep)
        "cat file | grep",  # Should use direct grep
        "ls -la",        # Should use lsd or exa
        "du -sh",        # Should use dust
        "ps aux",        # Should use procs
    ]

    return any(pattern in command for pattern in inefficient_patterns)


def _get_efficient_command(tool_input: Dict[str, Any]) -> str:
    """Get more efficient version of command."""
    command = tool_input.get("command", "")
    
    # Simple replacements for common patterns
    replacements = {
        "find . -name": "fd",
        "grep -r": "rg",
        "ls -la": "lsd -la",
        "du -sh": "dust",
        "ps aux": "procs",
    }

    for old_pattern, new_cmd in replacements.items():
        if old_pattern in command:
            # Simple replacement - could be more sophisticated
            return command.replace(old_pattern, new_cmd)

    return command


def _has_prior_analysis(context: Dict[str, Any]) -> bool:
    """Check if there was prior analysis in recent operations."""
    recent_ops = context.get("recent_operations", [])
    analysis_tools = ["Read", "Grep", "Glob", "mcp__filesystem__read_text_file"]
    
    return any(
        op.get("tool_name") in analysis_tools 
        for op in recent_ops
    )


def _is_trivial_file(file_path: str) -> bool:
    """Check if file is trivial enough to not need analysis."""
    # Small config files, simple scripts, etc.
    trivial_extensions = [".txt", ".md", ".json", ".yaml", ".yml"]
    return any(file_path.endswith(ext) for ext in trivial_extensions)


def _is_complex_bash(tool_input: Dict[str, Any]) -> bool:
    """Check if bash command is complex."""
    command = tool_input.get("command", "")
    
    # Complex indicators
    complexity_indicators = [
        "|",     # Pipes
        "&&",    # Chaining
        "||",    # Or chains
        "for ",  # Loops
        "while ", # Loops
        "if ",   # Conditionals
        "$(",    # Command substitution
        "`",     # Command substitution
    ]

    return any(indicator in command for indicator in complexity_indicators)


def _lacks_context_preparation(
    tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any],
) -> bool:
    """Check if operation lacks proper context preparation."""
    # Complex operations without prior exploration
    if tool_name in ["Edit", "MultiEdit", "Write"] and not _has_prior_analysis(context):
        file_path = tool_input.get("file_path", "")
        if file_path and not _is_trivial_file(file_path):
            return True

    # Bash operations without understanding
    if tool_name == "Bash" and _is_complex_bash(tool_input) and not _has_prior_analysis(context):
        return True

    return False


def _get_preparation_suggestion(
    tool_name: str, tool_input: Dict[str, Any],
) -> Dict[str, Any]:
    """Get suggestion for better preparation."""
    if tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = tool_input.get("file_path", "")
        return {
            "tool": "Read",
            "reason": "Read and understand file structure before making changes",
            "command": f"Read {file_path} first to understand the codebase",
        }

    if tool_name == "Bash":
        return {
            "tool": "mcp__zen__chat",
            "reason": "Complex bash operations benefit from planning",
            "command": "Plan the bash operation with an agent first",
        }

    return {}


def analyze_workflow_patterns(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: Dict[str, Any],
) -> Tuple[bool, str, List[str], Dict[str, Any]]:
    """Analyze workflow for anti-patterns.

    Args:
        tool_name: Name of the tool being used
        tool_input: Input parameters for the tool
        context: Session and operation context

    Returns:
        Tuple of (should_block, reason, warnings, alternative_action)
    """
    warnings: List[str] = []
    alternative_action: Dict[str, Any] = {}

    # Check for technical debt filename patterns
    if tool_name == "Write" and _has_technical_debt_filename(tool_input):
        filename = tool_input.get("file_path", "")
        debt_keyword = _extract_debt_keyword(filename)
        return (
            True,
            f"❌ TECHNICAL DEBT: Filename contains '{debt_keyword}' - no backup/versioned files allowed",
            warnings,
            {
                "tool": "Edit",
                "reason": "Update existing file instead of creating versioned copies",
                "command": f"Edit the original file directly, not {filename}",
            },
        )

    # Check for repetitive single-file operations
    if _is_repetitive_operation(tool_name, tool_input, context):
        batch_suggestion = _get_batch_alternative(tool_name, tool_input, context)
        if batch_suggestion:
            warnings.append(
                f"🔄 REPETITIVE PATTERN: Multiple {tool_name} operations - consider batching",
            )
            alternative_action = batch_suggestion

    # Check for inefficient command patterns
    if tool_name == "Bash" and _has_inefficient_command_pattern(tool_input):
        efficient_cmd = _get_efficient_command(tool_input)
        if efficient_cmd:
            warnings.append(
                "⚡ INEFFICIENT COMMAND: More efficient alternative available",
            )
            alternative_action = {
                "command": efficient_cmd,
                "reason": "Optimized command pattern for better performance",
            }

    # Check for missing context/preparation
    if _lacks_context_preparation(tool_name, tool_input, context):
        prep_suggestion = _get_preparation_suggestion(tool_name, tool_input)
        if prep_suggestion:
            warnings.append(
                "📋 MISSING CONTEXT: Operation could benefit from preparation",
            )
            alternative_action = prep_suggestion

    return False, "", warnings, alternative_action
