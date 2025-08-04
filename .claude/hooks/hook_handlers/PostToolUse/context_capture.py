#!/usr/bin/env python3
"""
Context Capture for PostToolUse Hook.

Analyzes tool usage outcomes and stores meaningful context for future revival.
This creates a feedback loop where successful patterns and encountered issues
are preserved for future reference.
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..UserPromptSubmit.context_manager import ContextManager

try:
    from ..UserPromptSubmit.context_manager import (
        get_context_manager,
        store_conversation_context,
    )
except ImportError:
    # Fallback if context manager is not available
    def get_context_manager(project_dir: Optional[str] = None) -> Optional["ContextManager"]:
        return None

    def store_conversation_context(
        user_prompt: str,
        context_data: str,
        files_involved: Optional[List[str]] = None,
        outcome: str = "unknown"
    ) -> Optional[int]:
        return None


@dataclass
class ToolOutcome:
    """Represents the outcome of a tool execution."""
    tool_name: str
    outcome: str  # success, partial_success, failure, unknown
    context_data: str
    files_involved: List[str]
    error_patterns: List[str]
    success_patterns: List[str]
    metadata: Dict[str, Any]


class ToolOutcomeAnalyzer:
    """Analyzes tool responses to determine outcomes and extract context."""

    def __init__(self):
        self.logger = logging.getLogger("ContextCapture")
        self._setup_logging()

        # Patterns for outcome classification
        self.error_patterns = {
            # File/path errors
            "file_not_found": [
                r"No such file or directory",
                r"FileNotFoundError",
                r"ENOENT",
                r"cannot find|not found",
                r"does not exist"
            ],
            "permission_denied": [
                r"Permission denied",
                r"EACCES",
                r"EPERM",
                r"Access denied"
            ],
            "syntax_errors": [
                r"SyntaxError",
                r"IndentationError",
                r"TabError",
                r"invalid syntax",
                r"unexpected token"
            ],
            "import_errors": [
                r"ImportError",
                r"ModuleNotFoundError",
                r"No module named",
                r"cannot import"
            ],
            "type_errors": [
                r"TypeError",
                r"AttributeError",
                r"NameError",
                r"KeyError",
                r"ValueError"
            ],
            "runtime_errors": [
                r"RuntimeError",
                r"Exception",
                r"Error:",
                r"\bFailed\b",
                r"Traceback"
            ]
        }

        self.success_patterns = [
            r"successfully",
            r"completed",
            r"✅",
            r"done",
            r"finished",
            r"created",
            r"updated",
            r"formatted",
            r"validated"
        ]

        self.partial_success_patterns = [
            r"warning",
            r"partially",
            r"some issues",
            r"⚠️",
            r"fixed.*but",
            r"completed.*with warnings"
        ]

    def _setup_logging(self):
        """Setup logging for the analyzer."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def analyze_tool_outcome(self, tool_name: str, tool_input: Dict[str, Any],
                           tool_response: str) -> ToolOutcome:
        """Analyze a tool execution to determine outcome and extract context."""

        # Extract files involved
        files_involved = self._extract_files_involved(tool_name, tool_input, tool_response)

        # Classify the outcome
        outcome = self._classify_outcome(tool_response)

        # Extract error patterns
        error_patterns = self._extract_error_patterns(tool_response)

        # Extract success patterns
        success_patterns = self._extract_success_patterns(tool_response)

        # Generate context data
        context_data = self._generate_context_data(
            tool_name, tool_input, tool_response, outcome, error_patterns, success_patterns
        )

        # Create metadata
        metadata = self._create_metadata(tool_name, tool_input, tool_response, outcome)

        return ToolOutcome(
            tool_name=tool_name,
            outcome=outcome,
            context_data=context_data,
            files_involved=files_involved,
            error_patterns=error_patterns,
            success_patterns=success_patterns,
            metadata=metadata
        )

    def _extract_files_involved(self, tool_name: str, tool_input: Dict[str, Any],
                              tool_response: str) -> List[str]:
        """Extract list of files involved in the tool operation."""
        files = set()

        # Extract from tool input
        if tool_name in ["Edit", "MultiEdit", "Write", "Read"]:
            file_path = tool_input.get("file_path")
            if file_path:
                files.add(file_path)

        elif tool_name.startswith("mcp__filesystem__"):
            # MCP filesystem operations
            path = tool_input.get("path")
            if path:
                files.add(path)

            source = tool_input.get("source")
            if source:
                files.add(source)

            destination = tool_input.get("destination")
            if destination:
                files.add(destination)

        elif tool_name == "Bash":
            # Extract file paths from bash commands
            command = tool_input.get("command", "")
            # Look for common file operations
            file_patterns = [
                r'(?:touch|cat|head|tail|less|more|vim|nano|code)\s+([^\s]+)',
                r'(?:cp|mv|rm|chmod|chown)\s+(?:[^\s]+\s+)?([^\s]+)',
                r'(?:grep|find|locate)\s+.*?([/\w.-]+\.[a-zA-Z]+)',
                r'([/\w.-]+\.[a-zA-Z]+)',  # Generic file pattern
            ]

            for pattern in file_patterns:
                matches = re.findall(pattern, command)
                for match in matches:
                    if os.path.exists(match):
                        files.add(match)

        # Extract from tool response (e.g., error messages mentioning files)
        file_path_pattern = r'(?:/[^\s]+/)?[^\s/]+\.[a-zA-Z]+'
        response_files = re.findall(file_path_pattern, tool_response)
        for file_path in response_files:
            if os.path.exists(file_path):
                files.add(file_path)

        return list(files)

    def _classify_outcome(self, tool_response: str) -> str:
        """Classify the tool outcome based on response content."""
        response_lower = tool_response.lower()

        # Check for explicit errors first
        error_indicators = [
            "error:", "traceback", "exception", "failed", "cannot", "unable to",
            "permission denied", "no such file", "syntax error", "import error"
        ]

        if any(indicator in response_lower for indicator in error_indicators):
            return "failure"

        # Check for partial success
        partial_patterns = [
            "warning", "some issues", "partially", "with warnings",
            "incomplete", "skipped"
        ]

        if any(pattern in response_lower for pattern in partial_patterns):
            return "partial_success"

        # Check for success indicators
        success_indicators = [
            "successfully", "completed", "done", "finished", "created",
            "updated", "formatted", "validated", "✅"
        ]

        if any(indicator in response_lower for indicator in success_indicators):
            return "success"

        # Default to unknown if no clear indicators
        return "unknown"

    def _extract_error_patterns(self, tool_response: str) -> List[str]:
        """Extract error patterns from tool response."""
        found_patterns = []

        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, tool_response, re.IGNORECASE):
                    found_patterns.append(f"{error_type}: {pattern}")
                    break  # Only add one pattern per error type

        # Extract specific error messages
        error_lines = [
            line.strip() for line in tool_response.split('\n')
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception'])
        ]

        for error_line in error_lines[:3]:  # Limit to first 3 error lines
            if len(error_line) > 10 and len(error_line) < 200:
                found_patterns.append(f"specific_error: {error_line}")

        return found_patterns

    def _extract_success_patterns(self, tool_response: str) -> List[str]:
        """Extract success patterns from tool response."""
        found_patterns = []

        for pattern in self.success_patterns:
            if re.search(pattern, tool_response, re.IGNORECASE):
                found_patterns.append(pattern)

        # Extract specific success messages
        success_lines = [
            line.strip() for line in tool_response.split('\n')
            if any(keyword in line.lower() for keyword in ['success', 'completed', 'done', '✅'])
        ]

        for success_line in success_lines[:2]:  # Limit to first 2 success lines
            if len(success_line) > 5 and len(success_line) < 150:
                found_patterns.append(f"specific_success: {success_line}")

        return found_patterns

    def _generate_context_data(self, tool_name: str, tool_input: Dict[str, Any],
                             tool_response: str, outcome: str, error_patterns: List[str],
                             success_patterns: List[str]) -> str:
        """Generate meaningful context data from the tool interaction."""

        context_parts = [
            f"Tool: {tool_name}",
            f"Outcome: {outcome}",
        ]

        # Add key input details
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if command:
                context_parts.append(f"Command: {command[:200]}")  # Truncate long commands

        elif tool_name in ["Edit", "MultiEdit", "Write"]:
            file_path = tool_input.get("file_path")
            if file_path:
                context_parts.append(f"File: {file_path}")

        # Add error context
        if error_patterns:
            context_parts.append("Errors encountered:")
            for pattern in error_patterns[:3]:  # Limit error patterns
                context_parts.append(f"  - {pattern}")

        # Add success context
        if success_patterns:
            context_parts.append("Success indicators:")
            for pattern in success_patterns[:2]:  # Limit success patterns
                context_parts.append(f"  - {pattern}")

        # Add response summary (truncated)
        response_summary = self._create_response_summary(tool_response)
        if response_summary:
            context_parts.append(f"Response: {response_summary}")

        return "\n".join(context_parts)

    def _create_response_summary(self, tool_response: str) -> str:
        """Create a concise summary of the tool response."""
        if not tool_response:
            return ""

        # Remove excessive whitespace and limit length
        summary = re.sub(r'\s+', ' ', tool_response.strip())

        if len(summary) <= 300:
            return summary

        # Try to find a good truncation point
        sentences = summary.split('. ')
        if sentences:
            truncated = sentences[0]
            for sentence in sentences[1:]:
                if len(truncated + '. ' + sentence) <= 250:
                    truncated += '. ' + sentence
                else:
                    break
            return truncated + '...'

        # Fallback to simple truncation
        return summary[:250] + "..."

    def _create_metadata(self, tool_name: str, tool_input: Dict[str, Any],
                        tool_response: str, outcome: str) -> Dict[str, Any]:
        """Create metadata for the tool interaction."""
        metadata = {
            "tool_name": tool_name,
            "outcome": outcome,
            "response_length": len(tool_response),
            "has_errors": outcome in ["failure", "partial_success"],
            "timestamp": str(Path.cwd()),  # Current working directory as context
        }

        # Add tool-specific metadata
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            metadata["command_type"] = self._classify_bash_command(command)
            metadata["command_length"] = len(command)

        elif tool_name in ["Edit", "MultiEdit", "Write"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                metadata["file_extension"] = Path(file_path).suffix
                metadata["file_directory"] = str(Path(file_path).parent)

        return metadata

    def _classify_bash_command(self, command: str) -> str:
        """Classify the type of bash command."""
        command_lower = command.lower().strip()

        if any(cmd in command_lower for cmd in ["git", "gh"]):
            return "version_control"
        elif any(cmd in command_lower for cmd in ["npm", "yarn", "pip", "cargo"]):
            return "package_management"
        elif any(cmd in command_lower for cmd in ["mkdir", "touch", "cp", "mv", "rm"]):
            return "file_operations"
        elif any(cmd in command_lower for cmd in ["grep", "find", "rg", "fd"]):
            return "search"
        elif any(cmd in command_lower for cmd in ["python", "node", "cargo run"]):
            return "execution"
        elif any(cmd in command_lower for cmd in ["ls", "cat", "head", "tail"]):
            return "inspection"
        else:
            return "other"


class ContextCaptureHandler:
    """Main handler for capturing tool usage context."""

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = project_dir or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.analyzer = ToolOutcomeAnalyzer()
        self.logger = logging.getLogger("ContextCaptureHandler")
        self._setup_logging()

        # Tools to capture context for
        self.monitored_tools = {
            "Bash", "Edit", "MultiEdit", "Write", "Read", "Grep", "Glob",
            "mcp__filesystem__write_file", "mcp__filesystem__edit_file",
            "mcp__filesystem__read_text_file", "mcp__filesystem__create_directory",
            "mcp__filesystem__move_file"
        }

        # Initialize context manager
        self.context_manager = None
        try:
            self.context_manager = get_context_manager()
            if self.context_manager:
                self.logger.info("Context manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize context manager: {e}")

    def _setup_logging(self):
        """Setup logging for the handler."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def should_capture_context(self, tool_name: str, tool_input: Dict[str, Any],
                             tool_response: str) -> bool:
        """Determine if context should be captured for this tool interaction."""

        # Skip if tool is not monitored
        if tool_name not in self.monitored_tools:
            return False

        # Skip if response is too short (likely not meaningful)
        if len(tool_response.strip()) < 10:
            return False

        # Skip if response is just standard success output with no context
        if tool_response.strip() in ["", "Success", "Done", "OK"]:
            return False

        # Skip repetitive or low-value operations
        if tool_name == "Read" and "Reading file" in tool_response:
            return False

        return True

    def capture_tool_context(self, tool_name: str, tool_input: Dict[str, Any],
                           tool_response: str) -> Optional[int]:
        """Capture context from a tool interaction."""

        if not self.should_capture_context(tool_name, tool_input, tool_response):
            return None

        try:
            # Analyze the tool outcome
            outcome = self.analyzer.analyze_tool_outcome(tool_name, tool_input, tool_response)

            # Create a user prompt context (this represents what the user was trying to do)
            user_prompt = self._generate_user_prompt_context(tool_name, tool_input, outcome)

            # Store the context
            if self.context_manager:
                context_id = self.context_manager.store_context(
                    user_prompt=user_prompt,
                    context_data=outcome.context_data,
                    files_involved=outcome.files_involved,
                    outcome=outcome.outcome,
                    metadata=outcome.metadata
                )

                if context_id:
                    self.logger.info(f"Captured context for {tool_name} (ID: {context_id})")
                    return context_id
                else:
                    self.logger.warning(f"Failed to store context for {tool_name}")
            else:
                # Fallback to convenience function
                context_id = store_conversation_context(
                    user_prompt=user_prompt,
                    context_data=outcome.context_data,
                    files_involved=outcome.files_involved,
                    outcome=outcome.outcome
                )

                if context_id:
                    self.logger.info(f"Captured context via fallback for {tool_name}")
                    return context_id

        except Exception as e:
            self.logger.error(f"Failed to capture context for {tool_name}: {e}")

        return None

    def _generate_user_prompt_context(self, tool_name: str, tool_input: Dict[str, Any],
                                    outcome: ToolOutcome) -> str:
        """Generate a representative user prompt for context storage."""

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            return f"Execute command: {command}"

        elif tool_name in ["Edit", "MultiEdit"]:
            file_path = tool_input.get("file_path", "")
            return f"Edit file: {file_path}"

        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            return f"Write to file: {file_path}"

        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            return f"Read file: {file_path}"

        elif tool_name.startswith("mcp__filesystem__"):
            operation = tool_name.replace("mcp__filesystem__", "").replace("_", " ")
            path = tool_input.get("path", "")
            return f"Filesystem {operation}: {path}"

        else:
            return f"Use {tool_name} tool"


def handle_context_capture(data: Dict[str, Any]) -> int:
    """
    Handle context capture for PostToolUse hook.

    Args:
        data: Hook event data containing tool_name, tool_input, and tool_response

    Returns:
        int: Exit code (0 for success)
    """

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", "")

    if not tool_name:
        return 0

    try:
        # Initialize handler
        handler = ContextCaptureHandler()

        # Capture context
        context_id = handler.capture_tool_context(tool_name, tool_input, tool_response)

        if context_id:
            # Success - context was captured
            print(f"📝 Context captured for {tool_name} interaction (ID: {context_id})",
                  file=sys.stderr)

        return 0

    except Exception as e:
        # Log error but don't block
        print(f"Warning: Context capture failed: {e}", file=sys.stderr)
        return 0


# For direct execution and testing
if __name__ == "__main__":
    # Read event data from stdin if available
    try:
        if not sys.stdin.isatty():
            event_data = json.loads(sys.stdin.read())
            exit_code = handle_context_capture(event_data)
            sys.exit(exit_code)
        else:
            print("Context Capture Handler - Use as part of PostToolUse hook")
            sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)