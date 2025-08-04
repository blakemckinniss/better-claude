#!/usr/bin/env python3
"""Integration tests for UserPromptSubmit hook handler.

This test suite covers:
- Full hook workflow integration
- Async injection orchestration
- End-to-end scenarios with real components
- API integration scenarios
- Token optimization workflow
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the hook handler directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import all the modules under test
try:
    from ai_context_optimizer_optimized import optimize_injection_sync
    from circuit_breaker_manager import CircuitBreakerManager
    from injection_orchestrator import InjectionOrchestrator
    from session_state_manager import SessionStateManager
    from token_optimizer import TokenOptimizer
    from unified_smart_advisor import get_smart_recommendations
    from UserPromptSubmit import handle, handle_async, should_inject_context
except ImportError as e:
    pytest.skip(f"Failed to import UserPromptSubmit modules: {e}", allow_module_level=True)


class TestFullWorkflowIntegration:
    """Test complete injection workflow from input to output."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_transcript = os.path.join(self.temp_dir, "test_transcript.json")
        
        # Create mock transcript file
        with open(self.test_transcript, 'w') as f:
            json.dump({"messages": []}, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_complete_injection_workflow_first_prompt(self):
        """Test complete injection workflow for first prompt (should inject)."""
        test_data = {
            "session_id": "integration-test-123",
            "transcript_path": self.test_transcript,
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Help me debug this error"
        }
        
        with patch('UserPromptSubmit.get_smart_recommendations', return_value="smart advice"), \
             patch('UserPromptSubmit.get_system_monitoring_injection', return_value="system info"), \
             patch('UserPromptSubmit.get_git_injection', return_value="git info"), \
             patch('UserPromptSubmit.get_context_revival_injection', return_value="context revival"), \
             patch('UserPromptSubmit.get_mcp_injection', return_value="mcp info"), \
             patch('UserPromptSubmit.optimize_injection_sync', return_value="optimized context"), \
             patch('sys.stdout') as mock_stdout, \
             pytest.raises(SystemExit) as exc_info:
            
            await handle_async(test_data)
        
        # Should exit with success code
        assert exc_info.value.code == 0
        
        # Should have written JSON output
        assert mock_stdout.write.called
        
        # Verify output structure
        output_calls = [call[0][0] for call in mock_stdout.write.call_args_list if call[0]]
        json_output = None
        for call in output_calls:
            try:
                json_output = json.loads(call)
                break
            except (json.JSONDecodeError, ValueError):
                continue
        
        assert json_output is not None, "Should produce valid JSON output"
        assert json_output["continue"] is True
        assert json_output["suppressOutput"] is False
        assert "hookSpecificOutput" in json_output
        assert json_output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    
    @pytest.mark.asyncio
    async def test_complete_injection_workflow_subsequent_prompt(self):
        """Test complete injection workflow for subsequent prompt (should not inject)."""
        # First, create a session state that indicates injection already happened
        try:
            from session_state import SessionState
            session_state = SessionState(self.temp_dir)
        except ImportError:
            pytest.skip("session_state module not available")
        session_state.mark_injected(self.test_transcript)
        
        test_data = {
            "session_id": "integration-test-123",
            "transcript_path": self.test_transcript,
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Follow up question"
        }
        
        with patch('sys.stdout') as mock_stdout, \
             pytest.raises(SystemExit) as exc_info:
            
            await handle_async(test_data)
        
        # Should exit with success code
        assert exc_info.value.code == 0
        
        # Should have written minimal JSON output (no context injection)
        assert mock_stdout.write.called
        
        # Verify minimal output structure
        output_calls = [call[0][0] for call in mock_stdout.write.call_args_list if call[0]]
        json_output = None
        for call in output_calls:
            try:
                json_output = json.loads(call)
                break
            except (json.JSONDecodeError, ValueError):
                continue
        
        assert json_output is not None
        assert json_output["continue"] is True
        assert json_output["hookSpecificOutput"]["additionalContext"] == ""  # No context
    
    def test_sync_wrapper_functionality(self):
        """Test synchronous wrapper around async handle function."""
        test_data = {
            "session_id": "sync-test-123",
            "transcript_path": self.test_transcript,
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Sync test prompt"
        }
        
        with patch('UserPromptSubmit.handle_async') as mock_handle_async, \
             patch('asyncio.run') as mock_asyncio_run:
            
            # Mock the async function to avoid actual execution
            mock_handle_async.return_value = None
            
            # Should not raise exception
            handle(test_data)
            
            # Should have called asyncio.run with handle_async
            mock_asyncio_run.assert_called_once()
    
    def test_sync_wrapper_with_existing_event_loop(self):
        """Test sync wrapper when event loop is already running."""
        test_data = {
            "session_id": "sync-loop-test-123",
            "transcript_path": self.test_transcript,
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Event loop test"
        }
        
        async def run_in_event_loop():
            with patch('UserPromptSubmit.handle_async') as mock_handle_async, \
                 patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
                
                mock_handle_async.return_value = None
                mock_future = MagicMock()
                mock_future.result.return_value = None
                mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
                
                # Should not raise exception
                handle(test_data)
                
                # Should have used ThreadPoolExecutor
                mock_executor.assert_called_once()
        
        # Run test within an event loop
        asyncio.run(run_in_event_loop())


class TestAsyncInjectionOrchestration:
    """Test async injection orchestration and parallel execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.circuit_manager = CircuitBreakerManager()
        self.orchestrator = InjectionOrchestrator(self.circuit_manager)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_parallel_injection_execution_timing(self):
        """Test that injections execute in parallel for performance."""
        user_prompt = "Test parallel execution"
        project_dir = self.temp_dir
        
        # Mock injection functions with delays to test parallelism
        async def slow_system_monitor(*args):
            await asyncio.sleep(0.1)
            return "system_info"
        
        def slow_smart_recommendations(*args):
            time.sleep(0.1)
            return "smart_advice"
        
        async def slow_git_injection(*args):
            await asyncio.sleep(0.1)
            return "git_info"
        
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', side_effect=slow_smart_recommendations), \
             patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', side_effect=slow_system_monitor), \
             patch('UserPromptSubmit.injection_orchestrator.get_git_injection', side_effect=slow_git_injection), \
             patch('UserPromptSubmit.injection_orchestrator.optimize_injection_sync', return_value="optimized_context"):
            
            start_time = time.time()
            result = await self.orchestrator.execute_injections(user_prompt, project_dir)
            end_time = time.time()
            
            # Should complete in roughly the time of the slowest injection (0.1s)
            # If sequential, would take 0.3s+. Allow some overhead.
            assert end_time - start_time < 0.25, "Injections should execute in parallel"
            assert "optimized_context" in result
    
    @pytest.mark.asyncio
    async def test_timeout_handling_in_orchestration(self):
        """Test timeout handling for slow injections."""
        user_prompt = "Test timeout handling"
        project_dir = self.temp_dir
        
        # Mock injection that takes longer than timeout
        async def very_slow_injection(*args):
            await asyncio.sleep(35)  # Exceeds 30s timeout
            return "slow_result"
        
        with patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', side_effect=very_slow_injection), \
             pytest.raises(SystemExit) as exc_info:
            
            await self.orchestrator.execute_injections(user_prompt, project_dir)
        
        assert exc_info.value.code == 2  # Blocking error exit code
    
    @pytest.mark.asyncio
    async def test_exception_propagation_in_orchestration(self):
        """Test exception handling and propagation in parallel injections."""
        user_prompt = "Test exception handling"
        project_dir = self.temp_dir
        
        # Mock injection that raises exception
        def failing_injection(*args):
            raise ValueError("Simulated injection failure")
        
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', side_effect=failing_injection), \
             pytest.raises(SystemExit) as exc_info:
            
            await self.orchestrator.execute_injections(user_prompt, project_dir)
        
        assert exc_info.value.code == 2  # Blocking error exit code
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration_in_orchestration(self):
        """Test that circuit breakers properly control injection execution."""
        user_prompt = "Test circuit breaker integration"
        project_dir = self.temp_dir
        
        # Disable some injections via circuit breaker
        self.circuit_manager.disable_injection("git")
        self.circuit_manager.disable_injection("mcp")
        
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', return_value="smart_advice"), \
             patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', return_value="system_info"), \
             patch('UserPromptSubmit.injection_orchestrator.get_git_injection') as mock_git, \
             patch('UserPromptSubmit.injection_orchestrator.get_mcp_injection') as mock_mcp, \
             patch('UserPromptSubmit.injection_orchestrator.optimize_injection_sync', return_value="optimized_context"):
            
            result = await self.orchestrator.execute_injections(user_prompt, project_dir)
            
            # Disabled injections should not be called
            mock_git.assert_not_called()
            mock_mcp.assert_not_called()
            
            assert "optimized_context" in result
    
    @pytest.mark.asyncio
    async def test_result_validation_in_orchestration(self):
        """Test that orchestrator validates injection results."""
        user_prompt = "Test result validation"
        project_dir = self.temp_dir
        
        # Mock injection that returns None (invalid)
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', return_value=None), \
             pytest.raises(SystemExit) as exc_info:
            
            await self.orchestrator.execute_injections(user_prompt, project_dir)
        
        assert exc_info.value.code == 2  # Should exit with blocking error


class TestTokenOptimizationIntegration:
    """Test token optimization workflow integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = TokenOptimizer()
    
    def test_token_optimization_with_ai_integration(self):
        """Test integration between token optimization and AI enhancement."""
        large_context = "This is a large context. " * 1000  # Create large context
        user_prompt = "Optimize this context"
        
        with patch('UserPromptSubmit.ai_context_optimizer_optimized.optimize_injection_with_ai') as mock_ai_optimize:
            mock_ai_optimize.return_value = "AI optimized context"
            
            # First apply token optimization
            token_optimized = self.optimizer.optimize_context(large_context, user_prompt)
            
            # Then apply AI optimization
            result = optimize_injection_sync(user_prompt, token_optimized)
            
            # Should be significantly reduced from original
            assert len(result) < len(large_context)
    
    def test_context_caching_integration(self):
        """Test that context caching works properly across multiple calls."""
        context = "Test context for caching integration"
        prompt = "test prompt"
        
        # First call
        result1 = self.optimizer.optimize_context(context, prompt)
        
        # Second call should use cache
        start_time = time.time()
        result2 = self.optimizer.optimize_context(context, prompt)
        end_time = time.time()
        
        # Results should be identical
        assert result1 == result2
        
        # Second call should be much faster (cached)
        assert end_time - start_time < 0.01  # Very fast due to caching
    
    def test_priority_content_preservation_integration(self):
        """Test that priority content is preserved through optimization workflow."""
        context_with_priority = """
        Normal content line 1
        ERROR: Critical system failure detected in authentication module
        Normal content line 2
        git commit abc123: Fixed security vulnerability in user validation
        Normal content line 3
        test_user_auth.py: FAILED - AuthenticationError: Invalid credentials
        Normal content line 4
        performance issue: Database query taking 5000ms
        Normal content line 5
        TODO: Refactor legacy authentication system
        """ * 10  # Make it large enough to trigger aggressive optimization
        
        prompt = "Help me debug the authentication error"
        
        result = self.optimizer.optimize_context(context_with_priority, prompt)
        
        # Priority content should be preserved
        assert "ERROR: Critical system failure" in result
        assert "git commit abc123" in result
        assert "FAILED - AuthenticationError" in result
        assert "performance issue" in result
        assert "TODO: Refactor legacy" in result


class TestSessionStateIntegration:
    """Test session state integration with injection decisions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SessionStateManager()
        self.test_transcript = os.path.join(self.temp_dir, "test_transcript.json")
        
        # Create mock transcript
        with open(self.test_transcript, 'w') as f:
            json.dump({"messages": [{"type": "user", "message": "hello"}]}, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_injection_decision_caching_integration(self):
        """Test that injection decisions are properly cached."""
        test_data = {
            "transcript_path": self.test_transcript,
            "prompt": "test prompt"
        }
        
        # First call
        start_time = time.time()
        result1 = self.session_manager.should_inject_context(test_data)
        mid_time = time.time()
        
        # Second call should use cache
        result2 = self.session_manager.should_inject_context(test_data)
        end_time = time.time()
        
        # Results should be consistent
        assert result1 == result2
        
        # Second call should be faster (cached)
        first_duration = mid_time - start_time
        second_duration = end_time - mid_time
        assert second_duration < first_duration * 0.5  # Significantly faster
    
    def test_transcript_change_detection_integration(self):
        """Test that transcript changes properly trigger injection."""
        # Create second transcript
        second_transcript = os.path.join(self.temp_dir, "test_transcript2.json")
        with open(second_transcript, 'w') as f:
            json.dump({"messages": [{"type": "user", "message": "different content"}]}, f)
        
        test_data1 = {"transcript_path": self.test_transcript, "prompt": "test"}
        test_data2 = {"transcript_path": second_transcript, "prompt": "test"}
        
        # First transcript
        result1 = self.session_manager.should_inject_context(test_data1)
        
        # Different transcript should trigger injection
        result2 = self.session_manager.should_inject_context(test_data2)
        
        # Both should require injection (different transcripts)
        assert result1 is True
        assert result2 is True
    
    def test_concurrent_session_state_integration(self):
        """Test concurrent access to session state doesn't cause issues."""
        import threading
        
        results = []
        errors = []
        
        def access_session_state():
            try:
                test_data = {"transcript_path": self.test_transcript, "prompt": "concurrent test"}
                result = self.session_manager.should_inject_context(test_data)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = [threading.Thread(target=access_session_state) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should not have errors
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"
        
        # Should have results
        assert len(results) == 10
        
        # All results should be boolean
        for result in results:
            assert isinstance(result, bool)


class TestErrorHandlingIntegration:
    """Test error handling integration across components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_credential_scrubbing_integration(self):
        """Test that credentials are scrubbed across all error scenarios."""
        test_data = {
            "session_id": "test-session-123",
            "transcript_path": "/nonexistent/path",
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test with API_KEY=sk-secret123456"
        }
        
        with patch('sys.stderr') as mock_stderr, \
             pytest.raises(SystemExit):
            
            await handle_async(test_data)
        
        # Check that credentials were scrubbed from error output
        stderr_calls = [str(call) for call in mock_stderr.write.call_args_list]
        full_stderr = " ".join(stderr_calls)
        
        assert "sk-secret123456" not in full_stderr, "API key should be scrubbed"
        assert "[REDACTED]" in full_stderr or "Error:" in full_stderr, "Should have error output"
    
    @pytest.mark.asyncio
    async def test_exit_code_consistency_integration(self):
        """Test that exit codes are consistent across different error scenarios."""
        # Test blocking error scenario
        test_data_blocking = {
            "session_id": "test-session-123",
            "transcript_path": "/nonexistent/path",  # Will cause blocking error
            "cwd": self.temp_dir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test"
        }
        
        with pytest.raises(SystemExit) as exc_info:
            await handle_async(test_data_blocking)
        
        # Should be blocking error (exit code 2)
        assert exc_info.value.code == 2
    
    def test_validation_error_integration(self):
        """Test integration of validation errors through the pipeline."""
        invalid_data_cases = [
            {"session_id": "invalid id!"},  # Invalid session ID
            {"session_id": "test-123", "hook_event_name": "WrongHook"},  # Wrong hook
            {"session_id": "test-123", "transcript_path": "../../../etc/passwd"},  # Path traversal
        ]
        
        try:
            from UserPromptSubmit import validate_input_data
        except ImportError:
            pytest.skip("validate_input_data function not available")
        
        for invalid_data in invalid_data_cases:
            # Should be rejected by validation
            result = validate_input_data(invalid_data)
            assert result is None, f"Should reject invalid data: {invalid_data}"


class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    def test_circuit_breaker_environment_integration(self):
        """Test that environment variables properly control circuit breakers."""
        # Test with environment overrides
        env_vars = {
            "CIRCUIT_BREAKER_GIT": "false",
            "CIRCUIT_BREAKER_MCP": "false",
            "CIRCUIT_BREAKER_FIRECRAWL": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            circuit_manager = CircuitBreakerManager()
            
            # Should respect environment overrides
            assert circuit_manager.is_injection_enabled("git") is False
            assert circuit_manager.is_injection_enabled("mcp") is False
            assert circuit_manager.is_injection_enabled("firecrawl") is True
    
    @pytest.mark.asyncio
    async def test_configuration_loading_integration(self):
        """Test that configuration is properly loaded and used."""
        try:
            from config import get_config
        except ImportError:
            pytest.skip("config module not available")

        # Mock environment variables for config
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "test-api-key",
            "OPENROUTER_MODEL": "test-model",
            "CONTEXT_MAX_TOKENS": "1000"
        }):
            config = get_config()
            
            # Should load from environment
            assert config.openrouter.api_key == "test-api-key"
            assert config.openrouter.default_model == "test-model"
            assert config.context.max_context_tokens == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])