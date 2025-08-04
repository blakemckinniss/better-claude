"""Centralized configuration management for UserPromptSubmit module."""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration."""

    api_key: str = ""
    url: str = "https://openrouter.ai/api/v1/chat/completions"
    default_model: str = "google/gemini-2.5-flash"
    fallback_models: list = field(default_factory=lambda: ["google/gemini-2.5-pro"])
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: float = 30.0


@dataclass
class FirecrawlConfig:
    """Firecrawl API configuration."""

    api_key: str = ""
    base_url: str = "https://api.firecrawl.dev/v1"
    search_limit: int = 3
    content_limit: int = 1500
    url_limit: int = 3


@dataclass
class ContextConfig:
    """Context processing configuration."""

    max_context_tokens: int = 2000
    relevance_threshold: float = 0.3
    content_limit: int = 1500
    database_timeout: float = 30.0
    recovery_timeout: int = 300


@dataclass
class PerformanceConfig:
    """Performance and resource limits."""

    max_memory_mb: int = 512
    max_execution_time: float = 30.0
    max_concurrent_requests: int = 10
    connection_pool_limit: int = 50
    connection_pool_limit_per_host: int = 20
    keepalive_timeout: float = 30.0


@dataclass
class ConfigSchema:
    """Complete configuration schema."""

    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    firecrawl: FirecrawlConfig = field(default_factory=FirecrawlConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


class ConfigManager:
    """Manages configuration with environment override support."""

    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "config.json")

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_path()
        self._config: Optional[ConfigSchema] = None

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "openrouter": {
                "api_key": "",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "default_model": "google/gemini-2.5-flash",
                "fallback_models": ["google/gemini-2.5-pro"],
                "temperature": 0.3,
                "max_tokens": 2000,
                "timeout": 30.0,
            },
            "firecrawl": {
                "api_key": "",
                "base_url": "https://api.firecrawl.dev/v1",
                "search_limit": 3,
                "content_limit": 1500,
                "url_limit": 3,
            },
            "context": {
                "max_context_tokens": 2000,
                "relevance_threshold": 0.3,
                "content_limit": 1500,
                "database_timeout": 30.0,
                "recovery_timeout": 300,
            },
            "performance": {
                "max_memory_mb": 512,
                "max_execution_time": 30.0,
                "max_concurrent_requests": 10,
                "connection_pool_limit": 50,
                "connection_pool_limit_per_host": 20,
                "keepalive_timeout": 30.0,
            },
        }

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> None:
        """Apply environment variable overrides."""
        # OpenRouter overrides
        if env_key := os.environ.get("OPENROUTER_API_KEY"):
            config_dict["openrouter"]["api_key"] = env_key
        if env_url := os.environ.get("OPENROUTER_URL"):
            config_dict["openrouter"]["url"] = env_url
        if env_model := os.environ.get("OPENROUTER_MODEL"):
            config_dict["openrouter"]["default_model"] = env_model
        if env_temp := os.environ.get("OPENROUTER_TEMPERATURE"):
            config_dict["openrouter"]["temperature"] = float(env_temp)
        if env_tokens := os.environ.get("OPENROUTER_MAX_TOKENS"):
            config_dict["openrouter"]["max_tokens"] = int(env_tokens)
        if env_timeout := os.environ.get("OPENROUTER_TIMEOUT"):
            config_dict["openrouter"]["timeout"] = float(env_timeout)

        # Firecrawl overrides
        if env_key := os.environ.get("FIRECRAWL_API_KEY"):
            config_dict["firecrawl"]["api_key"] = env_key
        if env_url := os.environ.get("FIRECRAWL_BASE_URL"):
            config_dict["firecrawl"]["base_url"] = env_url
        if env_limit := os.environ.get("FIRECRAWL_SEARCH_LIMIT"):
            config_dict["firecrawl"]["search_limit"] = int(env_limit)
        if env_content := os.environ.get("FIRECRAWL_CONTENT_LIMIT"):
            config_dict["firecrawl"]["content_limit"] = int(env_content)

        # Context overrides
        if env_tokens := os.environ.get("CONTEXT_MAX_TOKENS"):
            config_dict["context"]["max_context_tokens"] = int(env_tokens)
        if env_threshold := os.environ.get("CONTEXT_RELEVANCE_THRESHOLD"):
            config_dict["context"]["relevance_threshold"] = float(env_threshold)
        if env_limit := os.environ.get("CONTEXT_CONTENT_LIMIT"):
            config_dict["context"]["content_limit"] = int(env_limit)
        if env_timeout := os.environ.get("CONTEXT_DATABASE_TIMEOUT"):
            config_dict["context"]["database_timeout"] = float(env_timeout)

        # Performance overrides
        if env_memory := os.environ.get("PERFORMANCE_MAX_MEMORY_MB"):
            config_dict["performance"]["max_memory_mb"] = int(env_memory)
        if env_time := os.environ.get("PERFORMANCE_MAX_EXECUTION_TIME"):
            config_dict["performance"]["max_execution_time"] = float(env_time)
        if env_requests := os.environ.get("PERFORMANCE_MAX_CONCURRENT_REQUESTS"):
            config_dict["performance"]["max_concurrent_requests"] = int(env_requests)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _dict_to_config(self, config_dict: Dict[str, Any]) -> ConfigSchema:
        """Convert dictionary to configuration objects."""
        return ConfigSchema(
            openrouter=OpenRouterConfig(**config_dict["openrouter"]),
            firecrawl=FirecrawlConfig(**config_dict["firecrawl"]),
            context=ContextConfig(**config_dict["context"]),
            performance=PerformanceConfig(**config_dict["performance"]),
        )

    def load_config(self) -> ConfigSchema:
        """Load configuration with environment overrides."""
        if self._config is not None:
            return self._config

        # Start with defaults
        config_dict = self._get_default_config()

        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file) as f:
                    file_config = json.load(f)
                    config_dict = self._deep_merge(config_dict, file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")

        # Apply environment overrides
        self._apply_env_overrides(config_dict)

        # Create config object
        self._config = self._dict_to_config(config_dict)
        return self._config

    def validate_config(self) -> bool:
        """Validate configuration and log warnings for missing required values."""
        config = self.load_config()
        valid = True

        if not config.openrouter.api_key:
            logger.warning("OPENROUTER_API_KEY not set - AI optimization disabled")
            valid = False

        if not config.firecrawl.api_key:
            logger.warning("FIRECRAWL_API_KEY not set - web search disabled")

        # Validate numeric ranges
        if not (0.0 <= config.openrouter.temperature <= 2.0):
            logger.error(f"Invalid temperature: {config.openrouter.temperature}")
            valid = False

        if config.openrouter.max_tokens <= 0:
            logger.error(f"Invalid max_tokens: {config.openrouter.max_tokens}")
            valid = False

        if config.performance.max_execution_time <= 0:
            logger.error(
                f"Invalid max_execution_time: {config.performance.max_execution_time}",
            )
            valid = False

        return valid

    def reload_config(self) -> ConfigSchema:
        """Reload configuration from file and environment."""
        self._config = None
        return self.load_config()


# Global configuration manager instance
_config_manager = ConfigManager()


def get_config() -> ConfigSchema:
    """Get current configuration."""
    return _config_manager.load_config()


def validate_startup_config() -> bool:
    """Validate configuration on startup."""
    return _config_manager.validate_config()


def reload_config() -> ConfigSchema:
    """Reload configuration (useful for hot-reloading)."""
    return _config_manager.reload_config()
