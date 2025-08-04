#!/usr/bin/env python3
# Testing PostToolUse hook for Pylance fixes - trigger 3
import glob
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None

# Import session monitor
try:
    from session_monitor import get_session_monitor
    HAS_SESSION_MONITOR = True
except ImportError:
    HAS_SESSION_MONITOR = False
    get_session_monitor = None


def handle(data):
    """Handle Stop hook events."""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(data, "Stop")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Debug: Print received data
    print(f"Stop hook called at {timestamp}", file=sys.stderr)
    print(f"Received data: {json.dumps(data, indent=2)}", file=sys.stderr)

    # Clean up hook_logs subfolders, keeping only the latest 5 files
    project_root = os.environ.get(
        "CLAUDE_PROJECT_DIR",
        "/home/devcontainers/better-claude",
    )
    hook_logs_dir = os.path.join(project_root, ".claude/hooks/hook_logs")
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
    # Initialize variables to avoid "possibly unbound" errors
    last_claude_message = None
    text_content = ""

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
                stop_log_dir = os.path.join(
                    project_root,
                    ".claude/hooks/hook_logs/stop_hook_logs",
                )
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
        stop_log_dir = os.path.join(
            project_root,
            ".claude/hooks/hook_logs/stop_hook_logs",
        )
        os.makedirs(stop_log_dir, exist_ok=True)

        error_log_path = os.path.join(
            stop_log_dir,
            f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        with open(error_log_path, "w") as f:
            f.write(f"Error logging Claude message: {str(e)}\n")

    # Auto-commit functionality
    try:
        # Check if auto-commit is enabled via environment variable
        auto_commit_enabled = (
            os.environ.get("CLAUDE_AUTO_COMMIT", "false").lower() == "true"
        )

        if auto_commit_enabled:
            print("Auto-commit is enabled, checking for changes...", file=sys.stderr)

            # Change to project directory
            original_dir = os.getcwd()
            os.chdir(project_root)

            # Check git status
            import subprocess

            # Check if there are any changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
            )

            if status_result.returncode == 0 and status_result.stdout.strip():
                print("Changes detected, preparing to commit...", file=sys.stderr)

                # Add all changes
                add_result = subprocess.run(
                    ["git", "add", "-A"],
                    capture_output=True,
                    text=True,
                )

                if add_result.returncode == 0:
                    # Generate commit message
                    commit_message = f"Auto-commit: Session ended at {timestamp}"

                    # If we have the last Claude message, use it to create a better commit message
                    if "last_claude_message" in locals() and last_claude_message:
                        # Extract first line of Claude's response as commit summary
                        if "text_content" in locals() and text_content:
                            first_line = text_content.strip().split("\n")[0]
                            # Truncate to 50 chars for commit message convention
                            if len(first_line) > 50:
                                first_line = f"{first_line[:47]}..."
                            commit_message = f"Auto-commit: {first_line}"

                    # Commit changes
                    commit_result = subprocess.run(
                        ["git", "commit", "-m", commit_message],
                        capture_output=True,
                        text=True,
                    )

                    if commit_result.returncode == 0:
                        print(
                            f"Successfully auto-committed changes: {commit_message}",
                            file=sys.stderr,
                        )
                        print(f"Commit output: {commit_result.stdout}", file=sys.stderr)
                    else:
                        print(
                            f"Failed to commit: {commit_result.stderr}", file=sys.stderr
                        )
                else:
                    print(
                        f"Failed to add changes: {add_result.stderr}", file=sys.stderr
                    )
            else:
                print("No changes to commit", file=sys.stderr)

            # Return to original directory
            os.chdir(original_dir)

    except Exception as e:
        print(f"Error during auto-commit: {str(e)}", file=sys.stderr)
        # Don't fail the hook due to auto-commit errors
        if hook_logger:
            hook_logger.log_error(data, e)

    # Finalize session monitor
    if HAS_SESSION_MONITOR and get_session_monitor:
        try:
            session_id = data.get("session_id", "unknown")
            if session_id != "unknown":
                monitor = get_session_monitor(session_id)

                # Log the last Claude response if we have it
                if "last_claude_message" in locals() and last_claude_message and "text_content" in locals() and text_content:
                    monitor.log_response(text_content, {
                        "source": "final_response",
                        "timestamp": timestamp
                    })

                # Finalize the session
                status = "completed"
                if data.get("error"):
                    status = "error"
                elif data.get("cancelled"):
                    status = "cancelled"

                monitor.finalize(status)
                print(f"Session monitor finalized for {session_id[:8]}", file=sys.stderr)
        except Exception as e:
            print(f"Error finalizing session monitor: {e}", file=sys.stderr)
            if os.environ.get("DEBUG_HOOKS"):
                import traceback
                traceback.print_exc()

    # Log successful exit
    if hook_logger:
        hook_logger.log_hook_exit(data, 0, result="success")
    sys.exit(0)
