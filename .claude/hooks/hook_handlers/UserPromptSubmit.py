#!/usr/bin/env python3
import asyncio
import functools
import json
import os
import sys
import time
from typing import Dict, Optional, Tuple

# Add the current directory to the path so we can import the UserPromptSubmit module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Circuit breaker configuration for enabling/disabling injections
# Set to False to disable specific injections
INJECTION_CIRCUIT_BREAKERS = {
    "prefix": True,
    "suffix": True,
    "zen": True,
    "content": True,
    "trigger": True,
    "tree_sitter": True,
    "tree_sitter_hints": True,
    "mcp": True,
    "agent": True,
    "git": True,
    "runtime_monitoring": False,
    "test_status": False,
    "lsp_diagnostics": False,
    "context_history": True,
    "firecrawl": False,
    "ai_optimization": True,  # Controls AI context optimization
}

# Pre-compute enabled injections for performance
ENABLED_INJECTIONS = {k: v for k, v in INJECTION_CIRCUIT_BREAKERS.items() if v}

# File cache for transcript reads
_transcript_cache: Dict[str, Tuple[bytes, float]] = {}
CACHE_TTL = 5.0  # 5 seconds TTL for transcript cache


def perf_monitor(func):
    """Performance monitoring decorator for critical functions."""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            if duration > 0.5:  # Log slow operations
                print(
                    f"[PERF] Slow operation {func.__name__}: {duration:.3f}s",
                    file=sys.stderr,
                )
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(
                f"[PERF] Failed {func.__name__} after {duration:.3f}s: {e}",
                file=sys.stderr,
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            if duration > 0.1:  # Lower threshold for sync operations
                print(
                    f"[PERF] Slow operation {func.__name__}: {duration:.3f}s",
                    file=sys.stderr,
                )
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(
                f"[PERF] Failed {func.__name__} after {duration:.3f}s: {e}",
                file=sys.stderr,
            )
            raise

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file if it exists."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Handle case where CLAUDE_PROJECT_DIR is a placeholder
    if project_dir == "$CLAUDE_PROJECT_DIR" or not os.path.isdir(project_dir):
        project_dir = os.getcwd()

    env_file = os.path.join(project_dir, ".env")

    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


# Load .env file early
load_env_file()

from UserPromptSubmit.ai_context_optimizer import optimize_injection_sync  # noqa: E402
from UserPromptSubmit.content_injection import get_content_injection  # noqa: E402
from UserPromptSubmit.context_history_injection import get_context_history_injection
from UserPromptSubmit.firecrawl_injection import get_firecrawl_injection  # noqa: E402
from UserPromptSubmit.git_injection import get_git_injection  # noqa: E402
from UserPromptSubmit.lsp_diagnostics_injection import get_lsp_diagnostics_injection
from UserPromptSubmit.mcp_injector import get_mcp_injection  # noqa: E402
from UserPromptSubmit.prefix_injection import get_prefix  # noqa: E402
from UserPromptSubmit.runtime_monitoring_injection import (
    get_runtime_monitoring_injection,
)
from UserPromptSubmit.session_state import SessionState  # noqa: E402
from UserPromptSubmit.suffix_injection import get_suffix  # noqa: E402
from UserPromptSubmit.test_status_injection import get_test_status_injection
from UserPromptSubmit.tree_sitter_injection import (  # noqa: E402
    create_tree_sitter_injection,
    get_tree_sitter_hints,
)
from UserPromptSubmit.trigger_injection import get_trigger_injection  # noqa: E402
from UserPromptSubmit.zen_injection import get_zen_injection  # noqa: E402


def read_transcript_cached(transcript_path: str) -> Optional[bytes]:
    """Read transcript with caching to reduce I/O operations."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    # Check cache
    now = time.time()
    if transcript_path in _transcript_cache:
        content, timestamp = _transcript_cache[transcript_path]
        if now - timestamp < CACHE_TTL:
            return content

    # Read file and update cache
    try:
        with open(transcript_path, "rb") as f:
            content = f.read()
        _transcript_cache[transcript_path] = (content, now)

        # Clean old entries
        for path, (_, ts) in list(_transcript_cache.items()):
            if now - ts > CACHE_TTL:
                del _transcript_cache[path]

        return content
    except OSError:
        return None


def has_user_messages_optimized(transcript_path: str) -> bool:
    """Check if transcript has user messages with optimized I/O."""
    content = read_transcript_cached(transcript_path)
    if not content:
        return False

    # Quick binary search for user messages
    return b'"type":"user"' in content and b'"message"' in content


def should_inject_context(data, session_state=None):
    """Determine if we should inject context based on session state and transcript."""
    try:
        # Get transcript path from hook data
        transcript_path = data.get("transcript_path")

        # Use provided session state or create new one
        if session_state is None:
            session_state = SessionState()

        # First check session state rules (forced injection, message count, etc.)
        if session_state.should_inject(transcript_path):
            # This will return True for:
            # - First time (inject_next is True by default)
            # - After SubagentStop or PreCompact marked for injection
            # - After 5 messages
            # - When transcript changes
            return True

        # If session state says no injection needed, check if this is truly the first prompt
        # in the transcript (for cases where state was lost or corrupted)
        if not transcript_path or not os.path.exists(transcript_path):
            return True

        # Optimized check for user messages
        if not has_user_messages_optimized(transcript_path):
            return True

        return False

    except Exception as e:
        # On any error, default to including context (safer option)
        print(f"Error checking injection status: {e}", file=sys.stderr)
        return True


async def handle_async(data):
    """Async handle UserPromptSubmit hook events with parallel execution."""
    # Extract user prompt from data if available
    user_prompt = data.get("prompt", "") if isinstance(data, dict) else ""

    # Initialize session state once
    session_state = SessionState()
    transcript_path = data.get("transcript_path")

    # Check if we should inject context (pass session state to avoid duplicate)
    should_inject = should_inject_context(data, session_state)

    if not should_inject:
        # Increment message count for next check
        session_state.increment_message_count()

        # Return minimal context for continued conversation
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",  # Empty context for subsequent prompts
            },
        }
        print(json.dumps(output))
        sys.exit(0)

    # Mark that we're injecting context
    # Ensure transcript_path is a valid string (fallback to empty string if None)
    session_state.mark_injected(
        str(transcript_path) if transcript_path is not None else "",
    )

    # Get project directory from environment
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Import and get agent recommendations
    from UserPromptSubmit.agent_injector import get_agent_injection

    # Create ALL tasks for true parallel execution
    all_tasks = []
    task_names = []

    # Add sync injections wrapped in asyncio.to_thread for true parallelism
    if ENABLED_INJECTIONS.get("prefix"):
        all_tasks.append(asyncio.to_thread(get_prefix))
        task_names.append("prefix")

    if ENABLED_INJECTIONS.get("zen"):
        all_tasks.append(asyncio.to_thread(get_zen_injection, user_prompt))
        task_names.append("zen")

    if ENABLED_INJECTIONS.get("content"):
        all_tasks.append(asyncio.to_thread(get_content_injection, user_prompt))
        task_names.append("content")

    if ENABLED_INJECTIONS.get("trigger"):
        all_tasks.append(asyncio.to_thread(get_trigger_injection, user_prompt))
        task_names.append("trigger")

    if ENABLED_INJECTIONS.get("tree_sitter"):
        all_tasks.append(asyncio.to_thread(create_tree_sitter_injection, user_prompt))
        task_names.append("tree_sitter")

    if ENABLED_INJECTIONS.get("tree_sitter_hints"):
        all_tasks.append(asyncio.to_thread(get_tree_sitter_hints, user_prompt))
        task_names.append("tree_sitter_hints")

    if ENABLED_INJECTIONS.get("mcp"):
        all_tasks.append(asyncio.to_thread(get_mcp_injection, user_prompt))
        task_names.append("mcp")

    if ENABLED_INJECTIONS.get("suffix"):
        all_tasks.append(asyncio.to_thread(get_suffix, user_prompt))
        task_names.append("suffix")

    if ENABLED_INJECTIONS.get("agent"):
        all_tasks.append(asyncio.to_thread(get_agent_injection, user_prompt))
        task_names.append("agent")

    # Add native async injections
    if ENABLED_INJECTIONS.get("git"):
        all_tasks.append(get_git_injection(project_dir))
        task_names.append("git")

    if ENABLED_INJECTIONS.get("runtime_monitoring"):
        all_tasks.append(get_runtime_monitoring_injection())
        task_names.append("runtime_monitoring")

    if ENABLED_INJECTIONS.get("test_status"):
        all_tasks.append(get_test_status_injection(user_prompt, project_dir))
        task_names.append("test_status")

    if ENABLED_INJECTIONS.get("lsp_diagnostics"):
        all_tasks.append(get_lsp_diagnostics_injection(user_prompt, project_dir))
        task_names.append("lsp_diagnostics")

    if ENABLED_INJECTIONS.get("context_history"):
        all_tasks.append(get_context_history_injection(user_prompt, project_dir))
        task_names.append("context_history")

    if ENABLED_INJECTIONS.get("firecrawl"):
        all_tasks.append(get_firecrawl_injection(user_prompt, project_dir))
        task_names.append("firecrawl")

    # Execute ALL tasks in parallel and gather results
    if all_tasks:
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Create result dictionary mapping task names to results
        results_dict = {}
        for i, (name, result) in enumerate(zip(task_names, results)):
            if isinstance(result, Exception):
                print(f"Error in {name} injection: {result}", file=sys.stderr)
                results_dict[name] = ""
            else:
                results_dict[name] = result or ""
    else:
        results_dict = {}

    # Extract results with defaults for any missing/disabled injections
    prefix = results_dict.get("prefix", "")
    zen_instruction = results_dict.get("zen", "")
    content_instruction = results_dict.get("content", "")
    trigger_instruction = results_dict.get("trigger", "")
    tree_sitter_injection = results_dict.get("tree_sitter", "")
    tree_sitter_hints = results_dict.get("tree_sitter_hints", "")
    mcp_recommendations = results_dict.get("mcp", "")
    suffix = results_dict.get("suffix", "")
    agent_recommendations = results_dict.get("agent", "")
    git_injection = results_dict.get("git", "")
    runtime_monitoring = results_dict.get("runtime_monitoring", "")
    test_status = results_dict.get("test_status", "")
    lsp_diagnostics = results_dict.get("lsp_diagnostics", "")
    context_history = results_dict.get("context_history", "")
    firecrawl_context = results_dict.get("firecrawl", "")

    # Build additional context - combine all injections
    # Git injection goes early for foundational context, firecrawl provides web context
    raw_context = (
        f"{git_injection}\n{runtime_monitoring}{test_status}{lsp_diagnostics}{context_history}"
        f"{firecrawl_context}{zen_instruction}{content_instruction}{prefix}{trigger_instruction}"
        f"{tree_sitter_injection}{tree_sitter_hints}{mcp_recommendations}{agent_recommendations}{suffix}"
    )

    # Optimize context with AI if enabled
    ai_optimization_enabled = (
        INJECTION_CIRCUIT_BREAKERS["ai_optimization"]
        and os.environ.get("CLAUDE_AI_CONTEXT_OPTIMIZATION", "false").lower() == "true"
    )
    if ai_optimization_enabled:
        additional_context = optimize_injection_sync(user_prompt, raw_context)
    else:
        additional_context = raw_context

    # Return JSON output with additional context
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }

    print(json.dumps(output))
    sys.exit(0)


def handle(data):
    """Synchronous wrapper for async handle function."""
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()

        # If we're in an async context, use ThreadPoolExecutor
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(handle_async(data)),
            )
            future.result()
    except RuntimeError:
        # No event loop running, safe to create new one
        asyncio.run(handle_async(data))


if __name__ == "__main__":
    # When called directly, read data from stdin
    data = json.loads(sys.stdin.read())
    handle(data)
