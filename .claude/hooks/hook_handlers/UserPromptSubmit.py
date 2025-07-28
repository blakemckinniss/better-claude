#!/usr/bin/env python3
import sys
from datetime import datetime


def handle(data):
    """Handle UserPromptSubmit hook events"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Output current time to stdout which will be added to context
    print(f"Current time: {timestamp}")

    sys.exit(0)
