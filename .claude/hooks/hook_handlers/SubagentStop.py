#!/usr/bin/env python3
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.session_state import SessionState

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None


def handle(data):
    """Handle SubagentStop hook events"""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(data, "SubagentStop")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log the subagent stop
    log_dir = os.path.expanduser("~/.claude")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "session-log.txt")

    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] Claude Code subagent session completed\n")
    
    # Mark for injection on next user prompt to refresh context
    try:
        session_state = SessionState()
        session_state.request_next_injection("subagent_stop")
        print("Marked for context injection on next prompt after subagent completion", file=sys.stderr)
    except Exception as e:
        print(f"Error marking for injection: {e}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_error(data, e)

    # Log successful exit
    if hook_logger:
        hook_logger.log_hook_exit(data, 0, result="success")
    sys.exit(0)
