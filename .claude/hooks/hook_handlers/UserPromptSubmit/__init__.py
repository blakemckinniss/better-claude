"""UserPromptSubmit package for handling user prompt modifications."""

# Core modules
from .ai_context_optimizer_optimized import (
    OptimizedAIContextOptimizer,
    optimize_injection_sync,
    optimize_injection_with_ai,
)
from .config import get_config, reload_config, validate_startup_config
from .context_manager import ContextManager
from .context_revival import (
    ContextRevivalHook, get_context_revival_hook,
    get_context_revival_injection,
)
from .firecrawl_injection import get_firecrawl_injection
from .git_injection import get_git_injection
from .http_session_manager import HTTPSessionManager, cleanup_http_sessions
from .mcp_injector import get_mcp_injection
from .path_utils import get_claude_dir, get_project_root
from .performance_monitor import (
    PerformanceMonitor,
    cleanup_performance_monitoring,
)
from .session_state import SessionState
from .static_content import StaticContentInjector, get_static_content_injection
from .system_monitor import SystemMonitor
from .unified_smart_advisor import UnifiedSmartAdvisor

__all__ = [
    # Core modules
    "OptimizedAIContextOptimizer",
    "ContextManager",
    "ContextRevivalHook",
    "HTTPSessionManager",
    "PerformanceMonitor",
    "SessionState",
    "StaticContentInjector",
    "SystemMonitor",
    "UnifiedSmartAdvisor",
    # Functions
    "optimize_injection_with_ai",
    "optimize_injection_sync",
    "get_context_revival_hook",
    "get_context_revival_injection",
    "get_firecrawl_injection",
    "get_git_injection",
    "get_mcp_injection",
    "cleanup_http_sessions",
    "cleanup_performance_monitoring",
    "get_config",
    "validate_startup_config",
    "reload_config",
    "get_claude_dir",
    "get_project_root",
    "get_static_content_injection",
]
