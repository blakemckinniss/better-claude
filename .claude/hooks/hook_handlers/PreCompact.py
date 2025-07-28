#!/usr/bin/env python3
import sys
import os
from datetime import datetime

def handle(data):
    """Handle PreCompact hook events"""
    trigger = data.get('trigger', '')
    custom_instructions = data.get('custom_instructions', '')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_dir = os.path.expanduser('~/.claude')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'compact-log.txt')
    
    with open(log_path, 'a') as f:
        f.write(f"[{timestamp}] Compact triggered: {trigger}\n")
        if custom_instructions:
            f.write(f"  Custom instructions: {custom_instructions}\n")
    
    sys.exit(0)