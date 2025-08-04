#!/usr/bin/env python3
"""
Comprehensive Testing Framework for Educational Feedback System.

Tests all implementations:
- Original enhanced version (with security fixes)
- Performance optimized version 
- Service layer architecture version
"""

import unittest
import sys
import json
import time
import tempfile
import io
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the modules to test
try:
    from . import educational_feedback_enhanced
    from . import performance_optimized_feedback
    from . import feedback_service_layer
except ImportError:
    # Direct execution fallback
    import educational_feedback_enhanced
    import performance_optimized_feedback
    import feedback_service_layer


class TestEducationalFeedbackEnhanced(unittest.TestCase):
    """Test suite for the enhanced educational feedback system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": "File content here",
            "session_id": "test_session_123"
        }
    
    def test_handle_educational_feedback_success(self):
        """Test successful feedback generation."""
        result = educational_feedback_enhanced.handle_educational_feedback(self.test_data)
        self.assertEqual(result, 0)
    
    def test_handle_educational_feedback_empty_tool_name(self):
        """Test handling of empty tool name."""
        data = self.test_data.copy()
        data["tool_name"] = ""
        
        result = educational_feedback_enhanced.handle_educational_feedback(data)
        self.assertEqual(result, 0)
    
    def test_feedback_system_initialization(self):
        """Test feedback system can be initialized."""
        system = educational_feedback_enhanced.EducationalFeedbackSystem()
        self.assertIsNotNone(system)
        self.assertIsNotNone(system.session_tracker)
    
    def test_error_response_feedback(self):
        """Test feedback generation for error responses."""
        system = educational_feedback_enhanced.EducationalFeedbackSystem()
        
        # Test with error response (use unique session ID for test isolation)
        error_data = self.test_data.copy()
        error_data["tool_response"] = "Error: File not found"
        error_data["session_id"] = f"error_test_session_{hash('error_test') % 10000}"
        
        feedback = system._get_response_feedback(
            error_data["tool_name"], 
            error_data["tool_response"], 
            error_data["session_id"]
        )
        
        # Should generate error learning feedback
        self.assertIsNotNone(feedback)
        self.assertIn("LEARNING OPPORTUNITY", feedback)
    
    def test_large_output_feedback(self):
        """Test feedback for large outputs."""
        system = educational_feedback_enhanced.EducationalFeedbackSystem()
        
        # Create large response (use unique session ID for test isolation)
        large_response = "x" * 6000
        unique_session_id = f"large_output_test_session_{hash('large_output_test') % 10000}"
        
        feedback = system._get_response_feedback(
            "Read", 
            large_response, 
            unique_session_id
        )
        
        self.assertIsNotNone(feedback)
        self.assertIn("LARGE OUTPUT", feedback)
    
    def test_context_building_security_fix(self):
        """Test that context building uses real timestamps."""
        system = educational_feedback_enhanced.EducationalFeedbackSystem()
        
        context = system._build_enhanced_context("test_session", "Read", {})
        
        # Check that we have real timestamp data
        self.assertIn("recent_operations", context)
        # Should not have fake calculated timestamps
        for op in context["recent_operations"]:
            if "timestamp" in op:
                # Should be close to current time (within 1 second)
                time_diff = abs(time.time() - op["timestamp"])
                self.assertLess(time_diff, 1.0)


class TestPerformanceOptimizedFeedback(unittest.TestCase):
    """Test suite for performance-optimized feedback system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": "File content here",
            "session_id": "test_session_123"
        }
    
    def test_ultra_fast_feedback_handler(self):
        """Test ultra-fast feedback handler."""
        result = performance_optimized_feedback.handle_ultra_fast_feedback(self.test_data)
        self.assertEqual(result, 0)
    
    def test_fast_error_detection(self):
        """Test fast error detection."""
        error_data = self.test_data.copy()
        error_data["tool_response"] = "Error: Something went wrong"
        
        feedback = performance_optimized_feedback.get_fast_feedback(
            error_data["tool_name"],
            error_data["tool_response"],
            error_data["session_id"]
        )
        
        self.assertIsNotNone(feedback)
        self.assertIn("Error detected", feedback)
    
    def test_fast_large_output_detection(self):
        """Test fast large output detection."""
        large_data = self.test_data.copy()
        large_data["tool_response"] = "x" * 6000
        
        feedback = performance_optimized_feedback.get_fast_feedback(
            large_data["tool_name"],
            large_data["tool_response"],
            large_data["session_id"]
        )
        
        self.assertIsNotNone(feedback)
        self.assertIn("Large output", feedback)
    
    def test_performance_timing(self):
        """Test that optimized version is fast."""
        start_time = time.time()
        
        # Run multiple iterations
        for _ in range(100):
            performance_optimized_feedback.handle_ultra_fast_feedback(self.test_data)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast - less than 100ms for 100 iterations
        self.assertLess(total_time, 0.1)
    
    def test_warning_caching(self):
        """Test that warning caching works correctly."""
        session_id = "cache_test_session"
        warning_type = "test_warning"
        
        # First call should return True
        result1 = performance_optimized_feedback.should_show_warning_cached(
            session_id, warning_type, 0
        )
        self.assertTrue(result1)
        
        # Subsequent calls with same parameters should use cache
        result2 = performance_optimized_feedback.should_show_warning_cached(
            session_id, warning_type, 0
        )
        self.assertTrue(result2)


class TestServiceLayerFeedback(unittest.TestCase):
    """Test suite for service layer feedback architecture."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {
            "tool_name": "Read", 
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": "File content here",
            "session_id": "test_session_123"
        }
        
        # Create fresh service layer for each test
        self.controller = feedback_service_layer.create_feedback_system()
    
    def test_service_layer_creation(self):
        """Test service layer can be created."""
        controller = feedback_service_layer.create_feedback_system()
        self.assertIsNotNone(controller)
    
    def test_handle_feedback_request(self):
        """Test handling feedback request through service layer."""
        result = self.controller.handle_feedback_request(self.test_data)
        self.assertEqual(result, 0)
    
    def test_feedback_context_creation(self):
        """Test feedback context domain object."""
        context = feedback_service_layer.FeedbackContext(
            session_id="test",
            tool_name="Read",
            tool_input={},
            tool_response="test response"
        )
        
        self.assertEqual(context.session_id, "test")
        self.assertEqual(context.tool_name, "Read")
        self.assertIsNotNone(context.timestamp)
    
    def test_error_analyzer(self):
        """Test error feedback analyzer."""
        analyzer = feedback_service_layer.ErrorFeedbackAnalyzer()
        
        context = feedback_service_layer.FeedbackContext(
            session_id="test",
            tool_name="Read",
            tool_input={},
            tool_response="Error: File not found"
        )
        
        message = analyzer.analyze(context)
        self.assertIsNotNone(message)
        self.assertEqual(message.feedback_type, "error_learning")
        self.assertIn("Error detected", message.content)
    
    def test_large_output_analyzer(self):
        """Test large output analyzer."""
        analyzer = feedback_service_layer.LargeOutputFeedbackAnalyzer(size_threshold=100)
        
        context = feedback_service_layer.FeedbackContext(
            session_id="test",
            tool_name="Read",
            tool_input={},
            tool_response="x" * 200  # Large response
        )
        
        message = analyzer.analyze(context)
        self.assertIsNotNone(message)
        self.assertEqual(message.feedback_type, "large_output")
    
    def test_success_pattern_analyzer(self):
        """Test success pattern analyzer."""
        analyzer = feedback_service_layer.SuccessPatternAnalyzer()
        
        context = feedback_service_layer.FeedbackContext(
            session_id="test",
            tool_name="Read", 
            tool_input={},
            tool_response="Operation completed successfully"
        )
        
        message = analyzer.analyze(context)
        # May or may not return message due to random factor
        if message:
            self.assertEqual(message.feedback_type, "success_pattern")
    
    def test_session_repository(self):
        """Test session repository functionality."""
        repo = feedback_service_layer.InMemorySessionRepository()
        
        # Test initial state
        count = repo.get_warning_count("test_session", "test_warning")
        self.assertEqual(count, 0)
        
        # Test increment
        repo.increment_warning_count("test_session", "test_warning")
        count = repo.get_warning_count("test_session", "test_warning")
        self.assertEqual(count, 1)
        
        # Test should_show_warning logic
        should_show = repo.should_show_warning("new_session", "new_warning")
        self.assertTrue(should_show)  # First time should always show
    
    def test_feedback_service_integration(self):
        """Test complete feedback service integration."""
        repo = feedback_service_layer.InMemorySessionRepository()
        service = feedback_service_layer.FeedbackService(repo)
        
        context = feedback_service_layer.FeedbackContext(
            session_id="integration_test",
            tool_name="Read",
            tool_input={},
            tool_response="Error: Test error"
        )
        
        message = service.generate_feedback(context)
        self.assertIsNotNone(message)
        
        # Check that warning was recorded
        count = repo.get_warning_count("integration_test", "error_learning")
        self.assertEqual(count, 1)


class TestIntegrationAndPerformance(unittest.TestCase):
    """Integration tests and performance comparisons."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": "File content here",
            "session_id": "integration_test_session"
        }
    
    def test_all_implementations_work(self):
        """Test that all implementations handle the same input."""
        # Test enhanced version
        result1 = educational_feedback_enhanced.handle_educational_feedback(self.test_data)
        self.assertEqual(result1, 0)
        
        # Test performance version
        result2 = performance_optimized_feedback.handle_ultra_fast_feedback(self.test_data)
        self.assertEqual(result2, 0)
        
        # Test service layer version
        result3 = feedback_service_layer.handle_service_layer_feedback(self.test_data)
        self.assertEqual(result3, 0)
    
    def test_error_handling_consistency(self):
        """Test that all implementations handle errors gracefully."""
        error_data = self.test_data.copy()
        error_data["tool_response"] = "Error: Test error message"
        
        # All should return 0 (no blocking)
        result1 = educational_feedback_enhanced.handle_educational_feedback(error_data)
        result2 = performance_optimized_feedback.handle_ultra_fast_feedback(error_data)
        result3 = feedback_service_layer.handle_service_layer_feedback(error_data)
        
        self.assertEqual(result1, 0)
        self.assertEqual(result2, 0)
        self.assertEqual(result3, 0)
    
    def test_malformed_input_handling(self):
        """Test handling of malformed input data."""
        malformed_data = {"invalid": "data"}
        
        # All implementations should handle gracefully
        result1 = educational_feedback_enhanced.handle_educational_feedback(malformed_data)
        result2 = performance_optimized_feedback.handle_ultra_fast_feedback(malformed_data)
        result3 = feedback_service_layer.handle_service_layer_feedback(malformed_data)
        
        self.assertEqual(result1, 0)
        self.assertEqual(result2, 0)
        self.assertEqual(result3, 0)
    
    def test_performance_comparison(self):
        """Compare performance of different implementations."""
        iterations = 1000
        
        # Test enhanced version
        start = time.time()
        for _ in range(iterations):
            educational_feedback_enhanced.handle_educational_feedback(self.test_data)
        enhanced_time = time.time() - start
        
        # Test performance version
        start = time.time()
        for _ in range(iterations):
            performance_optimized_feedback.handle_ultra_fast_feedback(self.test_data)
        optimized_time = time.time() - start
        
        # Test service layer version
        start = time.time()
        for _ in range(iterations):
            feedback_service_layer.handle_service_layer_feedback(self.test_data)
        service_time = time.time() - start
        
        print(f"\nPerformance Comparison ({iterations} iterations):")
        print(f"Enhanced version: {enhanced_time:.4f}s")
        print(f"Optimized version: {optimized_time:.4f}s")
        print(f"Service layer version: {service_time:.4f}s")
        
        # Optimized version should be significantly faster
        self.assertLess(optimized_time, enhanced_time)
    
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_stderr_output_capture(self, mock_stderr):
        """Test that feedback is properly output to stderr."""
        error_data = self.test_data.copy()
        error_data["tool_response"] = "Error: Test error for stderr"
        
        # Run performance optimized version (most likely to generate output)
        performance_optimized_feedback.handle_ultra_fast_feedback(error_data)
        
        stderr_content = mock_stderr.getvalue()
        # Should have some output for error case
        self.assertTrue(len(stderr_content) > 0)


class TestSecurityImprovements(unittest.TestCase):
    """Test security improvements and fixes."""
    
    def test_no_sys_path_manipulation(self):
        """Test that sys.path is not manipulated dangerously."""
        # Check the enhanced version for secure imports
        import inspect
        
        # Get source code of the enhanced module
        source = inspect.getsource(educational_feedback_enhanced)
        
        # Should not contain dangerous sys.path.insert(0, ...) patterns
        self.assertNotIn("sys.path.insert(0,", source)
        
        # Should contain security comments
        self.assertIn("SECURITY FIX", source)
    
    def test_timestamp_authenticity(self):
        """Test that timestamps are real, not fake."""
        system = educational_feedback_enhanced.EducationalFeedbackSystem()
        
        before = time.time()
        context = system._build_enhanced_context("test", "Read", {})
        after = time.time()
        
        # Any timestamps in context should be between before and after
        for op in context.get("recent_operations", []):
            if "timestamp" in op:
                self.assertGreaterEqual(op["timestamp"], before)
                self.assertLessEqual(op["timestamp"], after)
            if "last_seen" in op:
                self.assertGreaterEqual(op["last_seen"], before)
                self.assertLessEqual(op["last_seen"], after)


def run_comprehensive_tests():
    """Run all tests with detailed output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEducationalFeedbackEnhanced,
        TestPerformanceOptimizedFeedback,
        TestServiceLayerFeedback,
        TestIntegrationAndPerformance,
        TestSecurityImprovements
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, error in result.failures:
            print(f"  - {test}: {error}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)