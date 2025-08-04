#!/usr/bin/env python3
"""
Enhanced Educational Feedback System for PostToolUse Hook.

This system integrates the shared intelligence components to provide
Claude with educational feedback via stderr + sys.exit(2) channel.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

# SECURITY FIX: Secure import resolution without sys.path manipulation
def _secure_import_shared_intelligence():
    """Securely import shared intelligence modules without sys.path manipulation."""
    try:
        # First try relative imports (preferred for package structure)
        from ..shared_intelligence.intelligent_router import analyze_tool_for_routing
        from ..shared_intelligence.anti_pattern_detector import analyze_workflow_patterns
        from ..shared_intelligence.performance_optimizer import check_performance_optimization
        from ..shared_intelligence.recommendation_engine import get_tool_recommendations
        return analyze_tool_for_routing, analyze_workflow_patterns, check_performance_optimization, get_tool_recommendations
    except ImportError:
        pass
    
    try:
        # Try direct import (for development/testing)
        import importlib.util
        base_dir = os.path.dirname(os.path.dirname(__file__))
        shared_intelligence_dir = os.path.join(base_dir, 'shared_intelligence')
        
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
            return (
                modules['intelligent_router'].analyze_tool_for_routing,
                modules['anti_pattern_detector'].analyze_workflow_patterns,
                modules['performance_optimizer'].check_performance_optimization,
                modules['recommendation_engine'].get_tool_recommendations
            )
    except Exception:
        pass
    
    # Graceful degradation if shared intelligence is unavailable
    def analyze_tool_for_routing(*args, **kwargs): return False, "", [], {}
    def analyze_workflow_patterns(*args, **kwargs): return False, "", [], {}
    def check_performance_optimization(*args, **kwargs): return False, "", [], {}
    def get_tool_recommendations(*args, **kwargs): return []
    
    return analyze_tool_for_routing, analyze_workflow_patterns, check_performance_optimization, get_tool_recommendations

# Secure import of shared intelligence modules
analyze_tool_for_routing, analyze_workflow_patterns, check_performance_optimization, get_tool_recommendations = _secure_import_shared_intelligence()

# Handle both relative and absolute imports for session tracker
try:
    from .session_tracker import get_session_tracker, extract_session_id, WarningTypes
except ImportError:
    # Secure fallback for direct execution
    try:
        from session_tracker import get_session_tracker, extract_session_id, WarningTypes
    except ImportError:
        # Graceful degradation
        class MockSessionTracker:
            def should_show_warning(self, *args): return True
            def should_show_warning_check_only(self, *args): return True
            def mark_warning_shown(self, *args): pass
        
        def get_session_tracker(): return MockSessionTracker()
        def extract_session_id(data): return data.get('session_id', 'default')
        class WarningTypes: pass


class EducationalFeedbackSystem:
    """Enhanced educational feedback system with shared intelligence."""
    
    def __init__(self):
        self.session_tracker = get_session_tracker()
        self.max_execution_time = 0.1  # 100ms limit
    
    def _build_enhanced_context(self, session_id: str, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Build enhanced context from session tracker and current operation."""
        context = {
            "session_info": session_id,
            "recent_operations": [],
        }
        
        # Try to get recent operations from session tracker
        try:
            # Look for recent warnings to infer operation history
            recent_warnings = getattr(self.session_tracker, '_session_warnings', {}).get(session_id, {})
            
            # SECURITY FIX: Use actual system time instead of fake timestamps
            current_time = time.time()
            recent_ops = []
            
            for warning_type, count in recent_warnings.items():
                if warning_type.startswith(('routing_', 'pattern_', 'performance_')):
                    # Use real intervals based on actual warning counts
                    recent_ops.append({
                        "tool_name": warning_type.split('_')[1] if '_' in warning_type else tool_name,
                        "warning_count": count,
                        "last_seen": current_time,  # Real timestamp
                    })
            
            context["recent_operations"] = recent_ops[-5:]  # Last 5 operations
            
        except (AttributeError, KeyError, TypeError) as e:
            # Fallback - minimal context with real data
            context["recent_operations"] = [{
                "tool_name": tool_name, 
                "tool_input": tool_input,
                "timestamp": time.time()
            }]
        
        return context
    
    def provide_educational_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_response: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Provide educational feedback using shared intelligence components.
        
        Returns feedback message if one should be shown, None otherwise.
        """
        start_time = time.time()
        
        # Build enhanced context if not provided
        if not context:
            context = self._build_enhanced_context(session_id, tool_name, tool_input)
        
        feedback_messages = []
        
        # 1. Intelligent Routing Analysis
        routing_feedback = self._get_routing_feedback(tool_name, tool_input, context, session_id)
        if routing_feedback:
            feedback_messages.append(routing_feedback)
        
        # 2. Anti-Pattern Detection
        pattern_feedback = self._get_pattern_feedback(tool_name, tool_input, context, session_id)
        if pattern_feedback:
            feedback_messages.append(pattern_feedback)
        
        # 3. Performance Optimization
        performance_feedback = self._get_performance_feedback(tool_name, tool_input, context, session_id)
        if performance_feedback:
            feedback_messages.append(performance_feedback)
        
        # 4. Tool Recommendations
        recommendation_feedback = self._get_recommendation_feedback(tool_name, tool_input, context, session_id)
        if recommendation_feedback:
            feedback_messages.append(recommendation_feedback)
        
        # 5. Response-based Learning Opportunities
        response_feedback = self._get_response_feedback(tool_name, tool_response, session_id)
        if response_feedback:
            feedback_messages.append(response_feedback)
        
        # Performance monitoring
        execution_time = time.time() - start_time
        if execution_time > self.max_execution_time:
            # Log performance warning but don't show to user
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Educational feedback took {execution_time:.3f}s (>{self.max_execution_time}s)", file=sys.stderr)
        
        # Combine all feedback with appropriate spacing
        if feedback_messages:
            return "\n".join(feedback_messages)
        
        return None
    
    def _get_routing_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        context: Dict[str, Any],
        session_id: str
    ) -> Optional[str]:
        """Get intelligent routing feedback."""
        try:
            should_redirect, redirect_reason, warnings, alternative_action = \
                analyze_tool_for_routing(tool_name, tool_input, context)
            
            if should_redirect and alternative_action:
                feedback_type = f"routing_{tool_name}_{hash(str(alternative_action)) % 1000}"
                
                if self.session_tracker.should_show_warning(session_id, feedback_type):
                    message = f"🚀 ROUTING INSIGHT: {redirect_reason}\n"
                    
                    if 'tool' in alternative_action:
                        message += f"   → Consider: {alternative_action['tool']}\n"
                    if 'command' in alternative_action:
                        message += f"   → Command: {alternative_action['command']}\n"
                    if 'reason' in alternative_action:
                        message += f"   → Why: {alternative_action['reason']}"
                    
                    return message
                    
        except (ImportError, AttributeError, TypeError, KeyError) as e:
            # Don't let feedback errors break the system
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Routing feedback error: {e}", file=sys.stderr)
        
        return None
    
    def _get_pattern_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        context: Dict[str, Any],
        session_id: str
    ) -> Optional[str]:
        """Get anti-pattern detection feedback."""
        try:
            should_block, pattern_reason, warnings, alternative_action = \
                analyze_workflow_patterns(tool_name, tool_input, context)
            
            # For PostToolUse, we don't block but provide educational feedback
            if warnings or alternative_action:
                feedback_type = f"pattern_{tool_name}"
                
                if self.session_tracker.should_show_warning(session_id, feedback_type):
                    message = "🔍 PATTERN ANALYSIS:"
                    
                    if warnings:
                        for warning in warnings[:2]:  # Limit to 2 warnings
                            message += f"\n   • {warning}"
                    
                    if alternative_action and 'reason' in alternative_action:
                        message += f"\n   💡 Suggestion: {alternative_action['reason']}"
                    
                    return message
                    
        except (ImportError, AttributeError, TypeError, KeyError) as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Pattern feedback error: {e}", file=sys.stderr)
        
        return None
    
    def _get_performance_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        context: Dict[str, Any],
        session_id: str
    ) -> Optional[str]:
        """Get performance optimization feedback."""
        try:
            should_optimize, optimize_reason, warnings, optimization_action = \
                check_performance_optimization(tool_name, tool_input, context)
            
            if should_optimize and optimization_action:
                feedback_type = f"performance_{tool_name}"
                
                if self.session_tracker.should_show_warning(session_id, feedback_type):
                    message = f"⚡ PERFORMANCE TIP: {optimize_reason}\n"
                    
                    if 'tool' in optimization_action:
                        message += f"   → Alternative: {optimization_action['tool']}\n"
                    if 'command' in optimization_action:
                        message += f"   → Command: {optimization_action['command']}\n"
                    if 'performance_gain' in optimization_action:
                        message += f"   → Potential gain: {optimization_action['performance_gain']}"
                    
                    return message
                    
        except (ImportError, AttributeError, TypeError, KeyError) as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Pattern feedback error: {e}", file=sys.stderr)
        
        return None
    
    def _get_recommendation_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        context: Dict[str, Any],
        session_id: str
    ) -> Optional[str]:
        """Get tool recommendation feedback."""
        try:
            recommendations = get_tool_recommendations(tool_name, tool_input, context)
            
            if recommendations:
                # Show the highest priority recommendation
                top_rec = recommendations[0]
                feedback_type = f"recommendation_{top_rec.get('type', 'general')}"
                
                if self.session_tracker.should_show_warning(session_id, feedback_type):
                    message = f"💡 {top_rec.get('title', 'Recommendation')}"
                    
                    if 'reason' in top_rec:
                        message = f"💡 TIP: {top_rec['reason']}"
                    
                    if 'suggested_action' in top_rec:
                        message += f"\n   → {top_rec['suggested_action']}"
                    
                    return message
                    
        except (ImportError, AttributeError, TypeError, KeyError) as e:
            if os.environ.get("DEBUG_HOOKS"):
                print(f"Pattern feedback error: {e}", file=sys.stderr)
        
        return None
    
    def _get_response_feedback(
        self, 
        tool_name: str, 
        tool_response: str, 
        session_id: str
    ) -> Optional[str]:
        """Get feedback based on tool response content."""
        if not tool_response or len(tool_response) < 10:
            return None
        
        response_lower = tool_response.lower()
        
        # Error-based learning opportunities
        if any(error in response_lower for error in ["error:", "failed", "exception", "traceback"]):
            feedback_type = "error_learning"
            
            if self.session_tracker.should_show_warning(session_id, feedback_type):
                return ("📚 LEARNING OPPORTUNITY: Errors are valuable for learning.\n"
                       "   → Consider using debugging agents to understand the issue\n"
                       "   → Break complex operations into smaller steps")
        
        # Success patterns
        if "successfully" in response_lower or "completed" in response_lower:
            # Occasionally provide positive reinforcement
            feedback_type = "success_pattern"
            
            if self.session_tracker.should_show_warning_check_only(session_id, feedback_type):
                # Only show this occasionally (1 in 5 chance)
                if hash(session_id + tool_name) % 5 == 0:
                    self.session_tracker.mark_warning_shown(session_id, feedback_type)
                    return ("✅ SUCCESS PATTERN: Well done!\n"
                           "   → Consider documenting successful approaches for future reference")
        
        # Large output detection
        if len(tool_response) > 5000:
            feedback_type = "large_output"
            
            if self.session_tracker.should_show_warning(session_id, feedback_type):
                return ("📊 LARGE OUTPUT DETECTED: Consider processing large data in chunks\n"
                       "   → Use pagination, filtering, or summary tools for better efficiency")
        
        return None


def handle_educational_feedback(data: Dict[str, Any]) -> int:
    """
    Main handler for educational feedback in PostToolUse.
    
    Returns:
        int: Always returns 0 (doesn't block operations)
    """
    try:
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        tool_response = data.get("tool_response", "")
        
        if not tool_name:
            return 0
        
        # Extract session information
        session_id = extract_session_id(data)
        
        # Initialize feedback system
        feedback_system = EducationalFeedbackSystem()
        
        # Get educational feedback (context will be built automatically)
        feedback = feedback_system.provide_educational_feedback(
            tool_name, tool_input, tool_response, session_id
        )
        
        if feedback:
            # Output to stderr for Claude to see
            print(feedback, file=sys.stderr)
            print("", file=sys.stderr)  # Add spacing
        
        return 0
        
    except Exception as e:
        # Log error but don't block
        print(f"Educational feedback error: {e}", file=sys.stderr)
        return 0


# For testing and direct execution
if __name__ == "__main__":
    try:
        if not sys.stdin.isatty():
            event_data = json.loads(sys.stdin.read())
            exit_code = handle_educational_feedback(event_data)
            sys.exit(exit_code)
        else:
            print("Enhanced Educational Feedback System - Use as part of PostToolUse hook")
            sys.exit(0)
    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)