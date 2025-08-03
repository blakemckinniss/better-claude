#!/usr/bin/env python3
"""
Fixed demonstration of PostToolUse warning behavior.

This script shows how warnings should appear by using the 
force_show_warning method for consistent demonstration.
"""

import sys
import json
from pathlib import Path

# Add the PostToolUse module to path
sys.path.insert(0, str(Path(__file__).parent / "hook_handlers" / "PostToolUse"))

from session_tracker import get_session_tracker, WarningTypes


def demo_warning_with_force_show():
    """Demonstrate warnings that always show for demo purposes."""
    
    tracker = get_session_tracker()
    session_id = "demo_session"
    
    print("=== DEMO: Force Show Warning Behavior ===\n")
    
    # Test 1: Subagent delegation warning (always shows)
    print("Test 1: Subagent delegation warning")
    should_show = tracker.force_show_warning(session_id, WarningTypes.SUBAGENT_DELEGATION)
    print(f"First call - should show: {should_show}")
    
    should_show = tracker.force_show_warning(session_id, WarningTypes.SUBAGENT_DELEGATION) 
    print(f"Second call - should show: {should_show}")
    print()
    
    # Test 2: Complex bash warning (always shows)
    print("Test 2: Complex bash warning")
    should_show = tracker.force_show_warning(session_id, WarningTypes.COMPLEX_BASH)
    print(f"First call - should show: {should_show}")
    
    should_show = tracker.force_show_warning(session_id, WarningTypes.COMPLEX_BASH)
    print(f"Second call - should show: {should_show}")
    print()


def demo_normal_suppression():
    """Demonstrate normal warning suppression behavior."""
    
    tracker = get_session_tracker()
    session_id = "normal_session"
    
    print("=== DEMO: Normal Warning Suppression ===\n")
    
    # Test 1: First call shows, second suppresses
    print("Test 1: Normal suppression behavior")
    should_show = tracker.should_show_warning(session_id, WarningTypes.SUBAGENT_DELEGATION)
    print(f"First call - should show: {should_show}")
    
    should_show = tracker.should_show_warning(session_id, WarningTypes.SUBAGENT_DELEGATION)
    print(f"Second call - should show: {should_show} (suppressed)")
    print()


if __name__ == "__main__":
    demo_warning_with_force_show()
    demo_normal_suppression()
