#!/usr/bin/env python3
"""Comprehensive test suite for the Context Revival System."""

import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to Python path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit"))

try:
    from context_revival import (
        ContextRevivalHook, ContextRevivalAnalyzer, ContextFormatter,
        get_context_revival_hook, get_context_revival_injection
    )
    from context_manager import ContextManager, ContextEntry, CircuitBreaker
    from session_state import SessionState
except ImportError as e:
    print(f"Import error: {e}")
    print("Some tests may be skipped due to missing dependencies")


class TestContextRevivalAnalyzer(unittest.TestCase):
    """Test the context revival analyzer."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "triggers": {
                "keywords": ["similar", "before", "previous", "like", "remember"],
                "error_indicators": ["error", "bug", "issue", "problem"],
                "success_indicators": ["worked", "success", "fixed"],
                "file_extensions": [".py", ".js", ".ts"]
            }
        }
        self.analyzer = ContextRevivalAnalyzer(self.config)
    
    def test_empty_prompt(self):
        """Test analysis of empty prompt."""
        result = self.analyzer.analyze_prompt("")
        self.assertFalse(result["should_retrieve"])
        self.assertEqual(result["confidence"], 0.0)
    
    def test_trigger_keywords(self):
        """Test trigger keyword detection."""
        prompt = "This is similar to before when I had the same issue"
        result = self.analyzer.analyze_prompt(prompt)
        
        self.assertIn("similar", result["keywords_found"])
        self.assertIn("before", result["keywords_found"])
        self.assertGreater(result["confidence"], 0.2)  # Should have some confidence
    
    def test_error_indicators(self):
        """Test error indicator detection."""
        prompt = "I'm getting an error when trying to debug this problem"
        result = self.analyzer.analyze_prompt(prompt)
        
        self.assertGreater(result["confidence"], 0.5)  # High confidence for errors
        self.assertTrue(any("Error-related" in reason for reason in result["reasons"]))
    
    def test_success_indicators(self):
        """Test success indicator detection."""
        prompt = "The previous fix worked successfully"
        result = self.analyzer.analyze_prompt(prompt)
        
        self.assertGreater(result["confidence"], 0.3)  # Moderate confidence
        self.assertTrue(any("Success-related" in reason for reason in result["reasons"]))
    
    def test_file_mentions(self):
        """Test file mention detection."""
        prompt = "There's an issue in login.py and auth.js files"
        result = self.analyzer.analyze_prompt(prompt)
        
        self.assertGreater(result["confidence"], 0.1)
        self.assertTrue(any("Mentions" in reason and "files" in reason for reason in result["reasons"]))
    
    def test_complex_prompt(self):
        """Test complex prompt detection."""
        prompt = "I need help debugging a complex authentication error that occurred when users try to login through the OAuth flow, similar to what we fixed before in the user management system"
        result = self.analyzer.analyze_prompt(prompt)
        
        self.assertGreater(result["confidence"], 0.5)  # Should be high confidence
        self.assertTrue(result["should_retrieve"])
        self.assertTrue(any("Complex/detailed prompt" in reason for reason in result["reasons"]))
    
    def test_pattern_matching(self):
        """Test context type pattern matching."""
        test_cases = [
            ("How to implement this feature?", "implementation_context"),
            ("This error keeps happening", "error_context"),
            ("What's the best practice approach?", "pattern_context"),
            ("The file structure needs refactoring", "file_context")
        ]
        
        for prompt, expected_type in test_cases:
            result = self.analyzer.analyze_prompt(prompt)
            self.assertIn(expected_type, result["context_types"], 
                         f"Failed to detect {expected_type} in '{prompt}'")
    
    def test_confidence_threshold(self):
        """Test confidence threshold for retrieval decision."""
        # Low confidence prompt
        low_confidence = "Hello world"
        result = self.analyzer.analyze_prompt(low_confidence)
        self.assertFalse(result["should_retrieve"])
        
        # High confidence prompt
        high_confidence = "I have an error similar to before with the login.py file"
        result = self.analyzer.analyze_prompt(high_confidence)
        self.assertTrue(result["should_retrieve"])


class TestContextFormatter(unittest.TestCase):
    """Test the context formatter."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "injection": {
                "max_context_tokens": 2000,
                "include_file_context": True
            }
        }
        self.formatter = ContextFormatter(self.config)
    
    def test_empty_contexts(self):
        """Test formatting with no contexts."""
        result = self.formatter.format_contexts([], {})
        self.assertEqual(result, "")
    
    def test_single_context_formatting(self):
        """Test formatting a single context."""
        context = ContextEntry(
            id=1,
            session_id="test_session",
            user_prompt="Test prompt",
            context_data="Test context data",
            files_involved=["test.py"],
            timestamp=datetime.now(),
            outcome="success",
            metadata={"tools_used": "Edit"},
            relevance_score=0.8
        )
        
        analysis = {
            "confidence": 0.75,
            "reasons": ["Test reason"]
        }
        
        result = self.formatter.format_contexts([context], analysis)
        
        self.assertIn('<context-revival confidence="0.75">', result)
        self.assertIn("## Context 1/1 ✅", result)
        self.assertIn("**Relevance:** 0.80", result)
        self.assertIn("**Prompt:** Test prompt", result)
        self.assertIn("**Files:** test.py", result)
        self.assertIn("**Context:**", result)
        self.assertIn("Test context data", result)
        self.assertIn("</context-revival>", result)
    
    def test_multiple_contexts_sorting(self):
        """Test sorting of multiple contexts by relevance."""
        contexts = [
            ContextEntry(id=1, relevance_score=0.5, timestamp=datetime.now()),
            ContextEntry(id=2, relevance_score=0.8, timestamp=datetime.now()),
            ContextEntry(id=3, relevance_score=0.6, timestamp=datetime.now())
        ]
        
        result = self.formatter.format_contexts(contexts, {"confidence": 0.7})
        
        # Should be sorted by relevance (highest first)
        lines = result.split('\n')
        context_lines = [line for line in lines if "## Context" in line]
        
        self.assertEqual(len(context_lines), 3)
        # The order should be based on relevance score
        self.assertIn("0.80", context_lines[0])  # Highest relevance first
    
    def test_token_limit_enforcement(self):
        """Test that token limits are enforced."""
        # Create a very large context
        large_context = ContextEntry(
            context_data="x" * 10000,  # Very large context
            relevance_score=0.8,
            timestamp=datetime.now()
        )
        
        small_config = {
            "injection": {
                "max_context_tokens": 100,  # Very small limit
                "include_file_context": True
            }
        }
        formatter = ContextFormatter(small_config)
        
        result = formatter.format_contexts([large_context], {"confidence": 0.7})
        
        # Should be much shorter than the original
        self.assertLess(len(result.split()), 500)  # Rough token estimate
    
    def test_outcome_indicators(self):
        """Test outcome indicator display."""
        test_cases = [
            ("success", "✅"),
            ("partial", "🟡"),
            ("failure", "❌"),
            ("unknown", "❓")
        ]
        
        for outcome, expected_indicator in test_cases:
            context = ContextEntry(
                outcome=outcome,
                relevance_score=0.5,
                timestamp=datetime.now()
            )
            result = self.formatter.format_contexts([context], {"confidence": 0.5})
            self.assertIn(expected_indicator, result)
    
    def test_file_context_inclusion(self):
        """Test file context inclusion/exclusion."""
        context = ContextEntry(
            files_involved=["test1.py", "test2.js", "test3.ts"],
            relevance_score=0.5,
            timestamp=datetime.now()
        )
        
        # With file context enabled
        result_with_files = self.formatter.format_contexts([context], {"confidence": 0.5})
        self.assertIn("**Files:**", result_with_files)
        self.assertIn("test1.py", result_with_files)
        
        # With file context disabled
        no_file_config = {
            "injection": {
                "max_context_tokens": 2000,
                "include_file_context": False
            }
        }
        formatter_no_files = ContextFormatter(no_file_config)
        result_no_files = formatter_no_files.format_contexts([context], {"confidence": 0.5})
        self.assertNotIn("**Files:**", result_no_files)


class TestCircuitBreaker(unittest.TestCase):
    """Test the circuit breaker implementation."""
    
    def setUp(self):
        """Set up circuit breaker for testing."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            half_open_max_calls=2
        )
    
    def test_successful_calls(self):
        """Test successful function calls."""
        def success_func():
            return "success"
        
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "CLOSED")
    
    def test_failure_handling(self):
        """Test failure handling and state transitions."""
        def failure_func():
            raise Exception("Test failure")
        
        # Should handle failures and eventually open
        for i in range(3):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(failure_func)
        
        self.assertEqual(self.circuit_breaker.state, "OPEN")
        
        # Should fail fast when open
        with self.assertRaises(Exception) as cm:
            self.circuit_breaker.call(failure_func)
        self.assertIn("Circuit breaker is OPEN", str(cm.exception))
    
    def test_recovery_mechanism(self):
        """Test circuit breaker recovery."""
        def failure_func():
            raise Exception("Test failure")
        
        def success_func():
            return "recovered"
        
        # Trigger circuit breaker to open
        for i in range(3):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(failure_func)
        
        self.assertEqual(self.circuit_breaker.state, "OPEN")
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should transition to HALF_OPEN and allow success
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "recovered")
        self.assertEqual(self.circuit_breaker.state, "CLOSED")


class TestContextManager(unittest.TestCase):
    """Test the context manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            "database": {"filename": "test_context.db", "timeout": 5.0},
            "storage": {"max_context_age_days": 30, "compression_enabled": False},
            "retrieval": {
                "max_results": 5,
                "relevance_threshold": 0.3,
                "scoring_weights": {
                    "recency": 0.3,
                    "relevance": 0.4,
                    "outcome_success": 0.2,
                    "file_overlap": 0.1
                }
            },
            "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
            "performance": {"cache_size": 10, "cache_ttl": 3600},
            "logging": {"level": "ERROR"}  # Reduce log noise in tests
        }
        
        # Mock session state
        with patch('context_manager.SessionState') as mock_session:
            mock_session.return_value.get_state.return_value = {"last_transcript_path": "test_session.json"}
            self.context_manager = ContextManager(self.temp_dir)
            self.context_manager.config = self.test_config
            self.context_manager._init_database()
    
    def tearDown(self):
        """Clean up test environment."""
        try:
            self.context_manager.close()
        except:
            pass
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_context(self):
        """Test storing a context entry."""
        context_id = self.context_manager.store_context(
            user_prompt="Test prompt",
            context_data="Test context data", 
            files_involved=["test.py"],
            outcome="success",
            metadata={"test": "value"}
        )
        
        self.assertIsNotNone(context_id)
        self.assertIsInstance(context_id, int)
    
    def test_retrieve_contexts(self):
        """Test retrieving relevant contexts."""
        # Store some test contexts
        for i in range(3):
            self.context_manager.store_context(
                user_prompt=f"Test prompt {i} about authentication error",
                context_data=f"Test context data {i}",
                files_involved=["auth.py"],
                outcome="success"
            )
        
        # Retrieve contexts
        contexts = self.context_manager.retrieve_relevant_contexts(
            query="authentication error",
            files_involved=["auth.py"],
            max_results=5
        )
        
        self.assertGreater(len(contexts), 0)
        self.assertLessEqual(len(contexts), 3)
        
        # Check that contexts have relevance scores
        for context in contexts:
            self.assertGreater(context.relevance_score, 0)
    
    def test_relevance_calculation(self):
        """Test relevance score calculation."""
        # Create test context
        context = ContextEntry(
            user_prompt="authentication error in login system",
            context_data="Fixed login authentication issue",
            files_involved=["auth.py", "login.js"],
            timestamp=datetime.now() - timedelta(hours=1),
            outcome="success"
        )
        
        # Test query with good overlap
        score = self.context_manager._calculate_relevance(
            context, 
            "authentication error",
            ["auth.py"]
        )
        
        self.assertGreater(score, 0.3)  # Should be reasonably relevant
        self.assertLessEqual(score, 1.0)  # Should not exceed 1.0
    
    def test_cleanup_old_contexts(self):
        """Test cleanup of old contexts."""
        # Store an old context
        old_context = ContextEntry(
            user_prompt="Old prompt",
            context_data="Old data",
            timestamp=datetime.now() - timedelta(days=35)  # Older than default 30 days
        )
        
        with self.context_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO contexts (session_id, user_prompt, context_data, 
                                     files_involved, timestamp, outcome, metadata, compressed, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "test_session",
                old_context.user_prompt,
                old_context.context_data,
                "[]",
                old_context.timestamp.isoformat(),
                "unknown",
                "{}",
                False,
                "test_hash"
            ))
            conn.commit()
        
        # Cleanup should remove the old context
        deleted_count = self.context_manager.cleanup_old_contexts(30)
        self.assertEqual(deleted_count, 1)
    
    def test_caching_mechanism(self):
        """Test the caching mechanism."""
        # Store a context
        self.context_manager.store_context(
            user_prompt="Test caching prompt",
            context_data="Test context"
        )
        
        # First retrieval (should hit database)
        contexts1 = self.context_manager.retrieve_relevant_contexts("test caching")
        
        # Second retrieval (should hit cache)
        contexts2 = self.context_manager.retrieve_relevant_contexts("test caching")
        
        # Should return same results
        self.assertEqual(len(contexts1), len(contexts2))
        if contexts1:
            self.assertEqual(contexts1[0].user_prompt, contexts2[0].user_prompt)
    
    def test_compression(self):
        """Test context compression."""
        # Enable compression
        self.context_manager.config["storage"]["compression_enabled"] = True
        
        # Store large context
        large_data = "x" * 2000  # Large enough to trigger compression
        context_id = self.context_manager.store_context(
            user_prompt="Large context test",
            context_data=large_data
        )
        
        # Verify it was stored compressed
        with self.context_manager.get_connection() as conn:
            cursor = conn.execute("SELECT compressed, context_data FROM contexts WHERE id = ?", (context_id,))
            row = cursor.fetchone()
            
            self.assertTrue(row["compressed"])
            self.assertNotEqual(row["context_data"], large_data)  # Should be compressed
    
    def test_health_status(self):
        """Test health status reporting."""
        health = self.context_manager.get_health_status()
        
        self.assertIn("status", health)
        self.assertIn("total_contexts", health)
        self.assertIn("circuit_breaker_state", health)
        self.assertEqual(health["circuit_breaker_state"], "CLOSED")
    
    def test_session_integration(self):
        """Test session state integration."""
        session_id = self.context_manager._get_current_session_id()
        self.assertIsNotNone(session_id)
        self.assertIsInstance(session_id, str)
    
    def test_concurrent_access(self):
        """Test concurrent access to context manager."""
        def store_context(thread_id):
            for i in range(5):
                self.context_manager.store_context(
                    user_prompt=f"Thread {thread_id} prompt {i}",
                    context_data=f"Thread {thread_id} data {i}"
                )
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=store_context, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all contexts were stored
        with self.context_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM contexts")
            count = cursor.fetchone()["count"]
            self.assertEqual(count, 15)  # 3 threads * 5 contexts each


class TestContextRevivalHook(unittest.TestCase):
    """Test the main context revival hook."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        config_path = Path(self.temp_dir) / "test_config.json"
        test_config = {
            "database": {"filename": "test_hook.db", "timeout": 5.0},
            "storage": {"compression_enabled": False},
            "retrieval": {"max_results": 3, "relevance_threshold": 0.2},
            "injection": {"max_context_tokens": 1000, "include_file_context": True},
            "triggers": {
                "keywords": ["similar", "before"],
                "error_indicators": ["error", "bug"],
                "success_indicators": ["worked", "success"],
                "file_extensions": [".py", ".js"]
            },
            "performance": {"max_query_time_ms": 1000},
            "logging": {"level": "ERROR"}
        }
        
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Mock session state and context manager initialization
        with patch('context_revival.Path.__truediv__') as mock_path:
            mock_path.return_value = config_path
            with patch('context_revival.get_context_manager') as mock_get_cm:
                mock_cm = Mock()
                mock_cm.store_context.return_value = 1
                mock_cm.retrieve_relevant_contexts.return_value = []
                mock_get_cm.return_value = mock_cm
                
                self.hook = ContextRevivalHook(self.temp_dir)
                self.hook.context_manager = mock_cm
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_file_context(self):
        """Test file context extraction from prompts."""
        prompt = "There's an issue in auth.py and login.js files, also check config.json"
        files = self.hook.extract_file_context(prompt)
        
        expected_files = ["auth.py", "login.js"]  # config.json not in configured extensions
        for expected_file in expected_files:
            self.assertIn(expected_file, files)
    
    def test_generate_context_injection_no_trigger(self):
        """Test context injection when not triggered."""
        prompt = "Hello world"  # Should not trigger
        result = self.hook.generate_context_injection(prompt)
        
        self.assertEqual(result, "")  # No injection
    
    def test_generate_context_injection_triggered(self):
        """Test context injection when triggered."""
        # Mock context manager to return some contexts
        mock_contexts = [
            ContextEntry(
                id=1,
                user_prompt="Previous error",
                context_data="Fixed by updating config",
                files_involved=["config.py"],
                timestamp=datetime.now(),
                outcome="success",
                relevance_score=0.8
            )
        ]
        self.hook.context_manager.retrieve_relevant_contexts.return_value = mock_contexts
        
        prompt = "I have a similar error as before"  # Should trigger
        result = self.hook.generate_context_injection(prompt)
        
        self.assertNotEqual(result, "")  # Should have injection
        self.assertIn("<context-revival", result)
        self.assertIn("Previous error", result)
        self.assertIn("Fixed by updating config", result)
    
    def test_health_status(self):
        """Test health status reporting."""
        health = self.hook.get_health_status()
        
        self.assertIn("enabled", health)
        self.assertIn("stats", health)
        self.assertIn("config_loaded", health)
        
        # Should be enabled with mock context manager
        self.assertTrue(health["enabled"])
        self.assertTrue(health["config_loaded"])
    
    def test_performance_tracking(self):
        """Test performance statistics tracking."""
        initial_stats = self.hook.stats.copy()
        
        # Trigger context retrieval
        self.hook.context_manager.retrieve_relevant_contexts.return_value = [
            ContextEntry(relevance_score=0.5, timestamp=datetime.now())
        ]
        
        self.hook.generate_context_injection("similar error before")
        
        # Stats should be updated
        self.assertGreater(self.hook.stats["contexts_retrieved"], initial_stats["contexts_retrieved"])
        self.assertGreater(self.hook.stats["total_retrieval_time"], initial_stats["total_retrieval_time"])


class TestIntegrationScenarios(unittest.TestCase):
    """Test end-to-end integration scenarios."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('context_revival.get_context_manager')
    def test_full_workflow(self, mock_get_cm):
        """Test full context revival workflow."""
        # Mock context manager with realistic behavior
        mock_cm = Mock()
        mock_contexts = [
            ContextEntry(
                user_prompt="How to fix authentication error?",
                context_data="Update the session timeout in config.py",
                files_involved=["config.py", "auth.py"],
                timestamp=datetime.now() - timedelta(hours=2),
                outcome="success",
                relevance_score=0.85
            )
        ]
        mock_cm.retrieve_relevant_contexts.return_value = mock_contexts
        mock_cm.store_context.return_value = 1
        mock_get_cm.return_value = mock_cm
        
        # Test the full injection workflow
        prompt = "I'm getting an authentication error similar to before"
        result = get_context_revival_injection(prompt, self.temp_dir)
        
        self.assertNotEqual(result, "")
        self.assertIn("context-revival", result)
        self.assertIn("authentication error", result)
        self.assertIn("session timeout", result)
        self.assertIn("config.py", result)
        
        # Verify context manager was called appropriately
        mock_cm.retrieve_relevant_contexts.assert_called()
        mock_cm.store_context.assert_called()
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test with invalid project directory
        result = get_context_revival_injection("test prompt", "/nonexistent/path")
        # Should not crash, might return empty string
        self.assertIsInstance(result, str)
    
    def test_configuration_loading(self):
        """Test configuration loading and defaults."""
        # Test with missing config file
        with patch('context_revival.Path.exists', return_value=False):
            hook = ContextRevivalHook(self.temp_dir)
            
            # Should have default configuration
            self.assertIsNotNone(hook.config)
            self.assertIn("retrieval", hook.config)
            self.assertIn("injection", hook.config)
    
    def test_concurrent_usage(self):
        """Test concurrent usage of context revival."""
        results = []
        
        def get_injection(thread_id):
            result = get_context_revival_injection(f"Test prompt {thread_id}", self.temp_dir)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_injection, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should complete without error
        self.assertEqual(len(results), 5)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarks for the context revival system."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up performance test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skipIf(os.getenv('SKIP_PERFORMANCE_TESTS'), "Performance tests disabled")
    def test_analysis_performance(self):
        """Benchmark prompt analysis performance."""
        config = {
            "triggers": {
                "keywords": ["similar", "before", "previous", "like", "remember"],
                "error_indicators": ["error", "bug", "issue", "problem"],
                "success_indicators": ["worked", "success", "fixed"],
                "file_extensions": [".py", ".js", ".ts"]
            }
        }
        analyzer = ContextRevivalAnalyzer(config)
        
        # Test with various prompt sizes
        test_prompts = [
            "Short prompt",
            "Medium length prompt with some context and file mentions like test.py",
            "Very long and detailed prompt " * 20 + " with authentication error in login.py"
        ]
        
        for prompt in test_prompts:
            start_time = time.time()
            for _ in range(100):  # Run multiple times
                analyzer.analyze_prompt(prompt)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 100
            self.assertLess(avg_time, 0.01, f"Analysis too slow for prompt length {len(prompt)}")
    
    @unittest.skipIf(os.getenv('SKIP_PERFORMANCE_TESTS'), "Performance tests disabled")  
    def test_formatting_performance(self):
        """Benchmark context formatting performance."""
        config = {
            "injection": {
                "max_context_tokens": 2000,
                "include_file_context": True
            }
        }
        formatter = ContextFormatter(config)
        
        # Create test contexts of different sizes
        contexts = []
        for i in range(10):
            context = ContextEntry(
                user_prompt=f"Test prompt {i}",
                context_data="x" * (100 * (i + 1)),  # Varying sizes
                files_involved=[f"file{j}.py" for j in range(i + 1)],
                timestamp=datetime.now(),
                relevance_score=0.8 - (i * 0.05)
            )
            contexts.append(context)
        
        start_time = time.time()
        result = formatter.format_contexts(contexts, {"confidence": 0.7})
        end_time = time.time()
        
        format_time = end_time - start_time
        self.assertLess(format_time, 0.1, "Formatting too slow")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    # Configure test discovery and execution
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestContextRevivalAnalyzer,
        TestContextFormatter, 
        TestCircuitBreaker,
        TestContextManager,
        TestContextRevivalHook,
        TestIntegrationScenarios,
        TestPerformanceBenchmarks
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestClass(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        failfast=False,
        buffer=True
    )
    
    print("Running Context Revival System Tests...")
    print("=" * 60)
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].strip()}")
    
    # Exit with appropriate code
    exit_code = 0 if result.wasSuccessful() else 1
    print(f"\nTest suite {'PASSED' if result.wasSuccessful() else 'FAILED'}")
    sys.exit(exit_code)