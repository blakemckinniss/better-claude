#!/usr/bin/env python3
"""Comprehensive testing framework for PostToolUse educational feedback system."""

import asyncio
import json
import os
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

# Add system paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "shared_intelligence"))

# Import components under test
from educational_feedback_enhanced import EducationalFeedbackSystem, handle_educational_feedback
from session_tracker import SessionWarningTracker, get_session_tracker, extract_session_id
from intelligent_router import analyze_tool_for_routing
from anti_pattern_detector import analyze_workflow_patterns
from performance_optimizer import check_performance_optimization
from recommendation_engine import get_tool_recommendations


class TestDataFactory:
    """Factory for creating test data with various scenarios."""
    
    @staticmethod
    def create_hook_data(
        tool_name: str = "Read",
        tool_input: Optional[Dict[str, Any]] = None,
        tool_response: str = "test response",
        session_id: str = "test_session_123",
        success: bool = True
    ) -> Dict[str, Any]:
        """Create mock hook event data."""
        if tool_input is None:
            tool_input = {"file_path": "/test/file.py"}
        
        return {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": tool_response,
            "session_id": session_id,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_context(recent_operations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create mock session context."""
        if recent_operations is None:
            recent_operations = []
        
        return {
            "session_info": "test_session_123",
            "recent_operations": recent_operations
        }
    
    @staticmethod
    def create_bash_operation(command: str) -> Dict[str, Any]:
        """Create bash operation test data."""
        return TestDataFactory.create_hook_data(
            tool_name="Bash",
            tool_input={"command": command},
            tool_response=f"Command executed: {command}"
        )
    
    @staticmethod
    def create_file_operation(
        tool_name: str,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create file operation test data."""
        tool_input = {"file_path": file_path}
        if content and tool_name in ["Write", "Edit"]:
            if tool_name == "Edit":
                tool_input.update({"old_string": "old", "new_string": content})
            else:
                tool_input["content"] = content
                
        return TestDataFactory.create_hook_data(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=f"File {tool_name.lower()}ed: {file_path}"
        )


class MockSessionTracker:
    """Mock session tracker for testing isolation."""
    
    def __init__(self):
        self._warnings = {}
        self._call_counts = {}
    
    def should_show_warning(self, session_id: str, warning_type: str) -> bool:
        """Mock warning check - always show for testing."""
        key = f"{session_id}:{warning_type}"
        self._call_counts[key] = self._call_counts.get(key, 0) + 1
        return True
    
    def mark_warning_shown(self, session_id: str, warning_type: str) -> None:
        """Mock warning marking."""
        self._warnings[f"{session_id}:{warning_type}"] = time.time()
    
    def get_call_count(self, session_id: str, warning_type: str) -> int:
        """Get number of times warning was checked."""
        return self._call_counts.get(f"{session_id}:{warning_type}", 0)


class PerformanceTestCase(unittest.TestCase):
    """Performance testing for <100ms requirement compliance."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.max_execution_time = 0.1  # 100ms requirement
        self.feedback_system = EducationalFeedbackSystem()
    
    def measure_execution_time(self, func, *args, **kwargs):
        """Measure function execution time."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        execution_time = time.perf_counter() - start_time
        return result, execution_time
    
    def test_educational_feedback_performance(self):
        """Test that educational feedback generation meets <100ms requirement."""
        test_data = TestDataFactory.create_bash_operation("grep -r 'pattern' /large/directory")
        session_id = "perf_test_session"
        
        result, exec_time = self.measure_execution_time(
            self.feedback_system.provide_educational_feedback,
            test_data["tool_name"],
            test_data["tool_input"],
            test_data["tool_response"],
            session_id
        )
        
        self.assertLess(
            exec_time, 
            self.max_execution_time,
            f"Educational feedback took {exec_time:.3f}s, exceeding {self.max_execution_time}s limit"
        )
    
    def test_session_tracker_performance(self):
        """Test session tracker operations performance."""
        tracker = SessionWarningTracker()
        session_id = "perf_session"
        warning_type = "test_warning"
        
        # Test warning check performance
        result, exec_time = self.measure_execution_time(
            tracker.should_show_warning,
            session_id,
            warning_type
        )
        
        self.assertLess(exec_time, 0.01, "Session tracker operations too slow")
    
    def test_shared_intelligence_performance(self):
        """Test shared intelligence components performance."""
        test_data = TestDataFactory.create_bash_operation("find . -name '*.py' | grep test")
        context = TestDataFactory.create_context()
        
        # Test intelligent router performance
        result, exec_time = self.measure_execution_time(
            analyze_tool_for_routing,
            test_data["tool_name"],
            test_data["tool_input"],
            context
        )
        
        self.assertLess(exec_time, 0.05, "Intelligent router too slow")
        
        # Test anti-pattern detector performance
        result, exec_time = self.measure_execution_time(
            analyze_workflow_patterns,
            test_data["tool_name"],
            test_data["tool_input"],
            context
        )
        
        self.assertLess(exec_time, 0.05, "Anti-pattern detector too slow")
    
    def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        async def concurrent_feedback():
            tasks = []
            for i in range(10):
                test_data = TestDataFactory.create_bash_operation(f"command_{i}")
                task = asyncio.create_task(asyncio.to_thread(
                    self.feedback_system.provide_educational_feedback,
                    test_data["tool_name"],
                    test_data["tool_input"],
                    test_data["tool_response"],
                    f"session_{i}"
                ))
                tasks.append(task)
            
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks)
            exec_time = time.perf_counter() - start_time
            
            return results, exec_time
        
        results, exec_time = asyncio.run(concurrent_feedback())
        
        # Should handle 10 concurrent operations in reasonable time
        self.assertLess(exec_time, 0.5, "Concurrent operations too slow")


class SecurityTestCase(unittest.TestCase):
    """Security testing for import safety and session tracking."""
    
    def setUp(self):
        """Set up security test environment."""
        self.temp_dir = TemporaryDirectory()
        self.test_session_id = "security_test_session"
    
    def tearDown(self):
        """Clean up security test environment."""
        self.temp_dir.cleanup()
    
    def test_session_tracker_file_safety(self):
        """Test session tracker handles file operations safely."""
        # Test with malicious path
        malicious_path = "../../../etc/passwd"
        tracker = SessionWarningTracker(storage_path=malicious_path)
        
        # Should handle gracefully without security issues
        result = tracker.should_show_warning(self.test_session_id, "test_warning")
        self.assertIsInstance(result, bool)
    
    def test_input_sanitization(self):
        """Test that inputs are properly sanitized."""
        malicious_inputs = [
            {"command": "rm -rf /"},
            {"command": "; cat /etc/passwd"},
            {"file_path": "../../../sensitive_file"},
            {"pattern": "$(malicious_command)"},
        ]
        
        feedback_system = EducationalFeedbackSystem()
        
        for malicious_input in malicious_inputs:
            # Should not raise exceptions or execute malicious code
            try:
                result = feedback_system.provide_educational_feedback(
                    "Bash",
                    malicious_input,
                    "safe response",
                    self.test_session_id
                )
                # Should return None or safe feedback
                if result:
                    self.assertIsInstance(result, str)
            except Exception as e:
                # Should handle gracefully
                self.assertNotIn("malicious", str(e).lower())
    
    def test_session_isolation(self):
        """Test that sessions are properly isolated."""
        tracker = SessionWarningTracker()
        
        # Create warnings for different sessions
        session1 = "session_1"
        session2 = "session_2"
        warning_type = "test_warning"
        
        # Mark warning for session 1
        tracker.mark_warning_shown(session1, warning_type)
        
        # Session 2 should not be affected
        self.assertTrue(tracker.should_show_warning(session2, warning_type))
        
        # Session 1 should be affected
        self.assertFalse(tracker.has_shown_warning(session1, warning_type))
    
    def test_json_injection_safety(self):
        """Test safety against JSON injection attacks."""
        malicious_json_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": '"; eval(malicious_code); "'
            },
            "session_id": "'; DROP TABLE sessions; --"
        }
        
        # Should handle malicious JSON safely
        result = handle_educational_feedback(malicious_json_data)
        self.assertEqual(result, 0)  # Should not crash


class IntegrationTestCase(unittest.TestCase):
    """Integration testing for hook system components."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = TemporaryDirectory()
        self.test_session_id = "integration_test_session"
    
    def tearDown(self):
        """Clean up integration test environment."""
        self.temp_dir.cleanup()
    
    @patch('sys.stderr')
    def test_full_hook_integration(self, mock_stderr):
        """Test complete hook integration workflow."""
        test_data = TestDataFactory.create_bash_operation("grep -r 'pattern' /large/dir")
        
        # Test full hook handler
        result = handle_educational_feedback(test_data)
        
        # Should complete successfully
        self.assertEqual(result, 0)
        
        # Should output feedback to stderr
        mock_stderr.write.assert_called()
    
    def test_shared_intelligence_integration(self):
        """Test integration between shared intelligence components."""
        context = TestDataFactory.create_context([
            {"tool_name": "Read", "timestamp": time.time() - 60},
            {"tool_name": "Read", "timestamp": time.time() - 30},
        ])
        
        test_data = TestDataFactory.create_file_operation("Read", "/test/file.py")
        
        # Test that components work together
        routing_result = analyze_tool_for_routing(
            test_data["tool_name"],
            test_data["tool_input"],
            context
        )
        
        pattern_result = analyze_workflow_patterns(
            test_data["tool_name"],
            test_data["tool_input"],
            context
        )
        
        # Should return valid results
        self.assertIsInstance(routing_result, tuple)
        self.assertIsInstance(pattern_result, tuple)
        self.assertEqual(len(routing_result), 4)
        self.assertEqual(len(pattern_result), 4)
    
    def test_session_tracker_persistence(self):
        """Test session tracker persistence across instances."""
        storage_path = os.path.join(self.temp_dir.name, "test_warnings.json")
        
        # Create first tracker instance
        tracker1 = SessionWarningTracker(storage_path=storage_path)
        tracker1.mark_warning_shown(self.test_session_id, "persistent_warning")
        
        # Create second tracker instance
        tracker2 = SessionWarningTracker(storage_path=storage_path)
        
        # Should load persistent data
        self.assertTrue(tracker2.has_shown_warning(self.test_session_id, "persistent_warning"))


class UnitTestCase(unittest.TestCase):
    """Unit tests for individual components."""
    
    def setUp(self):
        """Set up unit test environment."""
        self.mock_session_tracker = MockSessionTracker()
        self.test_session_id = "unit_test_session"
    
    def test_educational_feedback_system_initialization(self):
        """Test educational feedback system initializes correctly."""
        system = EducationalFeedbackSystem()
        
        self.assertIsNotNone(system.session_tracker)
        self.assertEqual(system.max_execution_time, 0.1)
    
    def test_feedback_message_generation(self):
        """Test feedback message generation for different tools."""
        system = EducationalFeedbackSystem()
        
        test_cases = [
            ("Bash", {"command": "grep -r 'pattern' ."}, "Command executed"),
            ("Read", {"file_path": "/test/file.py"}, "File content"),
            ("Edit", {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"}, "File edited"),
        ]
        
        for tool_name, tool_input, tool_response in test_cases:
            with patch.object(system, 'session_tracker', self.mock_session_tracker):
                feedback = system.provide_educational_feedback(
                    tool_name, tool_input, tool_response, self.test_session_id
                )
                
                # Should generate some feedback or None
                self.assertIsInstance(feedback, (str, type(None)))
    
    def test_context_building(self):
        """Test enhanced context building."""
        system = EducationalFeedbackSystem()
        
        context = system._build_enhanced_context(
            self.test_session_id, "Read", {"file_path": "/test/file.py"}
        )
        
        self.assertIn("session_info", context)
        self.assertIn("recent_operations", context)
        self.assertIsInstance(context["recent_operations"], list)
    
    def test_session_tracker_warning_logic(self):
        """Test session tracker warning logic."""
        tracker = SessionWarningTracker()
        
        # First call should show warning
        self.assertTrue(tracker.should_show_warning(self.test_session_id, "test_warning"))
        
        # Second call should not show warning
        self.assertFalse(tracker.should_show_warning(self.test_session_id, "test_warning"))
        
        # Different warning type should show
        self.assertTrue(tracker.should_show_warning(self.test_session_id, "different_warning"))
    
    def test_session_id_extraction(self):
        """Test session ID extraction from various data formats."""
        test_cases = [
            ({"session_id": "explicit_session"}, "explicit_session"),
            ({"conversation_id": "conv_123"}, "conv_123"),
            ({"tool_name": "Read"}, "Read_"),  # Will include timestamp
            ({}, "unknown_"),  # Will include timestamp
        ]
        
        for data, expected_prefix in test_cases:
            session_id = extract_session_id(data)
            self.assertIsInstance(session_id, str)
            if expected_prefix != "unknown_" and expected_prefix != "Read_":
                self.assertEqual(session_id, expected_prefix)
            else:
                self.assertTrue(session_id.startswith(expected_prefix.split("_")[0]))


class EdgeCaseTestCase(unittest.TestCase):
    """Edge case and error handling tests."""
    
    def test_empty_data_handling(self):
        """Test handling of empty or malformed data."""
        edge_cases = [
            {},
            {"tool_name": ""},
            {"tool_name": None},
            {"tool_name": "Read", "tool_input": None},
            {"tool_name": "Read", "tool_input": {}, "tool_response": None},
        ]
        
        for data in edge_cases:
            # Should not raise exceptions
            result = handle_educational_feedback(data)
            self.assertEqual(result, 0)
    
    def test_large_data_handling(self):
        """Test handling of large data volumes."""
        # Create large tool response
        large_response = "x" * 100000  # 100KB response
        
        test_data = TestDataFactory.create_bash_operation("large_command")
        test_data["tool_response"] = large_response
        
        # Should handle large data gracefully
        result = handle_educational_feedback(test_data)
        self.assertEqual(result, 0)
    
    def test_unicode_handling(self):
        """Test handling of unicode and special characters."""
        unicode_data = TestDataFactory.create_bash_operation("echo '测试 🚀 émojis'")
        unicode_data["tool_response"] = "Unicode output: 测试 🚀 émojis"
        
        # Should handle unicode gracefully
        result = handle_educational_feedback(unicode_data)
        self.assertEqual(result, 0)
    
    def test_missing_shared_intelligence(self):
        """Test behavior when shared intelligence components are missing."""
        with patch('educational_feedback_enhanced.analyze_tool_for_routing', side_effect=ImportError):
            system = EducationalFeedbackSystem()
            
            feedback = system.provide_educational_feedback(
                "Bash", {"command": "test"}, "output", "session_test"
            )
            
            # Should handle missing components gracefully
            self.assertIsInstance(feedback, (str, type(None)))
    
    def test_concurrent_session_access(self):
        """Test concurrent access to session tracker."""
        tracker = SessionWarningTracker()
        
        def concurrent_access(session_suffix):
            session_id = f"concurrent_session_{session_suffix}"
            for i in range(10):
                tracker.should_show_warning(session_id, f"warning_{i}")
        
        # Run concurrent access
        import threading
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_access, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        stats = tracker.get_session_stats()
        self.assertGreater(stats["total_sessions"], 0)


class EndToEndTestCase(unittest.TestCase):
    """End-to-end workflow testing."""
    
    def setUp(self):
        """Set up E2E test environment."""
        self.temp_dir = TemporaryDirectory()
    
    def tearDown(self):
        """Clean up E2E test environment."""
        self.temp_dir.cleanup()
    
    @patch('sys.stderr')
    def test_complete_feedback_workflow(self, mock_stderr):
        """Test complete educational feedback workflow."""
        # Simulate user workflow: Read -> Edit -> Bash
        workflow_steps = [
            TestDataFactory.create_file_operation("Read", "/test/config.py"),
            TestDataFactory.create_file_operation("Edit", "/test/config.py", "updated content"),
            TestDataFactory.create_bash_operation("python -m pytest /test/"),
        ]
        
        session_id = "e2e_workflow_session"
        
        for step in workflow_steps:
            step["session_id"] = session_id
            result = handle_educational_feedback(step)
            self.assertEqual(result, 0)
        
        # Should have provided feedback
        self.assertTrue(mock_stderr.write.called)
    
    def test_performance_under_load(self):
        """Test system performance under realistic load."""
        operations_count = 100
        max_total_time = 5.0  # 5 seconds for 100 operations
        
        start_time = time.perf_counter()
        
        for i in range(operations_count):
            test_data = TestDataFactory.create_bash_operation(f"command_{i}")
            result = handle_educational_feedback(test_data)
            self.assertEqual(result, 0)
        
        total_time = time.perf_counter() - start_time
        
        self.assertLess(
            total_time, 
            max_total_time,
            f"System too slow under load: {total_time:.3f}s for {operations_count} operations"
        )
    
    def test_session_boundary_behavior(self):
        """Test behavior across session boundaries."""
        # Create operations in different sessions
        sessions = ["session_1", "session_2", "session_3"]
        
        for session in sessions:
            test_data = TestDataFactory.create_bash_operation("repeated_command")
            test_data["session_id"] = session
            
            result = handle_educational_feedback(test_data)
            self.assertEqual(result, 0)
        
        # Each session should be independent
        tracker = get_session_tracker()
        
        for session in sessions:
            # Should have independent warning states
            stats = tracker.get_session_stats()
            self.assertGreater(stats["total_sessions"], 0)


def run_test_suite():
    """Run the complete test suite with detailed reporting."""
    # Create test loader
    loader = unittest.TestLoader()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test cases
    test_cases = [
        UnitTestCase,
        IntegrationTestCase,
        PerformanceTestCase,
        SecurityTestCase,
        EdgeCaseTestCase,
        EndToEndTestCase,
    ]
    
    for test_case in test_cases:
        suite.addTests(loader.loadTestsFromTestCase(test_case))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("=" * 80)
    print("PostToolUse Educational Feedback System - Test Suite")
    print("=" * 80)
    print()
    
    start_time = time.perf_counter()
    result = runner.run(suite)
    execution_time = time.perf_counter() - start_time
    
    print()
    print("=" * 80)
    print(f"Test Suite Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Execution time: {execution_time:.3f}s")
    print(f"  Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the test suite
    success = run_test_suite()
    sys.exit(0 if success else 1)