#!/usr/bin/env python3
"""
Test script to demonstrate the context capture system functionality.

This script shows how the PostToolUse hook captures tool usage outcomes
and stores them for future context revival.
"""

import json
import sys
from pathlib import Path

# Add current directory and UserPromptSubmit to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "UserPromptSubmit"))

from context_capture import handle_context_capture, ContextCaptureHandler
from context_manager import get_context_manager


def test_context_capture_scenarios():
    """Test various tool usage scenarios and context capture."""
    
    print("🧪 Testing Context Capture System")
    print("=" * 50)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Successful Bash Command",
            "data": {
                "tool_name": "Bash",
                "tool_input": {"command": "echo 'Hello World'"},
                "tool_response": "Hello World\nCommand executed successfully"
            }
        },
        {
            "name": "Failed Bash Command", 
            "data": {
                "tool_name": "Bash",
                "tool_input": {"command": "non_existent_command"},
                "tool_response": "bash: non_existent_command: command not found\nError: Command failed with exit code 127"
            }
        },
        {
            "name": "File Edit Operation",
            "data": {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/tmp/example.py",
                    "old_string": "print('old')",
                    "new_string": "print('new')"
                },
                "tool_response": "File edited successfully. Changed 1 occurrence."
            }
        },
        {
            "name": "File Read Operation",
            "data": {
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/example.py"},
                "tool_response": "Reading file /tmp/example.py\nprint('new')\n"
            }
        },
        {
            "name": "MCP Filesystem Operation",
            "data": {
                "tool_name": "mcp__filesystem__write_file",
                "tool_input": {
                    "path": "/tmp/mcp_test.txt",
                    "content": "Test content"
                },
                "tool_response": "File written successfully to /tmp/mcp_test.txt"
            }
        }
    ]
    
    # Test each scenario
    captured_contexts = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        print("-" * 30)
        
        # Capture context
        exit_code = handle_context_capture(scenario["data"])
        print(f"   Exit code: {exit_code}")
        
        # Analyze the captured context
        handler = ContextCaptureHandler()
        outcome = handler.analyzer.analyze_tool_outcome(
            scenario["data"]["tool_name"],
            scenario["data"]["tool_input"], 
            scenario["data"]["tool_response"]
        )
        
        print(f"   Outcome: {outcome.outcome}")
        print(f"   Files involved: {outcome.files_involved}")
        print(f"   Error patterns: {len(outcome.error_patterns)}")
        print(f"   Success patterns: {len(outcome.success_patterns)}")
        
        captured_contexts.append(outcome)
    
    # Test context retrieval
    print(f"\n🔍 Testing Context Retrieval")
    print("=" * 50)
    
    cm = get_context_manager()
    
    # Test different queries
    queries = [
        ("bash command", ["Commands and shell operations"]),
        ("edit file", ["File modification operations"]),
        ("error", ["Failed operations and error patterns"]),
        ("success", ["Successful operations"])
    ]
    
    for query, description in queries:
        print(f"\nQuery: '{query}' - {description[0]}")
        print("-" * 40)
        
        contexts = cm.retrieve_relevant_contexts(query, max_results=3)
        print(f"Found {len(contexts)} relevant contexts:")
        
        for j, context in enumerate(contexts, 1):
            print(f"  {j}. {context.user_prompt} ({context.outcome}) - Score: {context.relevance_score:.2f}")
    
    # Show health status
    print(f"\n📊 Context Manager Health")
    print("=" * 50)
    
    health = cm.get_health_status()
    print(f"Status: {health['status']}")
    print(f"Total contexts: {health['total_contexts']}")
    print(f"Recent contexts: {health['recent_contexts']}")
    print(f"Cache size: {health['cache_size']}")
    
    session_summary = cm.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Total contexts: {session_summary['total_contexts']}")
    print(f"  Successful: {session_summary['successful']}")
    print(f"  Failed: {session_summary['failed']}")
    print(f"  Success rate: {session_summary['success_rate']:.1f}%")
    
    print(f"\n✅ Context capture test completed!")
    return captured_contexts


if __name__ == "__main__":
    try:
        captured = test_context_capture_scenarios()
        print(f"\nCaptured {len(captured)} context scenarios for testing.")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)