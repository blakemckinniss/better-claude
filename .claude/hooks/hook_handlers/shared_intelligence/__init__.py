"""Shared Intelligence Components for Hook System.

This package contains intelligence components that can be used by both
PreToolUse (for blocking/routing) and PostToolUse (for educational feedback).

Components:
- intelligent_router: Analyzes tools for optimizations and routing
- anti_pattern_detector: Detects workflow anti-patterns
- performance_optimizer: Identifies performance optimization opportunities
- recommendation_engine: Provides tool recommendations
"""

from .anti_pattern_detector import analyze_workflow_patterns
from .intelligent_router import analyze_tool_for_routing
from .performance_optimizer import check_performance_optimization
from .recommendation_engine import get_tool_recommendations

__all__ = [
    "analyze_tool_for_routing",
    "analyze_workflow_patterns", 
    "check_performance_optimization",
    "get_tool_recommendations",
]
