#!/usr/bin/env python3
"""
Streamlined PreToolUse Hook - Security-Only Blocking.

This streamlined version focuses solely on security and safety blocking.
All intelligence and educational features have been moved to PostToolUse
for better user experience (Claude sees educational feedback via stderr).

Target: <50ms execution time, <300 lines total.
"""

import json
import os
import sys
import time
from typing import Any, Dict, Tuple

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PreToolUse.command_validator import CommandValidator
# Import only essential security validators
from PreToolUse.path_validator import (
    check_path_access,
    check_recursive_claude_directory,
    get_file_operation_from_tool,
    is_blocked_path,
)
from PreToolUse.read_blocker import check_read_operation_block


class SecurityValidator:
    """Fast security-only validator."""
    
    def __init__(self):
        self.command_validator = CommandValidator()
        self.start_time = time.perf_counter()
    
    def check_file_size_reduction(
        self, file_path: str, operation: str, tool_input: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Quick check for destructive file operations."""
        if operation not in ["write", "edit"]:
            return False, ""
        
        try:
            if not os.path.exists(file_path):
                return False, ""
            
            current_size = os.path.getsize(file_path)
            if current_size < 1000:  # Skip small files
                return False, ""
            
            if operation == "write":
                new_content = tool_input.get("content", "")
                new_size = len(new_content.encode("utf-8"))
                
                if current_size > 0 and new_size < current_size * 0.5:
                    return True, (
                        f"❌ DESTRUCTIVE EDIT BLOCKED: Would remove {((current_size - new_size) / current_size * 100):.0f}% of file content\n"
                        f"   File: {file_path} ({current_size:,} → {new_size:,} bytes)\n"
                        f"   Action: Review changes - significant content removal detected"
                    )
            
            elif operation == "edit":
                old_string = tool_input.get("old_string", "")
                new_string = tool_input.get("new_string", "")
                
                if len(old_string) > 500 and len(new_string) < len(old_string) * 0.5:
                    return True, (
                        f"❌ DESTRUCTIVE EDIT BLOCKED: Replacing {len(old_string)} chars with {len(new_string)} chars\n"
                        f"   File: {file_path}\n"
                        f"   Action: Break into smaller, focused edits"
                    )
                    
        except OSError:
            pass  # Allow operation if can't check
        
        return False, ""
    
    def check_technical_debt_filename(self, file_path: str) -> Tuple[bool, str]:
        """Block technical debt filenames."""
        debt_keywords = [
            "backup", "v2", "enhanced", "legacy", "old", "revised", "new", "copy",
            "temp", "tmp", "bak", "orig", "v3", "v4", "original", "_old", "_new",
            "_backup", "_legacy", "_temp", "_copy",
        ]
        
        filename = os.path.basename(file_path).lower()
        for keyword in debt_keywords:
            if keyword in filename:
                return True, (
                    f"❌ TECHNICAL DEBT BLOCKED: Filename contains '{keyword}'\n"
                    f"   File: {file_path}\n"
                    f"   Policy: No backup/versioned files allowed\n"
                    f"   Action: Use proper descriptive name and update existing files"
                )
        
        return False, ""
    
    def validate_file_operation(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate file operations for security only."""
        # Get file operation details
        file_path, operation = get_file_operation_from_tool(tool_name, tool_input)
        
        # Read operation blocking (highest priority)
        # should_block_read, guidance = check_read_operation_block(tool_name, operation)
        # if should_block_read:
        #     return False, guidance
        
        if not file_path:
            return True, ""
        
        # Destructive edit protection
        is_destructive, reason = self.check_file_size_reduction(file_path, operation, tool_input)
        if is_destructive:
            return False, reason
        
        # Technical debt filename blocking (for write operations)
        if operation == "write":
            is_debt, debt_reason = self.check_technical_debt_filename(file_path)
            if is_debt:
                return False, debt_reason
        
        # Core security checks
        if check_recursive_claude_directory(file_path):
            return False, "❌ BLOCKED: Recursive .claude directories detected"
        
        if is_blocked_path(file_path):
            return False, f"❌ BLOCKED: Path contains blocked pattern: {file_path}"
        
        allowed, reason = check_path_access(file_path, operation)
        if not allowed:
            return False, f"❌ BLOCKED: {reason}"
        
        return True, ""
    
    def validate_bash_command(self, tool_input: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate bash commands for security only."""
        command = tool_input.get("command", "")
        if not command:
            return True, ""
        
        # Use existing command validator for security analysis
        allowed, reason, _ = self.command_validator.analyze_command(command)
        if not allowed:
            return False, f"❌ COMMAND BLOCKED: {reason}"
        
        return True, ""
    
    def get_execution_time(self) -> float:
        """Get execution time in milliseconds."""
        return (time.perf_counter() - self.start_time) * 1000


def handle(event_data: Dict[str, Any]) -> None:
    """Streamlined PreToolUse handler - security blocking only."""
    try:
        # Extract tool information
        tool_name = event_data.get("tool_name", "")
        tool_input = event_data.get("tool_input", {})
        
        if not tool_name:
            sys.exit(0)
        
        # Initialize security validator
        validator = SecurityValidator()
        
        # Validate based on tool type
        if tool_name in ["Read", "Write", "Edit", "MultiEdit"] or tool_name.startswith("mcp__filesystem__"):
            allowed, reason = validator.validate_file_operation(tool_name, tool_input)
        elif tool_name == "Bash":
            allowed, reason = validator.validate_bash_command(tool_input)
        else:
            # Allow all other tools
            allowed, reason = True, ""
        
        # Block if not allowed
        if not allowed:
            print(reason, file=sys.stderr)
            print("\n📝 Note: Hooks can be temporarily disabled in", file=sys.stderr)
            print("   /home/blake/better-claude/.claude/hooks/hook_handler.py", file=sys.stderr)
            sys.exit(2)
        
        # Performance monitoring (optional)
        exec_time = validator.get_execution_time()
        if exec_time > 100:  # Log slow operations (>100ms)
            print(f"⚠️ Hook performance: {exec_time:.1f}ms (target: <50ms)", file=sys.stderr)
        
        # Success - allow operation
        sys.exit(0)
        
    except Exception as e:
        # Don't fail operations due to hook errors
        print(f"Hook error (operation allowed): {str(e)}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    try:
        event_data = json.loads(sys.stdin.read())
        handle(event_data)
    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
