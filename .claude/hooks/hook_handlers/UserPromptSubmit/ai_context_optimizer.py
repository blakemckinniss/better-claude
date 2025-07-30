"""AI-powered context optimization for ultimate prompt engineering."""

import asyncio
import logging
import os
import sys
import time
from typing import Optional, Tuple

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

    def _create_optimization_prompt(self, user_prompt: str, raw_context: str) -> Tuple[str, str]:
        """Create system and user prompts for the context optimization AI."""
        # Check if context contains special data types
        has_firecrawl = "<firecrawl-context>" in raw_context
        has_git = "git" in raw_context.lower() or "branch:" in raw_context.lower()
        has_mcp = "<mcp-" in raw_context or "MCP_" in raw_context
        has_tree_sitter = "<tree-sitter" in raw_context
        has_zen = "<zen-" in raw_context
        has_errors = any(word in raw_context.lower() for word in ["error", "fail", "critical", "warning"])
        has_session = "session" in raw_context.lower() or "SessionStart" in raw_context
        
        # Always optimize context to create an enhanced instruction prompt
        system_prompt = """You are an AI prompt engineer specializing in optimizing context for Claude Code.

Your job is to analyze the user's question and the provided context, then create an enhanced instruction that will help Claude provide the best possible answer.

Key objectives:
1. Understand what the user is asking
2. Extract ALL relevant information from the context that could help
3. Create a clear, structured prompt that guides Claude
4. Include specific details from the context when relevant
5. Maintain the user's original question but enhance it with context

Context types you may encounter:
{f"- Git repository information (branches, commits, status)" if has_git else ""}
{f"- MCP tool descriptions and capabilities" if has_mcp else ""}
{f"- Web search results or scraped content" if has_firecrawl else ""}
{f"- Code analysis from tree-sitter" if has_tree_sitter else ""}
{f"- ZEN agent recommendations" if has_zen else ""}
{f"- Errors, warnings, or issues" if has_errors else ""}
{f"- Session information and history" if has_session else ""}

OUTPUT FORMAT:
Create a clear, actionable prompt that:
1. Restates the user's question with clarity
2. Provides relevant context that helps answer it
3. Guides Claude on how to approach the answer
4. Highlights any critical information from the context

DO NOT create AI roles or lengthy system instructions. Focus on creating a concise, enhanced version of the user's request."""

        user_content = f"""USER'S QUESTION:
{user_prompt}

AVAILABLE CONTEXT:
{raw_context}

TASK:
Create an optimized instruction prompt that helps Claude answer the user's question effectively. Include relevant context details that enhance understanding."""
        
        # Structure preserved for potential future use

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
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/blakemckinniss/better-claude",
            "X-Title": "Better Claude Context Optimizer",
        }

        # Build messages with system and user prompts
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        data = {
            "model": model,
            "messages": messages,
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
        
        # Identify different types of injected content
        context_sections = {
            "git": [],
            "mcp": [],
            "zen": [],
            "tree_sitter": [],
            "firecrawl": [],
            "errors": priority_lines,
            "session": [],
            "other": []
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
            for line in context_sections["errors"][:5]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        if context_sections["git"]:
            output += "**Git Context**:\n"
            for line in context_sections["git"][:3]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        if context_sections["mcp"]:
            output += "**Available MCP Tools**:\n"
            for line in context_sections["mcp"][:5]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        if context_sections["zen"]:
            output += "**ZEN Agent Recommendations**:\n"
            for line in context_sections["zen"][:3]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        if context_sections["firecrawl"]:
            output += "**Web Search Results**:\n"
            for line in context_sections["firecrawl"][:5]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        if context_sections["session"]:
            output += "**Session Information**:\n"
            for line in context_sections["session"][:3]:
                output += f"- {line.strip()}\n"
            output += "\n"
        
        # Add guidance based on question type
        output += "**Approach**: "
        question_lower = user_prompt.lower()
        if any(word in question_lower for word in ["error", "bug", "fix", "issue", "problem"]):
            output += "Focus on debugging and error resolution using the context above.\n"
        elif any(word in question_lower for word in ["implement", "create", "build", "add"]):
            output += "Use the available tools and context to implement the requested feature.\n"
        elif any(word in question_lower for word in ["explain", "what", "how", "why"]):
            output += "Provide a clear explanation using any relevant context available.\n"
        else:
            output += "Address the user's request using the context provided above.\n"
        
        return output

    async def optimize_context(self, user_prompt: str, raw_context: str) -> str:
        """Optimize context using OpenRouter with model fallbacks."""
        context_size_before = len(raw_context)
        logger.info(
            f"Starting context optimization: input_size={context_size_before} chars",
        )

        # Create system and user prompts
        system_prompt, user_content = self._create_optimization_prompt(user_prompt, raw_context)

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
            result = await self._call_openrouter(system_prompt, user_content, fallback_model)
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
            f"AI context optimization TIMEOUT: duration={optimization_duration:.2f}s, timeout=30.0s",
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