#!/usr/bin/env python3
"""Comprehensive test runner for PostToolUse educational feedback system."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import test modules
from test_framework import run_test_suite
from test_shared_intelligence import run_shared_intelligence_tests
from test_performance import run_performance_tests


class TestRunner:
    """Manages and executes comprehensive test suite."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "test_results"
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
    
    def run_test_category(self, category_name: str, test_function) -> bool:
        """Run a test category and capture results."""
        print(f"\n{'='*60}")
        print(f"Running {category_name} Tests")
        print(f"{'='*60}")
        
        start_time = time.perf_counter()
        
        # Capture stdout and stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Create output files
            stdout_file = self.output_dir / f"{category_name.lower().replace(' ', '_')}_stdout.log"
            stderr_file = self.output_dir / f"{category_name.lower().replace(' ', '_')}_stderr.log"
            
            with open(stdout_file, 'w') as stdout_capture, \
                 open(stderr_file, 'w') as stderr_capture:
                
                # Redirect output
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture
                
                # Run tests
                success = test_function()
                
        except Exception as e:
            print(f"ERROR: {category_name} tests failed with exception: {e}", file=original_stderr)
            success = False
        
        finally:
            # Restore output
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        execution_time = time.perf_counter() - start_time
        
        # Store results
        self.results[category_name] = {
            "success": success,
            "execution_time": execution_time,
            "stdout_file": str(stdout_file),
            "stderr_file": str(stderr_file)
        }
        
        # Print summary to console
        status = "PASSED" if success else "FAILED"
        print(f"{category_name}: {status} ({execution_time:.2f}s)")
        
        return success
    
    def generate_test_report(self) -> Dict:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result["success"])
        total_time = sum(result["execution_time"] for result in self.results.values())
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_categories": total_tests,
                "passed_categories": passed_tests,
                "failed_categories": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_execution_time": total_time
            },
            "categories": self.results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": str(Path.cwd()),
            }
        }
        
        return report
    
    def save_report(self, report: Dict):
        """Save test report to file."""
        report_file = self.output_dir / "test_report.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nTest report saved to: {report_file}")
    
    def print_summary(self, report: Dict):
        """Print test summary to console."""
        summary = report["summary"]
        
        print(f"\n{'='*80}")
        print("TEST SUITE SUMMARY")
        print(f"{'='*80}")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Categories: {summary['total_categories']}")
        print(f"Passed: {summary['passed_categories']}")
        print(f"Failed: {summary['failed_categories']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Time: {summary['total_execution_time']:.2f}s")
        
        print(f"\nCategory Results:")
        for category, result in report["categories"].items():
            status = "PASS" if result["success"] else "FAIL"
            print(f"  {category:<30} {status:>6} ({result['execution_time']:.2f}s)")
        
        print(f"\nOutput files in: {self.output_dir}")
        print(f"{'='*80}")
    
    def run_all_tests(self) -> bool:
        """Run all test categories."""
        test_categories = [
            ("Unit Tests", run_test_suite),
            ("Shared Intelligence Tests", run_shared_intelligence_tests),
            ("Performance Tests", run_performance_tests),
        ]
        
        all_passed = True
        
        for category_name, test_function in test_categories:
            success = self.run_test_category(category_name, test_function)
            if not success:
                all_passed = False
        
        # Generate and save report
        report = self.generate_test_report()
        self.save_report(report)
        self.print_summary(report)
        
        return all_passed


def create_test_configuration():
    """Create test configuration file."""
    config = {
        "performance_requirements": {
            "max_execution_time_ms": 100,
            "max_memory_growth_mb": 50,
            "max_concurrent_requests": 20
        },
        "test_data": {
            "iterations_per_test": 100,
            "concurrent_sessions": 1000,
            "test_file_sizes": [1024, 10240, 102400]  # 1KB, 10KB, 100KB
        },
        "coverage_requirements": {
            "minimum_line_coverage": 80,
            "minimum_branch_coverage": 75,
            "minimum_function_coverage": 90
        },
        "security_tests": {
            "test_malicious_inputs": true,
            "test_session_isolation": true,
            "test_file_safety": true,
            "test_injection_attacks": true
        },
        "integration_tests": {
            "test_hook_integration": true,
            "test_shared_intelligence": true,
            "test_session_persistence": true
        }
    }
    
    config_file = Path(__file__).parent / "test_config.json"
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Test configuration created: {config_file}")
    return config_file


def run_specific_test_category(category: str) -> bool:
    """Run a specific test category."""
    test_functions = {
        "unit": run_test_suite,
        "intelligence": run_shared_intelligence_tests,
        "performance": run_performance_tests,
    }
    
    if category not in test_functions:
        print(f"Unknown test category: {category}")
        print(f"Available categories: {', '.join(test_functions.keys())}")
        return False
    
    runner = TestRunner()
    return runner.run_test_category(f"{category.title()} Tests", test_functions[category])


def validate_system_requirements():
    """Validate system requirements for testing."""
    print("Validating system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        return False
    
    # Check required modules
    required_modules = [
        "unittest", "json", "time", "pathlib", "threading",
        "concurrent.futures", "statistics", "asyncio"
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"ERROR: Missing required modules: {', '.join(missing_modules)}")
        return False
    
    # Check available memory (rough estimate)
    try:
        import psutil
        available_memory = psutil.virtual_memory().available / 1024 / 1024  # MB
        if available_memory < 512:  # 512MB minimum
            print(f"WARNING: Low available memory: {available_memory:.0f}MB")
    except ImportError:
        print("WARNING: psutil not available, cannot check memory")
    
    print("System requirements validated successfully")
    return True


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for PostToolUse educational feedback system"
    )
    
    parser.add_argument(
        "--category",
        choices=["unit", "intelligence", "performance", "all"],
        default="all",
        help="Test category to run"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory for test output files"
    )
    
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create test configuration file"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate system requirements"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set environment variables for testing
    os.environ["TESTING"] = "1"
    if args.verbose:
        os.environ["DEBUG_HOOKS"] = "1"
    
    # Validate system requirements
    if not validate_system_requirements():
        sys.exit(1)
    
    if args.validate_only:
        print("System validation completed successfully")
        sys.exit(0)
    
    # Create configuration if requested
    if args.create_config:
        create_test_configuration()
        if args.category == "all":  # Don't run tests if only creating config
            sys.exit(0)
    
    # Run tests
    if args.category == "all":
        runner = TestRunner(args.output_dir)
        success = runner.run_all_tests()
    else:
        success = run_specific_test_category(args.category)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()