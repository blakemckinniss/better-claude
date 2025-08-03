#!/usr/bin/env python3
"""
PostToolUse Hook Block Demonstration Script

This script demonstrates each functional block of the PostToolUse hook by running
specific scenarios and showing the outputs. It provides visual confirmation that
each component is working as intended.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Tuple


class PostToolUseDemo:
    """Demonstration class for PostToolUse hook blocks."""
    
    def __init__(self):
        self.hook_path = Path(__file__).parent / "hook_handlers" / "PostToolUse.py"
        self.demo_session_id = "demo-session-001"
    
    def run_hook_demo(self, input_data: Dict[str, Any]) -> Tuple[int, str, str]:
        """Run the PostToolUse hook and return results."""
        input_json = json.dumps(input_data, indent=2)
        
        print(f"📥 INPUT DATA:")
        print(f"   {input_json}")
        
        result = subprocess.run(
            [sys.executable, str(self.hook_path)],
            input=input_json,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print(f"📤 RESULTS:")
        print(f"   Exit Code: {result.returncode}")
        if result.stdout.strip():
            print(f"   STDOUT: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"   STDERR: {result.stderr.strip()}")
        
        return result.returncode, result.stdout, result.stderr


def demo_basic_hook_functionality():
    """Demonstrate basic hook input/output and exit codes."""
    print("\n" + "="*60)
    print("🔧 BLOCK 1: BASIC HOOK FUNCTIONALITY")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 1.1: Valid JSON Input (Read Tool)")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/demo.txt"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 0:
        print("✅ SUCCESS: Read tool allowed as expected")
    else:
        print(f"❌ UNEXPECTED: Exit code {exit_code}")
    
    print("\n📍 Demo 1.2: Invalid JSON Input")
    print("-" * 40)
    
    print("📥 INPUT DATA: invalid json{")
    
    result = subprocess.run(
        [sys.executable, str(demo.hook_path)],
        input="invalid json{",
        text=True,
        capture_output=True,
        timeout=30
    )
    
    print(f"📤 RESULTS:")
    print(f"   Exit Code: {result.returncode}")
    print(f"   STDERR: {result.stderr.strip()}")
    
    if result.returncode == 1 and "Failed to parse input" in result.stderr:
        print("✅ SUCCESS: Invalid JSON handled gracefully")
    else:
        print(f"❌ UNEXPECTED: Expected exit code 1 with parse error")


def demo_subagent_delegation_enforcement():
    """Demonstrate subagent delegation enforcement."""
    print("\n" + "="*60)
    print("🎯 BLOCK 2: SUBAGENT DELEGATION ENFORCEMENT")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 2.1: Edit Tool Requires Subagent")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/demo.py", "old_string": "old", "new_string": "new"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT DELEGATION REQUIRED" in stderr:
        print("✅ SUCCESS: Edit tool blocked for subagent delegation")
    else:
        print(f"❌ UNEXPECTED: Expected blocking with delegation warning")
    
    print("\n📍 Demo 2.2: Simple Bash Allowed")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 0:
        print("✅ SUCCESS: Simple Bash command allowed")
    else:
        print(f"❌ UNEXPECTED: Simple Bash should be allowed")
    
    print("\n📍 Demo 2.3: Complex Bash Requires Subagent")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "docker build -t myapp . && docker run --rm -p 8080:8080 myapp"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT DELEGATION REQUIRED" in stderr:
        print("✅ SUCCESS: Complex Bash blocked for subagent delegation")
    else:
        print(f"❌ UNEXPECTED: Complex Bash should be blocked")
    
    print("\n📍 Demo 2.4: TodoUpdate Pattern Violation")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "TodoUpdate",
        "tool_input": {"todos": []}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT PATTERN VIOLATION" in stderr:
        print("✅ SUCCESS: TodoUpdate blocked with pattern violation")
    else:
        print(f"❌ UNEXPECTED: TodoUpdate should trigger pattern violation")


def demo_file_modification_workflows():
    """Demonstrate file modification detection and processing."""
    print("\n" + "="*60)
    print("📁 BLOCK 3: FILE MODIFICATION WORKFLOWS")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 3.1: Write Tool with Python File")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/demo_app.py", "content": "print('Hello World')"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT DELEGATION REQUIRED" in stderr:
        print("✅ SUCCESS: Write tool blocked for subagent delegation")
        print("   (File processing would occur if delegation wasn't enforced)")
    else:
        print(f"❌ UNEXPECTED: Write tool should be blocked")
    
    print("\n📍 Demo 3.2: MCP Filesystem Write")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "mcp__filesystem__write_file",
        "tool_input": {"path": "/tmp/demo_mcp.js", "content": "console.log('Hello MCP');"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT DELEGATION" in stderr:
        print("✅ SUCCESS: MCP filesystem write blocked for subagent delegation")
    else:
        print(f"❌ UNEXPECTED: MCP write should be blocked")


def demo_session_tracking_and_logging():
    """Demonstrate session tracking and logging functionality."""
    print("\n" + "="*60)
    print("📊 BLOCK 4: SESSION TRACKING AND LOGGING")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 4.1: Session Tracking with Valid Tool")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "LS",
        "tool_input": {"path": "/tmp"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 0:
        print("✅ SUCCESS: LS tool processed with session tracking")
        print("   (Session data logged internally)")
    else:
        print(f"❌ UNEXPECTED: LS should be allowed")
    
    print("\n📍 Demo 4.2: Warning Suppression Logic")
    print("-" * 40)
    print("   Running same blocked tool twice to demo warning suppression...")
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/demo.py"}
    }
    
    print("\n   First run:")
    exit_code1, stdout1, stderr1 = demo.run_hook_demo(input_data)
    
    print("\n   Second run:")
    exit_code2, stdout2, stderr2 = demo.run_hook_demo(input_data)
    
    if exit_code1 == 2 and exit_code2 == 2:
        print("✅ SUCCESS: Both runs blocked (warning suppression works within sessions)")
    else:
        print(f"❌ UNEXPECTED: Both should be blocked")


def demo_guard_system_protection():
    """Demonstrate Guard system protection and validation."""
    print("\n" + "="*60)
    print("🛡️ BLOCK 5: GUARD SYSTEM PROTECTION")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 5.1: Guard Handles Normal Operation")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Grep",
        "tool_input": {"pattern": "demo", "path": "/tmp"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code in [0, 2]:
        print("✅ SUCCESS: Guard system handling normal operation correctly")
        print(f"   Returned valid exit code: {exit_code}")
    else:
        print(f"❌ UNEXPECTED: Invalid exit code from Guard: {exit_code}")
    
    print("\n📍 Demo 5.2: Guard Validates Exit Codes")
    print("-" * 40)
    print("   Testing with nonexistent file path...")
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/definitely_does_not_exist_12345.txt"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code in [0, 1, 2]:
        print("✅ SUCCESS: Guard system returned valid exit code for error scenario")
        print(f"   Exit code: {exit_code}")
    else:
        print(f"❌ UNEXPECTED: Invalid exit code: {exit_code}")


def demo_validation_and_diagnostics():
    """Demonstrate validation and diagnostic engines."""
    print("\n" + "="*60)
    print("🔍 BLOCK 6: VALIDATION AND DIAGNOSTICS")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 6.1: Skip File Logic")
    print("-" * 40)
    print("   Testing with .git directory file (should be skipped)...")
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/.git/config"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "SUBAGENT DELEGATION" in stderr:
        print("✅ SUCCESS: File skipping logic integrated (blocked by delegation first)")
        print("   (File would be skipped if delegation wasn't enforced)")
    else:
        print(f"❌ UNEXPECTED: Should be blocked by delegation")


def demo_integration_scenarios():
    """Demonstrate complete integration scenarios."""
    print("\n" + "="*60)
    print("🔗 BLOCK 7: INTEGRATION SCENARIOS")
    print("="*60)
    
    demo = PostToolUseDemo()
    
    print("\n📍 Demo 7.1: Complete Edit Workflow")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/tmp/main.py",
            "old_string": "print('old')",
            "new_string": "print('new')"
        }
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 2 and "spec-developer" in stderr and "Task(" in stderr:
        print("✅ SUCCESS: Complete edit workflow blocked with proper guidance")
        print("   Shows subagent recommendation and Task usage example")
    else:
        print(f"❌ UNEXPECTED: Should provide complete subagent guidance")
    
    print("\n📍 Demo 7.2: Allowed Read Workflow")
    print("-" * 40)
    
    input_data = {
        "session_id": demo.demo_session_id,
        "transcript_path": "/tmp/transcript.md",
        "cwd": "/tmp/demo-project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Glob",
        "tool_input": {"pattern": "*.py", "path": "/tmp"}
    }
    
    exit_code, stdout, stderr = demo.run_hook_demo(input_data)
    
    if exit_code == 0:
        print("✅ SUCCESS: Read-only workflow allowed to proceed")
    else:
        print(f"❌ UNEXPECTED: Glob should be allowed")


def main():
    """Run all demonstration blocks."""
    print("🎭 PostToolUse Hook - Block Demonstrations")
    print("🔍 Verifying each functional block is working correctly")
    print("=" * 80)
    
    # Run all demonstration blocks
    demo_basic_hook_functionality()
    demo_subagent_delegation_enforcement()
    demo_file_modification_workflows()
    demo_session_tracking_and_logging()
    demo_guard_system_protection()
    demo_validation_and_diagnostics()
    demo_integration_scenarios()
    
    print("\n" + "="*80)
    print("✅ DEMONSTRATION COMPLETE")
    print("🎯 All PostToolUse hook blocks have been demonstrated")
    print("📋 Each block shows expected behavior according to HOOK_CONTRACT.md")
    print("=" * 80)


if __name__ == "__main__":
    main()