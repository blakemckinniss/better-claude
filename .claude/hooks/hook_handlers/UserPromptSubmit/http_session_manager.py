"""Optimized HTTP session manager with connection pooling and resource management."""

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class HTTPSessionManager:
    """Singleton HTTP session manager with connection pooling."""

    _instance: Optional["HTTPSessionManager"] = None
    _session: Optional[aiohttp.ClientSession] = None
    _created_at: float = 0
    _session_timeout: float = 300  # 5 minutes
    _lock = asyncio.Lock()

    def __new__(cls) -> "HTTPSessionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create optimized HTTP session with connection pooling."""
        cls()

        async with cls._lock:
            now = time.time()

            # Create new session if none exists or expired
            if (
                cls._session is None
                or cls._session.closed
                or (now - cls._created_at) > cls._session_timeout
            ):

                if cls._session and not cls._session.closed:
                    await cls._session.close()

                # Optimized connector with connection pooling
                connector = aiohttp.TCPConnector(
                    limit=50,  # Total connection pool size
                    limit_per_host=20,  # Max connections per host
                    ttl_dns_cache=300,  # DNS cache TTL
                    use_dns_cache=True,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True,
                    force_close=False,
                    # SSL optimization
                    ssl=False,  # Disable SSL verification for local dev
                )

                # Optimized timeout configuration
                timeout = aiohttp.ClientTimeout(
                    total=30,  # Total timeout
                    connect=5,  # Connection timeout
                    sock_read=15,  # Socket read timeout
                    sock_connect=5,  # Socket connect timeout
                )

                cls._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "User-Agent": "better-claude/1.0",
                        "Connection": "keep-alive",
                    },
                    # Optimize JSON handling
                    json_serialize=lambda obj: obj,
                    raise_for_status=False,
                    auto_decompress=True,
                )
                cls._created_at = now

                logger.debug("Created new HTTP session with connection pooling")

        return cls._session

    @classmethod
    async def close(cls):
        """Close the HTTP session and cleanup resources."""
        async with cls._lock:
            if cls._session and not cls._session.closed:
                await cls._session.close()
                cls._session = None
                cls._created_at = 0
                logger.debug("Closed HTTP session")

    @classmethod
    @asynccontextmanager
    async def request(cls, method: str, url: str, **kwargs):
        """Context manager for making HTTP requests with session reuse."""
        session = await cls.get_session()
        try:
            async with session.request(method, url, **kwargs) as response:
                yield response
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise


# Convenience functions for common HTTP methods
async def get(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make GET request using pooled session."""
    async with HTTPSessionManager.request("GET", url, **kwargs) as response:
        return response


async def post(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make POST request using pooled session."""
    async with HTTPSessionManager.request("POST", url, **kwargs) as response:
        return response


async def put(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make PUT request using pooled session."""
    async with HTTPSessionManager.request("PUT", url, **kwargs) as response:
        return response


async def delete(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make DELETE request using pooled session."""
    async with HTTPSessionManager.request("DELETE", url, **kwargs) as response:
        return response


# Cleanup function for module shutdown
async def cleanup_http_sessions():
    """Cleanup HTTP sessions on module shutdown."""
    await HTTPSessionManager.close()


class PatternRegistry:
    """Centralized registry for pre-compiled regex patterns organized by category."""

    def _initialize_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Initialize categorized patterns for better organization."""
        return {
            "web": {
                "url_pattern": re.compile(
                    r'https?://[^\s<>\\"{}|\\^`\[\]]+',
                    re.IGNORECASE,
                ),
                "git_patterns": re.compile(
                    r"github\.com[:/]([^/]+)/([^/\.]+)",
                    re.IGNORECASE,
                ),
            },
            "tech": {
                "tech_terms": re.compile(
                    r"\b(python|javascript|typescript|react|vue|angular|node|django|flask|fastapi|docker|kubernetes|aws|azure|gcp)\b",
                    re.IGNORECASE,
                ),
                "file_extensions": re.compile(r"\b\w+\.[a-zA-Z]+\b"),
                "code_terms": re.compile(
                    r"\b(function|class|method|variable|import|export|async|await|promise|callback)\b",
                    re.IGNORECASE,
                ),
                "modern_tools": re.compile(
                    r"\b(rg|fd|bat|fzf|zoxide|lsd|sd|jq|yq|mlr|ctags|delta|tree|tokei|scc|exa|dust|duf|procs|hyperfine|entr|xh|dog|podman|dive|trivy|tldr)\b",
                    re.IGNORECASE,
                ),
            },
            "performance": {
                "performance_terms": re.compile(
                    r"\b(performance|slow|optimize|speed|memory|cpu|cache|latency|throughput)\b",
                    re.IGNORECASE,
                ),
                "parallel_execution": re.compile(
                    r"\b(parallel|concurrent|async|simultaneous)\b",
                    re.IGNORECASE,
                ),
            },
            "quality": {
                "error_terms": re.compile(
                    r"\b(error|issue|problem|bug|exception|crash|fail)\b",
                    re.IGNORECASE,
                ),
                "best_practices": re.compile(
                    r"\b(best\s+practices?|how\s+to|guide|tutorial|documentation)\b",
                    re.IGNORECASE,
                ),
                "anti_patterns": re.compile(
                    r"\b(documentation|readme|backup|\.v2\.|\.enhanced\.|\.old\.|\.bak)\b",
                    re.IGNORECASE,
                ),
            },
            "workflow": {
                "delegation": re.compile(
                    r"\b(task|agent|delegate|subagent|parallel)\b",
                    re.IGNORECASE,
                ),
                "hooks": re.compile(
                    r"\b(hook|filter|middleware|interceptor|plugin)\b",
                    re.IGNORECASE,
                ),
                "feature_impl": re.compile(
                    r"\b(implement|create|build|add|develop|feature|functionality)\b",
                    re.IGNORECASE,
                ),
            },
            "security": {
                "security_rules": re.compile(
                    r"\b(security|vulnerability|exploit|injection|xss|csrf|auth|token|key|password)\b",
                    re.IGNORECASE,
                ),
            },
        }

    def __init__(self):
        self._patterns = self._initialize_patterns()

    def get_pattern(self, category: str, name: str) -> re.Pattern:
        """Get pattern by category and name."""
        return self._patterns.get(category, {}).get(name, re.compile(""))

    def get_category_patterns(self, category: str) -> Dict[str, re.Pattern]:
        """Get all patterns for a category."""
        return self._patterns.get(category, {})

    def get_all_patterns(self) -> Dict[str, re.Pattern]:
        """Get flattened dict of all patterns for backward compatibility."""
        flattened = {}
        for category_patterns in self._patterns.values():
            flattened.update(category_patterns)
        return flattened


# Global pattern registry instance
PATTERN_REGISTRY = PatternRegistry()

# Backward compatibility - maintain old interface
COMPILED_PATTERNS = PATTERN_REGISTRY.get_all_patterns()


def get_compiled_pattern(name: str) -> re.Pattern:
    """Get pre-compiled regex pattern for performance."""
    return COMPILED_PATTERNS.get(name, re.compile(""))


from pathlib import Path

# File I/O optimization utilities
try:
    import aiofiles  # type: ignore

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


async def read_file_async(file_path: str) -> str:
    """Optimized async file reading."""
    try:
        path = Path(file_path)
        if not path.exists() or path.stat().st_size > 10_000_000:  # 10MB limit
            return ""

        if HAS_AIOFILES:
            async with aiofiles.open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore",
            ) as f:
                return await f.read()
        else:
            # Fallback to sync I/O
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        return ""


async def write_file_async(file_path: str, content: str) -> bool:
    """Optimized async file writing."""
    try:
        if HAS_AIOFILES:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
        else:
            # Fallback to sync I/O
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        return True
    except Exception:
        return False


# JSON optimization utilities
try:
    import orjson  # type: ignore

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


def fast_json_loads(data: bytes) -> Any:
    """Fast JSON deserialization."""
    if HAS_ORJSON:
        try:
            return orjson.loads(data)  # type: ignore
        except Exception:
            pass

    # Fallback to standard json
    import json

    return json.loads(data.decode("utf-8"))


def fast_json_dumps(obj: Any) -> bytes:
    """Fast JSON serialization."""
    if HAS_ORJSON:
        try:
            return orjson.dumps(obj)  # type: ignore
        except Exception:
            pass

    # Fallback to standard json
    import json

    return json.dumps(obj).encode("utf-8")
