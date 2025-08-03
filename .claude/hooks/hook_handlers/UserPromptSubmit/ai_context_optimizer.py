"""AI-powered context optimization for ultimate prompt engineering."""

import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List

import aiohttp

# Import static content module
from .static_content import get_static_content_injection

# Logging will be configured from JSON config
logger = logging.getLogger(__name__)

# Try to import spacy - it's assumed to be available
import spacy
from spacy.matcher import Matcher


class AIContextOptimizer:
    """Uses AI to reformulate and optimize context injections."""

    def _setup_nlp_patterns(self):
        """Set up spaCy matcher patterns for common programming concepts."""
        # Pattern for programming language references
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
        # Load the English model - REQUIRED, no fallbacks
        model_name = self.config["spacy"]["model"]
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"spaCy model '{model_name}' loaded successfully")
        except OSError:
            error_msg = f"CRITICAL: spaCy model '{model_name}' not found. Install with: python -m spacy download {model_name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Initialize matcher for pattern detection
        self.matcher = Matcher(self.nlp.vocab)
        self._setup_nlp_patterns()

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

        # Load enhanced context detection patterns from config
        self.enhanced_context_patterns = self.config.get("enhanced_context_patterns", {})

    def _enhanced_context_detection(self, raw_context: str) -> Dict[str, List[str]]:
        """Enhanced context detection with better pattern matching."""
        detected = {}

        for category, patterns_list in self.enhanced_context_patterns.items():
            matches = []
            for pattern in patterns_list:
                # Use re.MULTILINE for better line-by-line matching
                found = re.findall(pattern, raw_context, re.MULTILINE | re.IGNORECASE)
                # Handle both string and tuple results from regex
                for item in found:
                    if isinstance(item, tuple):
                        # For capture groups, join non-empty parts
                        match_str = ' '.join(part for part in item if part)
                    else:
                        match_str = str(item)
                    if match_str:
                        matches.append(match_str)

            if matches:
                # Deduplicate while preserving order
                seen = set()
                unique_matches = []
                for match in matches:
                    if match not in seen:
                        seen.add(match)
                        unique_matches.append(match)
                detected[category] = unique_matches

        return detected

    def _analyze_prompt_with_nlp(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze user prompt using spaCy NLP for intelligent context generation."""
        try:
            # Process the prompt
            doc = self.nlp(user_prompt.lower())

            # Extract entities
            entities = [(ent.text, ent.label_) for ent in doc.ents]

            # Match patterns
            matches = self.matcher(doc)
            patterns = []
            for match_id, start, end in matches:
                span = doc[start:end]
                pattern_name = self.nlp.vocab.strings[match_id]
                patterns.append({"pattern": pattern_name, "text": span.text})

            # Extract key verbs and nouns
            verbs = [token.text for token in doc if token.pos_ == "VERB"]
            nouns = [token.text for token in doc if token.pos_ == "NOUN"]

            # Task classification from config
            task_categories = self.config.get("task_categories", {})
            task_type = "general"
            confidence = 0.0

            for category, keywords in task_categories.items():
                score = sum(1 for word in keywords if word in user_prompt.lower())
                if score > confidence:
                    task_type = category
                    confidence = score

            return {
                "entities": entities,
                "patterns": patterns,
                "key_verbs": list(set(verbs)),
                "key_nouns": list(set(nouns)),
                "task_type": task_type,
                "confidence": confidence,
                "token_count": len(doc),
            }
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return {
                "task_type": "general",
                "confidence": 0.0,
                "token_count": len(user_prompt.split()),
            }

    def _create_enhanced_prompt(
        self,
        user_prompt: str,
        raw_context: str,
        detected_elements: Dict[str, List[str]],
        nlp_analysis: Dict[str, Any],
    ) -> str:
        """Create an enhanced prompt based on NLP analysis and detected elements."""
        # Enhanced prompt templates from config
        templates = self.config.get("enhanced_prompt_templates", {})

        # Base template selection based on task type
        task_type = nlp_analysis.get("task_type", "general")
        template = templates.get(task_type, templates.get("general", ""))

        # Build detected elements summary
        elements_summary = []
        for category, items in detected_elements.items():
            if items:
                elements_summary.append(f"- {category}: {', '.join(items[:5])}")

        # Create the enhanced prompt with all context
        enhanced_prompt = template.format(
            user_prompt=user_prompt,
            context_preview=raw_context[:500] + "..." if len(raw_context) > 500 else raw_context,
            detected_elements="\n".join(elements_summary) if elements_summary else "No specific elements detected",
            task_type=task_type,
            key_verbs=", ".join(nlp_analysis.get("key_verbs", [])),
            key_nouns=", ".join(nlp_analysis.get("key_nouns", [])),
            full_context=raw_context,
        )

        return enhanced_prompt

    async def optimize_context_with_ai(self, user_prompt: str, raw_context: str) -> str:
        """Use OpenRouter AI to intelligently reformulate and optimize the context."""
        if not self.openrouter_config.get("api_key"):
            logger.warning("OpenRouter API key not found")
            return raw_context

        # Detect elements in raw context
        detected_elements = self._enhanced_context_detection(raw_context)

        # Analyze prompt with NLP
        nlp_analysis = self._analyze_prompt_with_nlp(user_prompt)

        # Create enhanced prompt
        enhanced_prompt = self._create_enhanced_prompt(user_prompt, raw_context, detected_elements, nlp_analysis)

        # Log token estimation
        estimated_tokens = len(enhanced_prompt.split()) // 4  # Rough estimation
        logger.info(f"Estimated tokens for AI optimization: {estimated_tokens}")

        # Prepare API request with timeout handling
        headers = {
            "Authorization": f"Bearer {self.openrouter_config['api_key']}",
            "Content-Type": "application/json",
        }

        # Get system prompts from config
        system_prompts = self.config.get("system_prompts", {})
        system_prompt = system_prompts.get(
            nlp_analysis.get("task_type", "general"),
            system_prompts.get("general", "You are a helpful assistant."),
        )

        data = {
            "model": self.openrouter_config["default_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_prompt},
            ],
            "temperature": self.openrouter_config.get("temperature", 0.3),
            "max_tokens": self.openrouter_config.get("max_tokens", 2000),
        }

        # Try primary model, fallback if needed
        models_to_try = [self.openrouter_config["default_model"]] + self.openrouter_config.get("fallback_models", [])

        async with aiohttp.ClientSession() as session:
            for model in models_to_try:
                try:
                    data["model"] = model
                    logger.info(f"Attempting OpenRouter API call with model: {model}")

                    # Add timeout configuration
                    timeout = aiohttp.ClientTimeout(total=self.openrouter_config.get("timeout", 30.0))

                    start_time = time.perf_counter()
                    async with session.post(
                        self.openrouter_config["url"],
                        headers=headers,
                        json=data,
                        timeout=timeout,
                    ) as response:
                        duration = time.perf_counter() - start_time

                        if response.status == 200:
                            result = await response.json()
                            content = result["choices"][0]["message"]["content"]

                            logger.info(
                                f"OpenRouter API SUCCESS: model={model}, duration={duration:.2f}s, response_len={len(content)}",
                            )
                            return self._post_process_ai_response(content, detected_elements)
                        else:
                            error_text = await response.text()
                            logger.warning(
                                f"OpenRouter API error with model {model}: {response.status} - {error_text}",
                            )
                            continue

                except asyncio.TimeoutError:
                    logger.warning(f"OpenRouter API timeout with model {model}")
                    continue
                except Exception as e:
                    logger.error(f"OpenRouter API error with model {model}: {str(e)}")
                    continue

        # If all models fail, return original context
        logger.error("All OpenRouter models failed, returning original context")
        return raw_context

    def _post_process_ai_response(self, ai_response: str, detected_elements: Dict[str, List[str]]) -> str:
        """Post-process the AI response to ensure quality and completeness."""
        # Clean up any potential formatting issues
        cleaned = ai_response.strip()

        # Ensure detected elements are mentioned if they were significant
        important_categories = ["recent_changes", "errors", "todos"]
        for category in important_categories:
            if category in detected_elements and detected_elements[category]:
                # Check if AI mentioned these elements
                mentioned = any(elem.lower() in cleaned.lower() for elem in detected_elements[category])
                if not mentioned:
                    # Append a note about missed elements
                    cleaned += f"\n\nNote: Detected {category}: {', '.join(detected_elements[category][:3])}"

        return cleaned

    async def enhance_context(self, user_prompt: str, raw_context: str) -> str:
        """Main entry point for AI context enhancement."""
        try:
            # Use AI to optimize the context
            result = await self.optimize_context_with_ai(user_prompt, raw_context)
        except Exception as e:
            logger.error(f"AI optimization failed: {e}")
            result = raw_context

        # Log successful enhancement
        logger.info(
            f"Successfully enhanced context using {self.openrouter_config['default_model']} (length: {len(result)} chars)",
        )

        # Return the Gemini-enhanced result
        return f"<!-- Context instruct optimized by Enhanced AI ({self.openrouter_config['default_model']}) -->\n\nINIT INSTRUCT: Hire agent Task zen-pro as a subagent to address the following in a focused and optimal approach, \n{result}"


def invoke_zed_pro(user_prompt: str, enhanced_context: str, config: Dict[str, Any]) -> str:
    """
    Append ZED-PRO static content to the enhanced context.
    This is the FINAL step that simply adds ZED-PRO orchestration content.
    
    Args:
        user_prompt: Original user prompt
        enhanced_context: The fully enhanced context (Gemini + static content)
        config: Configuration dictionary
        
    Returns:
        str: ZED-PRO content to append
    """
    # Get ZED-PRO config
    zed_config = config.get("zed_pro", {})
    
    try:
        # Get the ZED-PRO content template from config
        zed_pro_content = zed_config.get("prompt_template", "")
        
        # If we have content, format it with the user prompt and enhanced context
        if zed_pro_content:
            # Format the template with the provided data
            formatted_content = zed_pro_content.format(
                user_prompt=user_prompt,
                enhanced_context=enhanced_context
            )
            
            # Get the header
            header = zed_config.get("result_header", "\n\n# ZED-PRO ORCHESTRATOR ANALYSIS\n")
            
            # Log success
            logger.info("[ZED-PRO] Successfully appended orchestrator content")
            
            # Return the ZED-PRO content with header
            return f"{header}{formatted_content}"
        else:
            logger.warning("[ZED-PRO] No prompt_template found in config")
            return ""
            
    except Exception as e:
        # Log error but don't fail the entire process
        logger.error(f"[ZED-PRO] Error formatting content: {str(e)}")
        return ""


async def optimize_injection_with_ai(user_prompt: str, raw_context: str) -> str:
    """Main entry point for AI-powered context optimization with static content and ZED-PRO."""
    logger.info("Starting enhanced AI context optimization workflow")

    try:
        # Initialize the optimizer
        optimizer = AIContextOptimizer()

        # Stage 1: Run AI enhancement (Gemini)
        logger.info(f"Stage 1: Running AI enhancement with {optimizer.openrouter_config['default_model']}")
        enhanced_result = await optimizer.enhance_context(user_prompt, raw_context)

        # Stage 2: Append static content (prefix/suffix)
        logger.info("Stage 2: Appending static content and zen suffix")
        static_content = get_static_content_injection(user_prompt)
        result_with_static = enhanced_result + static_content

        # Stage 3: Invoke ZED-PRO (just append its content)
        logger.info("Stage 3: Invoking ZED-PRO orchestrator")
        zed_pro_result = invoke_zed_pro(user_prompt, result_with_static, optimizer.config)

        # Combine everything: Gemini + Static + ZED-PRO
        final_result = result_with_static + zed_pro_result

        logger.info("COMPLETE enhanced optimization workflow finished in %.2fs", time.perf_counter())
        return final_result

    except Exception as e:
        logger.error(f"AI optimization failed: {e}")
        # Return at least the static content if AI fails
        return get_static_content_injection(user_prompt)


def optimize_injection_sync(user_prompt: str, raw_context: str) -> str:
    """Synchronous wrapper for async AI optimization."""
    try:
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            logger.info("Detected running event loop, using thread pool executor")
            # We're in an async context, use ThreadPoolExecutor
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, optimize_injection_with_ai(user_prompt, raw_context))
                return future.result()
        except RuntimeError:
            # No event loop, safe to use asyncio.run
            logger.info("No event loop detected, using asyncio.run")
            return asyncio.run(optimize_injection_with_ai(user_prompt, raw_context))
    except Exception as e:
        logger.error(f"Failed to run async optimization: {e}")
        # Fallback to static content only
        return get_static_content_injection(user_prompt)
