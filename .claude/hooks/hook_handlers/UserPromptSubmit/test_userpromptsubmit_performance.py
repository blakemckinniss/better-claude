#!/usr/bin/env python3
"""Performance tests for UserPromptSubmit hook handler.

This test suite covers:
- Token optimization performance
- Parallel execution performance
- Memory usage optimization
- Cache efficiency
- Timeout handling under load
- Resource cleanup
"""

import asyncio
import gc
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil
import pytest

# Add the hook handler directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import performance-related modules
try:
    from circuit_breaker_manager import CircuitBreakerManager
    from injection_orchestrator import InjectionOrchestrator
    from performance_monitor import PerformanceMonitor
    from session_state_manager import SessionStateManager
    from token_optimizer import TokenOptimizer, optimize_for_tokens
    from UserPromptSubmit import handle_async, perf_monitor
except ImportError as e:
    pytest.skip(f"Failed to import performance modules: {e}", allow_module_level=True)


class TestTokenOptimizationPerformance:
    """Test performance of token optimization algorithms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = TokenOptimizer()
    
    def test_token_optimization_speed(self):
        """Test that token optimization completes within reasonable time."""
        large_context = "This is a test line with various content. " * 1000  # ~40KB
        user_prompt = "Optimize this context efficiently"
        
        start_time = time.perf_counter()
        result = self.optimizer.optimize_context(large_context, user_prompt)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        # Should complete within 1 second for 40KB input
        assert duration < 1.0, f"Token optimization too slow: {duration:.3f}s"
        
        # Should produce some output
        assert len(result) > 0
        assert len(result) <= len(large_context)  # Should not grow
    
    def test_token_estimation_accuracy(self):
        """Test accuracy and speed of token estimation."""
        test_texts = [
            "Short text",
            "Medium length text " * 50,
            "Very long text with lots of repetition " * 1000,
        ]
        
        for text in test_texts:
            start_time = time.perf_counter()
            estimated_tokens = self.optimizer._estimate_tokens(text)
            end_time = time.perf_counter()
            
            # Should be very fast
            assert end_time - start_time < 0.001, "Token estimation too slow"
            
            # Should be reasonable estimate (4 chars per token)
            expected_tokens = len(text) // 4
            assert abs(estimated_tokens - expected_tokens) / expected_tokens < 0.1, \
                "Token estimation inaccurate"
    
    def test_cache_efficiency(self):
        """Test that caching improves performance significantly."""
        context = "Test context for caching performance " * 100
        prompt = "test prompt"
        
        # First call (no cache)
        start_time = time.perf_counter()
        result1 = self.optimizer.optimize_context(context, prompt)
        mid_time = time.perf_counter()
        
        # Second call (should use cache)
        result2 = self.optimizer.optimize_context(context, prompt)
        end_time = time.perf_counter()
        
        first_duration = mid_time - start_time
        second_duration = end_time - mid_time
        
        # Results should be identical
        assert result1 == result2
        
        # Second call should be much faster (>10x speedup)
        assert second_duration < first_duration / 10, \
            f"Cache not effective: {first_duration:.3f}s vs {second_duration:.3f}s"
    
    def test_memory_usage_optimization(self):
        """Test that token optimization doesn't consume excessive memory."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Process large context
        large_context = "Large context content " * 10000  # ~200KB
        prompt = "test prompt"
        
        # Run optimization multiple times
        for _ in range(10):
            result = self.optimizer.optimize_context(large_context, prompt)
            assert len(result) > 0
        
        # Force garbage collection
        gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not increase memory by more than 50MB
        assert memory_increase < 50 * 1024 * 1024, \
            f"Excessive memory usage: {memory_increase / 1024 / 1024:.1f}MB"
    
    def test_aggressive_optimization_performance(self):
        """Test performance of aggressive optimization with large inputs."""
        # Create large context that will trigger aggressive optimization
        huge_context = "Content line " * 50000  # ~500KB, exceeds token budget
        prompt = "optimize this huge context"
        
        start_time = time.perf_counter()
        result = self.optimizer.optimize_context(huge_context, prompt)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        # Should still complete within reasonable time
        assert duration < 2.0, f"Aggressive optimization too slow: {duration:.3f}s"
        
        # Should be significantly reduced
        assert len(result) < len(huge_context) / 2, "Should significantly reduce large context"
    
    def test_concurrent_optimization_performance(self):
        """Test performance under concurrent optimization requests."""
        context = "Concurrent test context " * 500  # ~10KB
        
        def optimize_worker(worker_id):
            prompt = f"worker {worker_id} prompt"
            start_time = time.perf_counter()
            result = self.optimizer.optimize_context(context, prompt)
            end_time = time.perf_counter()
            return end_time - start_time, len(result)
        
        # Run multiple workers concurrently
        num_workers = 10
        threads = []
        results = []
        
        start_time = time.perf_counter()
        
        for i in range(num_workers):
            thread = threading.Thread(target=lambda i=i: results.append(optimize_worker(i)))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Should complete all workers within reasonable time
        assert total_duration < 3.0, f"Concurrent optimization too slow: {total_duration:.3f}s"
        
        # All workers should have completed
        assert len(results) == num_workers


class TestParallelExecutionPerformance:
    """Test performance of parallel injection execution."""
    
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
    async def test_parallel_execution_speedup(self):
        """Test that parallel execution provides speedup over sequential."""
        user_prompt = "Test parallel performance"
        project_dir = self.temp_dir
        
        # Mock injections with delays to simulate I/O
        async def slow_async_injection(*args):
            await asyncio.sleep(0.1)
            return "async_result"
        
        def slow_sync_injection(*args):
            time.sleep(0.1)
            return "sync_result"
        
        # Test parallel execution
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', side_effect=slow_sync_injection), \
             patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', side_effect=slow_async_injection), \
             patch('UserPromptSubmit.injection_orchestrator.get_git_injection', side_effect=slow_async_injection), \
             patch('UserPromptSubmit.injection_orchestrator.optimize_injection_sync', return_value="optimized"):
            
            start_time = time.perf_counter()
            result = await self.orchestrator.execute_injections(user_prompt, project_dir)
            end_time = time.perf_counter()
            
            parallel_duration = end_time - start_time
            
            # Should complete in roughly the time of slowest injection (~0.1s)
            # If sequential, would take ~0.3s+
            assert parallel_duration < 0.2, f"Parallel execution not efficient: {parallel_duration:.3f}s"
            assert "optimized" in result
    
    @pytest.mark.asyncio
    async def test_timeout_performance(self):
        """Test that timeout enforcement doesn't add significant overhead."""
        user_prompt = "Test timeout performance"
        project_dir = self.temp_dir
        
        # Mock fast injections
        async def fast_injection(*args):
            await asyncio.sleep(0.01)  # Very fast
            return "fast_result"
        
        with patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', side_effect=fast_injection), \
             patch('UserPromptSubmit.injection_orchestrator.optimize_injection_sync', return_value="optimized"):
            
            start_time = time.perf_counter()
            result = await self.orchestrator.execute_injections(user_prompt, project_dir)
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            
            # Should not add significant overhead for fast operations
            assert duration < 0.05, f"Timeout enforcement adds too much overhead: {duration:.3f}s"
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        user_prompt = "Test error handling performance"
        project_dir = self.temp_dir
        
        # Mock injection that raises exception
        def failing_injection(*args):
            raise ValueError("Simulated failure")
        
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', side_effect=failing_injection), \
             pytest.raises(SystemExit):
            
            start_time = time.perf_counter()
            await self.orchestrator.execute_injections(user_prompt, project_dir)
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            
            # Error handling should be fast
            assert duration < 0.1, f"Error handling too slow: {duration:.3f}s"
    
    @pytest.mark.asyncio
    async def test_context_caching_performance(self):
        """Test performance of context caching in orchestrator."""
        user_prompt = "Test context caching"
        project_dir = self.temp_dir
        
        # Mock injections
        with patch('UserPromptSubmit.injection_orchestrator.get_smart_recommendations', return_value="advice"), \
             patch('UserPromptSubmit.injection_orchestrator.get_system_monitoring_injection', return_value="system"), \
             patch('UserPromptSubmit.injection_orchestrator.optimize_injection_sync', return_value="optimized"):
            
            # First call
            start_time = time.perf_counter()
            result1 = await self.orchestrator.execute_injections(user_prompt, project_dir)
            mid_time = time.perf_counter()
            
            # Second call (should use cache)
            result2 = await self.orchestrator.execute_injections(user_prompt, project_dir)
            end_time = time.perf_counter()
            
            first_duration = mid_time - start_time
            second_duration = end_time - mid_time
            
            # Results should be identical
            assert result1 == result2
            
            # Second call should be faster (cached)
            assert second_duration < first_duration, \
                f"Cache not improving performance: {first_duration:.3f}s vs {second_duration:.3f}s"


class TestMemoryManagement:
    """Test memory management and resource cleanup."""
    
    def test_memory_leak_prevention(self):
        """Test that repeated operations don't cause memory leaks."""
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run many optimization cycles
        optimizer = TokenOptimizer()
        
        for i in range(100):
            context = f"Test context iteration {i} " * 100
            prompt = f"prompt {i}"
            result = optimizer.optimize_context(context, prompt)
            assert len(result) > 0
            
            # Occasionally force garbage collection
            if i % 20 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        
        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not increase significantly (allow 20MB for reasonable growth)
        assert memory_increase < 20 * 1024 * 1024, \
            f"Possible memory leak: {memory_increase / 1024 / 1024:.1f}MB increase"
    
    def test_cache_cleanup_performance(self):
        """Test that cache cleanup doesn't impact performance."""
        optimizer = TokenOptimizer()
        
        # Fill cache with many entries
        for i in range(100):
            context = f"Context {i}"
            prompt = f"Prompt {i}"
            optimizer.optimize_context(context, prompt)
        
        # Measure cleanup performance
        start_time = time.perf_counter()
        
        # Trigger cache cleanup by waiting for TTL
        time.sleep(0.1)
        
        # Access optimizer again (should trigger cleanup)
        result = optimizer.optimize_context("new context", "new prompt")
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should complete quickly even with cleanup
        assert duration < 0.2, f"Cache cleanup too slow: {duration:.3f}s"
        assert len(result) > 0
    
    def test_large_context_memory_efficiency(self):
        """Test memory efficiency with very large contexts."""
        # Create very large context
        huge_context = "Large content block " * 100000  # ~2MB
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        optimizer = TokenOptimizer()
        result = optimizer.optimize_context(huge_context, "optimize")
        
        final_memory = process.memory_info().rss
        memory_used = final_memory - initial_memory
        
        # Should not use excessive memory relative to input size
        input_size = len(huge_context)
        memory_ratio = memory_used / input_size
        
        # Memory usage should be reasonable (less than 5x input size)
        assert memory_ratio < 5.0, f"Excessive memory usage ratio: {memory_ratio:.1f}x"
        
        # Should produce smaller output
        assert len(result) < len(huge_context)


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""
    
    def test_performance_monitor_overhead(self):
        """Test that performance monitoring adds minimal overhead."""
        @perf_monitor
        def fast_function():
            return "result"
        
        @perf_monitor
        async def fast_async_function():
            return "async_result"
        
        # Test sync function
        start_time = time.perf_counter()
        for _ in range(1000):
            result = fast_function()
            assert result == "result"
        end_time = time.perf_counter()
        
        sync_duration = end_time - start_time
        
        # Should add minimal overhead
        assert sync_duration < 0.1, f"Performance monitoring adds too much overhead: {sync_duration:.3f}s"
        
        # Test async function
        async def test_async_overhead():
            start_time = time.perf_counter()
            for _ in range(1000):
                result = await fast_async_function()
                assert result == "async_result"
            end_time = time.perf_counter()
            return end_time - start_time
        
        async_duration = asyncio.run(test_async_overhead())
        assert async_duration < 0.1, f"Async performance monitoring adds too much overhead: {async_duration:.3f}s"
    
    def test_performance_monitor_memory(self):
        """Test that performance monitoring doesn't consume excessive memory."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        @perf_monitor
        def monitored_function(data):
            return len(data)
        
        # Run many monitored operations
        for i in range(1000):
            data = f"test data {i}" * 100
            result = monitored_function(data)
            assert result > 0
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not consume excessive memory
        assert memory_increase < 10 * 1024 * 1024, \
            f"Performance monitoring uses too much memory: {memory_increase / 1024 / 1024:.1f}MB"
    
    def test_performance_logging_efficiency(self):
        """Test that performance logging is efficient."""
        @perf_monitor
        def slow_function():
            time.sleep(0.6)  # Triggers slow operation logging
            return "slow_result"
        
        with patch('sys.stderr') as mock_stderr:
            start_time = time.perf_counter()
            result = slow_function()
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            
            # Should not add significant overhead beyond the sleep
            assert duration < 0.65, f"Performance logging adds overhead: {duration:.3f}s"
            assert result == "slow_result"
            
            # Should have logged the slow operation
            assert mock_stderr.write.called


class TestSessionStatePerformance:
    """Test session state management performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SessionStateManager()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_injection_decision_caching_performance(self):
        """Test performance of injection decision caching."""
        # Create test transcript
        transcript_path = os.path.join(self.temp_dir, "test_transcript.json") 
        with open(transcript_path, 'w') as f:
            json.dump({"messages": [{"type": "user", "message": "test"}]}, f)
        
        test_data = {"transcript_path": transcript_path, "prompt": "test"}
        
        # First call (no cache)
        start_time = time.perf_counter()
        result1 = self.session_manager.should_inject_context(test_data)
        mid_time = time.perf_counter()
        
        # Multiple cached calls
        for _ in range(100):
            result2 = self.session_manager.should_inject_context(test_data)
            assert result2 == result1
        
        end_time = time.perf_counter()
        
        first_call_duration = mid_time - start_time
        cached_calls_duration = end_time - mid_time
        
        # Cached calls should be much faster
        avg_cached_time = cached_calls_duration / 100
        assert avg_cached_time < first_call_duration / 10, \
            f"Caching not effective: {first_call_duration:.3f}s vs {avg_cached_time:.3f}s avg"
    
    def test_concurrent_session_access_performance(self):
        """Test performance under concurrent session state access."""
        transcript_path = os.path.join(self.temp_dir, "concurrent_transcript.json")
        with open(transcript_path, 'w') as f:
            json.dump({"messages": [{"type": "user", "message": "concurrent test"}]}, f)
        
        results = []
        errors = []
        
        def concurrent_access():
            try:
                start_time = time.perf_counter()
                test_data = {"transcript_path": transcript_path, "prompt": "concurrent"}
                result = self.session_manager.should_inject_context(test_data)
                end_time = time.perf_counter()
                results.append((result, end_time - start_time))
            except Exception as e:
                errors.append(e)
        
        # Start many concurrent threads
        threads = [threading.Thread(target=concurrent_access) for _ in range(20)]
        
        start_time = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        end_time = time.perf_counter()
        
        total_duration = end_time - start_time
        
        # Should complete without errors
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"
        assert len(results) == 20
        
        # Should complete within reasonable time
        assert total_duration < 2.0, f"Concurrent access too slow: {total_duration:.3f}s"
        
        # Individual operations should be reasonably fast
        avg_duration = sum(duration for _, duration in results) / len(results)
        assert avg_duration < 0.1, f"Individual operations too slow: {avg_duration:.3f}s avg"


class TestResourceCleanup:
    """Test resource cleanup and lifecycle management."""
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        initial_temp_files = len(list(Path(tempfile.gettempdir()).glob("*")))
        
        # Create and use temporary resources
        for i in range(10):
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "test.json")
            
            with open(temp_file, 'w') as f:
                json.dump({"test": f"data {i}"}, f)
            
            # Simulate usage
            with open(temp_file, 'r') as f:
                data = json.load(f)
                assert data["test"] == f"data {i}"
            
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)
        
        # Check that cleanup worked
        final_temp_files = len(list(Path(tempfile.gettempdir()).glob("*")))
        
        # Should not have significantly more temp files
        assert final_temp_files <= initial_temp_files + 2, \
            "Temporary files not properly cleaned up"
    
    def test_thread_cleanup(self):
        """Test that threads are properly cleaned up."""
        import threading
        
        initial_thread_count = threading.active_count()
        
        # Start some threads that complete quickly
        threads = []
        for i in range(5):
            def worker():
                time.sleep(0.1)
                return f"worker {i} done"
            
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Give time for cleanup
        time.sleep(0.1)
        
        final_thread_count = threading.active_count()
        
        # Should return to initial count
        assert final_thread_count == initial_thread_count, \
            f"Threads not cleaned up: {initial_thread_count} -> {final_thread_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])