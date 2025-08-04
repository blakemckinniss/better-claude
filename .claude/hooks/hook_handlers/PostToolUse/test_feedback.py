#!/usr/bin/env python3
"""Test script for educational feedback system."""

import sys
from educational_feedback_enhanced import handle_educational_feedback

# Test data
test_data = {
    "tool_name": "Read",
    "tool_input": {"file_path": "test.py"},
    "tool_response": "File content here",
    "session_id": "test_session_123"
}

print("Testing educational feedback system...")
result = handle_educational_feedback(test_data)
print(f"Result: {result}")
print("Test completed successfully!")