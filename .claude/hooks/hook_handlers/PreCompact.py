#!/usr/bin/env python3
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UserPromptSubmit.session_state import SessionState

def handle(data):
    """Handle PreCompact hook events"""
    trigger = data.get('trigger', '')
    custom_instructions = data.get('custom_instructions', '')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Log the compact event
    log_dir = os.path.expanduser('~/.claude')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'compact-log.txt')
    
    with open(log_path, 'a') as f:
        f.write(f"[{timestamp}] Compact triggered: {trigger}\n")
        if custom_instructions:
            f.write(f"  Custom instructions: {custom_instructions}\n")
    
    # Mark for injection on next user prompt since context was compacted
    try:
        session_state = SessionState()
        session_state.request_next_injection("pre_compact")
        print(f"Marked for context injection on next prompt after compact (trigger: {trigger})", file=sys.stderr)
    except Exception as e:
        print(f"Error marking for injection: {e}", file=sys.stderr)
    
    sys.exit(0)