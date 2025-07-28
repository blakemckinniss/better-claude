#!/usr/bin/env python3
import sys
import os
from datetime import datetime


def handle(data):
    """Handle SubagentStop hook events"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_dir = os.path.expanduser("~/.claude")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "session-log.txt")

    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] Claude Code subagent session completed\n")

    sys.exit(0)
