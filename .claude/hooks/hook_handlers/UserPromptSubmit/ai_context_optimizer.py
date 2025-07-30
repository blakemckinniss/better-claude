"""AI-powered context optimization for ultimate prompt engineering."""

import asyncio
import logging
import os
import sys
import time
from typing import Optional

import aiohttp

# Configure logging to stderr to avoid interfering with hook JSON output
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [AI_OPTIMIZER] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AIContextOptimizer:
    """Uses AI to reformulate and optimize context injections."""

    def __init__(self):
        # OpenRouter as primary AI provider
        self.openrouter_config = {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key": os.environ.get("OPENROUTER_API_KEY"),
            "default_model": "google/gemini-2.5-flash",
            "fallback_models": [
                "google/gemini-2.5-pro",
                "meta-llama/llama-3.1-8b-instruct:free",
            ],
        }

    def _create_optimization_prompt(self, user_prompt: str, raw_context: str) -> str:
        """Create the prompt for the context optimization AI."""
        # Check if context contains Firecrawl data
        has_firecrawl = "<firecrawl-context>" in raw_context
        firecrawl_note = (
            " Pay special attention to integrating web search results and scraped content into actionable insights."
            if has_firecrawl
            else ""
        )

        return f"""Analyze the user's prompt and raw context below, then create a specialized AI assistant role to handle their specific request.{firecrawl_note}

USER'S ORIGINAL PROMPT:
{user_prompt}

RAW CONTEXT DATA:
{raw_context}

INSTRUCTIONS:
Based on the above user prompt and context, create a role-based prompt that:
1. Identifies what the user is trying to accomplish
2. Extracts and prioritizes the most relevant information from the raw context
3. Highlights any critical warnings, errors, or blockers from the context
4. Creates a specialized assistant role tailored to this specific task
5. Includes the analyzed context as part of the role's knowledge

OUTPUT FORMAT - Use this exact structure:

# Role: [Specific Role Name Based on User's Task]

## Profile
- language: English
- description: [Description specific to handling the user's request]
- expertise: [Relevant expertise for this task]
- focus: [What this role specifically helps with]

## Current Context
[Summarize the key information from the raw context that's relevant to the user's task, including:
- Git status if relevant
- System state if relevant  
- Any errors or warnings
- Key files or changes mentioned
- Any other critical context]

## Task Analysis
[Explain what the user is asking for and how to approach it based on the context]

## Key Priorities
1. [Most important aspect based on context]
2. [Second priority]
3. [Third priority]

## Recommended Approach
[Specific steps to address the user's request based on the available context]

IMPORTANT: 
- Start directly with "# Role:" (no preamble)
- Fill in all sections with specific information from the context
- Focus on the actual task at hand, not generic capabilities
- Include real data from the context, not placeholders"""

    async def _call_openrouter(
        self,
        prompt: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call OpenRouter API with fallback model support."""
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
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/blakemckinniss/better-claude",
            "X-Title": "Better Claude Context Optimizer",
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000,
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

    def _fallback_optimization(self, user_prompt: str, raw_context: str) -> str:
        """Fallback optimization using rules when AI is unavailable."""
        lines = raw_context.strip().split("\n")

        # Simple rule-based prioritization
        priority_keywords = ["error", "fail", "critical", "warning", "TODO", "FIXME"]
        priority_lines = []
        normal_lines = []

        for line in lines:
            if any(keyword in line.lower() for keyword in priority_keywords):
                priority_lines.append(line)
            else:
                normal_lines.append(line)

        # Detect user intent for role creation
        intent_keywords = {
            "debug": ["debug", "error", "fix", "issue", "problem", "bug"],
            "implement": ["implement", "create", "build", "add", "develop", "feature"],
            "analyze": ["analyze", "understand", "explain", "review", "check"],
            "optimize": ["optimize", "improve", "performance", "speed", "refactor"],
            "test": ["test", "coverage", "pytest", "jest", "unit"],
            "git": ["git", "commit", "merge", "branch", "pull"],
        }

        detected_intent = "Development"
        for intent, keywords in intent_keywords.items():
            if any(keyword in user_prompt.lower() for keyword in keywords):
                detected_intent = intent
                break

        # Create structured fallback with simplified format
        output = "<!-- Context optimized by rules (AI unavailable) -->\n\n"
        output += f"# Role: {detected_intent.title()} Assistant\n\n"
        output += "## Profile\n"
        output += "- language: English\n"
        output += f"- description: Assistant specialized in {detected_intent} tasks\n"
        output += f"- expertise: {detected_intent.title()} and software development\n"
        output += f"- focus: Helping with the current {detected_intent} request\n\n"

        output += "## Current Context\n"

        # Extract git info if present
        git_lines = [
            line for line in lines if "git" in line.lower() or "branch:" in line.lower()
        ]
        if git_lines:
            output += "Git Status:\n"
            for line in git_lines[:5]:
                output += f"- {line.strip()}\n"
            output += "\n"

        if priority_lines:
            output += "Critical Issues Found:\n"
            for line in priority_lines[:5]:
                output += f"- {line.strip()}\n"
            output += "\n"

        output += "Other Context:\n"
        for line in normal_lines[:5]:
            if line.strip():
                output += f"- {line.strip()}\n"

        output += "\n## Task Analysis\n"
        output += (
            f"User is requesting help with {detected_intent} based on the prompt.\n"
        )

        output += "\n## Key Priorities\n"
        output += f"1. Address the {detected_intent} request directly\n"
        if priority_lines:
            output += "2. Resolve any errors or warnings found in context\n"
            output += "3. Provide clear, actionable guidance\n"
        else:
            output += "2. Use available context effectively\n"
            output += "3. Provide clear, actionable guidance\n"

        output += "\n## Recommended Approach\n"
        output += f"Focus on {detected_intent}-related assistance using the available context.\n"

        return output

    async def optimize_context(self, user_prompt: str, raw_context: str) -> str:
        """Optimize context using OpenRouter with model fallbacks."""
        context_size_before = len(raw_context)
        logger.info(
            f"Starting context optimization: input_size={context_size_before} chars",
        )

        optimization_prompt = self._create_optimization_prompt(user_prompt, raw_context)

        # Try default model first
        logger.info(f"Trying primary model: {self.openrouter_config['default_model']}")
        result = await self._call_openrouter(
            optimization_prompt,
            self.openrouter_config["default_model"],
        )
        if result:
            context_size_after = len(result)
            logger.info(
                f"Primary model SUCCESS: size_reduction={context_size_before - context_size_after} chars",
            )
            return f"<!-- Context optimized by OpenRouter ({self.openrouter_config['default_model']}) -->\n{result}"

        # Fallback to free models if default fails
        logger.warning(
            f"Primary model failed, trying {len(self.openrouter_config['fallback_models'])} fallback models",
        )
        for i, fallback_model in enumerate(
            self.openrouter_config["fallback_models"],
            1,
        ):
            logger.info(
                f"Trying fallback model {i}/{len(self.openrouter_config['fallback_models'])}: {fallback_model}",
            )
            result = await self._call_openrouter(optimization_prompt, fallback_model)
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
        optimized = await asyncio.wait_for(
            optimizer.optimize_context(user_prompt, raw_context),
            timeout=30.0,  # 30 second timeout - increased for larger contexts
        )
        optimization_duration = time.time() - optimization_start_time
        logger.info(
            f"AI context optimization COMPLETED: total_duration={optimization_duration:.2f}s",
        )
        return optimized
    except asyncio.TimeoutError:
        optimization_duration = time.time() - optimization_start_time
        logger.error(
            f"AI context optimization TIMEOUT: duration={optimization_duration:.2f}s, timeout=10.0s",
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
                result = future.result(timeout=15)  # 15 second total timeout
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
