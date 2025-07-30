#!/usr/bin/env python3
"""Test session state management for injection control."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hook_handlers"))

from UserPromptSubmit.session_state import SessionState


def test_session_state():
    """Test the session state management."""
    print("Testing session state management...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a session state instance
        state = SessionState(temp_dir)
        
        # Test 1: Default state should inject
        print("\nTest 1: Default state")
        assert state.should_inject() is True, "Default state should inject"
        print("✅ Default state requests injection")
        
        # Test 2: After marking injected, should not inject
        print("\nTest 2: After injection")
        state.mark_injected("/test/transcript.jsonl")
        assert state.should_inject() is False, "Should not inject after marking"
        print("✅ After injection, no inject needed")
        
        # Test 3: After 5 messages, should inject
        print("\nTest 3: Message limit")
        for i in range(5):
            state.increment_message_count()
        assert state.should_inject() is True, "Should inject after 5 messages"
        print("✅ Injects after 5 messages")
        
        # Test 4: Request next injection
        print("\nTest 4: Forced injection")
        state.mark_injected()  # Reset
        state.request_next_injection("test_reason")
        assert state.should_inject() is True, "Should inject when requested"
        saved_state = state.get_state()
        assert saved_state["reason"] == "test_reason", "Should save reason"
        print("✅ Forced injection works")
        
        # Test 5: Transcript change
        print("\nTest 5: Transcript change")
        state.mark_injected("/test/transcript1.jsonl")
        assert state.should_inject("/test/transcript2.jsonl") is True, "Should inject on transcript change"
        print("✅ Injects on transcript change")
        
        # Test 6: Clear state
        print("\nTest 6: Clear state")
        state.clear_state()
        new_state = state.get_state()
        assert new_state["inject_next"] is True, "Cleared state should inject"
        print("✅ Clear state resets to default")


def test_integration_scenario():
    """Test a realistic usage scenario."""
    print("\n\nTesting integration scenario...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        state = SessionState(temp_dir)
        transcript = "/test/session.jsonl"
        
        # User message 1 - should inject
        print("\n1. First user message")
        assert state.should_inject(transcript) is True
        state.mark_injected(transcript)
        print("   Injected context ✅")
        
        # User messages 2-6 - increment after each
        for i in range(2, 7):
            print(f"\n{i}. User message {i}")
            if i < 7:  # Messages 2-6 don't inject
                assert state.should_inject(transcript) is False
                state.increment_message_count()
                print("   No injection ✅")
        
        # User message 7 - should inject (after 5 messages)
        print("\n7. User message 7 (after 5 non-injected messages)")
        assert state.should_inject(transcript) is True
        state.mark_injected(transcript)
        print("   Injected context (5 message limit) ✅")
        
        # Subagent completes - mark for injection
        print("\n7. Subagent completes")
        state.request_next_injection("subagent_stop")
        print("   Marked for next injection ✅")
        
        # User message 7 - should inject (forced)
        print("\n8. User message after subagent")
        assert state.should_inject(transcript) is True
        state.mark_injected(transcript)
        print("   Injected context (after subagent) ✅")
        
        # Compact happens - mark for injection
        print("\n9. Compact triggered")
        state.request_next_injection("pre_compact")
        print("   Marked for next injection ✅")
        
        # User message 8 - should inject (forced)
        print("\n10. User message after compact")
        assert state.should_inject(transcript) is True
        state.mark_injected(transcript)
        print("   Injected context (after compact) ✅")
        
        print("\n✅ Integration scenario passed!")


if __name__ == "__main__":
    test_session_state()
    test_integration_scenario()