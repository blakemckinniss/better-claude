#!/usr/bin/env python3
"""Test transcript-based session tracking."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hook_handlers.UserPromptSubmit import is_first_user_prompt


def test_transcript_tracking():
    """Test the transcript-based session tracking."""
    print("Testing transcript-based session tracking...")
    
    # Create a temporary home directory structure
    with tempfile.TemporaryDirectory() as temp_home:
        # Override HOME to use our temp directory
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = temp_home
        
        try:
            # Test 1: No transcript directory - should be first prompt
            result1 = is_first_user_prompt()
            print(f"Test 1 - No transcripts: {result1} (expected: True)")
            assert result1 is True, "No transcripts should return True"
            
            # Test 2: Create transcript directory but no files
            transcript_dir = Path(temp_home) / ".claude" / "projects" / "test"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            
            result2 = is_first_user_prompt()
            print(f"Test 2 - Empty transcript dir: {result2} (expected: True)")
            assert result2 is True, "Empty transcript dir should return True"
            
            # Test 3: Create transcript with no user messages
            transcript_file = transcript_dir / "session.jsonl"
            with open(transcript_file, 'w') as f:
                # Write some non-user entries
                f.write(json.dumps({"type": "system", "message": {"content": "Welcome"}}))
                f.write("\n")
                f.write(json.dumps({"type": "assistant", "message": {"content": "Hello"}}))
                f.write("\n")
            
            result3 = is_first_user_prompt()
            print(f"Test 3 - No user messages: {result3} (expected: True)")
            assert result3 is True, "Transcript with no user messages should return True"
            
            # Test 4: Add a user message
            with open(transcript_file, 'a') as f:
                f.write(json.dumps({"type": "user", "message": {"content": "Hi there"}}))
                f.write("\n")
            
            result4 = is_first_user_prompt()
            print(f"Test 4 - Has user message: {result4} (expected: False)")
            assert result4 is False, "Transcript with user message should return False"
            
            # Test 5: Simulate /clear by creating a newer empty transcript
            new_transcript = transcript_dir / "new_session.jsonl"
            with open(new_transcript, 'w') as f:
                f.write(json.dumps({"type": "system", "message": {"content": "New session"}}))
                f.write("\n")
            
            # Touch the file to make it newer
            import time
            time.sleep(0.1)
            os.utime(new_transcript, None)
            
            result5 = is_first_user_prompt()
            print(f"Test 5 - After /clear (new transcript): {result5} (expected: True)")
            assert result5 is True, "New empty transcript should return True"
            
            print("\nAll tests passed! ✅")
            
        finally:
            # Restore original HOME
            if original_home:
                os.environ["HOME"] = original_home
            else:
                del os.environ["HOME"]


if __name__ == "__main__":
    test_transcript_tracking()