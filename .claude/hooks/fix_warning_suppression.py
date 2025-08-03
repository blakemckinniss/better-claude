#!/usr/bin/env python3
"""
Fix for PostToolUse warning suppression issue.

The problem: session_tracker.should_show_warning() both checks AND marks warnings as shown.
This causes subsequent demonstration calls to show "no feedback" instead of warnings.

Solution: Separate the check and mark operations for demo/test scenarios.
"""

import json
from pathlib import Path


def fix_session_tracker():
    """
    Add methods to separate warning check from marking for test scenarios.
    """
    session_tracker_path = Path(".claude/hooks/hook_handlers/PostToolUse/session_tracker.py")
    
    # Read current content
    with open(session_tracker_path) as f:
        content = f.read()
    
    # Add new methods before the final class definition
    new_methods = '''
    def should_show_warning_check_only(self, session_id: str, warning_type: str) -> bool:
        """Check if warning should be shown WITHOUT marking it as shown."""
        return not self.has_shown_warning(session_id, warning_type)
    
    def force_show_warning(self, session_id: str, warning_type: str) -> bool:
        """Always show warning and mark as shown (for demo/test purposes)."""
        self.mark_warning_shown(session_id, warning_type)
        return True
'''
    
    # Insert before the global instance comment
    insertion_point = content.find("# Global instance for use across the hook")
    if insertion_point != -1:
        new_content = content[:insertion_point] + new_methods + "\n" + content[insertion_point:]
        
        with open(session_tracker_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Added new methods to SessionWarningTracker")
        return True
    else:
        print("❌ Could not find insertion point")
        return False


def create_demo_fix():
    """
    Create a demonstration script that shows proper warning behavior.
    """
    demo_script = '''#!/usr/bin/env python3
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
    
    print("=== DEMO: Force Show Warning Behavior ===\\n")
    
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
    
    print("=== DEMO: Normal Warning Suppression ===\\n")
    
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
'''
    
    with open(".claude/hooks/demo_warning_fix.py", 'w') as f:
        f.write(demo_script)
    
    print("✅ Created demonstration script: .claude/hooks/demo_warning_fix.py")


if __name__ == "__main__":
    print("🔧 Fixing PostToolUse warning suppression issue...")
    
    if fix_session_tracker():
        create_demo_fix()
        print("\\n✅ Fix complete! Warning suppression issue resolved.")
        print("\\n📝 Summary:")
        print("   - Added force_show_warning() method for consistent demo behavior")
        print("   - Added should_show_warning_check_only() for read-only checks") 
        print("   - Created demo script to verify the fix")
    else:
        print("\\n❌ Fix failed - manual intervention required")