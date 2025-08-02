#!/usr/bin/env python3
"""Configuration management for PostToolUse hook."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class FormatterConfig:
    """Configuration for code formatters."""

    python: List[str] = field(
        default_factory=lambda: [
            "autoflake",
            "absolufy-imports",
            "isort",
            "flynt",
            "pyupgrade",
            "docformatter",
            "add-trailing-comma",
            "ssort",
            "black",
            "ruff",
            "refurb",
        ],
    )
    javascript: List[str] = field(default_factory=lambda: ["prettier"])
    typescript: List[str] = field(default_factory=lambda: ["prettier"])

    # File extensions mapping
    extensions: Dict[str, str] = field(
        default_factory=lambda: {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        },
    )


@dataclass
class ValidatorConfig:
    """Configuration for validators."""

    # Enable/disable specific validators
    security_enabled: bool = True
    data_loss_enabled: bool = True
    performance_enabled: bool = True
    react_enabled: bool = True
    file_size_enabled: bool = True

    # File size limits
    max_file_lines: int = 1000
    max_function_lines: int = 50
    max_class_lines: int = 200

    # Severity filters
    block_on_severity: Set[str] = field(default_factory=lambda: {"CRITICAL"})
    report_severity: Set[str] = field(default_factory=lambda: {"CRITICAL", "WARNING"})


@dataclass
class DiagnosticConfig:
    """Configuration for diagnostics."""

    # Enable/disable specific tools
    mypy_enabled: bool = True
    pylint_enabled: bool = True
    ruff_enabled: bool = True
    async_checker_enabled: bool = True
    unbound_checker_enabled: bool = True

    # Tool-specific options
    mypy_options: List[str] = field(
        default_factory=lambda: [
            "--no-error-summary",
            "--show-error-codes",
            "--show-column-numbers",
        ],
    )
    pylint_options: List[str] = field(
        default_factory=lambda: [
            "--errors-only",
            "--output-format=parseable",
        ],
    )
    ruff_options: List[str] = field(
        default_factory=lambda: [
            "check",
            "--output-format=text",
        ],
    )


@dataclass
class PostToolUseConfig:
    """Main configuration for PostToolUse hook."""

    # Sub-configurations
    formatters: FormatterConfig = field(default_factory=FormatterConfig)
    validators: ValidatorConfig = field(default_factory=ValidatorConfig)
    diagnostics: DiagnosticConfig = field(default_factory=DiagnosticConfig)

    # Global settings
    enabled: bool = True
    skip_directories: Set[str] = field(
        default_factory=lambda: {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "PostToolUse",  # Skip our own modules
        },
    )

    # Performance settings
    parallel_formatters: bool = False  # Future enhancement
    cache_results: bool = True

    @classmethod
    def _from_dict(cls, data: Dict) -> "PostToolUseConfig":
        """Create config from dictionary."""
        config = cls()

        # Update formatters
        if "formatters" in data:
            fmt_data = data["formatters"]
            if "python" in fmt_data:
                config.formatters.python = fmt_data["python"]
            if "javascript" in fmt_data:
                config.formatters.javascript = fmt_data["javascript"]
            if "typescript" in fmt_data:
                config.formatters.typescript = fmt_data["typescript"]
            if "extensions" in fmt_data:
                config.formatters.extensions.update(fmt_data["extensions"])

        # Update validators
        if "validators" in data:
            val_data = data["validators"]
            for key, value in val_data.items():
                if hasattr(config.validators, key):
                    setattr(config.validators, key, value)

        # Update diagnostics
        if "diagnostics" in data:
            diag_data = data["diagnostics"]
            for key, value in diag_data.items():
                if hasattr(config.diagnostics, key):
                    setattr(config.diagnostics, key, value)

        # Update global settings
        if "enabled" in data:
            config.enabled = data["enabled"]
        if "skip_directories" in data:
            config.skip_directories = set(data["skip_directories"])
        if "parallel_formatters" in data:
            config.parallel_formatters = data["parallel_formatters"]
        if "cache_results" in data:
            config.cache_results = data["cache_results"]

        return config

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "PostToolUseConfig":
        """Load configuration from a JSON/YAML file."""
        if config_path is None:
            # Look for config in standard locations
            search_paths = [
                Path.cwd() / ".claude" / "hooks" / "config" / "posttooluse.json",
                Path.cwd() / ".claude" / "posttooluse.json",
                Path.home() / ".claude" / "posttooluse.json",
            ]

            for path in search_paths:
                if path.exists():
                    config_path = path
                    break
            else:
                # No config file found, use defaults
                return cls()

        try:
            with open(config_path) as f:
                data = json.load(f)

            return cls._from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()

    def should_skip_file(self, file_path: str) -> bool:
        """Check if a file should be skipped."""
        path = Path(file_path)

        # Check if any parent directory should be skipped
        for parent in path.parents:
            if parent.name in self.skip_directories:
                return True

        # Check if the file is in a skip directory
        for skip_dir in self.skip_directories:
            if skip_dir in str(path):
                return True

        return False

    def get_formatter_language(self, file_path: str) -> Optional[str]:
        """Get the language/formatter type for a file."""
        ext = Path(file_path).suffix.lower()
        return self.formatters.extensions.get(ext)

    def get_formatters_for_file(self, file_path: str) -> List[str]:
        """Get the list of formatters to run for a file."""
        language = self.get_formatter_language(file_path)
        if not language:
            return []

        if language == "python":
            return self.formatters.python
        elif language == "javascript":
            return self.formatters.javascript
        elif language == "typescript":
            return self.formatters.typescript
        else:
            return []


# Global config instance
_config: Optional[PostToolUseConfig] = None


def get_config() -> PostToolUseConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = PostToolUseConfig.load_from_file()
    return _config


def reload_config() -> PostToolUseConfig:
    """Reload the configuration from file."""
    global _config
    _config = PostToolUseConfig.load_from_file()
    return _config
