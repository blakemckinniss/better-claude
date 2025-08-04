#!/usr/bin/env python3
"""Circuit Breaker Manager for UserPromptSubmit injection controls."""

import os
from typing import Any, Dict


class CircuitBreakerManager:
    """Manages circuit breakers for various injection components."""
    
    def __init__(self):
        """Initialize circuit breaker configurations."""
        # Set default circuit breaker states
        self._injection_circuit_breakers = {
            "enhanced_ai_optimizer": True,  # AI context optimization
            "unified_smart_advisor": True,  # Zen, agent, content, trigger
            "code_intelligence_hub": False,  # Tree-sitter, LSP diagnostics (legacy)
            "code_intelligence": True,  # Code intelligence with AST analysis and diagnostics
            "system_monitor": True,  # Runtime monitoring, test status, context history
            "project_intelligence": True,  # Project analysis and tech stack detection
            "static_content": True,  # Prefix, suffix
            "context_revival": True,  # Historical context injection
            "git": True,  # Git injection (standalone)
            "mcp": True,  # MCP injection (standalone)
            "firecrawl": False,  # Firecrawl injection
            "zen_pro_orchestrator": True,  # zen-pro master orchestrator (CRITICAL - DO NOT DISABLE)
        }
        
        # Load environment overrides FIRST to apply settings
        self._load_env_overrides()
        
        # THEN compute enabled injections from updated circuit breakers
        self._enabled_injections = {k: v for k, v in self._injection_circuit_breakers.items() if v}
    
    def _load_env_overrides(self):
        """Load circuit breaker overrides from environment variables."""
        for key in self._injection_circuit_breakers:
            env_key = f"CIRCUIT_BREAKER_{key.upper()}"
            if env_key in os.environ:
                self._injection_circuit_breakers[key] = os.environ[env_key].lower() == "true"
    
    def is_injection_enabled(self, injection_name: str) -> bool:
        """Check if a specific injection is enabled."""
        return self._enabled_injections.get(injection_name, False)
    
    def is_circuit_breaker_enabled(self, breaker_name: str) -> bool:
        """Check if a specific circuit breaker is enabled."""
        return self._injection_circuit_breakers.get(breaker_name, False)
    
    def get_enabled_injections(self) -> Dict[str, bool]:
        """Get all enabled injections."""
        return self._enabled_injections.copy()
    
    def get_circuit_breakers(self) -> Dict[str, bool]:
        """Get all circuit breaker states."""
        return self._injection_circuit_breakers.copy()
    
    def disable_injection(self, injection_name: str):
        """Disable a specific injection."""
        if injection_name in self._injection_circuit_breakers:
            self._injection_circuit_breakers[injection_name] = False
            self._enabled_injections[injection_name] = False
    
    def enable_injection(self, injection_name: str):
        """Enable a specific injection."""
        if injection_name in self._injection_circuit_breakers:
            self._injection_circuit_breakers[injection_name] = True
            self._enabled_injections[injection_name] = True
    
    def trip_circuit_breaker(self, breaker_name: str):
        """Trip (disable) a circuit breaker."""
        if breaker_name in self._injection_circuit_breakers:
            self._injection_circuit_breakers[breaker_name] = False
            self._enabled_injections[breaker_name] = False
    
    def reset_circuit_breaker(self, breaker_name: str):
        """Reset (enable) a circuit breaker."""
        if breaker_name in self._injection_circuit_breakers:
            self._injection_circuit_breakers[breaker_name] = True
            self._enabled_injections[breaker_name] = True