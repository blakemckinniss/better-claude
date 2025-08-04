#!/usr/bin/env python3
"""Educational feedback system for PostToolUse hook using shared intelligence.

This module provides intelligent educational feedback to Claude after tool operations
complete successfully, leveraging the intelligence components from the shared layer.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add shared intelligence to path
shared_intelligence_path = Path(__file__).parent.parent.parent / "shared_intelligence"
if str(shared_intelligence_path) not in sys.path:
    sys.path.insert(0, str(shared_intelligence_path))

try:
    from shared_intelligence import (
        get_intelligence_analysis,
        format_educational_feedback,
    )
    HAS_SHARED_INTELLIGENCE = True
except ImportError:
    HAS_SHARED_INTELLIGENCE = False


class EducationalFeedbackProvider:
    """Provides educational feedback using shared intelligence components."""
    
    def __init__(self):
        self.feedback_enabled = HAS_SHARED_INTELLIGENCE
        
    def generate_feedback(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any], 
        tool_response: str,
        outcome: str = "success"
    ) -> Optional[str]:
        """Generate educational feedback for a completed tool operation."""
        
        if not self.feedback_enabled:
            return None
            
        try:
            # Get comprehensive intelligence analysis
            analysis = get_intelligence_analysis(tool_name, tool_input)
            
            # Format as educational feedback
            feedback = format_educational_feedback(analysis, tool_name, outcome)
            
            # Add tool-specific insights
            additional_feedback = self._get_tool_specific_feedback(
                tool_name, tool_input, tool_response, analysis
            )
            
            if additional_feedback:
                if feedback:
                    feedback += "\n" + additional_feedback
                else:
                    feedback = additional_feedback
                    
            return feedback if feedback else None
            
        except Exception as e:
            # Don't fail operations due to feedback errors
            return f"📊 Intelligence feedback temporarily unavailable: {str(e)}"
    
    def _get_tool_specific_feedback(
        self,
        tool_name: str,
        tool_input: Dict[str, Any], 
        tool_response: str,
        analysis: Dict[str, Any]
    ) -> Optional[str]:
        """Generate tool-specific educational feedback."""
        
        feedback_lines = []
        
        # Bash command insights
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            
            # Check for common patterns
            if any(old_cmd in command for old_cmd in ["grep", "find", "cat", "ls"]):
                feedback_lines.append("🔧 Command Optimization:")
                feedback_lines.append("  • Consider modern alternatives for better performance")
                
            # Check for complex bash operations
            if len(command) > 100 or "&&" in command or "|" in command:
                feedback_lines.append("🎯 Complex Operation Detected:")
                feedback_lines.append("  • Consider using specialized agents for multi-step tasks")
                feedback_lines.append("  • Task tool can delegate to expert subagents")
        
        # File operation insights
        elif tool_name in ["Read", "Write", "Edit"]:
            file_path = tool_input.get("file_path", "")
            
            if file_path:
                file_ext = Path(file_path).suffix
                
                # Python file insights
                if file_ext == ".py":
                    feedback_lines.append("🐍 Python Development:")
                    feedback_lines.append("  • Consider using python-expert agent for complex Python tasks")
                    
                # Configuration file insights
                elif file_ext in [".json", ".yaml", ".yml", ".toml"]:
                    feedback_lines.append("⚙️ Configuration Management:")
                    feedback_lines.append("  • Consider using config-manager agent for complex configurations")
        
        # MCP tool insights
        elif tool_name.startswith("mcp__"):
            feedback_lines.append("🔌 MCP Tool Usage:")
            feedback_lines.append("  • MCP tools provide enhanced capabilities and error handling")
            
        return "\n".join(feedback_lines) if feedback_lines else None


# Global instance
_feedback_provider: Optional[EducationalFeedbackProvider] = None


def get_feedback_provider() -> EducationalFeedbackProvider:
    """Get the global educational feedback provider."""
    global _feedback_provider
    if _feedback_provider is None:
        _feedback_provider = EducationalFeedbackProvider()
    return _feedback_provider


def provide_educational_feedback(
    tool_name: str,
    tool_input: Dict[str, Any], 
    tool_response: str,
    outcome: str = "success"
) -> bool:
    """Provide educational feedback to Claude via stderr.
    
    Returns True if feedback was provided, False otherwise.
    """
    try:
        provider = get_feedback_provider()
        feedback = provider.generate_feedback(tool_name, tool_input, tool_response, outcome)
        
        if feedback:
            print(f"\n{feedback}", file=sys.stderr)
            return True
            
        return False
        
    except Exception as e:
        # Don't fail operations due to feedback errors
        print(f"\nWarning: Educational feedback error: {e}", file=sys.stderr)
        return False


def should_provide_feedback(tool_name: str, outcome: str) -> bool:
    """Determine if educational feedback should be provided for this tool/outcome."""
    
    # Only provide feedback for successful operations
    if outcome != "success":
        return False
        
    # Provide feedback for tools that commonly have optimization opportunities
    educational_tools = {
        "Bash",
        "Read", 
        "Write", 
        "Edit",
        "Grep",
        "Glob",
    }
    
    # Also include MCP tools
    if tool_name.startswith("mcp__"):
        return True
        
    return tool_name in educational_tools