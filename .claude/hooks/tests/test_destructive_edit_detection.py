#!/usr/bin/env python3
"""Test file for destructive edit detection."""

import json
import os
import subprocess
import sys


def test_destructive_write_detection():
    """Test that writing significantly smaller content to a file is blocked."""
    # Create a test file with substantial content
    test_file = "/tmp/test_destructive_edit.py"

    # Write initial content (400 lines)
    initial_content = []
    for i in range(400):
        initial_content.append(f"def function_{i}():")
        initial_content.append(f'    """Function {i} documentation."""')
        initial_content.append(f"    result = {i} * 2")
        initial_content.append("    return result")
        initial_content.append("")

    with open(test_file, "w") as f:
        f.write("\n".join(initial_content))

    print(f"Created test file with {len(initial_content)} lines")

    # Try to replace with minimal content (should be blocked)
    minimal_content = "# This file was cleared\npass\n"

    # Create hook event data
    event_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": test_file,
            "content": minimal_content,
        },
    }

    # Run the hook
    process = subprocess.Popen(
        [
            sys.executable,
            "/home/devcontainers/better-claude/.claude/hooks/hook_handlers/PreToolUse.py",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate(json.dumps(event_data).encode())

    print("Exit code:", process.returncode)
    print("Stderr output:")
    print(stderr.decode())

    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

    # Check if it was blocked (exit code 2)
    assert process.returncode == 2, f"Expected exit code 2, got {process.returncode}"
    assert "DESTRUCTIVE EDIT BLOCKED" in stderr.decode(), (
        "Expected destructive edit message"
    )

    print("✅ Destructive write detection test passed!")


def test_large_edit_detection():
    """Test that large edit replacements are blocked."""
    # Create a test file
    test_file = "/tmp/test_large_edit.py"

    # Write initial content
    with open(test_file, "w") as f:
        f.write(f"# Large function below\n{'x' * 1000}")

    # Create hook event data for a large edit
    event_data = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": test_file,
            "old_string": "x" * 1000,
            "new_string": "# Removed",
        },
    }

    # Run the hook
    process = subprocess.Popen(
        [
            sys.executable,
            "/home/devcontainers/better-claude/.claude/hooks/hook_handlers/PreToolUse.py",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate(json.dumps(event_data).encode())

    print("\nLarge edit test:")
    print("Exit code:", process.returncode)
    print("Stderr output:")
    print(stderr.decode())

    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

    # Check if it was blocked
    assert process.returncode == 2, f"Expected exit code 2, got {process.returncode}"
    assert "DESTRUCTIVE EDIT BLOCKED" in stderr.decode(), (
        "Expected destructive edit message"
    )

    print("✅ Large edit detection test passed!")


def test_critical_file_warning():
    """Test that modifying critical files generates warnings."""
    # Create a fake UserPromptSubmit.py in temp
    test_file = "/tmp/UserPromptSubmit.py"

    with open(test_file, "w") as f:
        f.write("# Test critical file\n")

    # Create hook event data
    event_data = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": test_file,
            "old_string": "# Test critical file",
            "new_string": "# Modified critical file",
        },
    }

    # Run the hook
    process = subprocess.Popen(
        [
            sys.executable,
            "/home/devcontainers/better-claude/.claude/hooks/hook_handlers/PreToolUse.py",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate(json.dumps(event_data).encode())

    print("\nCritical file test:")
    print("Exit code:", process.returncode)
    print("Stderr output:")
    print(stderr.decode())

    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

    # Should not block but should warn
    assert process.returncode == 0, f"Expected exit code 0, got {process.returncode}"
    assert "CRITICAL FILE" in stderr.decode(), "Expected critical file warning"

    print("✅ Critical file warning test passed!")


if __name__ == "__main__":
    print("Testing destructive edit detection...")
    test_destructive_write_detection()
    test_large_edit_detection()
    test_critical_file_warning()
    print("\n✅ All tests passed!")
