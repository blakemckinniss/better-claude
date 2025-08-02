"""AI-powered context optimization for ultimate prompt engineering."""

import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# Logging will be configured from JSON config
logger = logging.getLogger(__name__)

# Try to import spacy - it's assumed to be available
try:
    import spacy
    from spacy.matcher import Matcher

    SPACY_AVAILABLE = True
except ImportError:
    logger.warning("spaCy not available - using fallback analysis")
    SPACY_AVAILABLE = False


class AIContextOptimizer:
    """Uses AI to reformulate and optimize context injections."""

    def _setup_nlp_patterns(self):
        """Set up spaCy matcher patterns for common programming concepts."""
        if not self.nlp:
            return

        patterns_config = self.config["spacy"]["patterns"]

        # Pattern for urgency detection
        urgency_pattern = [
            {
                "LOWER": {"IN": patterns_config["urgency"]},
            },
        ]
        self.matcher.add("URGENCY", [urgency_pattern])

        # Pattern for technical debt
        debt_pattern = [
            {
                "LOWER": {"IN": patterns_config["tech_debt"]},
                "POS": {"IN": ["ADJ", "ADV"]},
            },
            {"LOWER": "fix", "POS": "NOUN", "OP": "?"},
        ]
        self.matcher.add("TECH_DEBT", [debt_pattern])

        # Pattern for framework/library mentions
        framework_pattern = [
            {
                "ORTH": {"IN": patterns_config["frameworks"]},
            },
        ]
        self.matcher.add("FRAMEWORK", [framework_pattern])

    def _init_nlp_analyzer(self):
        """Initialize spaCy NLP analyzer for intelligent questionnaire generation."""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available - NLP analysis disabled")
            self.nlp = None
            return

        try:
            # Load the English model
            model_name = self.config["spacy"]["model"]
            self.nlp = spacy.load(model_name)
            logger.info(f"spaCy model '{model_name}' loaded successfully")

            # Initialize matcher for pattern detection
            self.matcher = Matcher(self.nlp.vocab)
            self._setup_nlp_patterns()

        except OSError:
            logger.error(
                f"spaCy model not found. Install with: python -m spacy download {self.config['spacy']['model']}",
            )
            self.nlp = None

    def _configure_logging(self):
        """Configure logging from JSON config."""
        if "logging" in self.config:
            log_config = self.config["logging"]

            # Map string level to logging constant
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }

            level = level_map.get(log_config.get("level", "INFO"), logging.INFO)
            format_str = log_config.get(
                "format",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

            # Configure basic logging to stderr to avoid interfering with hook JSON output
            logging.basicConfig(
                stream=sys.stderr,
                level=level,
                format=format_str,
                datefmt="%Y-%m-%d %H:%M:%S",
                force=True,  # Override any existing configuration
            )

    def __init__(self):
        # Load configuration from JSON file
        config_path = os.path.join(
            os.path.dirname(__file__),
            "ai_optimizer_config.json",
        )
        try:
            with open(config_path) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise

        # Configure logging from config
        self._configure_logging()

        # Set up OpenRouter configuration
        self.openrouter_config = {
            **self.config["openrouter"],
            "api_key": os.environ.get("OPENROUTER_API_KEY"),
        }

        # Initialize NLP analyzer if spaCy is available
        self._init_nlp_analyzer()

    def _create_optimization_prompt(
        self,
        user_prompt: str,
        raw_context: str,
    ) -> Tuple[str, str]:
        """Create system and user prompts for the context optimization AI."""
        # Check if context contains special data types
        has_firecrawl = "<firecrawl-context>" in raw_context
        has_git = "git" in raw_context.lower() or "branch:" in raw_context.lower()
        has_mcp = "<mcp-" in raw_context or "MCP_" in raw_context
        has_tree_sitter = "<tree-sitter" in raw_context
        has_zen = "<zen-" in raw_context
        has_errors = any(
            word in raw_context.lower()
            for word in ["error", "fail", "critical", "warning"]
        )
        has_session = "session" in raw_context.lower() or "SessionStart" in raw_context

        # Build context type descriptions
        context_types = []
        if has_git:
            context_types.append(
                "- Git repository information (branches, commits, status)",
            )
        if has_mcp:
            context_types.append("- MCP tool descriptions and capabilities")
        if has_firecrawl:
            context_types.append("- Web search results or scraped content")
        if has_tree_sitter:
            context_types.append("- Code analysis from tree-sitter")
        if has_zen:
            context_types.append("- ZEN agent recommendations")
        if has_errors:
            context_types.append("- Errors, warnings, or issues")
        if has_session:
            context_types.append("- Session information and history")

        # Get system prompt template and add context types
        system_prompt = self.config["prompts"]["system_template"]
        if context_types:
            context_section = (
                f"Context types you may encounter:\n{'\n'.join(context_types)}\n\n"
            )
            # Insert context types after the "Context types you may encounter:" placeholder
            system_prompt = system_prompt.replace(
                "Context types you may encounter:",
                context_section,
            )

        # Create user content from template
        user_content = self.config["prompts"]["user_template"].format(
            user_prompt=user_prompt,
            raw_context=raw_context,
        )

        return system_prompt, user_content

    async def _call_openrouter(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call OpenRouter API with system and user prompts."""
        if not self.openrouter_config["api_key"]:
            logger.warning("OpenRouter API key not configured")
            return None

        # Use provided model or default
        if model is None:
            model = self.openrouter_config["default_model"]

        logger.info(f"Attempting OpenRouter API call with model: {model}")
        api_start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.openrouter_config['api_key']}",
            **self.config["api"]["headers"],
        }

        # Build messages with system and user prompts
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        data = {
            "model": model,
            "messages": messages,
            "temperature": self.openrouter_config["temperature"],
            "max_tokens": self.openrouter_config["max_tokens"],
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.openrouter_config["url"],
                    headers=headers,
                    json=data,
                ) as response:
                    api_duration = time.time() - api_start_time

                    if response.status == 200:
                        result = await response.json()
                        # Safely access nested dictionary with error handling
                        if "choices" in result and len(result["choices"]) > 0:
                            choice = result["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                                logger.info(
                                    f"OpenRouter API SUCCESS: model={model}, duration={api_duration:.2f}s, response_len={len(content)}",
                                )
                                return content
                        logger.error(
                            f"OpenRouter API malformed response: model={model}, structure={result}",
                        )
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"OpenRouter API FAILURE: model={model}, status={response.status}, duration={api_duration:.2f}s, error={error_text}",
                        )
            except Exception as e:
                api_duration = time.time() - api_start_time
                logger.error(
                    f"OpenRouter API EXCEPTION: model={model}, duration={api_duration:.2f}s, error={str(e)}",
                )
        return None

    def _generate_base_context_analysis(
        self,
        user_prompt: str,
        raw_context: str,
    ) -> str:
        """Generate base context analysis without questionnaire."""
        lines = raw_context.strip().split("\n")

        # Simple rule-based prioritization
        priority_keywords = self.config["analysis"]["priority_keywords"]
        priority_lines = []
        normal_lines = []

        for line in lines:
            if any(keyword in line.lower() for keyword in priority_keywords):
                priority_lines.append(line)
            else:
                normal_lines.append(line)

        # Identify different types of injected content
        context_sections = {
            "git": [],
            "mcp": [],
            "zen": [],
            "tree_sitter": [],
            "firecrawl": [],
            "errors": priority_lines,
            "session": [],
            "other": [],
        }

        for line in lines:
            line_lower = line.lower()
            if "git" in line_lower or "branch:" in line_lower:
                context_sections["git"].append(line)
            elif "<mcp-" in line or "MCP_" in line:
                context_sections["mcp"].append(line)
            elif "<zen-" in line:
                context_sections["zen"].append(line)
            elif "<tree-sitter" in line:
                context_sections["tree_sitter"].append(line)
            elif "<firecrawl" in line:
                context_sections["firecrawl"].append(line)
            elif "session" in line_lower or "SessionStart" in line:
                context_sections["session"].append(line)
            elif line not in priority_lines:
                context_sections["other"].append(line)

        # Create an enhanced prompt using rule-based approach
        output = "<!-- Context optimized by rules (AI unavailable) -->\n\n"
        output += f"**User Question**: {user_prompt}\n\n"

        # Add relevant context sections
        if context_sections["errors"]:
            output += "**Important Issues Found**:\n"
            for line in context_sections["errors"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if context_sections["git"]:
            output += "**Git Context**:\n"
            for line in context_sections["git"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if context_sections["mcp"]:
            output += "**Available MCP Tools**:\n"
            for line in context_sections["mcp"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if context_sections["zen"]:
            output += "**ZEN Agent Recommendations**:\n"
            for line in context_sections["zen"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if context_sections["firecrawl"]:
            output += "**Web Search Results**:\n"
            for line in context_sections["firecrawl"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if context_sections["session"]:
            output += "**Session Information**:\n"
            for line in context_sections["session"][
                : self.config["display"]["max_context_sections"]
            ]:
                output += f"- {line.strip()}\n"
            output += "\n"

        # Add guidance based on question type
        output += "**Approach**: "
        question_lower = user_prompt.lower()
        if any(
            word in question_lower
            for word in ["error", "bug", "fix", "issue", "problem"]
        ):
            output += (
                "Focus on debugging and error resolution using the context above.\n"
            )
        elif any(
            word in question_lower for word in ["implement", "create", "build", "add"]
        ):
            output += "Use the available tools and context to implement the requested feature.\n"
        elif any(word in question_lower for word in ["explain", "what", "how", "why"]):
            output += (
                "Provide a clear explanation using any relevant context available.\n"
            )
        else:
            output += "Address the user's request using the context provided above.\n"

        return output

    def _analyze_prompt_fallback(
        self,
        user_prompt: str,
        context: str,
    ) -> Dict[str, Any]:
        """Fallback analysis when spaCy is not available."""
        prompt_lower = user_prompt.lower()
        task_categories = self.config["task_categories"]
        risk_indicators = self.config["risk_indicators"]

        # Simple keyword-based analysis
        task_types = []
        for category, keywords in task_categories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                task_types.append(category)

        # Simple complexity assessment
        complexity = "simple"
        if len(user_prompt.split()) > 20:
            complexity = "moderate"
        tech_terms = self.config["analysis"]["tech_terms"]
        if any(word in prompt_lower for word in tech_terms):
            complexity = "complex"

        # Simple risk detection
        risks = []
        for risk_type, indicators in risk_indicators.items():
            if any(indicator in prompt_lower for indicator in indicators):
                risks.append(risk_type)

        return {
            "task_type": task_types if task_types else ["general"],
            "complexity": complexity,
            "urgency": any(
                word in prompt_lower
                for word in self.config["spacy"]["patterns"]["urgency"]
            ),
            "risks": risks,
            "systems": [],
            "technical_concepts": [],
            "has_errors": "error" in context.lower() if context else False,
        }

    def _identify_task_type(self, doc) -> List[str]:
        """Identify the type of task based on verb analysis and keywords."""
        task_types = []
        doc_lower = doc.text.lower()
        task_categories = self.config["task_categories"]

        for category, keywords in task_categories.items():
            if any(keyword in doc_lower for keyword in keywords):
                task_types.append(category)

        return task_types if task_types else ["general"]

    def _assess_complexity(self, doc) -> str:
        """Assess task complexity based on linguistic features."""
        doc_lower = doc.text.lower()
        complexity_indicators = self.config["complexity_indicators"]

        # Check for explicit complexity indicators
        for level, indicators in complexity_indicators.items():
            if any(indicator in doc_lower for indicator in indicators):
                return level

        # Use heuristics based on sentence structure
        complexity_score = 0

        # Longer sentences often indicate more complex requirements
        if len(doc) > 20:
            complexity_score += 1
        if len(doc) > 40:
            complexity_score += 1

        # Technical terms increase complexity
        tech_terms = self.config["analysis"]["tech_terms"]
        complexity_score += sum(1 for term in tech_terms if term in doc_lower)

        # Map score to complexity level
        if complexity_score <= 1:
            return "simple"
        elif complexity_score <= 3:
            return "moderate"
        else:
            return "complex"

    def _detect_urgency(self, doc) -> bool:
        """Detect if the request is urgent."""
        if not self.nlp:
            return False

        # Check matcher patterns
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            if self.nlp.vocab.strings[match_id] == "URGENCY":
                return True
        return False

    def _identify_risks(self, doc) -> List[str]:
        """Identify potential risks in the request."""
        risks = []
        doc_lower = doc.text.lower()
        risk_indicators = self.config["risk_indicators"]

        for risk_type, indicators in risk_indicators.items():
            if any(indicator in doc_lower for indicator in indicators):
                risks.append(risk_type)

        # Check for technical debt patterns
        if self.nlp:
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                if self.nlp.vocab.strings[match_id] == "TECH_DEBT":
                    if "technical_debt" not in risks:
                        risks.append("technical_debt")

        return risks

    def _identify_systems(self, doc) -> List[str]:
        """Identify system components mentioned in the prompt."""
        systems = []
        system_patterns = self.config["analysis"]["system_patterns"]

        for pattern in system_patterns:
            if pattern in doc.text.lower():
                systems.append(pattern)

        return list(set(systems))

    def _extract_technical_concepts(self, doc) -> List[str]:
        """Extract technical concepts and technologies mentioned."""
        concepts = []

        # Check for framework/library matches
        if self.nlp:
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                if self.nlp.vocab.strings[match_id] == "FRAMEWORK":
                    concepts.append(doc[start:end].text)

        # Look for technical nouns
        tech_keywords = self.config["analysis"]["tech_keywords"]
        for token in doc:
            if token.text.lower() in tech_keywords:
                concepts.append(token.text)

        return list(set(concepts))

    def _detect_errors_in_context(self, context: str) -> bool:
        """Detect if the context contains error messages."""
        error_patterns = self.config["analysis"]["error_patterns"]
        context_lower = context.lower()
        return any(re.search(pattern, context_lower) for pattern in error_patterns)

    def _analyze_prompt_with_nlp(
        self,
        user_prompt: str,
        context: str,
    ) -> Dict[str, Any]:
        """Analyze the prompt using NLP to extract insights."""
        if not self.nlp:
            return self._analyze_prompt_fallback(user_prompt, context)

        # Process the prompt
        doc = self.nlp(user_prompt)

        analysis = {
            "task_type": self._identify_task_type(doc),
            "complexity": self._assess_complexity(doc),
            "urgency": self._detect_urgency(doc),
            "risks": self._identify_risks(doc),
            "systems": self._identify_systems(doc),
            "technical_concepts": self._extract_technical_concepts(doc),
        }

        # Enhance with context analysis
        if context:
            analysis["has_errors"] = self._detect_errors_in_context(context)

        return analysis

    def _generate_nlp_questionnaire(self, user_prompt: str, context: str) -> str:
        """Generate the questionnaire based on NLP analysis."""
        analysis = self._analyze_prompt_with_nlp(user_prompt, context)
        questionnaire_config = self.config["questionnaire"]

        # Map analysis to questionnaire responses
        output = "\n=== CLAUDE CODE META ANALYSIS ===\n"

        # 1. Confidence Level
        confidence_config = questionnaire_config["confidence_levels"]
        confidence = confidence_config["base"]
        if analysis["urgency"]:
            confidence -= confidence_config["urgency_penalty"]
        if analysis["complexity"] == "complex":
            confidence -= confidence_config["complexity_penalty"]
        if len(analysis.get("entities", [])) > 2:
            confidence += confidence_config["entity_bonus"]
        output += f"1. Confidence Level: {confidence}/10\n"

        # 2. Additional Information Needed
        info_needed = []
        if (
            not analysis["technical_concepts"]
            and "implementation" in analysis["task_type"]
        ):
            info_needed.append("specific technology stack preferences")
        if analysis["has_errors"]:
            info_needed.append("detailed error messages and stack traces")
        if "migration" in analysis["task_type"]:
            info_needed.append("current and target versions")

        output += f"2. Additional Information Needed: {', '.join(info_needed) if info_needed else 'None immediately apparent'}\n"

        # 3. Primary Concerns
        concerns = []
        if "security" in analysis["risks"]:
            concerns.append("security implications require careful review")
        if "data_loss" in analysis["risks"]:
            concerns.append("data loss risk - ensure backups exist")
        if analysis["urgency"] and "technical_debt" in analysis["risks"]:
            concerns.append("rushing may create technical debt")
        if not concerns:
            concerns.append("code quality and maintainability")

        output += f"3. Primary Concerns: {concerns[0]}\n"

        # 4. Proposed Next Steps
        output += "4. Proposed Next Steps:\n"
        if "debugging" in analysis["task_type"]:
            steps = [
                "Analyze error messages and logs",
                "Identify root cause",
                "Implement fix",
                "Add tests to prevent regression",
            ]
        elif "implementation" in analysis["task_type"]:
            steps = [
                "Define requirements clearly",
                "Design solution architecture",
                "Implement core functionality",
                "Add comprehensive tests",
            ]
        else:
            steps = [
                "Understand requirements",
                "Plan approach",
                "Execute changes",
                "Verify functionality",
            ]

        for i, step in enumerate(steps, 1):
            output += f"   {i}. {step}\n"

        # 5-20. Continue with remaining questions using config
        frameworks = self.config["spacy"]["patterns"]["frameworks"]
        web_research = (
            any(tc in frameworks for tc in analysis["technical_concepts"])
            or "migration" in analysis["task_type"]
        )
        output += f"5. Web Research Recommended: {'Yes' if web_research else 'No'}\n"

        context7 = (
            bool(analysis["technical_concepts"])
            or "implementation" in analysis["task_type"]
        )
        output += f"6. Context7 Documentation Needed: {'Yes' if context7 else 'No'}\n"

        zen_advised = (
            analysis["complexity"] == "complex"
            or "architecture" in analysis["task_type"]
        )
        output += f"7. ZEN Consultation Advised: {'Yes' if zen_advised else 'No'}\n"

        complexity_map = questionnaire_config["complexity_map"]
        output += f"8. Task Complexity Assessment: {complexity_map.get(analysis['complexity'], 'Moderate')}\n"

        time_map = questionnaire_config["time_map"]
        output += (
            f"9. Estimated Time: {time_map.get(analysis['complexity'], '1-2 hours')}\n"
        )

        alternatives = []
        if "technical_debt" in analysis["risks"]:
            alternatives.append("consider proper refactoring instead of quick fix")
        output += f"10. Alternative Approaches: {alternatives[0] if alternatives else 'None immediately apparent'}\n"

        parallel = []
        if len(analysis["task_type"]) > 1:
            parallel.extend([f"{task} work" for task in analysis["task_type"]])
        output += f"11. Parallelizable Components: {', '.join(parallel) if parallel else 'None identified'}\n"

        # 12. Subagent Recommendations
        task_to_agent = questionnaire_config["task_to_agent"]
        subagents = []
        for task in analysis["task_type"]:
            if task in task_to_agent:
                subagents.append(task_to_agent[task])

        output += f"12. Subagent Recommendations: {', '.join(subagents) if subagents else 'None required'}\n"

        # 13-20: Remaining questionnaire items
        output += f"13. Warnings/Hidden Risks: {', '.join(analysis['risks']) if analysis['risks'] else 'None identified'}\n"
        output += f"14. Counter-Arguments: {'Consider long-term maintainability' if analysis['urgency'] else 'None'}\n"
        output += f"15. Technical Debt Impact: {'Creating' if 'technical_debt' in analysis['risks'] else 'Neutral'}\n"

        # Risk level calculation
        risk_config = questionnaire_config["risk_levels"]
        risk_level = (
            risk_config["base"]
            + len(analysis["risks"]) * risk_config["per_risk_multiplier"]
        )
        if analysis["urgency"]:
            risk_level += risk_config["urgency_bonus"]
        risk_level = min(risk_level, risk_config["max_risk"])
        output += f"16. Risk Level: {risk_level}/10\n"

        systems = analysis["systems"] if analysis["systems"] else ["To be determined"]
        output += f"17. Affected Systems: {', '.join(systems)}\n"

        output += f"18. Bias/Anti-Pattern Check: {'Yes' if 'technical_debt' in analysis['risks'] else 'No'}\n"
        output += f"19. Better Approach Available: {'Yes' if 'technical_debt' in analysis['risks'] else 'No'}\n"
        output += "20. Clarifying Questions: None at this time\n"
        output += "===\n"

        return output

    def _generate_keyword_based_fallback(
        self,
        user_prompt: str,
        raw_context: str,
    ) -> str:
        """Generate fallback with keyword-based questionnaire."""
        output = self._generate_base_context_analysis(user_prompt, raw_context)

        # Add the questionnaire with smart defaults based on the prompt
        output += "\n=== CLAUDE CODE META ANALYSIS ===\n"

        # Analyze prompt complexity
        question_lower = user_prompt.lower()
        task_categories = self.config["task_categories"]
        self.config["spacy"]["patterns"]["urgency"]

        # Parse context for error detection
        lines = raw_context.strip().split("\n")
        priority_keywords = self.config["analysis"]["priority_keywords"]
        priority_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in priority_keywords):
                priority_lines.append(line)

        context_sections = {"errors": priority_lines}

        # Determine characteristics
        is_complex = any(
            word in question_lower for word in self.config["analysis"]["tech_terms"]
        )
        is_debug = any(word in question_lower for word in task_categories["debugging"])
        is_security = any(
            word in question_lower for word in task_categories["security"]
        )
        is_library = any(
            word in question_lower
            for word in ["library", "update", "version", "upgrade"]
            + self.config["spacy"]["patterns"]["frameworks"]
        )
        is_quick = any(
            word in question_lower for word in ["quick", "simple", "just", "only"]
        )
        is_delete = any(
            word in question_lower
            for word in self.config["risk_indicators"]["data_loss"]
        )
        is_hack = any(
            word in question_lower
            for word in self.config["spacy"]["patterns"]["tech_debt"]
        )

        # Generate questionnaire responses using config
        questionnaire_config = self.config["questionnaire"]

        # 1. Confidence Level
        if is_debug and context_sections["errors"]:
            output += "1. Confidence Level: 8/10 (clear error context available)\n"
        elif is_complex:
            output += "1. Confidence Level: 6/10 (complex task requires analysis)\n"
        else:
            output += "1. Confidence Level: 7/10\n"

        # 2. Additional Information Needed
        if is_library:
            output += "2. Additional Information Needed: Current version details, breaking changes documentation\n"
        elif is_debug and not context_sections["errors"]:
            output += "2. Additional Information Needed: Error logs, stack traces, reproduction steps\n"
        else:
            output += "2. Additional Information Needed: None immediately apparent\n"

        # 3. Primary Concerns
        if is_security:
            output += (
                "3. Primary Concerns: security implications require careful review\n"
            )
        elif is_delete:
            output += "3. Primary Concerns: data loss risk - ensure backups exist\n"
        elif is_hack:
            output += (
                "3. Primary Concerns: creating technical debt with temporary solution\n"
            )
        else:
            output += "3. Primary Concerns: code quality and maintainability\n"

        # 4. Proposed Next Steps
        output += "4. Proposed Next Steps:\n"
        if is_debug:
            output += "   1. Analyze error messages and stack traces\n"
            output += "   2. Identify root cause\n"
            output += "   3. Implement fix\n"
            output += "   4. Add tests to prevent regression\n"
        else:
            output += "   1. Understand requirements\n"
            output += "   2. Plan implementation\n"
            output += "   3. Execute changes\n"
            output += "   4. Verify functionality\n"

        # 5. Web Research Recommended
        output += f"5. Web Research Recommended: {'Yes' if is_library else 'No'}\n"

        # 6. Context7 Documentation Needed
        output += f"6. Context7 Documentation Needed: {'Yes' if is_library else 'No'}\n"

        # 7. ZEN Consultation Advised
        output += f"7. ZEN Consultation Advised: {'Yes' if is_complex else 'No'}\n"

        # 8. Task Complexity Assessment
        complexity_map = questionnaire_config["complexity_map"]
        if is_complex:
            output += f"8. Task Complexity Assessment: {complexity_map['complex']}\n"
        elif is_quick:
            output += f"8. Task Complexity Assessment: {complexity_map['simple']}\n"
        else:
            output += f"8. Task Complexity Assessment: {complexity_map['moderate']}\n"

        # 9. Estimated Time
        time_map = questionnaire_config["time_map"]
        if is_complex:
            output += f"9. Estimated Time: {time_map['complex']}\n"
        elif is_quick:
            output += f"9. Estimated Time: {time_map['simple']}\n"
        else:
            output += f"9. Estimated Time: {time_map['moderate']}\n"

        # Continue with remaining questions...
        output += f"10. Alternative Approaches: {'Proper refactoring instead of quick hack' if is_hack else 'None immediately apparent'}\n"

        if ("authentication" in question_lower or "auth" in question_lower) and (
            "test" in question_lower or "implement" in question_lower
        ):
            output += "11. Parallelizable Components: UI components, Backend logic, Tests, Documentation\n"
        else:
            output += "11. Parallelizable Components: None identified\n"

        # 12. Subagent Recommendations
        task_to_agent = questionnaire_config["task_to_agent"]
        if is_security:
            output += f"12. Subagent Recommendations: {task_to_agent['security']}\n"
        elif is_debug:
            output += f"12. Subagent Recommendations: {task_to_agent['debugging']}\n"
        elif "refactor" in question_lower:
            output += f"12. Subagent Recommendations: {task_to_agent['refactoring']}\n"
        else:
            output += "12. Subagent Recommendations: None required\n"

        # 13-20. Complete remaining items
        if is_security:
            output += "13. Warnings/Hidden Risks: security implications require careful review\n"
        elif is_delete:
            output += (
                "13. Warnings/Hidden Risks: data loss risk - ensure backups exist\n"
            )
        elif is_quick:
            output += "13. Warnings/Hidden Risks: rushing may lead to technical debt\n"
        else:
            output += "13. Warnings/Hidden Risks: None identified\n"

        output += f"14. Counter-Arguments: {'rushing may lead to technical debt' if is_quick else 'None'}\n"
        output += f"15. Technical Debt Impact: {'Creating' if (is_hack or is_quick) else 'Reducing' if 'refactor' in question_lower else 'Neutral'}\n"

        # Risk level calculation
        risk_level = 3
        if is_delete:
            risk_level = 8
        elif is_security or "payment" in question_lower:
            risk_level = 7
        output += f"16. Risk Level: {risk_level}/10\n"

        # Affected systems
        if "user" in question_lower:
            output += "17. Affected Systems: user management system\n"
        elif "payment" in question_lower:
            output += "17. Affected Systems: payment processing\n"
        elif "auth" in question_lower:
            output += "17. Affected Systems: authentication system\n"
        else:
            output += "17. Affected Systems: To be determined\n"

        output += f"18. Bias/Anti-Pattern Check: {'Yes' if (is_hack or ('singleton' in question_lower and 'global' in question_lower)) else 'No'}\n"
        output += f"19. Better Approach Available: {'Yes' if is_hack else 'No'}\n"
        output += "20. Clarifying Questions: None at this time\n"
        output += "===\n"

        return output

    def _fallback_optimization(self, user_prompt: str, raw_context: str) -> str:
        """Fallback optimization using rules when AI is unavailable."""
        # Use NLP analyzer if available
        if SPACY_AVAILABLE and hasattr(self, "nlp") and self.nlp:
            try:
                nlp_questionnaire = self._generate_nlp_questionnaire(
                    user_prompt,
                    raw_context,
                )
                # Generate base context analysis
                base_output = self._generate_base_context_analysis(
                    user_prompt,
                    raw_context,
                )
                return base_output + nlp_questionnaire
            except Exception as e:
                logger.error(
                    f"NLP analyzer failed, falling back to keyword analysis: {str(e)}",
                )

        # Original keyword-based fallback
        return self._generate_keyword_based_fallback(user_prompt, raw_context)

    async def optimize_context(self, user_prompt: str, raw_context: str) -> str:
        """Optimize context using OpenRouter with model fallbacks."""
        context_size_before = len(raw_context)
        logger.info(
            f"Starting context optimization: input_size={context_size_before} chars",
        )

        # Create system and user prompts
        system_prompt, user_content = self._create_optimization_prompt(
            user_prompt,
            raw_context,
        )

        # Try default model first
        logger.info(f"Trying primary model: {self.openrouter_config['default_model']}")
        result = await self._call_openrouter(
            system_prompt,
            user_content,
            self.openrouter_config["default_model"],
        )
        if result:
            context_size_after = len(result)
            logger.info(
                f"Primary model SUCCESS: size_reduction={context_size_before - context_size_after} chars",
            )
            return f"<!-- Context optimized by OpenRouter ({self.openrouter_config['default_model']}) -->\n{result}"

        # Fallback to free models if default fails
        fallback_models = self.openrouter_config["fallback_models"]
        logger.warning(
            f"Primary model failed, trying {len(fallback_models)} fallback models",
        )

        for i, fallback_model in enumerate(fallback_models, 1):
            logger.info(
                f"Trying fallback model {i}/{len(fallback_models)}: {fallback_model}",
            )
            result = await self._call_openrouter(
                system_prompt,
                user_content,
                fallback_model,
            )
            if result:
                context_size_after = len(result)
                logger.info(
                    f"Fallback model {fallback_model} SUCCESS: size_reduction={context_size_before - context_size_after} chars",
                )
                return f"<!-- Context optimized by OpenRouter ({fallback_model}) -->\n{result}"

        # If all OpenRouter attempts fail, use rule-based fallback
        logger.warning("All AI models failed, using rule-based fallback")
        result = self._fallback_optimization(user_prompt, raw_context)
        context_size_after = len(result)
        logger.info(
            f"Rule-based fallback completed: size_change={context_size_after - context_size_before} chars",
        )
        return result


async def optimize_injection_with_ai(user_prompt: str, raw_context: str) -> str:
    """Main entry point for AI-powered context optimization."""
    logger.info("Starting AI context optimization workflow")
    optimization_start_time = time.time()

    optimizer = AIContextOptimizer()

    try:
        # Run optimization with timeout
        timeout = optimizer.config["openrouter"]["timeout"]
        optimized = await asyncio.wait_for(
            optimizer.optimize_context(user_prompt, raw_context),
            timeout=timeout,
        )
        optimization_duration = time.time() - optimization_start_time
        logger.info(
            f"AI context optimization COMPLETED: total_duration={optimization_duration:.2f}s",
        )
        return optimized
    except asyncio.TimeoutError:
        optimization_duration = time.time() - optimization_start_time
        logger.error(
            f"AI context optimization TIMEOUT: duration={optimization_duration:.2f}s, timeout={timeout}s",
        )
        # If optimization takes too long, return raw context
        return f"<!-- Context optimization timed out -->\n{raw_context}"
    except Exception as e:
        optimization_duration = time.time() - optimization_start_time
        logger.error(
            f"AI context optimization ERROR: duration={optimization_duration:.2f}s, error={str(e)}",
        )
        # If any error, return raw context
        return f"<!-- Context optimization error: {str(e)} -->\n{raw_context}"


def optimize_injection_sync(user_prompt: str, raw_context: str) -> str:
    """Synchronous wrapper for the async optimization."""
    sync_start_time = time.time()
    logger.info(
        f"Starting sync optimization wrapper: prompt_len={len(user_prompt)}, context_len={len(raw_context)}",
    )

    try:
        # Check if event loop is already running (like in tests)
        try:
            asyncio.get_running_loop()
            # If we reach here, an event loop is running
            # Use run_in_executor to avoid nested loop issues
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(
                        optimize_injection_with_ai(user_prompt, raw_context),
                    ),
                )
                # Use sync timeout from config
                optimizer = AIContextOptimizer()
                sync_timeout = optimizer.config["openrouter"]["sync_timeout"]
                result = future.result(timeout=sync_timeout)
        except RuntimeError:
            # No event loop running, safe to create one
            result = asyncio.run(optimize_injection_with_ai(user_prompt, raw_context))

        sync_duration = time.time() - sync_start_time
        logger.info(
            f"Sync optimization wrapper COMPLETED: total_duration={sync_duration:.2f}s",
        )
        return result
    except Exception as e:
        sync_duration = time.time() - sync_start_time
        logger.error(
            f"Sync optimization wrapper FAILED: duration={sync_duration:.2f}s, error={str(e)}",
        )
        # Fallback to raw context
        return f"<!-- Context optimization failed: {str(e)} -->\n{raw_context}"
