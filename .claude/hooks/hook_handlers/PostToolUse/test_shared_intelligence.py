#!/usr/bin/env python3
"""Unit tests for shared intelligence components."""

import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "shared_intelligence"))
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_router import (
    analyze_tool_for_routing,
    _is_single_file_read,
    _could_benefit_from_batch_read,
    _is_sequential_command,
    _get_parallel_alternative,
    _should_use_ripgrep,
    _convert_to_ripgrep,
    _is_complex_edit,
    _should_delegate_to_agent,
    _get_delegation_recommendation
)

from anti_pattern_detector import (
    analyze_workflow_patterns,
    _has_technical_debt_filename,
    _extract_debt_keyword,
    _is_repetitive_operation,
    _get_batch_alternative,
    _has_inefficient_command_pattern,
    _get_efficient_command,
    _lacks_context_preparation,
    _get_preparation_suggestion
)

from performance_optimizer import check_performance_optimization
from recommendation_engine import get_tool_recommendations


class IntelligentRouterTestCase(unittest.TestCase):
    """Test cases for intelligent router component."""
    
    def test_single_file_read_detection(self):
        """Test detection of single file read operations."""
        # Positive cases
        self.assertTrue(_is_single_file_read({"file_path": "/test/file.py"}))
        
        # Negative cases
        self.assertFalse(_is_single_file_read({"pattern": "search"}))
        self.assertFalse(_is_single_file_read({"file_path": ["file1", "file2"]}))
        self.assertFalse(_is_single_file_read({}))
    
    def test_batch_read_opportunity_detection(self):
        """Test detection of batch read opportunities."""
        context_with_reads = {
            "recent_operations": [
                {"tool_name": "Read", "file_path": "/test/file1.py"},
                {"tool_name": "Read", "file_path": "/test/file2.py"},
                {"tool_name": "Edit", "file_path": "/test/file3.py"},
            ]
        }
        
        # Should detect batch opportunity
        self.assertTrue(_could_benefit_from_batch_read({}, context_with_reads))
        
        # Should not detect with few reads
        context_few_reads = {
            "recent_operations": [
                {"tool_name": "Read", "file_path": "/test/file1.py"},
            ]
        }
        self.assertFalse(_could_benefit_from_batch_read({}, context_few_reads))
    
    def test_sequential_command_detection(self):
        """Test detection of sequential bash commands."""
        # Positive cases
        self.assertTrue(_is_sequential_command({"command": "mkdir test && cd test"}))
        self.assertTrue(_is_sequential_command({"command": "ls ; pwd"}))
        self.assertTrue(_is_sequential_command({"command": "test -f file || echo missing"}))
        
        # Negative cases
        self.assertFalse(_is_sequential_command({"command": "ls -la"}))
        self.assertFalse(_is_sequential_command({"command": "find . -name '*.py'"}))
    
    def test_parallel_alternative_generation(self):
        """Test generation of parallel alternatives."""
        sequential_cmd = {"command": "mkdir test && cd test && touch file"}
        parallel = _get_parallel_alternative(sequential_cmd)
        
        if parallel:
            self.assertIn("&", parallel)
            self.assertIn("wait", parallel)
        
        # Should handle simple cases
        simple_cmd = {"command": "echo hello && echo world"}
        simple_parallel = _get_parallel_alternative(simple_cmd)
        
        if simple_parallel:
            self.assertIn("(echo hello) &", simple_parallel)
            self.assertIn("echo world", simple_parallel)
    
    def test_ripgrep_recommendation(self):
        """Test ripgrep recommendation logic."""
        # Should recommend ripgrep for complex patterns
        self.assertTrue(_should_use_ripgrep({"pattern": "function.*return.*value"}))
        self.assertTrue(_should_use_ripgrep({"pattern": "test[0-9]+"}))
        
        # Should not recommend for simple patterns
        self.assertFalse(_should_use_ripgrep({"pattern": "simple"}))
        self.assertFalse(_should_use_ripgrep({"pattern": "test"}))
    
    def test_ripgrep_conversion(self):
        """Test conversion to ripgrep commands."""
        tool_input = {
            "pattern": "function.*test",
            "path": "/src",
            "glob": "*.py"
        }
        
        ripgrep_cmd = _convert_to_ripgrep(tool_input)
        
        self.assertIn("rg", ripgrep_cmd)
        self.assertIn("function.*test", ripgrep_cmd)
        self.assertIn("--glob '*.py'", ripgrep_cmd)
        self.assertIn("/src", ripgrep_cmd)
    
    def test_complex_edit_detection(self):
        """Test detection of complex edit operations."""
        # Large content changes
        large_edit = {
            "old_string": "x" * 1000,
            "new_string": "y" * 1000
        }
        self.assertTrue(_is_complex_edit(large_edit))
        
        # Many line changes
        multiline_edit = {
            "old_string": "\n".join(["line"] * 20),
            "new_string": "\n".join(["new_line"] * 20)
        }
        self.assertTrue(_is_complex_edit(multiline_edit))
        
        # Simple changes
        simple_edit = {
            "old_string": "old_value",
            "new_string": "new_value"
        }
        self.assertFalse(_is_complex_edit(simple_edit))
    
    def test_agent_delegation_recommendation(self):
        """Test agent delegation recommendations."""
        # Complex git operations
        git_context = {"recent_operations": []}
        
        should_delegate = _should_delegate_to_agent(
            "Bash",
            {"command": "git rebase -i HEAD~5 --autosquash"},
            git_context
        )
        self.assertTrue(should_delegate)
        
        # Complex build operations
        should_delegate_build = _should_delegate_to_agent(
            "Bash",
            {"command": "docker build --target production --build-arg ENV=prod"},
            git_context
        )
        self.assertTrue(should_delegate_build)
        
        # Simple operations
        should_not_delegate = _should_delegate_to_agent(
            "Bash",
            {"command": "ls -la"},
            git_context
        )
        self.assertFalse(should_not_delegate)
    
    def test_delegation_recommendation_content(self):
        """Test delegation recommendation content."""
        git_recommendation = _get_delegation_recommendation(
            "Bash",
            {"command": "git merge --squash feature-branch"},
            {}
        )
        
        self.assertIn("tool", git_recommendation)
        self.assertIn("reason", git_recommendation)
        self.assertIn("git", git_recommendation["reason"].lower())
    
    def test_full_routing_analysis(self):
        """Test complete routing analysis."""
        # Test batch read recommendation
        context_with_reads = {
            "recent_operations": [
                {"tool_name": "Read"}, {"tool_name": "Read"}
            ]
        }
        
        should_redirect, reason, warnings, action = analyze_tool_for_routing(
            "Read",
            {"file_path": "/test/file.py"},
            context_with_reads
        )
        
        if should_redirect:
            self.assertIsInstance(reason, str)
            self.assertIsInstance(warnings, list)
            self.assertIsInstance(action, dict)
            self.assertIn("tool", action)


class AntiPatternDetectorTestCase(unittest.TestCase):
    """Test cases for anti-pattern detector component."""
    
    def test_technical_debt_filename_detection(self):
        """Test detection of technical debt filenames."""
        debt_filenames = [
            "/test/file_backup.py",
            "/test/script_v2.py",
            "/test/enhanced_module.py",
            "/test/legacy_code.py",
            "/test/temp_fix.py",
        ]
        
        for filename in debt_filenames:
            self.assertTrue(
                _has_technical_debt_filename({"file_path": filename}),
                f"Should detect debt in {filename}"
            )
        
        clean_filenames = [
            "/test/user_service.py",
            "/test/data_processor.py",
            "/test/config_manager.py",
        ]
        
        for filename in clean_filenames:
            self.assertFalse(
                _has_technical_debt_filename({"file_path": filename}),
                f"Should not detect debt in {filename}"
            )
    
    def test_debt_keyword_extraction(self):
        """Test extraction of debt keywords from filenames."""
        test_cases = [
            ("file_backup.py", "backup"),
            ("script_v2.py", "v2"),
            ("temp_solution.py", "temp"),
            ("clean_file.py", "unknown"),
        ]
        
        for filename, expected in test_cases:
            result = _extract_debt_keyword(filename)
            if expected != "unknown":
                self.assertEqual(result, expected)
            else:
                self.assertEqual(result, "unknown")
    
    def test_repetitive_operation_detection(self):
        """Test detection of repetitive operations."""
        repetitive_context = {
            "recent_operations": [
                {"tool_name": "Read"},
                {"tool_name": "Read"},
                {"tool_name": "Edit"},
            ]
        }
        
        self.assertTrue(_is_repetitive_operation("Read", {}, repetitive_context))
        
        non_repetitive_context = {
            "recent_operations": [
                {"tool_name": "Read"},
                {"tool_name": "Edit"},
            ]
        }
        
        self.assertFalse(_is_repetitive_operation("Write", {}, non_repetitive_context))
    
    def test_batch_alternative_suggestions(self):
        """Test batch alternative suggestions."""
        read_alternative = _get_batch_alternative("Read", {}, {})
        self.assertIn("tool", read_alternative)
        self.assertIn("read_multiple_files", read_alternative["tool"])
        
        edit_alternative = _get_batch_alternative("Edit", {}, {})
        self.assertIn("MultiEdit", edit_alternative["tool"])
    
    def test_inefficient_command_detection(self):
        """Test detection of inefficient command patterns."""
        inefficient_commands = [
            {"command": "find . -name '*.py'"},
            {"command": "grep -r 'pattern' ."},
            {"command": "cat file.txt | grep 'test'"},
            {"command": "ls -la /tmp"},
        ]
        
        for cmd in inefficient_commands:
            self.assertTrue(
                _has_inefficient_command_pattern(cmd),
                f"Should detect inefficiency in {cmd['command']}"
            )
        
        efficient_commands = [
            {"command": "fd '*.py'"},
            {"command": "rg 'pattern'"},
            {"command": "lsd -la /tmp"},
        ]
        
        for cmd in efficient_commands:
            self.assertFalse(
                _has_inefficient_command_pattern(cmd),
                f"Should not detect inefficiency in {cmd['command']}"
            )
    
    def test_efficient_command_generation(self):
        """Test generation of efficient command alternatives."""
        test_cases = [
            ("find . -name '*.py'", "fd"),
            ("grep -r 'pattern'", "rg"),
            ("ls -la", "lsd -la"),
        ]
        
        for old_cmd, expected_tool in test_cases:
            result = _get_efficient_command({"command": old_cmd})
            self.assertIn(expected_tool, result)
    
    def test_context_preparation_analysis(self):
        """Test analysis of context preparation."""
        # Edit without prior analysis
        empty_context = {"recent_operations": []}
        
        lacks_context = _lacks_context_preparation(
            "Edit",
            {"file_path": "/complex/module.py"},
            empty_context
        )
        self.assertTrue(lacks_context)
        
        # Edit with prior analysis
        context_with_analysis = {
            "recent_operations": [
                {"tool_name": "Read"},
                {"tool_name": "Grep"},
            ]
        }
        
        has_context = _lacks_context_preparation(
            "Edit",
            {"file_path": "/complex/module.py"},
            context_with_analysis
        )
        self.assertFalse(has_context)
    
    def test_preparation_suggestions(self):
        """Test preparation suggestions."""
        edit_suggestion = _get_preparation_suggestion(
            "Edit",
            {"file_path": "/test/file.py"}
        )
        
        self.assertIn("tool", edit_suggestion)
        self.assertEqual(edit_suggestion["tool"], "Read")
        
        bash_suggestion = _get_preparation_suggestion(
            "Bash",
            {"command": "complex_command"}
        )
        
        self.assertIn("tool", bash_suggestion)
        self.assertIn("zen", bash_suggestion["tool"].lower())
    
    def test_full_pattern_analysis(self):
        """Test complete anti-pattern analysis."""
        # Test technical debt blocking
        should_block, reason, warnings, action = analyze_workflow_patterns(
            "Write",
            {"file_path": "/test/backup_file.py"},
            {}
        )
        
        self.assertTrue(should_block)
        self.assertIn("TECHNICAL DEBT", reason)
        self.assertIsInstance(action, dict)


class PerformanceOptimizerTestCase(unittest.TestCase):
    """Test cases for performance optimizer component."""
    
    def test_performance_optimization_analysis(self):
        """Test performance optimization analysis."""
        # Test with inefficient grep
        should_optimize, reason, warnings, action = check_performance_optimization(
            "Grep",
            {"pattern": "complex.*regex.*pattern"},
            {}
        )
        
        if should_optimize:
            self.assertIsInstance(reason, str)
            self.assertIsInstance(warnings, list)
            self.assertIsInstance(action, dict)


class RecommendationEngineTestCase(unittest.TestCase):
    """Test cases for recommendation engine component."""
    
    def test_tool_recommendations(self):
        """Test tool recommendation generation."""
        recommendations = get_tool_recommendations(
            "Bash",
            {"command": "find . -name '*.py' | xargs grep 'pattern'"},
            {}
        )
        
        if recommendations:
            self.assertIsInstance(recommendations, list)
            for rec in recommendations:
                self.assertIsInstance(rec, dict)
                self.assertIn("type", rec)


class SharedIntelligenceIntegrationTestCase(unittest.TestCase):
    """Integration tests for shared intelligence components."""
    
    def test_component_interaction(self):
        """Test interaction between intelligence components."""
        tool_name = "Bash"
        tool_input = {"command": "grep -r 'TODO' . | wc -l"}
        context = {"recent_operations": []}
        
        # All components should handle the same input
        routing_result = analyze_tool_for_routing(tool_name, tool_input, context)
        pattern_result = analyze_workflow_patterns(tool_name, tool_input, context)
        performance_result = check_performance_optimization(tool_name, tool_input, context)
        recommendations = get_tool_recommendations(tool_name, tool_input, context)
        
        # All should return valid results
        self.assertIsInstance(routing_result, tuple)
        self.assertIsInstance(pattern_result, tuple)
        self.assertIsInstance(performance_result, tuple)
        self.assertIsInstance(recommendations, list)
    
    def test_consistent_result_format(self):
        """Test that all analysis functions return consistent formats."""
        tool_name = "Read"
        tool_input = {"file_path": "/test/file.py"}
        context = {"recent_operations": []}
        
        analysis_functions = [
            analyze_tool_for_routing,
            analyze_workflow_patterns,
            check_performance_optimization,
        ]
        
        for func in analysis_functions:
            result = func(tool_name, tool_input, context)
            
            # Should return 4-tuple: (bool, str, list, dict)
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 4)
            self.assertIsInstance(result[0], bool)  # should_act
            self.assertIsInstance(result[1], str)   # reason
            self.assertIsInstance(result[2], list)  # warnings
            self.assertIsInstance(result[3], dict)  # action
    
    def test_performance_under_various_inputs(self):
        """Test performance of intelligence components with various inputs."""
        test_inputs = [
            ("Bash", {"command": "ls -la"}),
            ("Read", {"file_path": "/test/file.py"}),
            ("Edit", {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"}),
            ("Grep", {"pattern": "test.*pattern", "path": "/src"}),
        ]
        
        context = {"recent_operations": []}
        
        for tool_name, tool_input in test_inputs:
            start_time = time.perf_counter()
            
            # Test all components
            analyze_tool_for_routing(tool_name, tool_input, context)
            analyze_workflow_patterns(tool_name, tool_input, context)
            check_performance_optimization(tool_name, tool_input, context)
            get_tool_recommendations(tool_name, tool_input, context)
            
            execution_time = time.perf_counter() - start_time
            
            # Should complete quickly
            self.assertLess(
                execution_time, 0.1,
                f"Intelligence analysis too slow for {tool_name}: {execution_time:.3f}s"
            )


def run_shared_intelligence_tests():
    """Run shared intelligence test suite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_cases = [
        IntelligentRouterTestCase,
        AntiPatternDetectorTestCase,
        PerformanceOptimizerTestCase,
        RecommendationEngineTestCase,
        SharedIntelligenceIntegrationTestCase,
    ]
    
    for test_case in test_cases:
        suite.addTests(loader.loadTestsFromTestCase(test_case))
    
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("=" * 80)
    print("Shared Intelligence Components - Test Suite")
    print("=" * 80)
    
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_shared_intelligence_tests()
    sys.exit(0 if success else 1)