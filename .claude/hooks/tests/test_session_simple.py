#!/usr/bin/env python3
"""Simple test to verify the session tracking function works."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Test directly in the hook handler directory
os.chdir(Path(__file__).parent.parent / "hook_handlers")

# Now we can import the module directly
from UserPromptSubmit import is_first_user_prompt

# Create a temp directory for testing
with tempfile.TemporaryDirectory() as temp_dir:
    os.environ["CLAUDE_PROJECT_DIR"] = temp_dir
    
    print("Testing session tracking...")
    
    # First call
    result1 = is_first_user_prompt()
    print(f"First call: {result1} (expected: True)")
    
    # Second call
    result2 = is_first_user_prompt()
    print(f"Second call: {result2} (expected: False)")
    
    # Third call
    result3 = is_first_user_prompt()
    print(f"Third call: {result3} (expected: False)")
    
    # Check session file
    session_file = Path(temp_dir) / ".claude" / "hooks" / "session_data" / "current_session.json"
    if session_file.exists():
        with open(session_file) as f:
            data = json.load(f)
        print(f"\nSession data: {json.dumps(data, indent=2)}")
    
    if result1 and not result2 and not result3:
        print("\n✅ Session tracking works correctly!")
    else:
        print("\n❌ Session tracking failed!")
        sys.exit(1)