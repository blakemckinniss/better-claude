#!/usr/bin/env python3
"""Intelligent pattern detection for suspicious file paths and operations."""

import re
from typing import Any, Dict, List


class IntelligentPatternDetector:
    """Detect patterns that might indicate issues."""

    SUSPICIOUS_PATTERNS: Dict[str, Dict[str, Any]] = {
        "recursive_path": {
            "pattern": re.compile(r"(.+/)\1{2,}"),
            "message": "⚠️ Recursive path pattern detected - this might be unintentional",
            "severity": "warning",
        },
        "test_outside_tests": {
            "pattern": re.compile(r"(?<!tests/)test_.*\.py$"),
            "message": "💡 Test file outside tests/ directory - consider moving to tests/",
            "severity": "suggestion",
        },
        "temp_file_pattern": {
            "pattern": re.compile(r"\.(tmp|temp|swp|~)$"),
            "message": "⚠️ Temporary file pattern detected - these are usually auto-generated",
            "severity": "warning",
        },
        "mixed_separators": {
            "pattern": re.compile(r"[/\\].*[\\]|[\\].*[/]"),
            "message": "⚠️ Mixed path separators detected - use consistent separators",
            "severity": "warning",
        },
        "backup_file": {
            "pattern": re.compile(r"\.(bak|backup|old|orig)$"),
            "message": "⚠️ Backup file pattern detected - consider using version control instead",
            "severity": "warning",
        },
        "hidden_file": {
            "pattern": re.compile(r"/\.[^/]+$"),
            "message": "💡 Hidden file detected - make sure this is intentional",
            "severity": "info",
        },
        "multiple_extensions": {
            "pattern": re.compile(r"\.[^/]+\.[^/]+$"),
            "message": "💡 Multiple file extensions detected - verify this is correct",
            "severity": "info",
        },
        "very_long_path": {
            "pattern": re.compile(r"^.{200,}$"),
            "message": "⚠️ Very long path detected - might cause issues on some systems",
            "severity": "warning",
        },
        "special_chars": {
            "pattern": re.compile(r"[<>:|?*]"),
            "message": "⚠️ Special characters in path - might cause cross-platform issues",
            "severity": "warning",
        },
    }

    # Command patterns that might indicate issues
    COMMAND_PATTERNS: Dict[str, Dict[str, Any]] = {
        "force_flag": {
            "pattern": re.compile(r"\s+-[rf]f\s+|\s+--force\s+"),
            "message": "⚠️ Force flag detected - this will override safety checks",
            "severity": "warning",
        },
        "recursive_delete": {
            "pattern": re.compile(r"rm\s+-rf?\s+|rm\s+-fr?\s+"),
            "message": "⚠️ Recursive delete detected - this will delete entire directories",
            "severity": "warning",
        },
        "sudo_usage": {
            "pattern": re.compile(r"^\s*sudo\s+"),
            "message": "⚠️ Sudo usage detected - elevated privileges requested",
            "severity": "warning",
        },
        "pipe_to_shell": {
            "pattern": re.compile(r"\|\s*sh\s*$|\|\s*bash\s*$"),
            "message": "🚨 Piping to shell detected - potential security risk",
            "severity": "critical",
        },
        "curl_pipe": {
            "pattern": re.compile(r"curl.*\|\s*(sh|bash)"),
            "message": "🚨 Downloading and executing remote code - high security risk",
            "severity": "critical",
        },
    }

    @classmethod
    def check_patterns(cls, file_path: str) -> List[Dict[str, Any]]:
        """Check for suspicious patterns in file paths."""
        warnings = []

        for name, config in cls.SUSPICIOUS_PATTERNS.items():
            if config["pattern"].search(file_path):
                warnings.append(
                    {
                        "type": name,
                        "message": config["message"],
                        "severity": config["severity"],
                    }
                )

        return warnings

    @classmethod
    def check_command_patterns(cls, command: str) -> List[Dict[str, Any]]:
        """Check for suspicious patterns in bash commands."""
        warnings = []

        for name, config in cls.COMMAND_PATTERNS.items():
            if config["pattern"].search(command):
                warnings.append(
                    {
                        "type": name,
                        "message": config["message"],
                        "severity": config["severity"],
                    }
                )

        return warnings

    @classmethod
    def check_naming_pattern(cls, filename: str, bad_patterns: List[str]) -> bool:
        """Check if filename matches any bad naming patterns."""
        # Extract filename without extension
        import os

        name_without_ext = os.path.splitext(filename.lower())[0]

        for pattern in bad_patterns:
            if re.search(pattern, name_without_ext):
                return True

        return False

    @classmethod
    def suggest_alternative_name(cls, bad_filename: str) -> str:
        """Suggest an alternative name for a bad filename."""
        import os

        base, ext = os.path.splitext(bad_filename)

        # Remove bad patterns
        cleaned = base.lower()
        cleaned = re.sub(r"\benhanced\b", "", cleaned)
        cleaned = re.sub(r"\badvanced\b", "", cleaned)
        cleaned = re.sub(r"\bv\d+\b", "", cleaned)
        cleaned = re.sub(r"\bbackup\b", "", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned)  # Clean up multiple underscores
        cleaned = cleaned.strip("_")

        # If nothing left, suggest based on extension
        if not cleaned:
            type_map = {
                ".py": "module",
                ".js": "script",
                ".ts": "typescript",
                ".jsx": "component",
                ".tsx": "component",
                ".md": "documentation",
                ".json": "config",
                ".yaml": "config",
                ".yml": "config",
            }
            cleaned = type_map.get(ext.lower(), "file")

        return f"{cleaned}{ext}"
