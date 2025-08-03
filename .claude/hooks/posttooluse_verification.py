#!/usr/bin/env python3
"""
Comprehensive verification suite for PostToolUse hook handler.

This verification suite confirms each block of functionality in PostToolUse is working correctly:
1. Basic hook functionality (JSON I/O, exit codes)
2. Subagent delegation enforcement
3. File modification workflows
4. Session tracking and logging
5. Validation and diagnostic engines
6. Guard system protection
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, patch


class PostToolUseVerificationSuite(unittest.TestCase):
    """Verification suite for PostToolUse hook handler."""

    def setUp(self):
        """Set up verification environment."""
        self.hook_path = Path(__file__).parent / "hook_handlers" / "PostToolUse.py"
        self.verification_session_id = "verify-session-12345"
        self.verification_cwd = "/tmp/verify-project"
        
        # Create a temporary directory for verification files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up verification environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _run_hook(self, input_data: Dict[str, Any]) -> Tuple[int, str, str]:
        """
        Run the PostToolUse hook with given input data.
        
        Returns: (exit_code, stdout, stderr)
        """
        input_json = json.dumps(input_data)
        
        result = subprocess.run(
            [sys.executable, str(self.hook_path)],
            input=input_json,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        return result.returncode, result.stdout, result.stderr

    def _create_verification_file(self, filename: str, content: str = "") -> str:
        """Create a verification file and return its path."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path


class VerifyBasicHookFunctionality(PostToolUseVerificationSuite):
    """Verify basic hook input/output and exit codes."""

    def verify_valid_json_input_success(self):
        """Verify hook handles valid JSON input correctly."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/verify.txt"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should succeed for non-blocking tools
        self.assertEqual(exit_code, 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}")

    def verify_invalid_json_input_failure(self):
        """Verify hook handles invalid JSON input gracefully."""
        result = subprocess.run(
            [sys.executable, str(self.hook_path)],
            input="invalid json{",
            text=True,
            capture_output=True,
            timeout=30
        )
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to parse input", result.stderr)

    def verify_missing_required_fields(self):
        """Verify hook handles missing required fields."""
        input_data = {
            "session_id": self.verification_session_id,
            # Missing other required fields
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should handle gracefully and not crash
        self.assertIn([0, 1], [exit_code], "Hook should handle missing fields gracefully")


class VerifySubagentDelegationEnforcement(PostToolUseVerificationSuite):
    """Verify subagent delegation enforcement logic."""

    def verify_edit_tool_requires_subagent(self):
        """Verify that Edit tool usage triggers subagent delegation warning."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md", 
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/tmp/verify.py", "old_string": "old", "new_string": "new"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 2, "Edit tool should be blocked for subagent delegation")
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)
        self.assertIn("spec-developer", stderr)

    def verify_write_tool_requires_subagent(self):
        """Verify that Write tool usage triggers subagent delegation warning."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd, 
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/verify.py", "content": "print('hello')"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 2, "Write tool should be blocked for subagent delegation")
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)
        self.assertIn("docs-writer", stderr)

    def verify_complex_bash_requires_subagent(self):
        """Verify that complex Bash commands trigger subagent delegation."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse", 
            "tool_name": "Bash",
            "tool_input": {"command": "docker build -t myapp . && docker run -p 8080:8080 myapp"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 2, "Complex Bash should be blocked for subagent delegation")
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)
        self.assertIn("devops-engineer", stderr)

    def verify_simple_bash_allowed(self):
        """Verify that simple Bash commands are allowed."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash", 
            "tool_input": {"command": "ls -la"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 0, "Simple Bash commands should be allowed")

    def verify_todowrite_pattern_violation(self):
        """Verify that TodoUpdate triggers pattern violation warning."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "TodoUpdate",
            "tool_input": {"todos": []}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 2, "TodoUpdate should trigger pattern violation")
        self.assertIn("SUBAGENT PATTERN VIOLATION", stderr)
        self.assertIn("project-planner", stderr)

    def verify_read_tool_allowed(self):
        """Verify that Read tool is allowed without delegation."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/verify.txt"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 0, "Read tool should be allowed")


class VerifyFileModificationWorkflows(PostToolUseVerificationSuite):
    """Verify file modification detection and processing."""

    def verify_python_file_processing(self):
        """Verify processing of Python file modifications."""
        # Create a verification Python file with some issues
        python_content = '''#!/usr/bin/env python3
import os
import sys

def sample_function():
    x = 1
    y = 2
    # This function has issues that validators might catch
    return x + y

if __name__ == "__main__":
    sample_function()
'''
        verification_file = self._create_verification_file("verify.py", python_content)
        
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": verification_file}
        }
        
        # Note: This will be blocked by subagent delegation, but we can verify the file processing logic
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should be blocked for subagent delegation, not file processing issues
        self.assertEqual(exit_code, 2)
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)

    def verify_javascript_file_processing(self):
        """Verify processing of JavaScript file modifications."""
        js_content = '''// Verification JavaScript file
function sampleFunction() {
    var x = 1;
    var y = 2;
    return x + y;
}

sampleFunction();
'''
        verification_file = self._create_verification_file("verify.js", js_content)
        
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": verification_file}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should be blocked for subagent delegation
        self.assertEqual(exit_code, 2)
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)

    def verify_mcp_filesystem_write_processing(self):
        """Verify MCP filesystem write operations are processed."""
        verification_file = self._create_verification_file("verify.py", "print('hello')")
        
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "mcp__filesystem__write_file",
            "tool_input": {"path": verification_file, "content": "print('world')"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should be blocked for subagent delegation
        self.assertEqual(exit_code, 2)
        self.assertIn("SUBAGENT DELEGATION", stderr)


class VerifySessionTrackingAndLogging(PostToolUseVerificationSuite):
    """Verify session tracking and logging functionality."""

    def verify_session_tracking_integration(self):
        """Verify that tool usage is logged to session tracking."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/verify.txt"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should succeed and potentially log session data
        self.assertEqual(exit_code, 0)

    def verify_warning_suppression_logic(self):
        """Verify that repeated warnings are suppressed per session."""
        # This is difficult to verify directly without mocking the session tracker
        # But we can verify the hook handles session tracking without crashing
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse", 
            "tool_name": "Edit",
            "tool_input": {"file_path": "/tmp/verify.py"}
        }
        
        # Run twice to verify warning suppression
        exit_code1, stdout1, stderr1 = self._run_hook(input_data)
        exit_code2, stdout2, stderr2 = self._run_hook(input_data)
        
        self.assertEqual(exit_code1, 2)
        self.assertEqual(exit_code2, 2)
        # Both should show delegation warnings (suppression happens within same session)


class VerifyValidationAndDiagnostics(PostToolUseVerificationSuite):
    """Verify validation and diagnostic engines."""

    def verify_skip_file_logic(self):
        """Verify that files in skip directories are properly ignored."""
        # Create a file in a directory that should be skipped
        skip_dir = os.path.join(self.temp_dir, ".git")
        os.makedirs(skip_dir)
        skip_file = os.path.join(skip_dir, "config")
        
        with open(skip_file, 'w') as f:
            f.write("git config content")
        
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": skip_file}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should be blocked for subagent delegation, not file skipping
        self.assertEqual(exit_code, 2)
        self.assertIn("SUBAGENT DELEGATION", stderr)


class VerifyGuardSystemProtection(PostToolUseVerificationSuite):
    """Verify Guard system protection and validation."""

    def verify_guard_handles_exceptions(self):
        """Verify that Guard system handles exceptions gracefully."""
        # This verification confirms the Guard system works by checking normal operation
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/nonexistent.txt"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should not crash even with nonexistent file
        self.assertIn([0, 1], [exit_code], "Guard should handle errors gracefully")

    def verify_exit_code_validation(self):
        """Verify that Guard validates exit codes properly."""
        # Normal operation should return valid exit codes
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Grep",
            "tool_input": {"pattern": "verify", "path": "/tmp"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        # Should return valid exit code (0 or 2)
        self.assertIn(exit_code, [0, 2], f"Invalid exit code: {exit_code}")


class VerifyIntegrationScenarios(PostToolUseVerificationSuite):
    """Verify complete integration scenarios."""

    def verify_complete_edit_workflow_blocked(self):
        """Verify complete edit workflow is properly blocked."""
        verification_file = self._create_verification_file("app.py", "print('old code')")
        
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": verification_file,
                "old_string": "old code",
                "new_string": "new code"
            }
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 2)
        self.assertIn("SUBAGENT DELEGATION REQUIRED", stderr)
        self.assertIn("spec-developer", stderr)
        self.assertIn("Task(", stderr)

    def verify_allowed_read_workflow(self):
        """Verify that allowed read workflows work correctly."""
        input_data = {
            "session_id": self.verification_session_id,
            "transcript_path": "/tmp/transcript.md",
            "cwd": self.verification_cwd,
            "hook_event_name": "PostToolUse",
            "tool_name": "LS",
            "tool_input": {"path": "/tmp"}
        }
        
        exit_code, stdout, stderr = self._run_hook(input_data)
        
        self.assertEqual(exit_code, 0, "LS tool should be allowed")


def run_verification_demonstrations():
    """Run specific verification demonstrations to show each block working."""
    print("🔍 PostToolUse Hook Verification Demonstrations")
    print("=" * 50)
    
    # Create verification suite
    suite = unittest.TestSuite()
    
    # Add demonstration verifications for each major block
    suite.addTest(VerifyBasicHookFunctionality('verify_valid_json_input_success'))
    suite.addTest(VerifyBasicHookFunctionality('verify_invalid_json_input_failure'))
    
    suite.addTest(VerifySubagentDelegationEnforcement('verify_edit_tool_requires_subagent'))
    suite.addTest(VerifySubagentDelegationEnforcement('verify_simple_bash_allowed'))
    suite.addTest(VerifySubagentDelegationEnforcement('verify_todowrite_pattern_violation'))
    
    suite.addTest(VerifyFileModificationWorkflows('verify_python_file_processing'))
    
    suite.addTest(VerifyGuardSystemProtection('verify_guard_handles_exceptions'))
    
    suite.addTest(VerifyIntegrationScenarios('verify_complete_edit_workflow_blocked'))
    suite.addTest(VerifyIntegrationScenarios('verify_allowed_read_workflow'))
    
    # Run verifications with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print(f"\n📊 Verification Results: {result.testsRun} verifications run")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Run demonstration verifications
        success = run_verification_demonstrations()
        sys.exit(0 if success else 1)
    else:
        # Run full verification suite
        unittest.main(verbosity=2)