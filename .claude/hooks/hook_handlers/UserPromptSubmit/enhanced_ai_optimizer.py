"""Enhanced AI-powered context optimization with improved context detection and
analysis."""

import asyncio
import logging
import re
from typing import Dict, List, Tuple

# Import the existing optimizer as base
from .ai_context_optimizer import AIContextOptimizer

logger = logging.getLogger(__name__)


class EnhancedAIOptimizer(AIContextOptimizer):
    """Enhanced version of AI context optimizer with improved capabilities."""

    def __init__(self):
        super().__init__()

        # Enhanced context detection patterns
        self.enhanced_context_patterns = {
            "git_changes": [
                r"Modified files?:\s*\n(.+)",
                r"On branch\s+(.+)",
                r"Changes to be committed:\s*\n(.+)",
            ],
            "errors_critical": [
                r"(?i)(error|exception|failed|crash).*:(.+)",
                r"❌\s*(.+)",
                r"Traceback.*\n(.+)",
            ],
            "mcp_tools": [
                r"<mcp-([^>]+)>",
                r"mcp__([^_]+)__",
                r"Available tools:\s*\n(.+)",
            ],
            "code_analysis": [
                r"<tree-sitter[^>]*>(.+?)</tree-sitter>",
                r"AST analysis:\s*\n(.+)",
                r"Functions found:\s*\n(.+)",
            ],
            "performance_hints": [
                r"PERFORMANCE[^:]*:\s*(.+)",
                r"Optimization opportunity:\s*(.+)",
                r"Slow operation detected:\s*(.+)",
            ],
            "session_context": [
                r"Session started:\s*(.+)",
                r"Previous conversation:\s*(.+)",
                r"Context history:\s*(.+)",
            ],
        }

    def _enhanced_context_detection(self, raw_context: str) -> Dict[str, List[str]]:
        """Enhanced context detection with better pattern matching."""
        detected = {}

        for category, patterns in self.enhanced_context_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, raw_context, re.MULTILINE | re.DOTALL)
                if found:
                    # Flatten nested matches and clean up
                    for match in found:
                        if isinstance(match, tuple):
                            matches.extend([m.strip() for m in match if m.strip()])
                        else:
                            matches.append(match.strip())

            if matches:
                detected[category] = matches[:5]  # Limit to 5 matches per category

        return detected

    def _generate_enhanced_questionnaire(
        self,
        user_prompt: str,
        context: str,
        detected_context: Dict[str, List[str]],
    ) -> str:
        """Generate enhanced questionnaire with context-aware questions."""
        self._analyze_prompt_with_nlp(user_prompt, context)

        # Base questionnaire from parent class
        base_questionnaire = self._generate_nlp_questionnaire(user_prompt, context)

        # Add enhanced context-specific questions
        enhancements = []

        # Git-specific questions
        if "git_changes" in detected_context:
            enhancements.append(
                "21. Git Impact: Changes affect core functionality - test thoroughly",
            )

        # Error-specific questions
        if "errors_critical" in detected_context:
            enhancements.append(
                "22. Error Context: Critical errors detected - prioritize debugging",
            )

        # MCP tool recommendations
        if "mcp_tools" in detected_context:
            tools = detected_context["mcp_tools"][:3]
            enhancements.append(
                f"23. MCP Tools Available: {', '.join(tools)} - consider using these",
            )

        # Performance context
        if "performance_hints" in detected_context:
            enhancements.append(
                "24. Performance Notes: Optimization opportunities identified",
            )

        # Code analysis context
        if "code_analysis" in detected_context:
            enhancements.append(
                "25. Code Structure: AST analysis available - use for refactoring",
            )

        if enhancements:
            # Insert enhancements before the closing ===
            enhanced = base_questionnaire.replace(
                "===\n",
                f"{'\n'.join(enhancements)}\n===\n",
            )
            return enhanced

        return base_questionnaire

    def _format_structured_context(
        self,
        raw_context: str,
        detected_context: Dict[str, List[str]],
    ) -> str:
        """Format context in a structured way for better AI processing."""
        sections = []

        # Add detected structured sections first
        for category, items in detected_context.items():
            if items:
                category_title = category.replace("_", " ").title()
                sections.append(f"## {category_title}")
                for item in items:
                    sections.append(f"- {item}")
                sections.append("")

        # Add raw context
        sections.append("## Raw Context")
        sections.append(raw_context)

        return "\n".join(sections)

    def _create_enhanced_optimization_prompt(
        self,
        user_prompt: str,
        raw_context: str,
    ) -> Tuple[str, str]:
        """Create enhanced optimization prompt with better context analysis."""
        # Get enhanced context detection
        detected_context = self._enhanced_context_detection(raw_context)

        # Build context type descriptions with detected content
        context_types = []

        if detected_context.get("git_changes"):
            context_types.append("- Git repository changes and branch information")

        if detected_context.get("errors_critical"):
            context_types.append("- Critical errors and exception details")

        if detected_context.get("mcp_tools"):
            context_types.append("- Available MCP tools and capabilities")

        if detected_context.get("code_analysis"):
            context_types.append("- Code structure analysis from tree-sitter")

        if detected_context.get("performance_hints"):
            context_types.append("- Performance optimization opportunities")

        if detected_context.get("session_context"):
            context_types.append("- Session history and conversation context")

        # Enhanced system prompt with better instructions
        system_prompt = self.config["prompts"]["system_template"]

        if context_types:
            context_section = (
                f"Context types detected:\n{chr(10).join(context_types)}\n\n"
            )
            system_prompt = system_prompt.replace(
                "Context types you may encounter:",
                f"Context types detected in this request:\n{chr(10).join(context_types)}\n\nIMPORTANT: Pay special attention to these detected context types when creating your response.\n\nGeneral context types you may encounter:",
            )

        # Enhanced user content with structured context
        user_content = f"""USER'S QUESTION:
{user_prompt}

AVAILABLE CONTEXT (Structured):
{self._format_structured_context(raw_context, detected_context)}

TASK:
Create an optimized instruction prompt that helps Claude answer the user's question effectively. 
Include ALL relevant context details that enhance understanding.
CRITICAL: Always include the complete CLAUDE CODE META ANALYSIS questionnaire with enhanced context-specific questions."""

        return system_prompt, user_content

    def _enhanced_fallback_optimization(
        self,
        user_prompt: str,
        raw_context: str,
    ) -> str:
        """Enhanced fallback with better context detection."""
        detected_context = self._enhanced_context_detection(raw_context)

        # Generate base analysis
        base_output = self._generate_base_context_analysis(user_prompt, raw_context)

        # Add enhanced questionnaire with context awareness
        enhanced_questionnaire = self._generate_enhanced_questionnaire(
            user_prompt,
            raw_context,
            detected_context,
        )

        # Add context-specific recommendations
        recommendations = []

        if detected_context.get("git_changes"):
            recommendations.append(
                "🔄 **Git Changes Detected**: Review modified files carefully before proceeding",
            )

        if detected_context.get("errors_critical"):
            recommendations.append(
                "🚨 **Critical Errors Found**: Address errors before implementing new features",
            )

        if detected_context.get("mcp_tools"):
            tools = detected_context["mcp_tools"][:3]
            recommendations.append(
                f"🛠️ **MCP Tools Available**: Consider using {', '.join(tools)}",
            )

        if detected_context.get("performance_hints"):
            recommendations.append(
                "⚡ **Performance Opportunities**: Optimization suggestions available",
            )

        if recommendations:
            base_output += (
                f"\n\n**ENHANCED RECOMMENDATIONS:**\n{'\n'.join(recommendations)}\n"
            )

        return base_output + enhanced_questionnaire

    async def optimize_context(self, user_prompt: str, raw_context: str) -> str:
        """Enhanced context optimization with better AI prompting."""
        context_size_before = len(raw_context)
        logger.info(
            f"Starting enhanced context optimization: input_size={context_size_before} chars",
        )

        # Use enhanced prompt creation
        system_prompt, user_content = self._create_enhanced_optimization_prompt(
            user_prompt,
            raw_context,
        )

        # Try AI optimization with enhanced prompts
        result = await self._call_openrouter(
            system_prompt,
            user_content,
            self.openrouter_config["default_model"],
        )

        if result:
            context_size_after = len(result)
            logger.info(
                f"Enhanced AI optimization SUCCESS: size_change={context_size_after - context_size_before} chars",
            )
            return f"<!-- Context optimized by Enhanced AI ({self.openrouter_config['default_model']}) -->\n{result}"

        # Try fallback models
        for fallback_model in self.openrouter_config["fallback_models"]:
            logger.info(f"Trying fallback model: {fallback_model}")
            result = await self._call_openrouter(
                system_prompt,
                user_content,
                fallback_model,
            )
            if result:
                context_size_after = len(result)
                logger.info(
                    f"Fallback model {fallback_model} SUCCESS: size_change={context_size_after - context_size_before} chars",
                )
                return f"<!-- Context optimized by Enhanced AI ({fallback_model}) -->\n{result}"

        # Enhanced fallback
        logger.warning("All AI models failed, using enhanced rule-based fallback")
        result = self._enhanced_fallback_optimization(user_prompt, raw_context)
        context_size_after = len(result)
        logger.info(
            f"Enhanced fallback completed: size_change={context_size_after - context_size_before} chars",
        )
        return result


# Async and sync entry points
async def optimize_injection_with_enhanced_ai(
    user_prompt: str,
    raw_context: str,
) -> str:
    """Enhanced AI-powered context optimization."""
    logger.info("Starting enhanced AI context optimization workflow")
    optimizer = EnhancedAIOptimizer()

    try:
        timeout = optimizer.config["openrouter"]["timeout"]
        optimized = await asyncio.wait_for(
            optimizer.optimize_context(user_prompt, raw_context),
            timeout=timeout,
        )
        return optimized
    except asyncio.TimeoutError:
        logger.error("Enhanced AI context optimization TIMEOUT")
        # Enhanced fallback instead of raw context
        optimizer = EnhancedAIOptimizer()
        return optimizer._enhanced_fallback_optimization(user_prompt, raw_context)
    except Exception as e:
        logger.error(f"Enhanced AI context optimization ERROR: {str(e)}")
        # Enhanced fallback instead of raw context
        optimizer = EnhancedAIOptimizer()
        return optimizer._enhanced_fallback_optimization(user_prompt, raw_context)


def optimize_injection_enhanced_sync(user_prompt: str, raw_context: str) -> str:
    """Enhanced synchronous wrapper for the async optimization."""
    try:
        try:
            asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(
                        optimize_injection_with_enhanced_ai(user_prompt, raw_context),
                    ),
                )
                optimizer = EnhancedAIOptimizer()
                sync_timeout = optimizer.config["openrouter"]["sync_timeout"]
                return future.result(timeout=sync_timeout)
        except RuntimeError:
            return asyncio.run(
                optimize_injection_with_enhanced_ai(user_prompt, raw_context),
            )
    except Exception as e:
        logger.error(f"Enhanced sync optimization FAILED: {str(e)}")
        # Enhanced fallback
        optimizer = EnhancedAIOptimizer()
        return optimizer._enhanced_fallback_optimization(user_prompt, raw_context)
