#!/usr/bin/env python3
"""Test runner for UserPromptSubmit hook handler comprehensive test suite.

This script runs all test categories with appropriate configuration:
- Core functionality tests
- Integration tests  
- Security tests
- Performance tests

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --core             # Run only core tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --security         # Run only security tests
    python run_tests.py --performance      # Run only performance tests
    python run_tests.py --fast             # Skip slow tests
    python run_tests.py --coverage         # Include coverage report
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode != 0:
            print(f"❌ Command failed with exit code {result.returncode}")
            return False
        else:
            print("✅ Command completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run UserPromptSubmit test suite")
    parser.add_argument("--core", action="store_true", help="Run only core functionality tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--security", action="store_true", help="Run only security tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--coverage", action="store_true", help="Include coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop on first failure")
    
    args = parser.parse_args()
    
    # Determine which tests to run
    test_files = []
    
    if args.core or not any([args.integration, args.security, args.performance]):
        test_files.append("test_userpromptsubmit_core.py")
    
    if args.integration or not any([args.core, args.security, args.performance]):
        test_files.append("test_userpromptsubmit_integration.py")
    
    if args.security or not any([args.core, args.integration, args.performance]):
        test_files.append("test_userpromptsubmit_security.py")
    
    if args.performance or not any([args.core, args.integration, args.security]):
        test_files.append("test_userpromptsubmit_performance.py")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test files
    cmd.extend(test_files)
    
    # Add pytest options
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if args.failfast:
        cmd.append("-x")
    
    # Add markers for fast tests
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=70"
        ])
    
    # Additional pytest options for better output
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    # Change to the test directory
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    print(f"Running tests in directory: {test_dir}")
    print(f"Test files: {', '.join(test_files)}")
    
    # Run the tests
    success = run_command(cmd, "UserPromptSubmit Test Suite")
    
    if success:
        print(f"\n🎉 All tests passed successfully!")
        
        if args.coverage:
            print("\n📊 Coverage report generated in htmlcov/ directory")
            coverage_file = test_dir / "htmlcov" / "index.html"
            if coverage_file.exists():
                print(f"   Open: file://{coverage_file}")
        
        return 0
    else:
        print(f"\n💥 Some tests failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())