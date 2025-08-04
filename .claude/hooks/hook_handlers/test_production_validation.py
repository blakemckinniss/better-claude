#!/usr/bin/env python3
"""Production Validation Test Suite for Refactored Hook Architecture.

Validates:
1. PreToolUse security blocking functionality
2. PostToolUse educational feedback via stderr + exit(2)
3. shared_intelligence component integration
4. Performance benchmarks
5. Hook Contract compliance
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


class HookTester:
    """Comprehensive hook testing framework."""
    
    def __init__(self):
        self.hook_dir = Path(__file__).parent
        self.pretool_hook = self.hook_dir / "PreToolUse.py"
        self.posttool_hook = self.hook_dir / "PostToolUse" / "__init__.py"
        self.results: List[Dict[str, Any]] = []
        self.temp_files: List[str] = []
    
    def cleanup(self):
        """Clean up temporary test files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except OSError:
                pass
    
    def run_hook(self, hook_path: Path, event_data: Dict[str, Any]) -> Tuple[int, str, str, float]:
        """Run hook with event data and return exit code, stdout, stderr,
        execution_time."""
        start_time = time.perf_counter()
        
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(event_data),
            text=True,
            capture_output=True,
            timeout=5,  # 5 second timeout for tests
        )
        
        execution_time = (time.perf_counter() - start_time) * 1000  # ms
        
        return result.returncode, result.stdout, result.stderr, execution_time
    
    def test_pretool_security_blocking(self) -> List[Dict[str, Any]]:
        """Test PreToolUse security blocking functionality."""
        test_results = []
        
        # Test 1: Destructive edit blocking
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Original content\n" * 100)  # Large file
            temp_file = f.name
            self.temp_files.append(temp_file)
        
        event_data = {
            "session_id": "test-session",
            "tool_name": "Write",
            "tool_input": {
                "file_path": temp_file,
                "content": "small content",  # Much smaller
            },
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.pretool_hook, event_data)
        
        test_results.append({
            "test": "destructive_edit_blocking",
            "passed": exit_code == 2 and "DESTRUCTIVE EDIT BLOCKED" in stderr,
            "exit_code": exit_code,
            "stderr": stderr,
            "execution_time_ms": exec_time,
            "expected": "Should block destructive edits with exit code 2",
        })
        
        # Test 2: Technical debt filename blocking
        event_data = {
            "session_id": "test-session", 
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test_backup.py",
                "content": "new content",
            },
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.pretool_hook, event_data)
        
        test_results.append({
            "test": "technical_debt_blocking",
            "passed": exit_code == 2 and "TECHNICAL DEBT BLOCKED" in stderr,
            "exit_code": exit_code,
            "stderr": stderr,
            "execution_time_ms": exec_time,
            "expected": "Should block technical debt filenames with exit code 2",
        })
        
        # Test 3: Normal operation allowance
        event_data = {
            "session_id": "test-session",
            "tool_name": "Write", 
            "tool_input": {
                "file_path": "/tmp/normal_file.py",
                "content": "normal content",
            },
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.pretool_hook, event_data)
        
        test_results.append({
            "test": "normal_operation_allowance",
            "passed": exit_code == 0,
            "exit_code": exit_code,
            "stderr": stderr,
            "execution_time_ms": exec_time,
            "expected": "Should allow normal operations with exit code 0",
        })
        
        # Test 4: Performance benchmark (target <50ms)
        exec_times = [float(r["execution_time_ms"]) for r in test_results if "execution_time_ms" in r and isinstance(r["execution_time_ms"], (int, float))]
        avg_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
        test_results.append({
            "test": "performance_benchmark",
            "passed": avg_time < 50,
            "execution_time_ms": avg_time,
            "expected": "Average execution time should be <50ms",
        })
        
        return test_results
    
    def test_posttool_educational_feedback(self) -> List[Dict[str, Any]]:
        """Test PostToolUse educational feedback functionality."""
        test_results = []
        
        # Create a Python file with anti-patterns for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# Anti-pattern test file
def bad_function():
    # This has anti-patterns
    x = 1
    y = 2
    z = 3
    # Long function with many variables (anti-pattern)
    a = b = c = d = e = f = g = h = i = j = k = l = m = n = o = p = q = r = s = t = u = v = w = x = y = z = 1
    return x + y + z
""")
            temp_file = f.name
            self.temp_files.append(temp_file)
        
        # Test PostToolUse with file modification
        event_data = {
            "session_id": "test-session",
            "tool_name": "Write",
            "tool_input": {
                "file_path": temp_file,
            },
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.posttool_hook, event_data)
        
        test_results.append({
            "test": "educational_feedback_generation",
            "passed": len(stderr) > 0,  # Should provide feedback
            "exit_code": exit_code,
            "stderr_length": len(stderr),
            "execution_time_ms": exec_time,
            "expected": "Should provide educational feedback via stderr",
        })
        
        # Test performance benchmark (target <100ms for educational feedback)
        test_results.append({
            "test": "educational_feedback_performance",
            "passed": exec_time < 100,
            "execution_time_ms": exec_time,
            "expected": "Educational feedback should complete in <100ms",
        })
        
        return test_results
    
    def test_shared_intelligence_integration(self) -> List[Dict[str, Any]]:
        """Test shared_intelligence component integration."""
        test_results = []
        
        try:
            # Test imports
            sys.path.insert(0, str(self.hook_dir))
            
            from shared_intelligence import (
                analyze_tool_for_routing,
                analyze_workflow_patterns,
                check_performance_optimization,
                get_tool_recommendations,
            )

            # Test basic functionality with proper context
            context: Dict[str, Any] = {"recent_operations": []}
            tool_input: Dict[str, Any] = {"file_path": "/tmp/test.py"}
            
            routing_analysis = analyze_tool_for_routing("Write", tool_input, context)
            test_results.append({
                "test": "shared_intelligence_routing",
                "passed": routing_analysis is not None,
                "expected": "Should provide routing analysis",
            })
            
            workflow_patterns = analyze_workflow_patterns("Write", tool_input, context)
            test_results.append({
                "test": "shared_intelligence_patterns",
                "passed": workflow_patterns is not None,
                "expected": "Should analyze workflow patterns",
            })
            
            perf_optimization = check_performance_optimization("Write", tool_input, context)
            test_results.append({
                "test": "shared_intelligence_performance",
                "passed": perf_optimization is not None,
                "expected": "Should check performance optimization",
            })
            
            recommendations = get_tool_recommendations("Write", tool_input, context)
            test_results.append({
                "test": "shared_intelligence_recommendations",
                "passed": recommendations is not None,
                "expected": "Should provide tool recommendations",
            })
            
        except ImportError as e:
            test_results.append({
                "test": "shared_intelligence_import",
                "passed": False,
                "error": str(e),
                "expected": "Should import shared_intelligence components without error",
            })
        
        return test_results
    
    def test_hook_contract_compliance(self) -> List[Dict[str, Any]]:
        """Test compliance with Hook Contract specifications."""
        test_results = []
        
        # Test 1: PreToolUse exit code compliance
        # Should exit 0 for allowed operations
        event_data = {
            "session_id": "test",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/allowed.txt"},
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.pretool_hook, event_data)
        
        test_results.append({
            "test": "pretool_exit_code_compliance", 
            "passed": exit_code in [0, 2],  # Only 0 (allow) or 2 (block) per contract
            "exit_code": exit_code,
            "expected": "PreToolUse should only return exit codes 0 or 2",
        })
        
        # Test 2: JSON input handling
        # Should handle malformed JSON gracefully
        result = subprocess.run(
            [sys.executable, str(self.pretool_hook)],
            input="invalid json",
            text=True,
            capture_output=True,
        )
        
        test_results.append({
            "test": "json_error_handling",
            "passed": result.returncode == 1,  # Should fail with exit code 1 for JSON errors
            "exit_code": result.returncode,
            "expected": "Should handle JSON errors with exit code 1",
        })
        
        # Test 3: stderr usage for blocking messages
        # Per contract, exit code 2 should provide stderr that Claude sees
        event_data = {
            "session_id": "test",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test_backup_file.py",  # Should trigger blocking
                "content": "content",
            },
        }
        
        exit_code, stdout, stderr, exec_time = self.run_hook(self.pretool_hook, event_data)
        
        test_results.append({
            "test": "stderr_blocking_message",
            "passed": exit_code == 2 and len(stderr) > 0,
            "exit_code": exit_code,
            "stderr_provided": len(stderr) > 0,
            "expected": "Exit code 2 should provide stderr message for Claude",
        })
        
        return test_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete validation test suite."""
        print("🔍 Running Production Validation Test Suite...")
        print("=" * 60)
        
        all_results = {
            "pretool_security": self.test_pretool_security_blocking(),
            "posttool_education": self.test_posttool_educational_feedback(),
            "shared_intelligence": self.test_shared_intelligence_integration(),
            "contract_compliance": self.test_hook_contract_compliance(),
        }
        
        # Calculate summary
        total_tests = sum(len(results) for results in all_results.values())
        passed_tests = sum(
            sum(1 for test in results if test.get("passed", False))
            for results in all_results.values()
        )
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "production_ready": passed_tests == total_tests,
        }
        
        return {
            "summary": summary,
            "detailed_results": all_results,
        }
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        summary = results["summary"]
        detailed = results["detailed_results"]
        
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        print(f"Production Ready: {'✅ YES' if summary['production_ready'] else '❌ NO'}")
        
        print(f"\n📋 DETAILED RESULTS")
        print("=" * 60)
        
        for category, tests in detailed.items():
            print(f"\n{category.upper().replace('_', ' ')}:")
            for test in tests:
                status = "✅ PASS" if test.get("passed", False) else "❌ FAIL"
                print(f"  {status} {test['test']}")
                if not test.get("passed", False):
                    print(f"    Expected: {test.get('expected', 'N/A')}")
                    if 'error' in test:
                        print(f"    Error: {test['error']}")
                    if 'exit_code' in test:
                        print(f"    Exit Code: {test['exit_code']}")
                if 'execution_time_ms' in test:
                    print(f"    Execution Time: {test['execution_time_ms']:.1f}ms")


def main():
    """Main test execution."""
    tester = HookTester()
    try:
        results = tester.run_all_tests()
        tester.print_results(results)
        
        # Exit with appropriate code
        if results["summary"]["production_ready"]:
            print(f"\n🎉 All tests passed! System is production ready.")
            sys.exit(0)
        else:
            print(f"\n⚠️ Some tests failed. Review results before production deployment.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
