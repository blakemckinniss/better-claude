#!/usr/bin/env python3
"""Test suite for enhanced PreToolUse hook functionality."""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add hook_handlers to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hook_handlers"))


def run_hook(tool_name, tool_input):
    """Run the PreToolUse hook with given input."""
    data = {
        "tool_name": tool_name,
        "tool_input": tool_input
    }
    
    # Set environment
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(Path(__file__).parent.parent.parent.parent)
    env["CLAUDE_SESSION_ID"] = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run the hook
    process = subprocess.Popen(
        [sys.executable, "-c", "from PreToolUse import handle; import json, sys; handle(json.loads(sys.stdin.read()))"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(Path(__file__).parent.parent / "hook_handlers")
    )
    
    stdout, stderr = process.communicate(input=json.dumps(data).encode())
    
    return {
        "exit_code": process.returncode,
        "stdout": stdout.decode() if stdout else "",
        "stderr": stderr.decode() if stderr else ""
    }


def test_git_aware_warnings():
    """Test Git-aware warnings for uncommitted changes."""
    print("\n=== Testing Git-Aware Warnings ===")
    
    # Test editing a file with uncommitted changes (simulated)
    # Note: Git warnings require actual git status
    result = run_hook("Edit", {
        "file_path": ".claude/hooks/hook_handlers/PreToolUse.py"
    })
    
    print(f"Edit file - Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"Warnings/Errors:\n{result['stderr']}")
    else:
        print("(Git warnings require actual uncommitted changes)")
    
    # Test deleting a file with dependencies
    result = run_hook("Bash", {
        "command": "rm PreToolUse.py",
        "description": "Remove hook handler"
    })
    
    print(f"\nDeleting file - Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"Warnings/Errors:\n{result['stderr']}")


def test_old_tool_suggestions():
    """Test suggestions for using modern tools."""
    print("\n=== Testing Old Tool Suggestions ===")
    
    old_commands = [
        ("grep pattern file.txt", "Search for pattern"),
        ("find . -name '*.py'", "Find Python files"),
        ("cat README.md", "Display README")
    ]
    
    for command, desc in old_commands:
        result = run_hook("Bash", {
            "command": command,
            "description": desc
        })
        
        print(f"\nCommand: {command}")
        print(f"Exit code: {result['exit_code']}")
        if result['stderr']:
            print(f"Suggestions:\n{result['stderr']}")


def test_pattern_detection():
    """Test intelligent pattern detection."""
    print("\n=== Testing Pattern Detection ===")
    
    test_files = [
        "src/test_utils.py",  # Test file outside tests/
        "/tmp/temp_file.tmp",  # Temporary file
        "path/to/path/to/file.py",  # Recursive path
        "mixed\\path/separators.txt"  # Mixed separators
    ]
    
    for file_path in test_files:
        result = run_hook("Write", {
            "file_path": file_path,
            "content": "test content"
        })
        
        print(f"\nFile: {file_path}")
        print(f"Exit code: {result['exit_code']}")
        if result['stderr']:
            print(f"Warnings:\n{result['stderr']}")


def test_dependency_warnings():
    """Test dependency impact warnings."""
    print("\n=== Testing Dependency Warnings ===")
    
    # Create a mock Python file that imports many things
    mock_file = "/tmp/heavily_imported.py"
    with open(mock_file, "w") as f:
        f.write("# Mock file for testing\n")
    
    result = run_hook("Edit", {
        "file_path": mock_file
    })
    
    print(f"Editing heavily imported file - Exit code: {result['exit_code']}")
    if result['stderr']:
        print(f"Warnings:\n{result['stderr']}")
    
    # Clean up
    os.remove(mock_file)


def test_enhanced_logging():
    """Test that operations are being logged."""
    print("\n=== Testing Enhanced Logging ===")
    
    # Run a few operations
    operations = [
        ("Read", {"file_path": "README.md"}),
        ("Write", {"file_path": "/tmp/test_log.txt", "content": "test"}),
        ("Bash", {"command": "echo 'test'", "description": "Test echo"})
    ]
    
    for tool, input_data in operations:
        run_hook(tool, input_data)
    
    # Check if log files were created
    log_dir = Path.home() / ".claude" / "hooks" / "operation_logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("operations_*.jsonl"))
        if log_files:
            print(f"Found {len(log_files)} log file(s)")
            
            # Read latest log
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            with open(latest_log) as f:
                lines = f.readlines()
                print(f"Latest log has {len(lines)} entries")
                
                # Show last entry
                if lines:
                    last_entry = json.loads(lines[-1])
                    print(f"Last logged operation: {last_entry['tool']} - {last_entry['operation']}")
        else:
            print("No log files found")
    else:
        print("Log directory not created")


def test_non_blocking_suggestions():
    """Test non-blocking suggestions vs blocking errors."""
    print("\n=== Testing Non-Blocking vs Blocking Behavior ===")
    
    # This should give a suggestion but not block
    result = run_hook("Write", {
        "file_path": "src/test_example.py",
        "content": "# Test file"
    })
    
    print("Creating test file outside tests/ directory:")
    print(f"Exit code: {result['exit_code']} (0 = allowed with warning)")
    if result['stderr']:
        print(f"Suggestion:\n{result['stderr']}")
    
    # This should block (protected file)
    result = run_hook("Edit", {
        "file_path": ".claude/settings.json",
        "new_string": "test",
        "old_string": "{"
    })
    
    print("\nTrying to modify protected file:")
    print(f"Exit code: {result['exit_code']} (2 = blocked)")
    if result['stderr']:
        print(f"Error:\n{result['stderr']}")


if __name__ == "__main__":
    print("Testing Enhanced PreToolUse Hook")
    print("=" * 50)
    
    # Run all tests
    test_git_aware_warnings()
    test_old_tool_suggestions()
    test_pattern_detection()
    test_dependency_warnings()
    test_enhanced_logging()
    test_non_blocking_suggestions()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nKey enhancements demonstrated:")
    print("1. Git-aware warnings for uncommitted changes")
    print("2. Modern tool suggestions (rg, fd, bat)")
    print("3. Pattern detection for suspicious paths")
    print("4. Dependency impact warnings")
    print("5. Structured operation logging")
    print("6. Non-blocking suggestions vs blocking errors")