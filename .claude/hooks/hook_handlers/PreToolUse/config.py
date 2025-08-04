#!/usr/bin/env python3
"""Configuration for PreToolUse hook - Circuit breaker and path restrictions."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for path access control."""

    # Enable/disable circuit breaker (set to False to bypass all checks)
    enabled: bool = True

    # Paths that cannot be modified (read-only)
    read_only_paths: List[str] = field(default_factory=list)

    # Paths that cannot be accessed at all (no read, write, or execute)
    no_access_paths: List[str] = field(default_factory=list)

    # Paths where new files cannot be created (existing files can be edited)
    write_restricted_paths: List[str] = field(default_factory=list)

    # Paths that cannot be deleted
    delete_protected_paths: List[str] = field(
        default_factory=lambda: [
            ".claude/settings.json",
            ".claude/hooks/hook_handler.py",
        ],
    )

    # Protected files (exact match required)
    protected_files: List[str] = field(
        default_factory=lambda: [
            "/home/blake/better-claude/.claude/settings.json",
            "/home/blake/better-claude/.claude/hooks/hook_handler.py",
        ],
    )

    # File paths that should not be modified
    blocked_paths: List[str] = field(
        default_factory=lambda: [
            ".env",
            "package-lock.json",
            ".git/",
            "yarn.lock",
            "Gemfile.lock",
        ],
    )

    # Dangerous command patterns
    dangerous_patterns: List[str] = field(
        default_factory=lambda: [
            "rm -rf /",
            "dd if=/dev/zero",
            ":(){:|:&};:",  # Fork bomb
        ],
    )

    # Old tools and their modern replacements
    old_tool_suggestions: dict = field(
        default_factory=lambda: {
            "grep": "Consider using 'rg' (ripgrep) instead - it's 10-100x faster",
            "find": "Consider using 'fd' instead - it's simpler and faster",
            "cat": "Consider using 'bat' for syntax highlighting",
        },
    )

    # Protected command patterns
    protected_commands: List[str] = field(
        default_factory=lambda: [
            r"rm\s+-rf?\s+/",  # rm -rf /
            r":;\s*\(\)",  # Fork bomb
            r"dd\s+.*of=/dev/",  # dd to device
        ],
    )

    # Allow sudo commands
    allow_sudo: bool = False


@dataclass
class PermissionConfig:
    """Permission handling configuration."""

    mode: str = "standard"  # "standard" or "optimistic"
    auto_approve_reads: bool = False


@dataclass
class DisplayConfig:
    """Display configuration."""

    show_warnings: bool = True
    show_info: bool = True
    use_emojis: bool = True


@dataclass
class PreToolUseConfig:
    """Main configuration for PreToolUse hook."""

    # Circuit breaker configuration
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # Permission configuration
    permission: PermissionConfig = field(default_factory=PermissionConfig)

    # Display configuration
    display: DisplayConfig = field(default_factory=DisplayConfig)

    # Warning thresholds
    import_warning_threshold: int = 5  # Warn when file is imported by more than N files

    # Directory suggestions
    tests_directory: str = "/home/blake/better-claude/.claude/hooks/tests"
    docs_directory: str = "/home/blake/better-claude/.claude/hooks/docs"

    # Naming patterns to block
    bad_naming_patterns: List[str] = field(
        default_factory=lambda: [
            r"\benhanced\b",
            r"\badvanced\b",
            r"\bv2\b",
            r"\bv\d+\b",
            r"\bbackup\b",
        ],
    )

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "PreToolUseConfig":
        """Load configuration from JSON file."""
        if config_path is None:
            # Look for config in standard locations
            search_paths = [
                Path.cwd() / ".claude" / "hooks" / "config" / "pretooluse.json",
                Path.cwd() / ".claude" / "pretooluse.json",
                Path.home() / ".claude" / "pretooluse.json",
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

            config = cls()

            # Update circuit breaker settings
            if "circuit_breaker" in data:
                cb_data = data["circuit_breaker"]
                if "enabled" in cb_data:
                    config.circuit_breaker.enabled = cb_data["enabled"]
                if "read_only_paths" in cb_data:
                    config.circuit_breaker.read_only_paths = cb_data["read_only_paths"]
                if "no_access_paths" in cb_data:
                    config.circuit_breaker.no_access_paths = cb_data["no_access_paths"]
                if "write_restricted_paths" in cb_data:
                    config.circuit_breaker.write_restricted_paths = cb_data[
                        "write_restricted_paths"
                    ]
                if "delete_protected_paths" in cb_data:
                    config.circuit_breaker.delete_protected_paths = cb_data[
                        "delete_protected_paths"
                    ]
                if "protected_files" in cb_data:
                    config.circuit_breaker.protected_files = cb_data["protected_files"]
                if "blocked_paths" in cb_data:
                    config.circuit_breaker.blocked_paths = cb_data["blocked_paths"]
                if "dangerous_patterns" in cb_data:
                    config.circuit_breaker.dangerous_patterns = cb_data[
                        "dangerous_patterns"
                    ]
                if "protected_commands" in cb_data:
                    config.circuit_breaker.protected_commands = cb_data[
                        "protected_commands"
                    ]
                if "allow_sudo" in cb_data:
                    config.circuit_breaker.allow_sudo = cb_data["allow_sudo"]

            # Update permission settings
            if "permission" in data:
                perm_data = data["permission"]
                if "mode" in perm_data:
                    config.permission.mode = perm_data["mode"]
                if "auto_approve_reads" in perm_data:
                    config.permission.auto_approve_reads = perm_data[
                        "auto_approve_reads"
                    ]

            # Update display settings
            if "display" in data:
                disp_data = data["display"]
                if "show_warnings" in disp_data:
                    config.display.show_warnings = disp_data["show_warnings"]
                if "show_info" in disp_data:
                    config.display.show_info = disp_data["show_info"]
                if "use_emojis" in disp_data:
                    config.display.use_emojis = disp_data["use_emojis"]

            # Update other settings
            if "import_warning_threshold" in data:
                config.import_warning_threshold = data["import_warning_threshold"]
            if "tests_directory" in data:
                config.tests_directory = data["tests_directory"]
            if "docs_directory" in data:
                config.docs_directory = data["docs_directory"]
            if "bad_naming_patterns" in data:
                config.bad_naming_patterns = data["bad_naming_patterns"]

            return config

        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()


# Global config instance
_config: Optional[PreToolUseConfig] = None


def get_config() -> PreToolUseConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = PreToolUseConfig.load_from_file()
    return _config


def reload_config() -> PreToolUseConfig:
    """Reload the configuration from file."""
    global _config
    _config = PreToolUseConfig.load_from_file()
    return _config
