#!/usr/bin/env python3
"""Verify the transcript-based logic works correctly."""

import glob
import json
import os


def check_transcript_logic():
    """Test the transcript checking logic."""
    transcript_dir = os.path.expanduser("~/.claude/projects")
    
    print(f"Transcript directory: {transcript_dir}")
    print(f"Directory exists: {os.path.exists(transcript_dir)}")
    
    if not os.path.exists(transcript_dir):
        print("Result: Would return True (no transcript directory)")
        return
    
    # Find all JSONL transcript files
    pattern = os.path.join(transcript_dir, "**/*.jsonl")
    transcript_files = glob.glob(pattern, recursive=True)
    
    print(f"\nFound {len(transcript_files)} transcript files")
    
    if not transcript_files:
        print("Result: Would return True (no transcripts)")
        return
    
    # Get the most recent transcript file
    latest_transcript = max(transcript_files, key=os.path.getmtime)
    print(f"\nLatest transcript: {latest_transcript}")
    print(f"File size: {os.path.getsize(latest_transcript)} bytes")
    
    # Check if this transcript has any user messages yet
    user_message_count = 0
    total_entries = 0
    
    try:
        with open(latest_transcript, 'r') as f:
            for line in f:
                if line.strip():
                    total_entries += 1
                    try:
                        entry = json.loads(line)
                        # Check for user messages in the transcript
                        if entry.get("type") == "user" and "message" in entry:
                            user_message_count += 1
                            print(f"\nFound user message #{user_message_count}:")
                            msg = entry["message"]
                            content = msg.get("content", "")
                            if isinstance(content, list) and content:
                                content = content[0].get("text", "")[:50] + "..."
                            elif isinstance(content, str):
                                content = content[:50] + "..."
                            print(f"  Content preview: {content}")
                    except json.JSONDecodeError as e:
                        print(f"  JSON decode error: {e}")
                        continue
    except (IOError, OSError) as e:
        print(f"\nError reading transcript: {e}")
        print("Result: Would return True (can't read transcript)")
        return
    
    print(f"\nTotal entries: {total_entries}")
    print(f"User messages: {user_message_count}")
    
    # If we haven't seen any user messages yet, this is the first prompt
    is_first = user_message_count == 0
    print(f"\nResult: Would return {is_first}")
    
    if is_first:
        print("This would be treated as the FIRST user prompt (full context injected)")
    else:
        print("This would be treated as a CONTINUED conversation (minimal context)")


if __name__ == "__main__":
    check_transcript_logic()