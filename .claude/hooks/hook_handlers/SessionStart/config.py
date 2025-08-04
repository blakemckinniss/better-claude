"""Configuration constants for SessionStart hook."""

from enum import Enum
from typing import List


class OutputMode(Enum):
    """Output modes for SessionStart hook."""

    MINIMAL = "minimal"
    FULL = "full"


class EnvironmentVars:
    """Environment variable names used by SessionStart hook."""

    DEBUG_HOOKS = "DEBUG_HOOKS"
    CLAUDE_MINIMAL_HOOKS = "CLAUDE_MINIMAL_HOOKS"
    CLAUDE_PROJECT_DIR = "CLAUDE_PROJECT_DIR"


class Config:
    """Configuration constants for SessionStart hook."""

    # Command timeout
    FAST_TIMEOUT = 5  # seconds, reduced from 10s per CLAUDE.md

    # Performance optimizations
    CACHE_TTL = 30  # seconds for git command caching
    MAX_CONCURRENT_SUBPROCESSES = 5  # Connection pool size
    ENABLE_CACHING = True  # Global cache toggle

    # Environment variable caching
    ENV_CACHE_TIMEOUT = 60  # Cache env vars for 1 minute

    # Batch processing
    GIT_BATCH_SIZE = 10  # Max commands per batch

    # Required input fields for validation
    REQUIRED_FIELDS: List[str] = ["transcript_path", "cwd", "hook_event_name", "source"]

    # Security: blocked path prefixes
    BLOCKED_PATHS = ["..", "/etc"]

    # File limits for performance
    MAX_README_LINES = 50
    MAX_CONFIG_FILE_SIZE = 10000  # bytes
    MAX_CONFIG_LINES = 30
    MAX_STATUS_LINES = 10
    MAX_COMMIT_LINES = 5
    MAX_STRUCTURE_LINES = 15
    MAX_FILES_SHOWN = 20
    MAX_FILE_TYPES_SHOWN = 5

    # Git command limits
    MAX_RECENT_COMMITS = 10
    FAST_COMMIT_LIMIT = 3
    MAX_PROJECT_DEPTH = 3
