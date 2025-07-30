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
        # Analyze if the user is asking about AI roles/agents/prompts
        role_keywords = ["role", "agent", "prompt", "assistant", "ai role", "specialized role", "create role"]
        is_role_request = any(keyword in user_prompt.lower() for keyword in role_keywords)
        
        # Check if context contains special data types
        has_firecrawl = "<firecrawl-context>" in raw_context
        has_git = "git" in raw_context.lower() or "branch:" in raw_context.lower()
        has_mcp = "<mcp-" in raw_context or "MCP_" in raw_context
        has_tree_sitter = "<tree-sitter" in raw_context
        has_zen = "<zen-" in raw_context
        has_errors = any(word in raw_context.lower() for word in ["error", "fail", "critical", "warning"])
        
        if is_role_request:
            # System prompt for role creation
            system_prompt = """You are an AI assistant role architect. Your job is to analyze user requests and context data to create specialized AI assistant roles.

Your output must follow the exact format specified. Focus on:
1. Understanding the user's actual goal
2. Extracting only relevant context information
3. Creating a role that directly addresses their needs
4. Including real data from context, not generic placeholders

Key principles:
- Be specific and task-focused
- Include concrete context details
- Highlight critical information
- Create actionable guidance"""

            # User prompt with structured data
            user_content = f"""Create a specialized AI assistant role based on this request and context.

USER'S REQUEST:
{user_prompt}

AVAILABLE CONTEXT DATA:
{raw_context}

OUTPUT REQUIREMENTS:
Generate a role definition following this EXACT structure:

# Role: [Specific Role Name Based on User's Task]

## Profile
- language: English
- description: [Description specific to handling the user's request]
- expertise: [Relevant expertise areas]
- focus: [Primary objectives]

## Current Context
[Key information from the raw context, including:]
{f"- Git repository status and recent changes" if has_git else ""}
{f"- Web search results and scraped content" if has_firecrawl else ""}
{f"- Available MCP tools and their capabilities" if has_mcp else ""}
{f"- Code analysis from tree-sitter" if has_tree_sitter else ""}
{f"- ZEN agent recommendations" if has_zen else ""}
{f"- Critical errors or warnings" if has_errors else ""}
- Other relevant technical details

## Task Analysis
[Clear explanation of what the user needs and how to approach it]

## Key Priorities
1. [Most critical aspect]
2. [Secondary focus]
3. [Additional priority]

## Recommended Approach
[Specific, actionable steps based on the context]"""

        else:
            # System prompt for context optimization (non-role requests)
            system_prompt = f"""You are a context optimization specialist. Your job is to analyze user questions and raw context data to extract and organize ONLY the most relevant information.

Key objectives:
1. Understand what the user is actually asking
2. Extract context that directly helps answer their question
3. Remove irrelevant information
4. Organize remaining context clearly
5. Highlight critical details

Context types to consider:
{f"- Web search results and scraped content (Firecrawl data)" if has_firecrawl else ""}
{f"- Git repository status and changes" if has_git else ""}
{f"- MCP tool recommendations and capabilities" if has_mcp else ""}
{f"- Code structure analysis from tree-sitter" if has_tree_sitter else ""}
{f"- ZEN agent analysis and recommendations" if has_zen else ""}
{f"- Errors, warnings, and critical issues" if has_errors else ""}

IMPORTANT RULES:
- Do NOT create AI roles or assistant definitions
- Do NOT include generic advice
- Do NOT add system instructions unless directly relevant
- ONLY include context that helps answer the specific question
- Keep output concise and focused"""

            # User prompt with the actual data
            user_content = f"""Optimize this context for the user's question.

USER'S QUESTION:
{user_prompt}

RAW CONTEXT TO OPTIMIZE:
{raw_context}

TASK:
Extract and organize only the information that directly helps answer the user's question. Remove all irrelevant details."""

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

        # Check if this is a role/agent request
        role_keywords = ["role", "agent", "prompt", "assistant", "ai role", "specialized role", "create role"]
        is_role_request = any(keyword in user_prompt.lower() for keyword in role_keywords)
        
        # Identify different types of injected content
        context_sections = {
            "git": [],
            "mcp": [],
            "zen": [],
            "tree_sitter": [],
            "firecrawl": [],
            "errors": priority_lines,
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
            elif line not in priority_lines:
                context_sections["other"].append(line)
        
        if is_role_request:
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

            # Add relevant context sections
            if context_sections["git"]:
                output += "Git Status:\n"
                for line in context_sections["git"][:5]:
                    output += f"- {line.strip()}\n"
                output += "\n"

            if context_sections["errors"]:
                output += "Critical Issues Found:\n"
                for line in context_sections["errors"][:5]:
                    output += f"- {line.strip()}\n"
                output += "\n"
                
            if context_sections["mcp"]:
                output += "Available MCP Tools:\n"
                for line in context_sections["mcp"][:3]:
                    output += f"- {line.strip()}\n"
                output += "\n"

            output += "Other Context:\n"
            for line in context_sections["other"][:5]:
                if line.strip():
                    output += f"- {line.strip()}\n"

            output += "\n## Task Analysis\n"
            output += f"User is requesting help with {detected_intent} based on the prompt.\n"

            output += "\n## Key Priorities\n"
            output += f"1. Address the {detected_intent} request directly\n"
            if context_sections["errors"]:
                output += "2. Resolve any errors or warnings found in context\n"
                output += "3. Provide clear, actionable guidance\n"
            else:
                output += "2. Use available context effectively\n"
                output += "3. Provide clear, actionable guidance\n"

            output += "\n## Recommended Approach\n"
            output += f"Focus on {detected_intent}-related assistance using the available context.\n"
        else:
            # For non-role requests, organize relevant context based on the question
            output = "<!-- Context optimized by rules (AI unavailable) -->\n\n"
            output += "## Relevant Context\n\n"
            
            # Determine what context is relevant based on the question
            question_lower = user_prompt.lower()
            
            if context_sections["errors"]:
                output += "### Important Issues:\n"
                for line in context_sections["errors"][:5]:
                    output += f"- {line.strip()}\n"
                output += "\n"
            
            # Include git info if relevant
            if any(word in question_lower for word in ["git", "commit", "branch", "merge", "version"]):
                if context_sections["git"]:
                    output += "### Git Information:\n"
                    for line in context_sections["git"][:5]:
                        output += f"- {line.strip()}\n"
                    output += "\n"
            
            # Include MCP info if asking about tools/capabilities
            if any(word in question_lower for word in ["tool", "mcp", "capability", "function"]):
                if context_sections["mcp"]:
                    output += "### Available Tools:\n"
                    for line in context_sections["mcp"][:5]:
                        output += f"- {line.strip()}\n"
                    output += "\n"
            
            # Include web search results if relevant
            if context_sections["firecrawl"]:
                output += "### Web Search Results:\n"
                for line in context_sections["firecrawl"][:5]:
                    output += f"- {line.strip()}\n"
                output += "\n"
            
            # Add some general context
            if context_sections["other"]:
                output += "### Additional Context:\n"
                for line in context_sections["other"][:10]:
                    if line.strip():
                        output += f"- {line.strip()}\n"

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