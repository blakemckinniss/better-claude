#!/usr/bin/env python3
"""Session State Manager for UserPromptSubmit session tracking."""

import os
from typing import Optional

from UserPromptSubmit.security_validator import scrub_credentials
from UserPromptSubmit.session_state import SessionState


class SessionStateManager:
    """Manages session state and injection decisions."""
    
    def __init__(self):
        """Initialize session state manager."""
        self._session_state = SessionState()
        self._transcript_cache = {}
        self._cache_ttl = 60  # 60 seconds cache TTL
        self._injection_cache = {}  # Cache injection decisions
        self._injection_cache_ttl = 30  # 30 second cache for decisions
    
    def should_inject_context(self, data, session_state=None) -> bool:
        """Determine if we should inject context based on session state and transcript."""
        try:
            # Get transcript path from hook data
            transcript_path = data.get("transcript_path")
            
            # Check injection decision cache first  
            cache_key = f"{transcript_path}_{data.get('prompt', '')[:50]}"
            cached_decision = self._get_cached_injection_decision(cache_key)
            if cached_decision is not None:
                return cached_decision
            
            # Use provided session state or create new one
            if session_state is None:
                session_state = self._session_state
            
            # First check session state rules (forced injection, message count, etc.)
            if session_state.should_inject(transcript_path):
                # This will return True for:
                # - First time (inject_next is True)
                # - After SubagentStop or PreCompact marked for injection
                # - After 5 messages
                # - When transcript changes
                decision = True
                self._cache_injection_decision(cache_key, decision)
                return decision
            
            # If session state says no injection needed, check if this is truly the first prompt
            # in the transcript (for cases where state was lost or corrupted)
            if not transcript_path or not os.path.exists(transcript_path):
                decision = True
                self._cache_injection_decision(cache_key, decision)
                return decision
            
            # Optimized check for user messages
            if not self._has_user_messages_optimized(transcript_path):
                decision = True
                self._cache_injection_decision(cache_key, decision)
                return decision
            
            decision = False
            self._cache_injection_decision(cache_key, decision)
            return decision
            
        except Exception as e:
            import sys

            # Contract 2.2: Use exit code 2 for blocking errors
            secure_error = scrub_credentials(str(e))
            print(f"Error: Failed to check injection status: {secure_error}", file=sys.stderr)
            sys.exit(2)
    
    def _read_transcript_cached(self, transcript_path: str) -> Optional[bytes]:
        """Read transcript with caching to reduce I/O."""
        import time
        
        try:
            now = time.time()
            
            # Check cache first
            if transcript_path in self._transcript_cache:
                content, timestamp = self._transcript_cache[transcript_path]
                if now - timestamp < self._cache_ttl:
                    return content
            
            # Read file
            with open(transcript_path, "rb") as f:
                content = f.read()
            
            # Cache content
            self._transcript_cache[transcript_path] = (content, now)
            
            # Clean old entries
            for path, (_, ts) in list(self._transcript_cache.items()):
                if now - ts > self._cache_ttl:
                    del self._transcript_cache[path]
            
            return content
        except OSError:
            return None
    
    def _has_user_messages_optimized(self, transcript_path: str) -> bool:
        """Check if transcript has user messages with optimized I/O."""
        content = self._read_transcript_cached(transcript_path)
        if not content:
            return False
        
        # Quick binary search for user messages
        return b'"type":"user"' in content and b'"message"' in content
    
    def mark_injected(self, transcript_path: str):
        """Mark that context has been injected for this transcript."""
        self._session_state.mark_injected(transcript_path)
    
    def increment_message_count(self):
        """Increment the message count for session tracking."""
        self._session_state.increment_message_count()
    
    def get_session_state(self) -> SessionState:
        """Get the current session state."""
        return self._session_state
    
    def _get_cached_injection_decision(self, cache_key: str) -> Optional[bool]:
        """Get cached injection decision if valid."""
        import time
        if cache_key in self._injection_cache:
            decision, timestamp = self._injection_cache[cache_key]
            if time.time() - timestamp < self._injection_cache_ttl:
                return decision
        return None
    
    def _cache_injection_decision(self, cache_key: str, decision: bool):
        """Cache injection decision with cleanup."""
        import time
        now = time.time()
        self._injection_cache[cache_key] = (decision, now)
        
        # Cleanup old entries
        for key, (_, timestamp) in list(self._injection_cache.items()):
            if now - timestamp > self._injection_cache_ttl:
                del self._injection_cache[key]