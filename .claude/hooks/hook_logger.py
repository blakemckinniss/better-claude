#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path


class HookLogger:
    def __init__(self, log_dir="/home/devcontainers/better-claude/.claude/hooks/hook_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_existing_session_log(self, session_id):
        """Find an existing log file for the given session ID"""
        session_id_short = session_id[:8]
        
        # Search through all date directories
        for date_dir in self.log_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:  # Check if it's a date directory
                # Look for files matching this session ID
                for log_file in date_dir.glob(f"session_*_{session_id_short}.log"):
                    return log_file
        
        return None
    
    def log_hook_call(self, data):
        """Log a hook call to the session-specific log file"""
        session_id = data.get("session_id", "unknown_session")
        hook_event_name = data.get("hook_event_name", "unknown_hook")
        timestamp = datetime.now()
        
        # First, check if a log file already exists for this session
        existing_log_file = self._find_existing_session_log(session_id)
        
        if existing_log_file:
            # Use the existing log file
            log_file = existing_log_file
        else:
            # Create new log file for this session
            date_dir = self.log_dir / timestamp.strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Create readable session filename with current timestamp (12-hour format)
            readable_timestamp = timestamp.strftime("%I-%M-%S_%p")
            session_filename = f"session_{readable_timestamp}_{session_id[:8]}.log"
            log_file = date_dir / session_filename
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "hook_event_name": hook_event_name,
            "session_id": session_id,
            "transcript_path": data.get("transcript_path", ""),
            "cwd": data.get("cwd", ""),
        }
        
        # Add tool-specific information if available
        if "tool_name" in data:
            log_entry["tool_name"] = data["tool_name"]
            log_entry["tool_input"] = data.get("tool_input", {})
        
        # Add any additional data that might be useful
        for key in ["result", "error", "blocked", "action"]:
            if key in data:
                log_entry[key] = data[key]
        
        with open(log_file, "a") as f:
            # Write a human-readable format
            f.write(f"\n{'=' * 80}\n")
            f.write(f"[{timestamp.isoformat()}] {hook_event_name}")
            
            if "tool_name" in log_entry:
                f.write(f" - Tool: {log_entry['tool_name']}")
            
            f.write(f"\n{'-' * 80}\n")
            
            # Write key information
            f.write(f"Session ID: {session_id}\n")
            f.write(f"Working Directory: {log_entry.get('cwd', 'N/A')}\n")
            
            if "tool_name" in log_entry:
                f.write(f"\nTool: {log_entry['tool_name']}\n")
                tool_input = log_entry.get('tool_input', {})
                
                # Format tool input based on tool type
                if log_entry['tool_name'] == 'Bash':
                    f.write(f"Command: {tool_input.get('command', 'N/A')}\n")
                    f.write(f"Description: {tool_input.get('description', 'N/A')}\n")
                elif log_entry['tool_name'] in ['Edit', 'MultiEdit', 'Write']:
                    f.write(f"File: {tool_input.get('file_path', tool_input.get('path', 'N/A'))}\n")
                    if log_entry['tool_name'] == 'Write':
                        content = tool_input.get('content', '')
                        f.write(f"Content Preview: {content[:100]}{'...' if len(content) > 100 else ''}\n")
                else:
                    # Generic tool input display
                    f.write(f"Input: {json.dumps(tool_input, indent=2)}\n")
            
            # Write any results or errors
            if "result" in log_entry:
                f.write(f"\nResult: {log_entry['result']}\n")
            if "error" in log_entry:
                f.write(f"\nError: {log_entry['error']}\n")
            if "blocked" in log_entry:
                f.write(f"\nBlocked: {log_entry['blocked']}\n")
            
            # Also write raw JSON for programmatic access
            f.write(f"\nRAW JSON:\n{json.dumps(log_entry, indent=2)}\n")
    
    def get_session_log_path(self, session_id):
        """Get the path to a specific session log file"""
        return self._find_existing_session_log(session_id)
    
    def list_sessions(self):
        """List all session IDs that have logs, organized by date"""
        sessions_by_date = {}
        
        # Search through all date directories
        for date_dir in self.log_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:  # Check if it's a date directory
                date_str = date_dir.name
                sessions_by_date[date_str] = []
                
                for log_file in date_dir.glob("session_*.log"):
                    # Extract session info from filename
                    filename = log_file.stem
                    parts = filename.split('_')
                    if len(parts) >= 3:
                        time_str = parts[1]  # HH-MM-SS
                        session_id_short = parts[2]  # first 8 chars of session ID
                        sessions_by_date[date_str].append({
                            'time': time_str,
                            'session_id_short': session_id_short,
                            'full_path': log_file
                        })
                
                # Sort sessions by time within each date
                sessions_by_date[date_str].sort(key=lambda x: x['time'])
        
        return sessions_by_date


# Create a singleton instance
logger = HookLogger()