#!/usr/bin/env python3
"""Performance test script for optimized PreToolUse handler."""

import os
import sys
import time

# Add the hook_handlers directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_performance():
    """Test the performance improvements of the optimized handler."""
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Simple Read Operation',
            'event': {
                'tool_name': 'Read',
                'tool_input': {'file_path': '/home/devcontainers/better-claude/README.md'},
            },
        },
        {
            'name': 'Write Operation',
            'event': {
                'tool_name': 'Write', 
                'tool_input': {
                    'file_path': '/tmp/test_file.txt',
                    'content': 'Test content',
                },
            },
        },
        {
            'name': 'Bash Command',
            'event': {
                'tool_name': 'Bash',
                'tool_input': {'command': 'echo "Hello World"'},
            },
        },
    ]
    
    print("🚀 Performance Testing: Optimized PreToolUse Handler")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        
        # Import and test the optimized handler
        try:
            from PreToolUse import handle

            # Measure execution time
            start_time = time.perf_counter()
            
            try:
                handle(test_case['event'])
            except SystemExit as e:
                end_time = time.perf_counter()
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                
                if e.code == 0:
                    print(f"✅ PASSED - Execution time: {execution_time:.2f}ms")
                else:
                    print(f"⚠️  BLOCKED (expected) - Execution time: {execution_time:.2f}ms")
                    
        except ImportError as e:
            print(f"❌ Import Error: {e}")
        except Exception as e:
            print(f"❌ Test Failed: {e}")
    
    print(f"\n{'=' * 60}")
    print("🎯 Performance Targets:")
    print("  • 60-80% reduction in startup time")
    print("  • 40-60% reduction in memory usage") 
    print("  • 50-70% reduction in CPU utilization")
    print("  • 30-50% improvement in overall latency")
    
    print("\n⚡ Optimizations Implemented:")
    print("  • Lazy loading of validator modules")
    print("  • Module-level caching with 1s TTL")
    print("  • Parallel validation execution")
    print("  • Streaming file analysis")
    print("  • Fast-path for common operations")

if __name__ == "__main__":
    test_performance()
