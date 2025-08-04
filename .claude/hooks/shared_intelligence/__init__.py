#!/usr/bin/env python3
"""Shared intelligence components for Claude hooks system.

This module provides shared intelligence components that can be used by both
PreToolUse and PostToolUse hooks, enabling proper separation of concerns:

- PreToolUse: Uses intelligence for security blocking and routing
- PostToolUse: Uses intelligence for educational feedback to Claude

Components:
- intelligent_router: Core routing engine with tool optimization
- recommendation_engine: Proactive tool suggestions and best practices
- performance_optimizer: Performance monitoring and circuit breakers
- anti_pattern_detector: Advanced workflow pattern analysis
"""

from .anti_pattern_detector import (
    AntiPatternDetector,
    analyze_workflow_patterns, get_detector,
)
from .config import SharedIntelligenceConfig, get_config, reload_config
from .intelligent_router import (
    IntelligentRouter, analyze_tool_for_routing,
    get_router,
)
from .performance_optimizer import (
    PerformanceOptimizer,
    check_performance_optimization,
    get_optimizer,
)
from .recommendation_engine import (
    RecommendationEngine,
    get_recommendation_engine,
    get_tool_recommendations,
)

__all__ = [
    # Configuration
    "get_config",
    "reload_config", 
    "SharedIntelligenceConfig",
    
    # Intelligent Router
    "get_router",
    "analyze_tool_for_routing",
    "IntelligentRouter",
    
    # Recommendation Engine
    "get_recommendation_engine",
    "get_tool_recommendations",
    "RecommendationEngine",
    
    # Performance Optimizer
    "get_optimizer",
    "check_performance_optimization",
    "PerformanceOptimizer",
    
    # Anti-Pattern Detector
    "get_detector",
    "analyze_workflow_patterns",
    "AntiPatternDetector",
]


# Convenience functions for easy integration
def get_intelligence_analysis(tool_name: str, tool_input: dict, context: dict = None) -> dict:
    """Get comprehensive intelligence analysis for a tool request.

    Returns a combined analysis from all intelligence components.
    """
    analysis = {
        "routing": None,
        "recommendations": [],
        "performance": None,
        "anti_patterns": None,
        "should_block": False,
        "warnings": [],
        "suggestions": [],
    }
    
    try:
        # Routing analysis
        routing_result = analyze_tool_for_routing(tool_name, tool_input, context)
        if routing_result[0]:  # Should redirect
            analysis["routing"] = {
                "should_redirect": True,
                "reason": routing_result[1],
                "alternative": routing_result[3],
            }
            analysis["should_block"] = True
        analysis["warnings"].extend(routing_result[2])
        
        # Recommendations
        recommendations = get_tool_recommendations(tool_name, tool_input, context)
        analysis["recommendations"] = recommendations
        
        # Performance analysis
        perf_result = check_performance_optimization(tool_name, tool_input, context)
        if perf_result[0]:  # Should optimize
            analysis["performance"] = {
                "should_optimize": True,
                "reason": perf_result[1],
                "optimization": perf_result[3],
            }
            if perf_result[3] and perf_result[3].get("tool") != tool_name:
                analysis["should_block"] = True
        analysis["warnings"].extend(perf_result[2])
        
        # Anti-pattern analysis
        pattern_result = analyze_workflow_patterns(tool_name, tool_input, context)
        if pattern_result[0]:  # Should block
            analysis["anti_patterns"] = {
                "should_block": True,
                "reason": pattern_result[1],
                "alternative": pattern_result[3],
            }
            analysis["should_block"] = True
        analysis["warnings"].extend(pattern_result[2])
        
        # Consolidate suggestions
        for rec in recommendations:
            if rec.get("type") == "workflow_optimization":
                analysis["suggestions"].append(rec.get("title", ""))
        
    except Exception as e:
        analysis["error"] = str(e)
    
    return analysis


def format_educational_feedback(analysis: dict, tool_name: str, outcome: str = "success") -> str:
    """Format intelligence analysis as educational feedback for Claude.

    This function is designed for PostToolUse to provide educational feedback via stderr
    when tools complete successfully.
    """
    feedback_lines = []
    
    if outcome == "success" and analysis.get("recommendations"):
        feedback_lines.append("💡 Tool Usage Insights:")
        
        for rec in analysis["recommendations"][:2]:  # Limit to top 2
            rec_type = rec.get("type", "general")
            title = rec.get("title", "Recommendation available")
            
            if rec_type == "modern_cli":
                feedback_lines.append(f"  • {title}")
                if "example" in rec:
                    feedback_lines.append(f"    Example: {rec['example']}")
                    
            elif rec_type == "workflow_optimization":
                feedback_lines.append(f"  • {title}")
                if "examples" in rec and rec["examples"]:
                    feedback_lines.append(f"    Try: {rec['examples'][0]}")
    
    if analysis.get("warnings"):
        feedback_lines.append("⚠️ Performance Notes:")
        for warning in analysis["warnings"][:2]:  # Limit warnings
            feedback_lines.append(f"  • {warning}")
    
    if analysis.get("suggestions"):
        feedback_lines.append("🚀 Optimization Opportunities:")
        for suggestion in analysis["suggestions"][:2]:
            feedback_lines.append(f"  • {suggestion}")
    
    return "\n".join(feedback_lines) if feedback_lines else ""
