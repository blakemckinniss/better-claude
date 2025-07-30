#!/usr/bin/env python3
import asyncio
import json
import os
import sys

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
    "tree_sitter": False,
    "tree_sitter_hints": False,
    "mcp": True,
    "agent": True,
    "git": False,
    "runtime_monitoring": False,
    "test_status": False,
    "lsp_diagnostics": False,
    "context_history": False,
    "firecrawl": False,
    "ai_optimization": True,  # Controls AI context optimization
}


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


def should_inject_context(data):
    """Determine if we should inject context based on session state and transcript."""
    try:
        # Get transcript path from hook data
        transcript_path = data.get("transcript_path")
        
        # Initialize session state manager
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
        
        # Check if this transcript has any user messages yet
        user_message_count = 0
        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get("type") == "user" and "message" in entry:
                                user_message_count += 1
                        except json.JSONDecodeError:
                            continue
        except (IOError, OSError) as e:
            print(f"Error reading transcript {transcript_path}: {e}", file=sys.stderr)
            return True
        
        # If no user messages in transcript, force injection
        if user_message_count == 0:
            return True
        
        return False
        
    except Exception as e:
        # On any error, default to including context (safer option)
        print(f"Error checking injection status: {e}", file=sys.stderr)
        return True


async def handle_async(data):
    """Async handle UserPromptSubmit hook events with parallel execution."""
    # Extract user prompt from data if available
    user_prompt = data.get("userPrompt", "") if isinstance(data, dict) else ""
    
    # Check if we should inject context
    should_inject = should_inject_context(data)
    
    # Initialize session state for tracking
    session_state = SessionState()
    transcript_path = data.get("transcript_path")
    
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
    session_state.mark_injected(str(transcript_path) if transcript_path is not None else "")

    # Get project directory from environment
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Import and get agent recommendations
    from UserPromptSubmit.agent_injector import get_agent_injection

    # Create async tasks for parallel execution
    # Group 1: Basic injections (these are already sync, run directly)
    prefix = get_prefix() if INJECTION_CIRCUIT_BREAKERS["prefix"] else ""
    zen_instruction = get_zen_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["zen"] else ""
    content_instruction = get_content_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["content"] else ""
    trigger_instruction = get_trigger_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["trigger"] else ""
    tree_sitter_injection = create_tree_sitter_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["tree_sitter"] else ""
    tree_sitter_hints = get_tree_sitter_hints(user_prompt) if INJECTION_CIRCUIT_BREAKERS["tree_sitter_hints"] else ""
    mcp_recommendations = get_mcp_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["mcp"] else ""
    suffix = get_suffix(user_prompt) if INJECTION_CIRCUIT_BREAKERS["suffix"] else ""
    agent_recommendations = get_agent_injection(user_prompt) if INJECTION_CIRCUIT_BREAKERS["agent"] else ""

    # Group 2: Async injections that can run in parallel
    async_tasks = []
    async_results = {}
    
    # Build list of enabled async tasks
    if INJECTION_CIRCUIT_BREAKERS["git"]:
        async_tasks.append(("git", get_git_injection(project_dir)))
    if INJECTION_CIRCUIT_BREAKERS["runtime_monitoring"]:
        async_tasks.append(("runtime_monitoring", get_runtime_monitoring_injection()))
    if INJECTION_CIRCUIT_BREAKERS["test_status"]:
        async_tasks.append(("test_status", get_test_status_injection(user_prompt, project_dir)))
    if INJECTION_CIRCUIT_BREAKERS["lsp_diagnostics"]:
        async_tasks.append(("lsp_diagnostics", get_lsp_diagnostics_injection(user_prompt, project_dir)))
    if INJECTION_CIRCUIT_BREAKERS["context_history"]:
        async_tasks.append(("context_history", get_context_history_injection(user_prompt, project_dir)))
    if INJECTION_CIRCUIT_BREAKERS["firecrawl"]:
        async_tasks.append(("firecrawl", get_firecrawl_injection(user_prompt, project_dir)))
    
    # Execute enabled async tasks in parallel
    if async_tasks:
        task_names, task_coroutines = zip(*async_tasks)
        results = await asyncio.gather(*task_coroutines)
        async_results = dict(zip(task_names, results))
    
    # Get results with defaults for disabled injections
    git_injection = async_results.get("git", "")
    runtime_monitoring = async_results.get("runtime_monitoring", "")
    test_status = async_results.get("test_status", "")
    lsp_diagnostics = async_results.get("lsp_diagnostics", "")
    context_history = async_results.get("context_history", "")
    firecrawl_context = async_results.get("firecrawl", "")

    # Build additional context - combine all injections
    # Git injection goes early for foundational context, firecrawl provides web context
    raw_context = (
        f"{git_injection}\n{runtime_monitoring}{test_status}{lsp_diagnostics}{context_history}"
        f"{firecrawl_context}{zen_instruction}{content_instruction}{prefix}{trigger_instruction}"
        f"{tree_sitter_injection}{tree_sitter_hints}{mcp_recommendations}{agent_recommendations}{suffix}"
    )

    # Optimize context with AI if enabled
    ai_optimization_enabled = (
        INJECTION_CIRCUIT_BREAKERS["ai_optimization"] and
        os.environ.get("CLAUDE_AI_CONTEXT_OPTIMIZATION", "false").lower() == "true"
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
