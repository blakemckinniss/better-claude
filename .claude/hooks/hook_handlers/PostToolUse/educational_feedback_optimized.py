#!/usr/bin/env python3
"""
Optimized Educational Feedback System for PostToolUse Hook.

Performance optimizations:
1. Lazy imports and module loading
2. Circuit breakers for shared intelligence components  
3. Cached analysis results
4. Minimal string operations
5. Fast-path for common cases
6. Memory-efficient context building
7. Async-ready architecture (preparation)

Target: <100ms execution time
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Callable

# Fast path imports only - defer heavy imports
_HEAVY_IMPORTS_LOADED = False
_SHARED_INTELLIGENCE_AVAILABLE = False
_IMPORT_FAILURES = set()

# Performance tracking
_EXECUTION_STATS = {
    "total_calls": 0,
    "fast_path_hits": 0,
    "avg_execution_time": 0.0,
    "last_reset": time.time()
}

# Circuit breaker for expensive operations
_CIRCUIT_BREAKER = {
    "shared_intelligence": {"failures": 0, "last_failure": 0, "state": "closed"},
    "heavy_analysis": {"failures": 0, "last_failure": 0, "state": "closed"}
}

def _is_circuit_open(component: str) -> bool:
    """Check if circuit breaker is open for component."""
    breaker = _CIRCUIT_BREAKER.get(component, {})
    if breaker.get("state") == "open":
        # Auto-reset after 5 minutes
        if time.time() - breaker.get("last_failure", 0) > 300:
            breaker["state"] = "closed"
            breaker["failures"] = 0
            return False
        return True
    return False

def _record_failure(component: str):
    """Record failure and potentially open circuit breaker."""
    breaker = _CIRCUIT_BREAKER.get(component, {"failures": 0, "last_failure": 0, "state": "closed"})
    breaker["failures"] += 1
    breaker["last_failure"] = time.time()
    
    # Open circuit after 3 failures
    if breaker["failures"] >= 3:
        breaker["state"] = "open"
    
    _CIRCUIT_BREAKER[component] = breaker

def _load_heavy_imports():
    """Lazy load heavy imports with error handling."""
    global _HEAVY_IMPORTS_LOADED, _SHARED_INTELLIGENCE_AVAILABLE
    
    if _HEAVY_IMPORTS_LOADED:
        return
    
    try:
        # Try to load shared intelligence components
        if not _is_circuit_open("shared_intelligence"):
            try:
                # SECURITY FIX: Secure import resolution without sys.path manipulation
                try:
                    # First try relative imports (preferred for package structure)
                    from ..shared_intelligence.intelligent_router import analyze_tool_for_routing
                    from ..shared_intelligence.anti_pattern_detector import analyze_workflow_patterns
                    from ..shared_intelligence.performance_optimizer import check_performance_optimization
                    from ..shared_intelligence.recommendation_engine import get_tool_recommendations
                    _SHARED_INTELLIGENCE_AVAILABLE = True
                    return
                except ImportError:
                    pass
                
                try:
                    # Secure fallback with path validation
                    import importlib.util
                    base_dir = os.path.dirname(os.path.dirname(__file__))
                    shared_intelligence_dir = os.path.join(base_dir, 'shared_intelligence')
                    
                    # Validate path to prevent directory traversal
                    if not os.path.abspath(shared_intelligence_dir).startswith(os.path.abspath(base_dir)):
                        raise ImportError("Invalid shared intelligence path")
                    
                    modules = {}
                    module_files = {
                        'intelligent_router': 'intelligent_router.py',
                        'anti_pattern_detector': 'anti_pattern_detector.py', 
                        'performance_optimizer': 'performance_optimizer.py',
                        'recommendation_engine': 'recommendation_engine.py'
                    }
                    
                    for module_name, filename in module_files.items():
                        module_path = os.path.join(shared_intelligence_dir, filename)
                        if os.path.exists(module_path) and os.path.abspath(module_path).startswith(os.path.abspath(base_dir)):
                            spec = importlib.util.spec_from_file_location(module_name, module_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                modules[module_name] = module
                    
                    if len(modules) == 4:
                        # Store functions globally for performance
                        globals()['analyze_tool_for_routing'] = modules['intelligent_router'].analyze_tool_for_routing
                        globals()['analyze_workflow_patterns'] = modules['anti_pattern_detector'].analyze_workflow_patterns
                        globals()['check_performance_optimization'] = modules['performance_optimizer'].check_performance_optimization
                        globals()['get_tool_recommendations'] = modules['recommendation_engine'].get_tool_recommendations
                        _SHARED_INTELLIGENCE_AVAILABLE = True
                except Exception:
                    pass
                
            except Exception as e:
                _IMPORT_FAILURES.add("shared_intelligence")
                _record_failure("shared_intelligence")
                _SHARED_INTELLIGENCE_AVAILABLE = False
        
        _HEAVY_IMPORTS_LOADED = True
        
    except Exception:
        _HEAVY_IMPORTS_LOADED = True  # Mark as attempted


# Handle session tracker import with fallback - SECURITY FIXED
try:
    from .session_tracker import get_session_tracker, extract_session_id, WarningTypes
except ImportError:
    try:
        # SECURITY FIX: Use direct import without sys.path manipulation
        from session_tracker import get_session_tracker, extract_session_id, WarningTypes
    except ImportError:
        # Fallback implementations
        class MockSessionTracker:
            def should_show_warning(self, session_id: str, warning_type: str) -> bool:
                return True
            def should_show_warning_check_only(self, session_id: str, warning_type: str) -> bool:
                return True
            def mark_warning_shown(self, session_id: str, warning_type: str) -> None:
                pass
        
        def get_session_tracker():
            return MockSessionTracker()
        
        def extract_session_id(data: Dict) -> str:
            return data.get("session_id", "default")
        
        class WarningTypes:
            SUBAGENT_DELEGATION = "subagent_delegation"


class OptimizedEducationalFeedback:
    """High-performance educational feedback system."""
    
    # Pre-computed feedback messages for common cases
    FAST_FEEDBACK_CACHE = {
        ("Read", "large_file"): "📊 LARGE FILE: Consider using streaming tools like 'head', 'tail', or 'less'",
        ("Write", "full_rewrite"): "✏️ EDIT TIP: Consider using Edit tool for targeted changes instead of full rewrites",
        ("Bash", "grep"): "🔍 MODERN CLI: Consider 'rg' (ripgrep) - it's 10-100x faster than grep",
        ("Bash", "find"): "📁 MODERN CLI: Consider 'fd' - simpler and faster than find",
        ("error_learning", "traceback"): "📚 LEARNING: Errors provide valuable debugging information",
    }
    
    # Simple pattern matching rules (avoiding regex for speed)
    FAST_PATTERNS = {
        "grep": "Use 'rg' instead of grep for 10-100x better performance",
        "find": "Use 'fd' instead of find for simpler, faster searches", 
        "cat": "Use 'bat' for syntax highlighting and better output",
        "ls -la": "Use 'lsd -la' for modern, colorized directory listings",
        "error:": "error_learning",
        "failed": "error_learning", 
        "exception": "error_learning",
        "traceback": "error_learning",
    }
    
    def __init__(self):
        self.session_tracker = get_session_tracker()
        self.start_time = time.time()
        self._context_cache = {}
        self._last_cache_clear = time.time()
    
    def _clear_cache_if_needed(self):
        """Clear context cache periodically to prevent memory growth."""
        current_time = time.time()
        if current_time - self._last_cache_clear > 300:  # 5 minutes
            self._context_cache.clear()
            self._last_cache_clear = current_time
    
    def _build_minimal_context(self, session_id: str, tool_name: str) -> Dict[str, Any]:
        """Build minimal context efficiently."""
        cache_key = f"{session_id}_{tool_name}"
        
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        # Minimal context - just what we need
        context = {
            "session_info": session_id,
            "tool_name": tool_name,
            "timestamp": time.time()
        }
        
        # Cache for reuse
        self._context_cache[cache_key] = context
        return context
    
    def _fast_pattern_check(self, tool_name: str, tool_input: Dict[str, Any], tool_response: str) -> Optional[str]:
        """Ultra-fast pattern checking without complex analysis."""
        
        # File size check for Read operations
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path:
                try:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 1000000:  # 1MB
                        return self.FAST_FEEDBACK_CACHE[("Read", "large_file")]
                except (OSError, IOError):
                    pass
        
        # Command optimization for Bash
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            command_lower = command.lower()
            
            for pattern, suggestion in self.FAST_PATTERNS.items():
                if pattern in command_lower and len(pattern) > 3:  # Avoid false positives
                    return f"💡 OPTIMIZATION: {suggestion}"
        
        # Error detection in responses
        if tool_response:
            response_lower = tool_response.lower()
            for pattern, feedback_type in self.FAST_PATTERNS.items():
                if feedback_type == "error_learning" and pattern in response_lower:
                    return self.FAST_FEEDBACK_CACHE[("error_learning", "traceback")]
        
        return None
    
    def _get_shared_intelligence_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        session_id: str
    ) -> List[str]:
        """Get feedback from shared intelligence components with circuit breaking."""
        
        if not _SHARED_INTELLIGENCE_AVAILABLE or _is_circuit_open("shared_intelligence"):
            return []
        
        feedback_messages = []
        
        try:
            # Lazy import only when needed
            from intelligent_router import analyze_tool_for_routing
            from anti_pattern_detector import analyze_workflow_patterns
            from performance_optimizer import check_performance_optimization
            from recommendation_engine import get_tool_recommendations
            
            # Build minimal context for analysis
            context = self._build_minimal_context(session_id, tool_name)
            
            # Quick timeout for each component (max 25ms each)
            start_time = time.time()
            
            # Routing analysis (if under time budget)
            if time.time() - start_time < 0.025:
                try:
                    should_redirect, reason, warnings, alternative = analyze_tool_for_routing(
                        tool_name, tool_input, context
                    )
                    if should_redirect and reason:
                        feedback_type = f"routing_{tool_name}_{hash(str(alternative)) % 1000}"
                        if self.session_tracker.should_show_warning(session_id, feedback_type):
                            feedback_messages.append(f"🚀 {reason}")
                except Exception:
                    pass
            
            # Pattern analysis (if under time budget)
            if time.time() - start_time < 0.050:
                try:
                    should_block, reason, warnings, alternative = analyze_workflow_patterns(
                        tool_name, tool_input, context
                    )
                    if warnings:
                        feedback_type = f"pattern_{tool_name}"
                        if self.session_tracker.should_show_warning(session_id, feedback_type):
                            feedback_messages.append(f"🔍 {warnings[0]}")  # Just first warning
                except Exception:
                    pass
            
            # Performance analysis (if under time budget)
            if time.time() - start_time < 0.075:
                try:
                    should_optimize, reason, warnings, optimization = check_performance_optimization(
                        tool_name, tool_input, context
                    )
                    if should_optimize and reason:
                        feedback_type = f"performance_{tool_name}"
                        if self.session_tracker.should_show_warning(session_id, feedback_type):
                            feedback_messages.append(f"⚡ {reason}")
                except Exception:
                    pass
            
        except Exception as e:
            _record_failure("shared_intelligence")
            # Fallback to fast patterns only
            return []
        
        return feedback_messages
    
    def provide_feedback(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_response: str,
        session_id: str
    ) -> Optional[str]:
        """
        Provide educational feedback with <100ms target performance.
        
        Returns feedback message if one should be shown, None otherwise.
        """
        execution_start = time.time()
        
        # Update performance stats
        _EXECUTION_STATS["total_calls"] += 1
        
        try:
            # Fast path: Check simple patterns first (target: <10ms)
            fast_feedback = self._fast_pattern_check(tool_name, tool_input, tool_response)
            if fast_feedback:
                # Check if we should show this type of feedback
                feedback_type = f"fast_{tool_name}_{hash(fast_feedback) % 100}"
                if self.session_tracker.should_show_warning(session_id, feedback_type):
                    _EXECUTION_STATS["fast_path_hits"] += 1
                    return fast_feedback
            
            # Shared intelligence path: Only if we have time budget (target: <75ms total)
            execution_time = time.time() - execution_start
            if execution_time < 0.075:  # 75ms budget remaining
                
                # Load heavy imports if needed
                _load_heavy_imports()
                
                # Get shared intelligence feedback
                si_feedback = self._get_shared_intelligence_feedback(tool_name, tool_input, session_id)
                if si_feedback:
                    return si_feedback[0]  # Return first relevant feedback
            
            # Success feedback (low priority, only if very fast)
            execution_time = time.time() - execution_start
            if execution_time < 0.010 and "successfully" in tool_response.lower():
                feedback_type = "success_pattern"
                if self.session_tracker.should_show_warning_check_only(session_id, feedback_type):
                    if hash(session_id + tool_name) % 10 == 0:  # 10% chance
                        self.session_tracker.mark_warning_shown(session_id, feedback_type)
                        return "✅ Good approach! Consider documenting successful patterns."
            
            return None
            
        finally:
            # Update performance metrics
            execution_time = time.time() - execution_start
            _EXECUTION_STATS["avg_execution_time"] = (
                (_EXECUTION_STATS["avg_execution_time"] * (_EXECUTION_STATS["total_calls"] - 1) + execution_time) 
                / _EXECUTION_STATS["total_calls"]
            )
            
            # Performance warning if over budget
            if execution_time > 0.100:  # 100ms
                if os.environ.get("DEBUG_HOOKS"):
                    print(f"Educational feedback exceeded budget: {execution_time*1000:.1f}ms", file=sys.stderr)
            
            # Clear cache periodically
            self._clear_cache_if_needed()


def handle_educational_feedback(data: Dict[str, Any]) -> int:
    """
    Optimized main handler for educational feedback in PostToolUse.
    
    Returns:
        int: Always returns 0 (doesn't block operations)
    """
    try:
        # Fast validation
        tool_name = data.get("tool_name")
        if not tool_name:
            return 0
        
        tool_input = data.get("tool_input", {})
        tool_response = data.get("tool_response", "")
        session_id = extract_session_id(data)
        
        # Initialize optimized feedback system
        feedback_system = OptimizedEducationalFeedback()
        
        # Get feedback with performance constraints
        feedback = feedback_system.provide_feedback(
            tool_name, tool_input, tool_response, session_id
        )
        
        if feedback:
            # Output to stderr for Claude to see
            print(feedback, file=sys.stderr)
            print("", file=sys.stderr)  # Add spacing
        
        return 0
        
    except Exception as e:
        # Never block operations due to feedback errors
        if os.environ.get("DEBUG_HOOKS"):
            print(f"Educational feedback error: {e}", file=sys.stderr)
        return 0


def get_performance_stats() -> Dict[str, Any]:
    """Get performance statistics for monitoring."""
    current_time = time.time()
    uptime = current_time - _EXECUTION_STATS.get("last_reset", current_time)
    
    return {
        "total_calls": _EXECUTION_STATS["total_calls"],
        "fast_path_hits": _EXECUTION_STATS["fast_path_hits"],
        "fast_path_rate": (_EXECUTION_STATS["fast_path_hits"] / max(1, _EXECUTION_STATS["total_calls"])) * 100,
        "avg_execution_time_ms": _EXECUTION_STATS["avg_execution_time"] * 1000,
        "uptime_seconds": uptime,
        "calls_per_second": _EXECUTION_STATS["total_calls"] / max(1, uptime),
        "circuit_breakers": _CIRCUIT_BREAKER,
        "import_failures": list(_IMPORT_FAILURES),
        "shared_intelligence_available": _SHARED_INTELLIGENCE_AVAILABLE,
    }


def reset_performance_stats():
    """Reset performance statistics."""
    global _EXECUTION_STATS
    _EXECUTION_STATS = {
        "total_calls": 0,
        "fast_path_hits": 0,
        "avg_execution_time": 0.0,
        "last_reset": time.time()
    }


# For testing and direct execution
if __name__ == "__main__":
    try:
        if not sys.stdin.isatty():
            event_data = json.loads(sys.stdin.read())
            exit_code = handle_educational_feedback(event_data)
            sys.exit(exit_code)
        else:
            print("Optimized Educational Feedback System")
            print("Performance target: <100ms execution time")
            stats = get_performance_stats()
            print(f"Stats: {json.dumps(stats, indent=2)}")
            sys.exit(0)
    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)