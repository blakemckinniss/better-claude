#!/usr/bin/env python3
"""Performance tests to validate <100ms requirement for PostToolUse educational feedback."""

import asyncio
import concurrent.futures
import json
import statistics
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
import unittest

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "shared_intelligence"))

from educational_feedback_enhanced import EducationalFeedbackSystem, handle_educational_feedback
from session_tracker import SessionWarningTracker
from intelligent_router import analyze_tool_for_routing
from anti_pattern_detector import analyze_workflow_patterns
from performance_optimizer import check_performance_optimization
from recommendation_engine import get_tool_recommendations


class PerformanceBenchmark:
    """Performance benchmarking utilities."""
    
    def __init__(self, max_execution_time: float = 0.1):
        self.max_execution_time = max_execution_time
        self.measurements: List[float] = []
    
    def measure_execution(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure function execution time with high precision."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        execution_time = time.perf_counter() - start_time
        self.measurements.append(execution_time)
        return result, execution_time
    
    def get_statistics(self) -> Dict[str, float]:
        """Get performance statistics."""
        if not self.measurements:
            return {}
        
        return {
            "mean": statistics.mean(self.measurements),
            "median": statistics.median(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements),
            "std_dev": statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0,
            "p95": statistics.quantiles(self.measurements, n=20)[18] if len(self.measurements) >= 20 else max(self.measurements),
            "p99": statistics.quantiles(self.measurements, n=100)[98] if len(self.measurements) >= 100 else max(self.measurements),
        }
    
    def reset(self):
        """Reset measurements."""
        self.measurements = []
    
    def assert_performance_requirements(self, test_case: unittest.TestCase, operation_name: str):
        """Assert that performance requirements are met."""
        stats = self.get_statistics()
        
        if not stats:
            test_case.fail(f"No measurements for {operation_name}")
        
        # Mean execution time should be well below limit
        test_case.assertLess(
            stats["mean"],
            self.max_execution_time,
            f"{operation_name} mean execution time {stats['mean']:.3f}s exceeds {self.max_execution_time}s limit"
        )
        
        # 95th percentile should also be below limit for consistent performance
        test_case.assertLess(
            stats["p95"],
            self.max_execution_time * 1.5,  # Allow some variance
            f"{operation_name} p95 execution time {stats['p95']:.3f}s exceeds acceptable variance"
        )
        
        print(f"\n{operation_name} Performance Stats:")
        print(f"  Mean: {stats['mean']:.3f}s")
        print(f"  Median: {stats['median']:.3f}s")
        print(f"  Min: {stats['min']:.3f}s")
        print(f"  Max: {stats['max']:.3f}s")
        print(f"  P95: {stats['p95']:.3f}s")
        print(f"  Std Dev: {stats['std_dev']:.3f}s")


class TestDataGenerator:
    """Generate test data for performance testing."""
    
    @staticmethod
    def generate_tool_scenarios() -> List[Dict[str, Any]]:
        """Generate various tool usage scenarios."""
        return [
            # Simple read operations
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/simple/file.py"},
                "tool_response": "Simple file content",
                "session_id": "perf_session_1"
            },
            
            # Complex bash operations
            {
                "tool_name": "Bash",
                "tool_input": {"command": "find . -name '*.py' | xargs grep -l 'class' | head -10"},
                "tool_response": "Command executed successfully",
                "session_id": "perf_session_2"
            },
            
            # File editing operations
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/complex/module.py",
                    "old_string": "old_implementation",
                    "new_string": "new_implementation"
                },
                "tool_response": "File edited successfully",
                "session_id": "perf_session_3"
            },
            
            # Multi-edit operations
            {
                "tool_name": "MultiEdit",
                "tool_input": {
                    "file_path": "/large/file.py",
                    "edits": [
                        {"old_string": "old1", "new_string": "new1"},
                        {"old_string": "old2", "new_string": "new2"},
                        {"old_string": "old3", "new_string": "new3"}
                    ]
                },
                "tool_response": "Multiple edits applied",
                "session_id": "perf_session_4"
            },
            
            # Search operations
            {
                "tool_name": "Grep",
                "tool_input": {
                    "pattern": "complex.*regex.*pattern.*with.*multiple.*groups",
                    "path": "/large/codebase",
                    "glob": "*.py"
                },
                "tool_response": "Search completed: 42 matches found",
                "session_id": "perf_session_5"
            },
            
            # MCP operations
            {
                "tool_name": "mcp__filesystem__read_multiple_files",
                "tool_input": {
                    "file_paths": ["/file1.py", "/file2.py", "/file3.py"]
                },
                "tool_response": "Multiple files read successfully",
                "session_id": "perf_session_6"
            }
        ]
    
    @staticmethod
    def generate_context_with_history(operations_count: int = 10) -> Dict[str, Any]:
        """Generate context with operation history."""
        recent_operations = []
        
        for i in range(operations_count):
            recent_operations.append({
                "tool_name": ["Read", "Edit", "Bash", "Grep"][i % 4],
                "timestamp": time.time() - (i * 30),
                "details": f"operation_{i}"
            })
        
        return {
            "session_info": "performance_test_session",
            "recent_operations": recent_operations
        }


class CorePerformanceTestCase(unittest.TestCase):
    """Test core component performance requirements."""
    
    def setUp(self):
        """Set up performance testing environment."""
        self.benchmark = PerformanceBenchmark(max_execution_time=0.1)
        self.feedback_system = EducationalFeedbackSystem()
        self.test_iterations = 100
    
    def test_educational_feedback_system_performance(self):
        """Test educational feedback system meets performance requirements."""
        scenarios = TestDataGenerator.generate_tool_scenarios()
        
        for scenario in scenarios:
            for _ in range(self.test_iterations):
                result, exec_time = self.benchmark.measure_execution(
                    self.feedback_system.provide_educational_feedback,
                    scenario["tool_name"],
                    scenario["tool_input"],
                    scenario["tool_response"],
                    scenario["session_id"]
                )
        
        self.benchmark.assert_performance_requirements(self, "Educational Feedback System")
    
    def test_session_tracker_performance(self):
        """Test session tracker performance."""
        tracker = SessionWarningTracker()
        
        for i in range(self.test_iterations):
            session_id = f"perf_session_{i % 10}"  # 10 different sessions
            warning_type = f"warning_type_{i % 5}"  # 5 different warning types
            
            # Test warning check
            result, exec_time = self.benchmark.measure_execution(
                tracker.should_show_warning,
                session_id,
                warning_type
            )
        
        self.benchmark.assert_performance_requirements(self, "Session Tracker")
    
    def test_shared_intelligence_components_performance(self):
        """Test shared intelligence components performance."""
        scenarios = TestDataGenerator.generate_tool_scenarios()
        context = TestDataGenerator.generate_context_with_history()
        
        components = [
            ("Intelligent Router", analyze_tool_for_routing),
            ("Anti-Pattern Detector", analyze_workflow_patterns),
            ("Performance Optimizer", check_performance_optimization),
            ("Recommendation Engine", get_tool_recommendations),
        ]
        
        for component_name, component_func in components:
            self.benchmark.reset()
            
            for scenario in scenarios:
                for _ in range(20):  # Test each scenario 20 times
                    result, exec_time = self.benchmark.measure_execution(
                        component_func,
                        scenario["tool_name"],
                        scenario["tool_input"],
                        context
                    )
            
            self.benchmark.assert_performance_requirements(self, component_name)
    
    def test_full_hook_handler_performance(self):
        """Test complete hook handler performance."""
        scenarios = TestDataGenerator.generate_tool_scenarios()
        
        for scenario in scenarios:
            for _ in range(50):  # Test each scenario 50 times
                result, exec_time = self.benchmark.measure_execution(
                    handle_educational_feedback,
                    scenario
                )
        
        self.benchmark.assert_performance_requirements(self, "Full Hook Handler")


class LoadTestCase(unittest.TestCase):
    """Test performance under various load conditions."""
    
    def setUp(self):
        """Set up load testing environment."""
        self.benchmark = PerformanceBenchmark(max_execution_time=0.1)
    
    def test_concurrent_requests_performance(self):
        """Test performance under concurrent load."""
        scenarios = TestDataGenerator.generate_tool_scenarios()
        
        def process_scenario(scenario):
            start_time = time.perf_counter()
            result = handle_educational_feedback(scenario)
            execution_time = time.perf_counter() - start_time
            return result, execution_time
        
        # Test with different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        
        for concurrency in concurrency_levels:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                # Submit concurrent tasks
                futures = []
                start_time = time.perf_counter()
                
                for _ in range(concurrency * 5):  # 5 requests per worker
                    scenario = scenarios[_ % len(scenarios)]
                    future = executor.submit(process_scenario, scenario)
                    futures.append(future)
                
                # Wait for completion and collect results
                execution_times = []
                for future in concurrent.futures.as_completed(futures):
                    result, exec_time = future.result()
                    execution_times.append(exec_time)
                
                total_time = time.perf_counter() - start_time
                
                # Performance assertions
                avg_execution_time = sum(execution_times) / len(execution_times)
                max_execution_time = max(execution_times)
                
                self.assertLess(
                    avg_execution_time,
                    0.1,
                    f"Average execution time {avg_execution_time:.3f}s too high with {concurrency} concurrent requests"
                )
                
                self.assertLess(
                    max_execution_time,
                    0.2,
                    f"Max execution time {max_execution_time:.3f}s too high with {concurrency} concurrent requests"
                )
                
                throughput = len(futures) / total_time
                print(f"\nConcurrency {concurrency}: {throughput:.1f} requests/second")
    
    def test_memory_usage_under_load(self):
        """Test memory usage remains stable under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        scenarios = TestDataGenerator.generate_tool_scenarios()
        
        # Run many iterations
        for i in range(1000):
            scenario = scenarios[i % len(scenarios)]
            handle_educational_feedback(scenario)
            
            # Check memory every 100 iterations
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                self.assertLess(
                    memory_growth,
                    50,  # Max 50MB growth
                    f"Memory usage grew by {memory_growth:.1f}MB after {i} iterations"
                )
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"\nMemory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{total_growth:.1f}MB)")
    
    def test_session_scalability(self):
        """Test performance with many concurrent sessions."""
        tracker = SessionWarningTracker()
        
        # Simulate many sessions
        session_count = 1000
        warnings_per_session = 10
        
        start_time = time.perf_counter()
        
        for session_id in range(session_count):
            for warning_id in range(warnings_per_session):
                tracker.should_show_warning(f"session_{session_id}", f"warning_{warning_id}")
        
        total_time = time.perf_counter() - start_time
        operations = session_count * warnings_per_session
        avg_time_per_op = total_time / operations
        
        self.assertLess(
            avg_time_per_op,
            0.001,  # 1ms per operation
            f"Session tracker too slow: {avg_time_per_op:.4f}s per operation"
        )
        
        print(f"\nSession scalability: {operations} operations in {total_time:.3f}s ({avg_time_per_op*1000:.2f}ms/op)")


class RegressionTestCase(unittest.TestCase):
    """Test for performance regressions."""
    
    def setUp(self):
        """Set up regression testing."""
        self.benchmark = PerformanceBenchmark()
        self.baseline_file = Path(__file__).parent / "performance_baseline.json"
    
    def load_baseline(self) -> Dict[str, float]:
        """Load performance baseline data."""
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                return json.load(f)
        return {}
    
    def save_baseline(self, measurements: Dict[str, float]):
        """Save performance baseline data."""
        with open(self.baseline_file, 'w') as f:
            json.dump(measurements, f, indent=2)
    
    def test_performance_regression(self):
        """Test for performance regressions against baseline."""
        baseline = self.load_baseline()
        current_measurements = {}
        
        # Test core operations
        test_operations = [
            ("feedback_generation", self._measure_feedback_generation),
            ("session_tracking", self._measure_session_tracking),
            ("intelligence_analysis", self._measure_intelligence_analysis),
        ]
        
        for operation_name, measure_func in test_operations:
            avg_time = measure_func()
            current_measurements[operation_name] = avg_time
            
            if operation_name in baseline:
                baseline_time = baseline[operation_name]
                regression_threshold = baseline_time * 1.2  # 20% regression threshold
                
                self.assertLess(
                    avg_time,
                    regression_threshold,
                    f"Performance regression detected in {operation_name}: "
                    f"{avg_time:.3f}s vs baseline {baseline_time:.3f}s "
                    f"(>{((avg_time/baseline_time-1)*100):.1f}% slower)"
                )
            
            print(f"{operation_name}: {avg_time:.3f}s")
        
        # Update baseline with current measurements
        self.save_baseline(current_measurements)
    
    def _measure_feedback_generation(self) -> float:
        """Measure feedback generation performance."""
        feedback_system = EducationalFeedbackSystem()
        measurements = []
        
        for _ in range(100):
            start_time = time.perf_counter()
            feedback_system.provide_educational_feedback(
                "Bash",
                {"command": "grep -r 'pattern' ."},
                "Command output",
                "regression_test_session"
            )
            execution_time = time.perf_counter() - start_time
            measurements.append(execution_time)
        
        return statistics.mean(measurements)
    
    def _measure_session_tracking(self) -> float:
        """Measure session tracking performance."""
        tracker = SessionWarningTracker()
        measurements = []
        
        for i in range(100):
            start_time = time.perf_counter()
            tracker.should_show_warning(f"session_{i%10}", f"warning_{i%5}")
            execution_time = time.perf_counter() - start_time
            measurements.append(execution_time)
        
        return statistics.mean(measurements)
    
    def _measure_intelligence_analysis(self) -> float:
        """Measure intelligence analysis performance."""
        context = TestDataGenerator.generate_context_with_history()
        measurements = []
        
        for _ in range(50):
            start_time = time.perf_counter()
            analyze_tool_for_routing("Bash", {"command": "test command"}, context)
            analyze_workflow_patterns("Bash", {"command": "test command"}, context)
            check_performance_optimization("Bash", {"command": "test command"}, context)
            get_tool_recommendations("Bash", {"command": "test command"}, context)
            execution_time = time.perf_counter() - start_time
            measurements.append(execution_time)
        
        return statistics.mean(measurements)


def run_performance_tests():
    """Run the complete performance test suite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_cases = [
        CorePerformanceTestCase,
        LoadTestCase,
        RegressionTestCase,
    ]
    
    for test_case in test_cases:
        suite.addTests(loader.loadTestsFromTestCase(test_case))
    
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("=" * 80)
    print("PostToolUse Educational Feedback - Performance Test Suite")
    print("Target: <100ms per operation")
    print("=" * 80)
    
    start_time = time.perf_counter()
    result = runner.run(suite)
    total_execution_time = time.perf_counter() - start_time
    
    print(f"\nTotal test execution time: {total_execution_time:.3f}s")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)