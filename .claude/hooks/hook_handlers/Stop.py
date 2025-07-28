#!/usr/bin/env python3
# Testing PostToolUse hook for Pylance fixes - trigger 3
import glob
import json
import os
import shutil
import sys
from datetime import datetime


def handle(data):
    """Handle Stop hook events."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Debug: Print received data
    print(f"Stop hook called at {timestamp}", file=sys.stderr)
    print(f"Received data: {json.dumps(data, indent=2)}", file=sys.stderr)

    # Clean up hook_logs subfolders, keeping only the latest 5 files
    hook_logs_dir = ".claude/hooks/hook_logs"
    if os.path.exists(hook_logs_dir):
        print(
            f"Cleaning up contents of subfolders in {hook_logs_dir} (keeping latest 5 files)",
            file=sys.stderr,
        )
        for subfolder in os.listdir(hook_logs_dir):
            subfolder_path = os.path.join(hook_logs_dir, subfolder)
            if os.path.isdir(subfolder_path):
                # Get all files in the subfolder with their modification times
                files_with_times = []
                for item in os.listdir(subfolder_path):
                    item_path = os.path.join(subfolder_path, item)
                    if os.path.isfile(item_path):
                        files_with_times.append(
                            (item_path, os.path.getmtime(item_path)),
                        )

                # Sort files by modification time (newest first)
                files_with_times.sort(key=lambda x: x[1], reverse=True)

                # Delete files beyond the 5 most recent
                for i, (file_path, _) in enumerate(files_with_times):
                    if i >= 5:  # Keep only the first 5 (newest)
                        try:
                            os.remove(file_path)
                            print(f"Deleted old file: {file_path}", file=sys.stderr)
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}", file=sys.stderr)

                # Delete any subdirectories
                for item in os.listdir(subfolder_path):
                    item_path = os.path.join(subfolder_path, item)
                    if os.path.isdir(item_path):
                        try:
                            shutil.rmtree(item_path)
                            print(f"Deleted subdirectory: {item_path}", file=sys.stderr)
                        except Exception as e:
                            print(f"Error deleting {item_path}: {e}", file=sys.stderr)

    # Original logging
    log_dir = os.path.expanduser("~/.claude")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "session-log.txt")

    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] Claude Code session completed\n")

    # New functionality: Log last Claude message from transcript
    try:
        # Get transcript path from data if available
        transcript_path = data.get("transcript_path")
        print(f"Transcript path from data: {transcript_path}", file=sys.stderr)

        if not transcript_path:
            # Try to find the most recent transcript file
            transcript_dir = os.path.expanduser("~/.claude/projects")
            pattern = os.path.join(transcript_dir, "**/*.jsonl")
            print(f"Searching for transcripts in: {pattern}", file=sys.stderr)
            transcript_files = glob.glob(pattern, recursive=True)
            print(f"Found {len(transcript_files)} transcript files", file=sys.stderr)

            if transcript_files:
                # Get the most recently modified transcript
                transcript_path = max(transcript_files, key=os.path.getmtime)
                print(
                    f"Using most recent transcript: {transcript_path}",
                    file=sys.stderr,
                )

        if transcript_path and os.path.exists(transcript_path):
            # Read the transcript file
            last_claude_message = None

            with open(transcript_path) as f:
                line_count = 0
                assistant_count = 0
                for line in f:
                    line_count += 1
                    try:
                        entry = json.loads(line.strip())
                        # Check for the actual Claude Code transcript structure
                        if entry.get("type") == "assistant" and "message" in entry:
                            assistant_count += 1
                            # Extract the actual message content
                            message = entry["message"]
                            if message.get("role") == "assistant":
                                last_claude_message = {
                                    "role": "assistant",
                                    "content": message.get("content", []),
                                    "timestamp": entry.get("timestamp"),
                                    "model": message.get("model"),
                                    "id": message.get("id"),
                                }
                    except json.JSONDecodeError:
                        continue
                print(
                    f"Processed {line_count} lines, found {assistant_count} assistant messages",
                    file=sys.stderr,
                )

            # Log the last Claude message if found
            if last_claude_message:
                # Claude Code always runs from the project root
                stop_log_dir = ".claude/hooks/hook_logs/stop_hook_logs"
                os.makedirs(stop_log_dir, exist_ok=True)

                # Create a unique log filename with timestamp
                log_filename = (
                    f"stop_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                stop_log_path = os.path.join(stop_log_dir, log_filename)

                # Extract text content from content blocks
                text_content = ""
                if isinstance(last_claude_message.get("content"), list):
                    for block in last_claude_message["content"]:
                        if block.get("type") == "text":
                            text_content += block.get("text", "")

                # Write the last Claude message to the log
                log_entry = {
                    "timestamp": timestamp,
                    "transcript_path": transcript_path,
                    "last_claude_message": {
                        "role": last_claude_message["role"],
                        "content": text_content,
                        "model": last_claude_message.get("model"),
                        "id": last_claude_message.get("id"),
                        "timestamp": last_claude_message.get("timestamp"),
                    },
                }

                with open(stop_log_path, "w") as f:
                    json.dump(log_entry, f, indent=2)

                print(
                    f"Logged last Claude message to: {stop_log_path}",
                    file=sys.stderr,
                )
                # Also print to stdout for the hook system
                print("Successfully logged Claude's last message")
            else:
                print("No Claude messages found in transcript", file=sys.stderr)

    except Exception as e:
        # Log any errors but don't crash the hook
        # Initialize stop_log_dir to avoid "possibly unbound" error
        stop_log_dir = ".claude/hooks/hook_logs/stop_hook_logs"
        os.makedirs(stop_log_dir, exist_ok=True)

        error_log_path = os.path.join(
            stop_log_dir,
            f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        with open(error_log_path, "w") as f:
            f.write(f"Error logging Claude message: {str(e)}\n")

    sys.exit(0)
