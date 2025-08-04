#!/usr/bin/env python3
"""
PostToolUse hook handler - now uses the global Guard module.

This file maintains backwards compatibility while delegating to the modular system
with proper guard protection.
"""

import json
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the global guard
try:
    from Guard import create_guarded_handler
except ImportError as e:
    print(f"Error importing Guard module: {e}", file=sys.stderr)
    sys.exit(1)

# Import the modular handler
try:
    from PostToolUse import handle_hook
except ImportError as e:
    print(f"Error importing PostToolUse module: {e}", file=sys.stderr)
    sys.exit(1)

# Create the guarded handler for PostToolUse
handle = create_guarded_handler(handle_hook, "PostToolUse")


if __name__ == "__main__":
    try:
        # Read event data from stdin
        event_data = json.loads(sys.stdin.read())

        # Handle with guard
        handle(event_data)

    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)