#!/usr/bin/env python3
"""UserPromptSubmit Hook Handler.

Purpose: Inject contextual information before user prompts are processed by Claude.
This hook enhances Claude's understanding by providing:
- Git repository state
- Code intelligence (tree-sitter, LSP diagnostics)
- System monitoring information
- Smart recommendations
- Historical context
- MCP server information

Security: This hook validates all inputs and sanitizes file paths to prevent
path traversal and access to sensitive files.

Exit Codes:
- 0: Success (context injected or skipped appropriately)
- 1: Non-blocking error (execution continues)
- 2: Blocking error (prevents prompt processing)
"""
import asyncio
import datetime
import functools
import json
import os
import sys
import time
from typing import Dict, Optional, Tuple

# Performance monitoring imports
try:
    from UserPromptSubmit.http_session_manager import cleanup_http_sessions

    HAS_PERFORMANCE_MONITORING = True
except ImportError:
    HAS_PERFORMANCE_MONITORING = False
    monitor_performance = lambda f: f  # No-op decorator
    performance_context = None
    optimize_module_performance = None
    cleanup_performance_monitoring = None
    cleanup_http_sessions = None

# Add the current directory to the path so we can import the UserPromptSubmit module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure stderr logging
from UserPromptSubmit.logging_config import configure_stderr_logging

configure_stderr_logging()

# Set event loop policy for better async performance
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
else:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass  # Fall back to default event loop

# Import logging integration
try:
    from logger_integration import hook_logger
except ImportError:
    hook_logger = None

# Import session monitor
try:
    from session_monitor import get_session_monitor

    HAS_SESSION_MONITOR = True
except ImportError:
    HAS_SESSION_MONITOR = False
    get_session_monitor = None

# Circuit breaker configuration for enabling/disabling injections
# Set to False to disable specific injections
INJECTION_CIRCUIT_BREAKERS = {
    "enhanced_ai_optimizer": True,  # AI context optimization
    "unified_smart_advisor": True,  # Zen, agent, content, trigger
    "code_intelligence_hub": False,  # Tree-sitter, LSP diagnostics
    "system_monitor": True,  # Runtime monitoring, test status, context history
    "static_content": True,  # Prefix, suffix
    "context_revival": True,  # Historical context injection
    "git": True,  # Git injection (standalone)
    "mcp": True,  # MCP injection (standalone)
    "firecrawl": False,  # Firecrawl injection
    "zen_pro_orchestrator": True,  # zen-pro master orchestrator (CRITICAL - DO NOT DISABLE)
}

# Pre-compute enabled injections for performance
ENABLED_INJECTIONS = {k: v for k, v in INJECTION_CIRCUIT_BREAKERS.items() if v}

# File cache for transcript reads
_transcript_cache: Dict[str, Tuple[bytes, float]] = {}
CACHE_TTL = 5.0  # 5 seconds TTL for transcript cache

# Security: Sensitive file patterns to skip
SENSITIVE_PATTERNS = [
    ".env",
    ".git/",
    ".ssh/",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".pem",
    ".key",
    ".cert",
    ".crt",
    "password",
    "secret",
    "token",
    ".aws/",
    ".azure/",
    ".gcloud/",
    "credentials",
]


def is_path_secure(path: str) -> bool:
    """Validate that a path is secure and doesn't contain path traversal or sensitive
    files.

    Args:
        path: The file path to validate

    Returns:
        bool: True if path is secure, False otherwise
    """
    if not path:
        return True  # Empty path is safe

    # Check for path traversal
    if ".." in path:
        return False

    # Check for sensitive files
    path_lower = path.lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern in path_lower:
            return False

    # Check for system directories
    if path.startswith("/etc") or path.startswith("/sys") or path.startswith("/proc"):
        return False

    return True


def validate_input_data(data: Dict) -> Optional[Dict]:
    """Validate input data according to contract requirements.

    Args:
        data: Input data from stdin

    Returns:
        Dict: Validated data or None if validation fails
    """
    # Required fields according to contract section 3.1
    required_fields = ["session_id", "transcript_path", "cwd", "hook_event_name"]

    for field in required_fields:
        if field not in data:
            print(f"Error: Missing required field '{field}'", file=sys.stderr)
            return None

    # Validate hook event name
    if data["hook_event_name"] != "UserPromptSubmit":
        print(
            f"Error: Invalid hook event '{data['hook_event_name']}', expected 'UserPromptSubmit'",
            file=sys.stderr,
        )
        return None

    # Validate transcript path security
    transcript_path = data.get("transcript_path", "")
    if transcript_path and not is_path_secure(transcript_path):
        print(
            f"Security: Blocked access to sensitive path: {transcript_path}",
            file=sys.stderr,
        )
        return None

    # UserPromptSubmit specific: validate prompt field
    if "prompt" not in data:
        print("Error: Missing 'prompt' field for UserPromptSubmit", file=sys.stderr)
        return None

    return data


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


# Import consolidated injectors and remaining standalone injectors
from UserPromptSubmit.ai_context_optimizer_optimized import (
    optimize_injection_sync,  # noqa: E402
)
from UserPromptSubmit.context_revival import get_context_revival_injection  # noqa: E402
from UserPromptSubmit.firecrawl_injection import get_firecrawl_injection  # noqa: E402
from UserPromptSubmit.git_injection import get_git_injection  # noqa: E402
from UserPromptSubmit.mcp_injector import get_mcp_injection  # noqa: E402
from UserPromptSubmit.session_state import SessionState  # noqa: E402
from UserPromptSubmit.system_monitor import (
    get_system_monitoring_injection,  # noqa: E402
)
from UserPromptSubmit.unified_smart_advisor import (
    get_smart_recommendations,  # noqa: E402
)


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
            # - First time (inject_next is True)
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
        # Contract 2.2: Use exit code 2 for blocking errors
        print(f"Error: Failed to check injection status: {e}", file=sys.stderr)
        sys.exit(2)


async def handle_async(data):
    """Async handle UserPromptSubmit hook events with parallel execution."""
    # Log hook entry
    if hook_logger:
        hook_logger.log_hook_entry(data, "UserPromptSubmit")

    try:
        # Extract user prompt from data if available
        try:
            user_prompt = data.get("prompt", "") if isinstance(data, dict) else ""
        except Exception as e:
            if hook_logger:
                hook_logger.log_error(data, e)
            print(f"Error: Failed to extract user prompt: {e}", file=sys.stderr)
            sys.exit(1)

        # Log user prompt to session monitor
        if HAS_SESSION_MONITOR and get_session_monitor and user_prompt:
            try:
                session_id = data.get("session_id", "unknown")
                if session_id != "unknown":
                    monitor = get_session_monitor(session_id)
                    monitor.log_prompt(
                        user_prompt,
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "transcript_path": data.get("transcript_path", ""),
                            "cwd": data.get("cwd", ""),
                        },
                    )
            except Exception as e:
                if os.environ.get("DEBUG_HOOKS"):
                    print(f"Error logging to session monitor: {e}", file=sys.stderr)

        # Initialize session state once
        session_state = SessionState()
        transcript_path = data.get("transcript_path")

        # Check if we should inject context (pass session state to avoid duplicate)
        should_inject = should_inject_context(data, session_state)

        if not should_inject:
            # Increment message count for next check
            session_state.increment_message_count()

            # Return minimal context for continued conversation
            # Contract 3.2: Return proper JSON structure
            output = {
                "continue": True,  # Allow processing to continue
                "suppressOutput": False,  # Show in transcript
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "",  # Empty context for subsequent prompts
                },
            }
            print(json.dumps(output), file=sys.stdout)
            if hook_logger:
                hook_logger.log_hook_exit(data, 0, result="no_context_injection")
            sys.exit(0)

        # Mark that we're injecting context
        if transcript_path is None:
            print(
                "Error: transcript_path cannot be None when marking injection",
                file=sys.stderr,
            )
            sys.exit(2)
        session_state.mark_injected(str(transcript_path))

        # Get project directory from environment
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Create ALL tasks for true parallel execution
        all_tasks = []
        task_names = []

        # Add consolidated injectors wrapped in asyncio.to_thread for true parallelism
        if ENABLED_INJECTIONS.get("unified_smart_advisor"):
            all_tasks.append(asyncio.to_thread(get_smart_recommendations, user_prompt))
            task_names.append("unified_smart_advisor")

        if ENABLED_INJECTIONS.get("system_monitor"):
            # This is an async function, call directly without to_thread
            all_tasks.append(get_system_monitoring_injection(user_prompt, project_dir))
            task_names.append("system_monitor")

        # Note: Static content is now appended AFTER Gemini enhancement in ai_context_optimizer
        # Removing this from parallel tasks to prevent duplication

        if ENABLED_INJECTIONS.get("context_revival"):
            all_tasks.append(
                asyncio.to_thread(
                    get_context_revival_injection,
                    user_prompt,
                    project_dir,
                ),
            )
            task_names.append("context_revival")

        if ENABLED_INJECTIONS.get("mcp"):
            all_tasks.append(asyncio.to_thread(get_mcp_injection, user_prompt))
            task_names.append("mcp")

        # Add native async injections
        if ENABLED_INJECTIONS.get("git"):
            all_tasks.append(get_git_injection(project_dir))
            task_names.append("git")

        if ENABLED_INJECTIONS.get("firecrawl"):
            all_tasks.append(get_firecrawl_injection(user_prompt, project_dir))
            task_names.append("firecrawl")

        # Execute ALL tasks in parallel and gather results
        results_dict = {}
        if all_tasks:
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            # Create result dictionary mapping task names to results
            for i, (name, result) in enumerate(zip(task_names, results)):
                if isinstance(result, Exception):
                    # Contract 2.2: Use exit code 2 for blocking errors
                    print(
                        f"Error: Failed in {name} injection: {result}",
                        file=sys.stderr,
                    )
                    sys.exit(2)
                else:
                    if result is None:
                        print(
                            f"Error: {name} injection returned None - expected valid content",
                            file=sys.stderr,
                        )
                        sys.exit(2)
                    results_dict[name] = result

        # Extract results - fail if any expected injection is missing
        unified_advisor = results_dict.get("unified_smart_advisor")
        if unified_advisor is None and ENABLED_INJECTIONS.get("unified_smart_advisor"):
            print(
                "Error: unified_smart_advisor injection failed to produce content",
                file=sys.stderr,
            )
            sys.exit(2)

        code_intelligence = results_dict.get("code_intelligence_hub")
        if code_intelligence is None and ENABLED_INJECTIONS.get(
            "code_intelligence_hub",
        ):
            print(
                "Error: code_intelligence_hub injection failed to produce content",
                file=sys.stderr,
            )
            sys.exit(2)

        system_monitor = results_dict.get("system_monitor")
        if system_monitor is None and ENABLED_INJECTIONS.get("system_monitor"):
            print(
                "Error: system_monitor injection failed to produce content",
                file=sys.stderr,
            )
            sys.exit(2)

        context_revival = results_dict.get("context_revival")
        if context_revival is None and ENABLED_INJECTIONS.get("context_revival"):
            print(
                "Error: context_revival injection failed to produce content",
                file=sys.stderr,
            )
            sys.exit(2)

        mcp_recommendations = results_dict.get("mcp")
        if mcp_recommendations is None and ENABLED_INJECTIONS.get("mcp"):
            print("Error: mcp injection failed to produce content", file=sys.stderr)
            sys.exit(2)

        git_injection = results_dict.get("git")
        if git_injection is None and ENABLED_INJECTIONS.get("git"):
            print("Error: git injection failed to produce content", file=sys.stderr)
            sys.exit(2)

        firecrawl_context = results_dict.get("firecrawl")
        if firecrawl_context is None and ENABLED_INJECTIONS.get("firecrawl"):
            print(
                "Error: firecrawl injection failed to produce content",
                file=sys.stderr,
            )
            sys.exit(2)

        # Build context only from enabled injections
        unified_advisor = (
            unified_advisor if ENABLED_INJECTIONS.get("unified_smart_advisor") else ""
        )
        code_intelligence = (
            code_intelligence if ENABLED_INJECTIONS.get("code_intelligence_hub") else ""
        )
        system_monitor = (
            system_monitor if ENABLED_INJECTIONS.get("system_monitor") else ""
        )
        context_revival = (
            context_revival if ENABLED_INJECTIONS.get("context_revival") else ""
        )
        mcp_recommendations = (
            mcp_recommendations if ENABLED_INJECTIONS.get("mcp") else ""
        )
        git_injection = git_injection if ENABLED_INJECTIONS.get("git") else ""
        firecrawl_context = (
            firecrawl_context if ENABLED_INJECTIONS.get("firecrawl") else ""
        )

        # Build additional context - combine all injections
        # Git injection goes early for foundational context, context revival provides historical context
        # Note: static_content is now appended AFTER Gemini enhancement in ai_context_optimizer
        raw_context = (
            f"{git_injection}\n{context_revival}{system_monitor}{firecrawl_context}{unified_advisor}"
            f"{code_intelligence}{mcp_recommendations}"
        )

        # ALWAYS optimize context with AI - no env checks, fails loudly if API fails
        # This now includes: Gemini enhancement + static content + zen-pro
        if INJECTION_CIRCUIT_BREAKERS["enhanced_ai_optimizer"]:
            try:
                additional_context = optimize_injection_sync(user_prompt, raw_context)
            except Exception as e:
                # Contract 2.2: Use exit code 2 for blocking errors
                print(f"Error: AI optimization failed: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            # If circuit breaker is disabled, just use raw context (should not happen in production)
            print(
                "[AI_OPTIMIZER] WARNING - Circuit breaker disabled, using raw context",
                file=sys.stderr,
            )
            additional_context = raw_context

        # Note: zen-pro is now invoked INSIDE ai_context_optimizer.py after Gemini enhancement
        # This ensures the proper flow: User prompt → Gemini → Static content → zen-pro

        # Contract 3.2: Return proper JSON structure with all required fields
        output = {
            "continue": True,  # Allow processing to continue
            "suppressOutput": False,  # Show in transcript
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context,
            },
        }

        print(json.dumps(output), file=sys.stdout)
        if hook_logger:
            hook_logger.log_hook_exit(data, 0, result="context_injected")
        sys.exit(0)

    except Exception as e:
        # Log the error
        if hook_logger:
            hook_logger.log_error(data, e)
        # Contract 2.2: Use exit code 2 for blocking errors
        print(f"Error: Unexpected error in handle_async: {e}", file=sys.stderr)
        if hook_logger:
            hook_logger.log_hook_exit(data, 2, result="error")
        sys.exit(2)


def handle(data):
    """Synchronous wrapper for async handle function.

    Args:
        data: Validated input data from the hook
    """
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
    except Exception as e:
        # Contract 5.2: Handle unexpected errors gracefully
        print(f"Error: Unexpected error in handle: {e}", file=sys.stderr)
        sys.exit(1)  # Non-blocking error


if __name__ == "__main__":
    # Validate configuration on startup
    try:
        from UserPromptSubmit.config import validate_startup_config

        if not validate_startup_config():
            print(
                "Warning: Configuration validation failed - some features may be disabled",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"Warning: Configuration validation error: {e}", file=sys.stderr)

    # Contract 4.3: Validate JSON input
    try:
        raw_data = sys.stdin.read()
        data = json.loads(raw_data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)  # Non-blocking error - let execution continue
    except Exception as e:
        print(f"Error: Failed to read input: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate input data according to contract
    validated_data = validate_input_data(data)
    if validated_data is None:
        # Error already printed in validate_input_data
        sys.exit(1)  # Non-blocking error for invalid input

    # Handle the validated data
    handle(validated_data)
