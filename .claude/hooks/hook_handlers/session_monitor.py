"""Session monitoring system for Claude Code interactions.

This module provides comprehensive session logging with:
- Human-readable session logs with smart truncation
- Structured data storage for full interaction history  
- Integration with existing hooks system
- Minimal performance impact
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import threading


class SmartTruncator:
    """Handles intelligent text truncation while preserving readability."""
    
    TRUNCATION_LIMITS = {
        "user_prompt": 200,
        "tool_command": 150,
        "tool_output": 100,
        "response": 300,
        "error_message": 500,
    }
    
    @staticmethod
    def truncate(text: str, limit: int, preserve_structure: bool = True) -> Tuple[str, bool]:
        """Truncate text intelligently while preserving readability.
        
        Returns:
            Tuple of (truncated_text, was_truncated)
        """
        if not text or len(text) <= limit:
            return text, False
            
        # For structured content, try to preserve opening/closing markers
        if preserve_structure:
            # Check for JSON
            if text.strip().startswith('{') or text.strip().startswith('['):
                return text[:limit-20] + "...[truncated]...", True
            
            # Check for code blocks
            if '```' in text[:50]:
                code_start = text.find('```')
                if code_start != -1:
                    # Preserve language identifier
                    newline_pos = text.find('\n', code_start)
                    if newline_pos > code_start and newline_pos < limit:
                        return text[:newline_pos+1] + "...[truncated]...\n```", True
        
        # Standard truncation with word boundary respect
        truncated = text[:limit]
        last_space = truncated.rfind(' ')
        if last_space > limit * 0.8:  # If there's a space reasonably close
            truncated = truncated[:last_space]
        
        # Add line count indicator if multiple lines
        line_count = text.count('\n')
        if line_count > 1:
            truncated_lines = truncated.count('\n')
            remaining_lines = line_count - truncated_lines
            return f"{truncated}...[+{remaining_lines} lines]", True
        
        return truncated + "...", True
    
    @staticmethod
    def group_similar_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group similar tool calls for concise display."""
        if len(tools) <= 3:
            return tools
        
        # Group by tool name
        grouped = defaultdict(list)
        for tool in tools:
            grouped[tool.get('tool_name', 'unknown')].append(tool)
        
        result = []
        for tool_name, tool_list in grouped.items():
            if len(tool_list) == 1:
                result.append(tool_list[0])
            else:
                # Create a summary entry
                summary = {
                    'tool_name': tool_name,
                    'count': len(tool_list),
                    'summary': f"{tool_name}: {len(tool_list)} calls",
                    'details': [t.get('details', '') for t in tool_list[:3]]
                }
                result.append(summary)
        
        return result


class SessionMonitor:
    """Manages session-specific monitoring and logging."""
    
    _instances = {}  # Class-level storage for singleton per session
    _lock = threading.Lock()
    
    def __new__(cls, session_id: str):
        """Ensure singleton per session_id."""
        with cls._lock:
            if session_id not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[session_id] = instance
            return cls._instances[session_id]
    
    def __init__(self, session_id: str):
        """Initialize session monitor for a specific session."""
        # Skip re-initialization for existing instances
        if hasattr(self, '_initialized'):
            return
            
        self.session_id = session_id
        self.short_id = session_id[:8]
        self.base_dir = Path("/home/devcontainers/better-claude/.claude/logs/session_monitor")
        self.session_dir = self.base_dir / self.short_id
        self.interactions_dir = self.session_dir / "interactions"
        
        self.start_time = datetime.now()
        self.interaction_counter = 0
        self.prompt_counter = 0
        self.tool_counter = 0
        self.truncator = SmartTruncator()
        
        # Thread safety for file operations
        self.file_lock = threading.Lock()
        
        # Create directories
        self._ensure_directories()
        
        # Initialize session files
        self._initialize_session()
        
        self._initialized = True
    
    def _ensure_directories(self):
        """Create necessary directories."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.interactions_dir.mkdir(exist_ok=True)
    
    def _initialize_session(self):
        """Initialize session log and metadata files."""
        # Create session.log header
        header = f"""{'═' * 79}
SESSION: {self.session_id} | Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
{'═' * 79}

"""
        with self.file_lock:
            with open(self.session_dir / "session.log", 'w') as f:
                f.write(header)
        
        # Create initial summary.json
        summary = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "status": "active",
            "counters": {
                "prompts": 0,
                "tools": 0,
                "errors": 0
            }
        }
        with self.file_lock:
            with open(self.session_dir / "summary.json", 'w') as f:
                json.dump(summary, f, indent=2)
    
    def log_prompt(self, prompt: str, metadata: Optional[Dict] = None) -> None:
        """Log user prompt with truncation."""
        self.prompt_counter += 1
        self.interaction_counter += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Truncate for session log
        truncated, was_truncated = self.truncator.truncate(
            prompt, 
            self.truncator.TRUNCATION_LIMITS['user_prompt']
        )
        
        # Write to session.log
        log_entry = f"""
[{timestamp}] USER PROMPT #{self.prompt_counter}
{'─' * 78}
{truncated}
"""
        if was_truncated:
            log_entry += f"[see interactions/{self.interaction_counter:03d}_prompt.txt for full text]\n"
        
        with self.file_lock:
            with open(self.session_dir / "session.log", 'a') as f:
                f.write(log_entry)
        
        # Save full prompt to interactions
        interaction_file = self.interactions_dir / f"{self.interaction_counter:03d}_prompt.txt"
        with self.file_lock:
            with open(interaction_file, 'w') as f:
                f.write(prompt)
                if metadata:
                    f.write(f"\n\n--- METADATA ---\n{json.dumps(metadata, indent=2)}")
    
    def log_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Log tool usage with smart grouping."""
        if not tools:
            return
            
        self.tool_counter += len(tools)
        self.interaction_counter += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Group similar tools
        grouped_tools = self.truncator.group_similar_tools(tools)
        
        # Format for session.log
        log_entry = f"\n[{timestamp}] TOOLS USED ({len(tools)} calls)\n"
        log_entry += '─' * 78 + '\n'
        
        for tool in grouped_tools[:5]:  # Show first 5
            if 'count' in tool:  # Grouped entry
                log_entry += f"• {tool['summary']}\n"
                for detail in tool['details']:
                    truncated_detail, _ = self.truncator.truncate(detail, 100)
                    log_entry += f"  - {truncated_detail}\n"
            else:  # Single tool
                tool_desc = f"{tool.get('tool_name', 'Unknown')}: {tool.get('details', '')}"
                truncated_desc, _ = self.truncator.truncate(
                    tool_desc,
                    self.truncator.TRUNCATION_LIMITS['tool_command']
                )
                log_entry += f"• {truncated_desc}\n"
        
        if len(tools) > 5:
            log_entry += f"  ... and {len(tools) - 5} more\n"
        
        with self.file_lock:
            with open(self.session_dir / "session.log", 'a') as f:
                f.write(log_entry)
        
        # Save full tool details to interactions
        interaction_file = self.interactions_dir / f"{self.interaction_counter:03d}_tools.json"
        with self.file_lock:
            with open(interaction_file, 'w') as f:
                json.dump(tools, f, indent=2)
    
    def log_response(self, response: str, metadata: Optional[Dict] = None) -> None:
        """Log response summary."""
        self.interaction_counter += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Extract first substantive paragraph or summary
        summary = self._extract_response_summary(response)
        truncated, was_truncated = self.truncator.truncate(
            summary,
            self.truncator.TRUNCATION_LIMITS['response']
        )
        
        # Write to session.log
        log_entry = f"\n[{timestamp}] RESPONSE SUMMARY\n"
        log_entry += '─' * 78 + '\n'
        log_entry += truncated + '\n'
        
        if was_truncated:
            log_entry += f"[see interactions/{self.interaction_counter:03d}_response.txt for full text]\n"
        
        with self.file_lock:
            with open(self.session_dir / "session.log", 'a') as f:
                f.write(log_entry)
        
        # Save full response to interactions
        interaction_file = self.interactions_dir / f"{self.interaction_counter:03d}_response.txt"
        with self.file_lock:
            with open(interaction_file, 'w') as f:
                f.write(response)
                if metadata:
                    f.write(f"\n\n--- METADATA ---\n{json.dumps(metadata, indent=2)}")
    
    def log_error(self, error: str, context: Optional[Dict] = None) -> None:
        """Log errors with full context."""
        self.interaction_counter += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Errors get more space
        truncated, was_truncated = self.truncator.truncate(
            error,
            self.truncator.TRUNCATION_LIMITS['error_message']
        )
        
        log_entry = f"\n[{timestamp}] ERROR\n"
        log_entry += '─' * 78 + '\n'
        log_entry += truncated + '\n'
        
        with self.file_lock:
            with open(self.session_dir / "session.log", 'a') as f:
                f.write(log_entry)
        
        # Update error counter in summary
        self._update_summary({"errors": 1})
    
    def finalize(self, status: str = "completed") -> None:
        """Complete session logging."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # Add session footer
        footer = f"""
{'═' * 79}
SESSION ENDED: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | Duration: {duration}
Status: {status} | Prompts: {self.prompt_counter} | Tools: {self.tool_counter}
{'═' * 79}
"""
        with self.file_lock:
            with open(self.session_dir / "session.log", 'a') as f:
                f.write(footer)
        
        # Update summary
        summary_updates = {
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "status": status,
            "counters": {
                "prompts": self.prompt_counter,
                "tools": self.tool_counter,
                "interactions": self.interaction_counter
            }
        }
        self._update_summary(summary_updates)
        
        # Clean up class instance
        with self.__class__._lock:
            if self.session_id in self.__class__._instances:
                del self.__class__._instances[self.session_id]
    
    def _extract_response_summary(self, response: str) -> str:
        """Extract a meaningful summary from response."""
        # Remove markdown formatting
        clean = re.sub(r'```[\s\S]*?```', '[code block]', response)
        clean = re.sub(r'`[^`]+`', '[inline code]', clean)
        
        # Find first substantive paragraph
        paragraphs = clean.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50 and not para.startswith(('#', '-', '*', '1.')):
                return para
        
        # Fallback to first non-empty content
        return clean.strip() or "No response content"
    
    def _update_summary(self, updates: Dict[str, Any]) -> None:
        """Update summary.json with new data."""
        summary_file = self.session_dir / "summary.json"
        
        with self.file_lock:
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
            else:
                summary = {}
            
            # Deep merge updates
            for key, value in updates.items():
                if isinstance(value, dict) and key in summary and isinstance(summary[key], dict):
                    summary[key].update(value)
                else:
                    summary[key] = value
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)


# Singleton accessor for hooks
def get_session_monitor(session_id: str) -> SessionMonitor:
    """Get or create SessionMonitor instance for session."""
    return SessionMonitor(session_id)