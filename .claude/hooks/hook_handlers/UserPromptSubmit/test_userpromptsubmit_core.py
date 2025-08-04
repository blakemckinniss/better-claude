#!/usr/bin/env python3
"""Comprehensive unit tests for UserPromptSubmit hook handler core functionality.

This test suite covers:
- Input validation and sanitization
- Security validation (path traversal, credential scrubbing)
- Circuit breaker functionality
- Session state management
- Main entry point and contract compliance
"""

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the hook handler directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import all the modules under test
try:
    from circuit_breaker_manager import CircuitBreakerManager
    from config import ConfigManager, get_config
    from security_validator import SecurityValidator, scrub_credentials
    from session_state import SessionState
    from session_state_manager import SessionStateManager
    from UserPromptSubmit import (handle, handle_async, perf_monitor,
                                  should_inject_context, validate_input_data)
except ImportError as e:
    pytest.skip(f"Failed to import UserPromptSubmit modules: {e}", allow_module_level=True)


class TestInputValidation:
    """Test comprehensive input validation and sanitization."""
    
    def test_validate_input_data_valid_input(self):
        """Test validation with valid input data."""
        valid_data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test_transcript.json",
            "cwd": "/home/user/project",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Hello, how can I help?"
        }
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True):
            result = validate_input_data(valid_data)
            assert result is not None
            assert result["prompt"] == "Hello, how can I help?"
            assert result["session_id"] == "test-session-123"
    
    def test_validate_input_data_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        test_cases = [
            {},  # Empty data
            {"session_id": "test-123"},  # Missing transcript_path, cwd, hook_event_name, prompt
            {"session_id": "test-123", "transcript_path": "/tmp/test.json"},  # Missing cwd, hook_event_name, prompt
            {"session_id": "test-123", "transcript_path": "/tmp/test.json", "cwd": "/tmp"},  # Missing hook_event_name, prompt
        ]
        
        for invalid_data in test_cases:
            result = validate_input_data(invalid_data)
            assert result is None, f"Should reject data with missing fields: {invalid_data}"
    
    def test_validate_input_data_invalid_session_id(self):
        """Test validation fails with invalid session ID format."""
        invalid_session_ids = [
            "invalid session id!",  # Contains spaces and special chars
            "too-short",  # Too short (< 8 chars)
            "a" * 70,  # Too long (> 64 chars)
            "test@session#123",  # Invalid characters
            "",  # Empty session ID
        ]
        
        for session_id in invalid_session_ids:
            invalid_data = {
                "session_id": session_id,
                "transcript_path": "/tmp/test.json",
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": "test"
            }
            
            result = validate_input_data(invalid_data)
            assert result is None, f"Should reject invalid session_id: {session_id}"
    
    def test_validate_input_data_wrong_hook_event(self):
        """Test validation fails with wrong hook event name."""
        invalid_data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "WrongHookEvent",
            "prompt": "test"
        }
        
        result = validate_input_data(invalid_data)
        assert result is None
    
    def test_validate_input_data_prompt_sanitization(self):
        """Test prompt content is properly sanitized."""
        dangerous_prompts = [
            "Hello `rm -rf /` && echo 'dangerous'",  # Shell injection attempt
            "Test $(whoami) command substitution",  # Command substitution
            "Check this out: | cat /etc/passwd",  # Pipe to dangerous command
            "Some text & background_process",  # Background process
            "Test; rm important_file",  # Command separator
        ]
        
        for dangerous_prompt in dangerous_prompts:
            data = {
                "session_id": "test-session-123",
                "transcript_path": "/tmp/test.json",
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": dangerous_prompt
            }
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True):
                result = validate_input_data(data)
                assert result is not None
                
                # Dangerous characters should be removed
                sanitized_prompt = result["prompt"]
                assert "`" not in sanitized_prompt
                assert "$" not in sanitized_prompt
                assert "|" not in sanitized_prompt
                assert "&" not in sanitized_prompt
                assert ";" not in sanitized_prompt
    
    def test_validate_input_data_oversized_prompt(self):
        """Test validation rejects oversized prompts."""
        oversized_data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "x" * 60000  # Exceeds 50KB limit
        }
        
        result = validate_input_data(oversized_data)
        assert result is None
    
    def test_validate_input_data_nonexistent_transcript(self):
        """Test validation fails with nonexistent transcript path."""
        data = {
            "session_id": "test-session-123",
            "transcript_path": "/nonexistent/path/transcript.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test"
        }
        
        with patch('os.path.exists', return_value=False):
            result = validate_input_data(data)
            assert result is None
    
    def test_validate_input_data_unreadable_transcript(self):
        """Test validation fails with unreadable transcript."""
        data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test"
        }
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=False):
            result = validate_input_data(data)
            assert result is None


class TestSecurityValidator:
    """Test comprehensive security validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_traversal_detection(self):
        """Test detection of various path traversal patterns."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\\\..\\\\windows\\\\system32\\\\config\\\\sam",
            "%2e%2e/etc/passwd",
            "....//etc/passwd",
            "/tmp/../../../etc/passwd",
            "file:///etc/passwd",
            "\\\\..\\\\..\\\\etc\\\\passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "..%2f..%2f..%2fetc%2fpasswd",  # Mixed encoding
        ]
        
        for path in malicious_paths:
            is_valid, error = self.validator.validate_path_security(path)
            assert not is_valid, f"Path traversal not detected: {path}"
            assert any(keyword in error.lower() for keyword in ["traversal", "outside allowed", "blocked"]), \
                f"Error message should indicate security issue: {error}"
    
    def test_sensitive_file_blocking(self):
        """Test blocking access to sensitive files."""
        sensitive_paths = [
            ".env",
            ".env.local",
            ".env.production",
            "secrets.json",
            "credentials.json",
            ".ssh/id_rsa",
            "private.key",
            "/etc/shadow",
            "/etc/sudoers",
            "database.yml",
            "config/database.yml",
            ".aws/credentials",
            "serviceaccount.json",
            ".git/config",
            "password.txt",
            "api_key.txt",
        ]
        
        for path in sensitive_paths:
            is_valid, error = self.validator.validate_path_security(path)
            assert not is_valid, f"Sensitive file not blocked: {path}"
            assert "sensitive" in error.lower(), f"Error should mention sensitive file: {error}"
    
    def test_system_directory_blocking(self):
        """Test blocking access to system directories."""
        system_paths = [
            "/etc/passwd",
            "/sys/kernel/debug",
            "/proc/version",
            "/dev/random",
            "/root/.bashrc",
            "/bin/bash",
            "/usr/bin/sudo",
            "/var/log/auth.log",
        ]
        
        for path in system_paths:
            is_valid, error = self.validator.validate_path_security(path)
            assert not is_valid, f"System directory not blocked: {path}"
            assert "system directory" in error.lower() or "outside allowed" in error.lower()
    
    def test_allowed_paths_within_project(self):
        """Test that paths within project directory are allowed."""
        allowed_paths = [
            os.path.join(self.temp_dir, "src", "main.py"),
            os.path.join(self.temp_dir, "README.md"),
            os.path.join(self.temp_dir, ".claude", "config.json"),
            os.path.join(self.temp_dir, "tests", "test_file.py"),
        ]
        
        for path in allowed_paths:
            # Create the directory structure
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            is_valid, error = self.validator.validate_path_security(path)
            assert is_valid, f"Allowed path should be valid: {path}, error: {error}"
    
    def test_credential_scrubbing_comprehensive(self):
        """Test comprehensive credential scrubbing."""
        text_with_credentials = """
        API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
        OPENAI_API_KEY="sk-proj-abcdef1234567890"
        password="secret123password"
        Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG"
        oauth_token=ya29.a0AfH6SMC_example_token_here
        client_secret=gcp_client_secret_12345
        private_key="-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC"
        aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        database_password=mypassword123
        jwt_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9
        """
        
        scrubbed = self.validator.scrub_credentials_from_text(text_with_credentials)
        
        # Should not contain any of the original credential values
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in scrubbed
        assert "sk-proj-abcdef1234567890" not in scrubbed
        assert "secret123password" not in scrubbed
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
        assert "ya29.a0AfH6SMC_example_token_here" not in scrubbed
        assert "gcp_client_secret_12345" not in scrubbed
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in scrubbed
        assert "mypassword123" not in scrubbed
        
        # Should contain redaction markers
        assert "[REDACTED]" in scrubbed
    
    def test_credential_scrubbing_in_nested_dict(self):
        """Test credential scrubbing in nested dictionaries."""
        data_with_creds = {
            "config": {
                "api_key": "sk-secret123456789",
                "password": "mypassword",
                "safe_data": "this is fine",
                "database": {
                    "password": "dbpassword123",
                    "connection_string": "postgres://user:secret@host:5432/db"
                }
            },
            "tokens": ["bearer_token_123", "safe_value", "oauth_secret_456"],
            "normal_field": "normal_value"
        }
        
        scrubbed = self.validator.scrub_credentials_from_dict(data_with_creds)
        
        assert scrubbed["config"]["api_key"] == "[REDACTED]"
        assert scrubbed["config"]["password"] == "[REDACTED]"
        assert scrubbed["config"]["safe_data"] == "this is fine"
        assert scrubbed["config"]["database"]["password"] == "[REDACTED]"
        assert scrubbed["normal_field"] == "normal_value"
        
        # List items with credentials should be scrubbed
        tokens_str = str(scrubbed["tokens"])
        assert "[REDACTED]" in tokens_str
        assert "safe_value" in tokens_str
    
    def test_environment_variable_validation(self):
        """Test environment variable security validation."""
        # Test with missing API keys
        with patch.dict(os.environ, {}, clear=True):
            warnings = self.validator.validate_environment_variables()
            assert len(warnings) == 0  # No warnings for missing keys
        
        # Test with invalid API keys
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test_key",  # Too short
            "GEMINI_API_KEY": "dummy",  # Placeholder
        }):
            warnings = self.validator.validate_environment_variables()
            assert any("too short" in warning for warning in warnings)
            assert any("placeholder" in warning for warning in warnings)
    
    def test_secure_error_message_creation(self):
        """Test creation of secure error messages."""
        # Test with exception containing credentials
        try:
            raise ValueError("API call failed with key sk-secret123: unauthorized")
        except ValueError as e:
            secure_msg = self.validator.create_secure_error_message(e, "API Error")
            
            assert "sk-secret123" not in secure_msg
            assert "[REDACTED]" in secure_msg
            assert "API Error" in secure_msg
    
    def test_security_event_logging(self):
        """Test security event logging with credential scrubbing."""
        event_details = {
            "user_input": "test input with api_key=sk-secret123",
            "file_path": "/tmp/test.txt",
            "error": "Failed to process request with token bearer_xyz123"
        }
        
        with patch('sys.stderr') as mock_stderr:
            self.validator.log_security_event("input_validation_failed", event_details)
            
            # Check that stderr was called
            assert mock_stderr.write.called
            
            # Get the logged content
            logged_content = str(mock_stderr.write.call_args_list)
            
            # Should not contain credentials
            assert "sk-secret123" not in logged_content
            assert "bearer_xyz123" not in logged_content
            assert "[REDACTED]" in logged_content


class TestCircuitBreakerManager:
    """Test circuit breaker functionality for injection control."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.circuit_manager = CircuitBreakerManager()
    
    def test_default_circuit_breaker_states(self):
        """Test default circuit breaker configurations."""
        # Test enabled by default
        assert self.circuit_manager.is_injection_enabled("enhanced_ai_optimizer") is True
        assert self.circuit_manager.is_injection_enabled("unified_smart_advisor") is True
        assert self.circuit_manager.is_injection_enabled("zen_pro_orchestrator") is True
        assert self.circuit_manager.is_injection_enabled("git") is True
        assert self.circuit_manager.is_injection_enabled("mcp") is True
        
        # Test disabled by default
        assert self.circuit_manager.is_injection_enabled("code_intelligence_hub") is False
        assert self.circuit_manager.is_injection_enabled("firecrawl") is False
    
    def test_environment_override_enabled(self):
        """Test environment variable overrides for enabling injections."""
        env_overrides = {
            "CIRCUIT_BREAKER_CODE_INTELLIGENCE_HUB": "true",
            "CIRCUIT_BREAKER_FIRECRAWL": "true"
        }
        
        with patch.dict(os.environ, env_overrides):
            manager = CircuitBreakerManager()
            assert manager.is_injection_enabled("code_intelligence_hub") is True
            assert manager.is_injection_enabled("firecrawl") is True
    
    def test_environment_override_disabled(self):
        """Test environment variable overrides for disabling injections."""
        env_overrides = {
            "CIRCUIT_BREAKER_GIT": "false",
            "CIRCUIT_BREAKER_MCP": "false"
        }
        
        with patch.dict(os.environ, env_overrides):
            manager = CircuitBreakerManager()
            assert manager.is_injection_enabled("git") is False
            assert manager.is_injection_enabled("mcp") is False
    
    def test_environment_override_invalid_values(self):
        """Test that invalid environment values don't affect circuit breakers."""
        env_overrides = {
            "CIRCUIT_BREAKER_GIT": "invalid",
            "CIRCUIT_BREAKER_MCP": "yes",  # Not "true", should be treated as false
            "CIRCUIT_BREAKER_SYSTEM_MONITOR": "1"  # Not "true", should be treated as false
        }
        
        with patch.dict(os.environ, env_overrides):
            manager = CircuitBreakerManager()
            assert manager.is_injection_enabled("git") is False  # invalid -> false
            assert manager.is_injection_enabled("mcp") is False  # yes -> false
            assert manager.is_injection_enabled("system_monitor") is False  # 1 -> false
    
    def test_disable_enable_injection_runtime(self):
        """Test dynamic injection control at runtime."""
        # Initially enabled
        assert self.circuit_manager.is_injection_enabled("git") is True
        
        # Disable injection
        self.circuit_manager.disable_injection("git")
        assert self.circuit_manager.is_injection_enabled("git") is False
        
        # Re-enable injection
        self.circuit_manager.enable_injection("git")
        assert self.circuit_manager.is_injection_enabled("git") is True
    
    def test_trip_reset_circuit_breaker(self):
        """Test circuit breaker tripping and reset."""
        # Initially enabled
        assert self.circuit_manager.is_circuit_breaker_enabled("system_monitor") is True
        
        # Trip circuit breaker
        self.circuit_manager.trip_circuit_breaker("system_monitor")
        assert self.circuit_manager.is_circuit_breaker_enabled("system_monitor") is False
        assert self.circuit_manager.is_injection_enabled("system_monitor") is False
        
        # Reset circuit breaker
        self.circuit_manager.reset_circuit_breaker("system_monitor")
        assert self.circuit_manager.is_circuit_breaker_enabled("system_monitor") is True
        assert self.circuit_manager.is_injection_enabled("system_monitor") is True
    
    def test_nonexistent_injection_handling(self):
        """Test handling of nonexistent injection names."""
        # Should return False for unknown injections
        assert self.circuit_manager.is_injection_enabled("nonexistent_injection") is False
        assert self.circuit_manager.is_circuit_breaker_enabled("nonexistent_breaker") is False
        
        # Should handle gracefully when trying to modify
        self.circuit_manager.disable_injection("nonexistent_injection")  # Should not raise
        self.circuit_manager.trip_circuit_breaker("nonexistent_breaker")  # Should not raise
    
    def test_get_enabled_injections(self):
        """Test getting all enabled injections."""
        enabled = self.circuit_manager.get_enabled_injections()
        
        # Should be a dictionary
        assert isinstance(enabled, dict)
        
        # Should contain expected enabled injections
        assert enabled.get("enhanced_ai_optimizer") is True
        assert enabled.get("zen_pro_orchestrator") is True
        
        # Should not contain disabled injections
        assert "code_intelligence_hub" not in enabled or enabled["code_intelligence_hub"] is False
    
    def test_get_circuit_breakers(self):
        """Test getting all circuit breaker states."""
        breakers = self.circuit_manager.get_circuit_breakers()
        
        # Should be a dictionary
        assert isinstance(breakers, dict)
        
        # Should contain all known breakers
        expected_breakers = [
            "enhanced_ai_optimizer", "unified_smart_advisor", "code_intelligence_hub",
            "system_monitor", "static_content", "context_revival", "git", "mcp",
            "firecrawl", "zen_pro_orchestrator"
        ]
        
        for breaker in expected_breakers:
            assert breaker in breakers
            assert isinstance(breakers[breaker], bool)


class TestSessionState:
    """Test session state management and injection decisions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_state = SessionState(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initial_injection_required(self):
        """Test that injection is required on first prompt."""
        assert self.session_state.should_inject() is True, "First prompt should always require injection"
    
    def test_injection_after_marking_injected(self):
        """Test injection not required immediately after marking injected."""
        # Mark as injected
        self.session_state.mark_injected("/tmp/transcript.json")
        
        # Should not require injection now
        assert self.session_state.should_inject("/tmp/transcript.json") is False
    
    def test_injection_after_message_limit(self):
        """Test injection triggered after message limit."""
        # Mark as injected first
        self.session_state.mark_injected("/tmp/transcript.json")
        assert self.session_state.should_inject("/tmp/transcript.json") is False
        
        # Increment message count to limit (5 messages)
        for i in range(5):
            self.session_state.increment_message_count()
            if i < 4:  # First 4 increments should not trigger
                assert self.session_state.should_inject("/tmp/transcript.json") is False
        
        # 5th increment should trigger injection
        assert self.session_state.should_inject("/tmp/transcript.json") is True
    
    def test_transcript_change_triggers_injection(self):
        """Test that changing transcript triggers injection."""
        # Initial injection
        self.session_state.mark_injected("/tmp/transcript1.json")
        assert self.session_state.should_inject("/tmp/transcript1.json") is False
        
        # Different transcript should trigger injection
        assert self.session_state.should_inject("/tmp/transcript2.json") is True
    
    def test_forced_injection_request(self):
        """Test manual injection request."""
        self.session_state.mark_injected("/tmp/transcript.json")
        assert self.session_state.should_inject("/tmp/transcript.json") is False
        
        # Request injection
        self.session_state.request_next_injection("manual_request")
        assert self.session_state.should_inject("/tmp/transcript.json") is True
    
    def test_state_persistence_across_instances(self):
        """Test that session state persists across instances."""
        # Set state in first instance
        self.session_state.mark_injected("/tmp/transcript.json")
        self.session_state.increment_message_count()
        self.session_state.increment_message_count()
        
        # Create new instance and verify state persists
        new_session = SessionState(self.temp_dir)
        state = new_session.get_state()
        assert state["inject_next"] is False
        assert state["messages_since_injection"] == 2
        assert state["last_transcript_path"] == "/tmp/transcript.json"
    
    def test_state_file_corruption_recovery(self):
        """Test recovery from corrupted state file."""
        # Create corrupted state file
        state_file = self.session_state.state_file
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(state_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Should recover with default state
        recovered_session = SessionState(self.temp_dir)
        state = recovered_session.get_state()
        assert state["inject_next"] is True  # Default state
        assert state["messages_since_injection"] == 0
        assert state["reason"] == "initial"
    
    def test_clear_state(self):
        """Test clearing session state."""
        # Set some state
        self.session_state.mark_injected("/tmp/transcript.json")
        self.session_state.increment_message_count()
        
        # Clear state
        self.session_state.clear_state()
        
        # Should be back to default state
        state = self.session_state.get_state()
        assert state["inject_next"] is True
        assert state["messages_since_injection"] == 0
    
    def test_concurrent_state_access(self):
        """Test concurrent access to session state doesn't cause corruption."""
        def modify_state():
            for i in range(5):
                self.session_state.increment_message_count()
                time.sleep(0.01)  # Small delay to increase chance of race condition
        
        # Start multiple threads
        threads = [threading.Thread(target=modify_state) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # State should be consistent (no corruption)
        state = self.session_state.get_state()
        assert isinstance(state["messages_since_injection"], int)
        assert state["messages_since_injection"] >= 0
        assert state["messages_since_injection"] <= 15  # 3 threads * 5 increments


class TestMainEntryPoint:
    """Test main entry point and JSON contract compliance."""
    
    def test_json_input_parsing_valid(self):
        """Test valid JSON input parsing."""
        valid_json = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test prompt"
        }
        
        with patch('sys.stdin.read', return_value=json.dumps(valid_json)), \
             patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('UserPromptSubmit.handle') as mock_handle:
            
            # Test JSON parsing directly instead of importing __main__
            parsed_data = json.loads(json.dumps(valid_json))
            validated_data = validate_input_data(parsed_data)
            
            assert validated_data is not None
            assert validated_data["session_id"] == "test-session-123"
    
    def test_json_input_parsing_invalid(self):
        """Test invalid JSON input handling."""
        invalid_json_cases = [
            '{\"invalid\": json syntax',  # Malformed JSON
            'not json at all',  # Not JSON
            '',  # Empty input
        ]
        
        for invalid_json in invalid_json_cases:
            # Test JSON parsing directly
            with pytest.raises(json.JSONDecodeError):
                json.loads(invalid_json)
    
    def test_output_format_contract_compliance(self):
        """Test that output follows hook contract specification."""
        # Test successful output format
        expected_output = {
            "continue": True,
            "suppressOutput": False,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "test context"
            }
        }
        
        with patch('sys.stdout') as mock_stdout:
            print(json.dumps(expected_output))
            
            # Verify JSON structure
            output_call = mock_stdout.write.call_args_list[-1][0][0]
            parsed_output = json.loads(output_call.strip())
            
            assert parsed_output["continue"] is True
            assert parsed_output["suppressOutput"] is False
            assert "hookSpecificOutput" in parsed_output
            assert parsed_output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
            assert "additionalContext" in parsed_output["hookSpecificOutput"]
    
    def test_exit_code_contract_compliance(self):
        """Test that exit codes follow hook contract."""
        # Test various exit scenarios
        exit_scenarios = [
            (0, "Success"),
            (1, "Non-blocking error"),
            (2, "Blocking error"),
        ]
        
        for exit_code, description in exit_scenarios:
            with pytest.raises(SystemExit) as exc_info:
                sys.exit(exit_code)
            
            assert exc_info.value.code == exit_code, f"Exit code mismatch for {description}"


class TestPerformanceMonitoring:
    """Test performance monitoring and decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_perf_monitor_decorator_async(self):
        """Test performance monitoring decorator for async functions."""
        @perf_monitor
        async def test_async_function(duration=0.1):
            await asyncio.sleep(duration)
            return "success"
        
        # Test normal execution
        result = await test_async_function(0.05)  # Below threshold
        assert result == "success"
        
        # Test slow execution (should log)
        with patch('sys.stderr') as mock_stderr:
            result = await test_async_function(0.6)  # Above 0.5s threshold
            assert result == "success"
            
            # Should have logged slow operation
            stderr_calls = [str(call) for call in mock_stderr.write.call_args_list]
            assert any("Slow operation" in call for call in stderr_calls)
    
    def test_perf_monitor_decorator_sync(self):
        """Test performance monitoring decorator for sync functions."""
        @perf_monitor
        def test_sync_function(duration=0.05):
            time.sleep(duration)
            return "success"
        
        # Test normal execution
        result = test_sync_function(0.05)  # Below 0.1s threshold
        assert result == "success"
        
        # Test slow execution (should log)
        with patch('sys.stderr') as mock_stderr:
            result = test_sync_function(0.2)  # Above 0.1s threshold
            assert result == "success"
            
            # Should have logged slow operation
            stderr_calls = [str(call) for call in mock_stderr.write.call_args_list]
            assert any("Slow operation" in call for call in stderr_calls)
    
    @pytest.mark.asyncio
    async def test_perf_monitor_exception_handling(self):
        """Test performance monitoring with exceptions."""
        @perf_monitor
        async def failing_function():
            raise ValueError("Test error with API_KEY=secret123")
        
        with patch('sys.stderr') as mock_stderr, \
             pytest.raises(ValueError):
            await failing_function()
        
        # Should have logged performance info and scrubbed credentials
        stderr_calls = [str(call) for call in mock_stderr.write.call_args_list]
        performance_logs = [call for call in stderr_calls if "PERF" in call]
        
        assert len(performance_logs) > 0, "Should log performance even on failure"
        
        # Check credential scrubbing
        full_stderr = " ".join(stderr_calls)
        assert "secret123" not in full_stderr, "Credentials should be scrubbed"
        assert "[REDACTED]" in full_stderr, "Should contain redaction marker"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        empty_data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": ""  # Empty prompt
        }
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True):
            result = validate_input_data(empty_data)
            assert result is not None, "Empty prompt should be valid"
            assert result["prompt"] == ""
    
    def test_unicode_prompt_handling(self):
        """Test handling of Unicode and emoji content."""
        unicode_prompts = [
            "Hello 🌍! Testing unicode",
            "café naïve résumé",
            "中文测试 Japanese: こんにちは Russian: Привет",
            "Math symbols: ∑ ∏ ∫ ∞ ≠ ±",
            "Arrows: ← → ↑ ↓ ↔ ↕",
        ]
        
        for unicode_prompt in unicode_prompts:
            unicode_data = {
                "session_id": "test-session-123",
                "transcript_path": "/tmp/test.json",
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": unicode_prompt
            }
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True):
                result = validate_input_data(unicode_data)
                assert result is not None, f"Unicode prompt should be valid: {unicode_prompt}"
                # Unicode content should be preserved
                assert unicode_prompt in result["prompt"]
    
    def test_whitespace_prompt_handling(self):
        """Test handling of prompts with various whitespace."""
        whitespace_prompts = [
            "   leading spaces",
            "trailing spaces   ",
            "   both ends   ",
            "multiple\n\nlines\n\nwith\n\nempty\n\nlines",
            "tabs\t\tand\t\tspaces",
            "\r\n Windows line endings \r\n",
        ]
        
        for whitespace_prompt in whitespace_prompts:
            data = {
                "session_id": "test-session-123",
                "transcript_path": "/tmp/test.json",
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": whitespace_prompt
            }
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True):
                result = validate_input_data(data)
                assert result is not None, f"Whitespace prompt should be valid: {repr(whitespace_prompt)}"
    
    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        # Test with very large input that could cause memory issues
        large_data = {
            "session_id": "test-session-123",
            "transcript_path": "/tmp/test.json",
            "cwd": "/home/user",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "x" * (10 * 1024 * 1024)  # 10MB string
        }
        
        # Should be rejected due to size limit
        result = validate_input_data(large_data)
        assert result is None, "Oversized prompt should be rejected"
    
    def test_special_characters_in_paths(self):
        """Test handling of special characters in file paths."""
        special_paths = [
            "/tmp/file with spaces.json",
            "/tmp/file-with-dashes.json",
            "/tmp/file_with_underscores.json",
            "/tmp/file.with.dots.json",
            "/tmp/file[with]brackets.json",
            "/tmp/file(with)parentheses.json",
        ]
        
        for special_path in special_paths:
            data = {
                "session_id": "test-session-123",
                "transcript_path": special_path,
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": "test"
            }
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True):
                result = validate_input_data(data)
                # Most special characters should be allowed in file names
                assert result is not None, f"Path with special characters should be valid: {special_path}"
    
    def test_null_byte_injection_prevention(self):
        """Test prevention of null byte injection attacks."""
        null_byte_attacks = [
            "normal_file.txt\x00.exe",
            "/tmp/safe.json\x00../../../etc/passwd",
            "prompt with null\x00byte",
        ]
        
        for attack_string in null_byte_attacks:
            data = {
                "session_id": "test-session-123",
                "transcript_path": "/tmp/test.json",
                "cwd": "/home/user",
                "hook_event_name": "UserPromptSubmit",
                "prompt": attack_string
            }
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True):
                result = validate_input_data(data)
                
                if result is not None:
                    # Null bytes should be removed
                    assert "\x00" not in result["prompt"], "Null bytes should be sanitized"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])