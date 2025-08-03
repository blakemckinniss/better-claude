#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None


def handle(data):
    """Handle Notification hook events"""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(data, "Notification")
    
    message = data.get("message", "")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        log_dir = os.path.expanduser("~/.claude")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "notifications.log")

        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] Claude Code notification: {message}\n")
    except Exception as e:
        print(f"Error logging notification: {e}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_error(data, e)
        sys.exit(1)

    # Log successful exit
    if hook_logger:
        hook_logger.log_hook_exit(data, 0, result="success")
    sys.exit(0)
