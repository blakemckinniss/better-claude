#!/usr/bin/env python3
import os
import re
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

# ====================================================================
# CIRCUIT BREAKER CONFIGURATION
# ====================================================================
# Control file system access for Claude
# Paths should be absolute or relative to project root

# Paths that cannot be modified (read-only)
READ_ONLY_PATHS = [
    # Example: ".claude",  # Uncomment to make entire .claude directory read-only
    # Example: "/home/devcontainers/better-claude/.claude",  # Absolute path
]

# Paths that cannot be accessed at all (no read, write, or execute)
NO_ACCESS_PATHS = [
    # Example: ".env",
    # Example: "secrets/",
]

# Paths where new files cannot be created (existing files can be edited)
WRITE_RESTRICTED_PATHS = [
    # Example: ".claude/hooks/hook_handlers",  # Prevent new hook handlers
]

# Paths that cannot be deleted
DELETE_PROTECTED_PATHS = [
    ".claude/settings.json",
    ".claude/hooks/hook_handler.py",
]

# Enable/disable circuit breaker (set to False to bypass all checks)
CIRCUIT_BREAKER_ENABLED = True

# ====================================================================
# ENHANCED FEATURES
# ====================================================================

class GitAwareValidator:
    """Git-aware validation for safer operations."""
    
    @staticmethod
    def get_git_status(file_path):
        """Get git status for a file."""
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            result = subprocess.run(
                ["git", "status", "--porcelain", file_path],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout:
                status = result.stdout.strip()[:2]
                return {
                    "M": "modified",
                    "A": "added", 
                    "D": "deleted",
                    "??": "untracked",
                    "AM": "added-modified"
                }.get(status.strip(), "unknown")
            return "clean"
        except:
            return "unknown"
    
    @staticmethod
    def check_uncommitted_changes(file_path):
        """Check if file has uncommitted changes."""
        status = GitAwareValidator.get_git_status(file_path)
        return status in ["modified", "added-modified"]
    
    @staticmethod
    def is_ignored_file(file_path):
        """Check if file is git-ignored."""
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            result = subprocess.run(
                ["git", "check-ignore", file_path],
                cwd=project_dir,
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False


class DependencyAnalyzer:
    """Analyze file dependencies for impact assessment."""
    
    @staticmethod
    def check_import_impact(file_path):
        """Check how many files import this module."""
        if not file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            return 0
            
        try:
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
            basename = os.path.basename(file_path).replace(os.path.splitext(file_path)[1], "")
            
            # Quick grep for imports
            result = subprocess.run(
                ["grep", "-r", f"import.*{basename}", ".", "--include=*.py", "--include=*.js", "--include=*.ts"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.stdout:
                return len(result.stdout.strip().split('\n'))
        except:
            pass
        return 0


class OperationLogger:
    """Enhanced logging with structured data."""
    
    def __init__(self):
        self.log_dir = Path("~/.claude/hooks/operation_logs").expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
        
    def log_operation(self, tool_name, tool_input, result, warnings=None):
        """Log operation with structured data."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "tool": tool_name,
            "operation": self._extract_operation_type(tool_name, tool_input),
            "target": self._extract_target(tool_input),
            "result": result,
            "warnings": warnings or [],
            "git_status": None
        }
        
        # Add git status for file operations
        if target := log_entry.get("target"):
            if os.path.exists(target):
                log_entry["git_status"] = GitAwareValidator.get_git_status(target)
        
        # Write to daily log file
        log_file = self.log_dir / f"operations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def _extract_operation_type(self, tool_name, tool_input):
        """Extract operation type from tool and input."""
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if "rm" in command or "unlink" in command:
                return "delete"
            elif "mv" in command:
                return "move"
            elif "cp" in command:
                return "copy"
            elif ">" in command:
                return "write"
            return "execute"
        return tool_name.lower()
    
    def _extract_target(self, tool_input):
        """Extract target file/path from tool input."""
        return tool_input.get("file_path", tool_input.get("path", tool_input.get("command", "")))


class IntelligentPatternDetector:
    """Detect patterns that might indicate issues."""
    
    SUSPICIOUS_PATTERNS = {
        "recursive_path": {
            "pattern": re.compile(r"(.+/)\1{2,}"),
            "message": "⚠️ Recursive path pattern detected - this might be unintentional",
            "severity": "warning"
        },
        "test_outside_tests": {
            "pattern": re.compile(r"(?<!tests/)test_.*\.py$"),
            "message": "💡 Test file outside tests/ directory - consider moving to tests/",
            "severity": "suggestion"
        },
        "temp_file_pattern": {
            "pattern": re.compile(r"\.(tmp|temp|swp|~)$"),
            "message": "⚠️ Temporary file pattern detected - these are usually auto-generated",
            "severity": "warning"
        },
        "mixed_separators": {
            "pattern": re.compile(r"[/\\].*[\\]|[\\].*[/]"),
            "message": "⚠️ Mixed path separators detected - use consistent separators",
            "severity": "warning"
        }
    }
    
    @classmethod
    def check_patterns(cls, file_path):
        """Check for suspicious patterns and return warnings."""
        warnings = []
        
        for name, config in cls.SUSPICIOUS_PATTERNS.items():
            if config["pattern"].search(file_path):
                warnings.append({
                    "type": name,
                    "message": config["message"],
                    "severity": config["severity"]
                })
        
        return warnings


# Global instances
logger = OperationLogger()
operation_history = deque(maxlen=20)


def normalize_path(path):
    """Normalize a path for consistent comparison."""
    # Convert to absolute path if relative
    if not os.path.isabs(path):
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        path = os.path.join(project_dir, path)
    return os.path.normpath(path)


def check_path_access(path, operation):
    """Check if the given path can be accessed for the specified operation.

    Args:
        path: The file/directory path to check
        operation: One of "read", "write", "edit", "delete", "execute"

    Returns:
        (allowed, reason): Tuple of (bool, str) - whether allowed and reason if blocked
    """
    if not CIRCUIT_BREAKER_ENABLED:
        return True, ""

    normalized_path = normalize_path(path)

    # Check NO_ACCESS_PATHS first (most restrictive)
    for blocked_path in NO_ACCESS_PATHS:
        normalized_blocked = normalize_path(blocked_path)
        if (
            normalized_path.startswith(normalized_blocked + os.sep)
            or normalized_path == normalized_blocked
        ):
            return False, f"Circuit breaker: {blocked_path} is in NO_ACCESS_PATHS"

    # Check operation-specific restrictions
    if operation in ["write", "edit", "delete"]:
        # Check READ_ONLY_PATHS
        for readonly_path in READ_ONLY_PATHS:
            normalized_readonly = normalize_path(readonly_path)
            if (
                normalized_path.startswith(normalized_readonly + os.sep)
                or normalized_path == normalized_readonly
            ):
                return False, f"Circuit breaker: {readonly_path} is in READ_ONLY_PATHS"

    if operation == "write":
        # Check WRITE_RESTRICTED_PATHS (only for new file creation)
        for restricted_path in WRITE_RESTRICTED_PATHS:
            normalized_restricted = normalize_path(restricted_path)
            if (
                normalized_path.startswith(normalized_restricted + os.sep)
                or normalized_path == normalized_restricted
            ):
                # Check if file already exists
                if not os.path.exists(normalized_path):
                    return (
                        False,
                        f"Circuit breaker: Cannot create new files in {restricted_path}",
                    )

    if operation == "delete":
        # Check DELETE_PROTECTED_PATHS
        for protected_path in DELETE_PROTECTED_PATHS:
            normalized_protected = normalize_path(protected_path)
            if normalized_path == normalized_protected:
                return (
                    False,
                    f"Circuit breaker: {protected_path} is in DELETE_PROTECTED_PATHS",
                )

    return True, ""


def emit_warnings(warnings):
    """Emit warnings to stderr without blocking."""
    if warnings:
        print("\n=== PreToolUse Warnings ===", file=sys.stderr)
        for warning in warnings:
            print(f"{warning['message']}", file=sys.stderr)
        print("=========================\n", file=sys.stderr)


def handle(data):
    """Handle PreToolUse hook events."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    warnings = []
    
    # Track operation
    operation_history.append({
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
        "input": tool_input
    })

    # ====================================================================
    # CIRCUIT BREAKER CHECKS
    # ====================================================================

    # Handle Read operations
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            allowed, reason = check_path_access(file_path, "read")
            if not allowed:
                logger.log_operation(tool_name, tool_input, "blocked", [reason])
                print(reason, file=sys.stderr)
                sys.exit(2)

    # Handle Write operations
    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if file_path:
            allowed, reason = check_path_access(file_path, "write")
            if not allowed:
                logger.log_operation(tool_name, tool_input, "blocked", [reason])
                print(reason, file=sys.stderr)
                sys.exit(2)
            
            # Check patterns
            pattern_warnings = IntelligentPatternDetector.check_patterns(file_path)
            warnings.extend(pattern_warnings)
            
            # Check if overwriting existing file with uncommitted changes
            if os.path.exists(file_path) and GitAwareValidator.check_uncommitted_changes(file_path):
                warnings.append({
                    "message": f"⚠️ File '{file_path}' has uncommitted changes - consider committing first",
                    "severity": "warning"
                })

    # Handle Edit operations
    elif tool_name in ["Edit", "MultiEdit"]:
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
        else:  # MultiEdit
            file_path = tool_input.get("file_path", "")

        if file_path:
            allowed, reason = check_path_access(file_path, "edit")
            if not allowed:
                logger.log_operation(tool_name, tool_input, "blocked", [reason])
                print(reason, file=sys.stderr)
                sys.exit(2)
            
            # Warn about editing files with many dependencies
            import_count = DependencyAnalyzer.check_import_impact(file_path)
            if import_count > 5:
                warnings.append({
                    "message": f"⚠️ File '{file_path}' is imported by {import_count} other files - changes may have wide impact",
                    "severity": "warning"
                })

    # Handle Bash commands - check for file operations
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Warn about using old tools
        old_tools = {
            "grep": "Consider using 'rg' (ripgrep) instead - it's 10-100x faster",
            "find": "Consider using 'fd' instead - it's simpler and faster",
            "cat": "Consider using 'bat' for syntax highlighting"
        }
        
        for old_tool, suggestion in old_tools.items():
            if re.search(rf"\b{old_tool}\b", command) and not re.search(rf"\b{old_tool}\s+-", command):
                warnings.append({
                    "message": f"💡 {suggestion}",
                    "severity": "suggestion"
                })

        # Extract file paths from common commands

        # Check for rm/unlink commands (delete operations)
        if re.search(r"\b(rm|unlink)\b", command):
            # Extract paths after rm/unlink
            matches = re.findall(r"(?:rm|unlink)\s+(?:-[rf]+\s+)?([^\s;|&]+)", command)
            for path in matches:
                path = path.strip("\"'")
                allowed, reason = check_path_access(path, "delete")
                if not allowed:
                    logger.log_operation(tool_name, tool_input, "blocked", [reason])
                    print(reason, file=sys.stderr)
                    sys.exit(2)
                
                # Warn about deleting files with uncommitted changes
                if os.path.exists(path) and GitAwareValidator.check_uncommitted_changes(path):
                    warnings.append({
                        "message": f"⚠️ Deleting '{path}' with uncommitted changes - consider committing first",
                        "severity": "warning"
                    })
                
                # Warn about deleting imported files
                if path.endswith(".py"):
                    import_count = DependencyAnalyzer.check_import_impact(path)
                    if import_count > 0:
                        warnings.append({
                            "message": f"⚠️ File '{path}' is imported by {import_count} other files",
                            "severity": "warning"
                        })

        # Check for redirect operations (write)
        if ">" in command:
            # Extract paths after > or >>
            matches = re.findall(r">\s*([^\s;|&]+)", command)
            for path in matches:
                path = path.strip("\"'")
                allowed, reason = check_path_access(path, "write")
                if not allowed:
                    logger.log_operation(tool_name, tool_input, "blocked", [reason])
                    print(reason, file=sys.stderr)
                    sys.exit(2)

        # Check for commands that read files
        read_commands = ["cat", "less", "more", "head", "tail", "grep", "awk", "sed"]
        for cmd in read_commands:
            if re.search(rf"\b{cmd}\b", command):
                # Simple extraction - may need refinement
                matches = re.findall(rf"{cmd}\s+(?:-[^\s]+\s+)*([^\s;|&]+)", command)
                for path in matches:
                    path = path.strip("\"'")
                    if os.path.exists(path) or not path.startswith("-"):
                        allowed, reason = check_path_access(path, "read")
                        if not allowed:
                            logger.log_operation(tool_name, tool_input, "blocked", [reason])
                            print(reason, file=sys.stderr)
                            sys.exit(2)

    # ====================================================================
    # EXISTING PROTECTION LOGIC
    # ====================================================================

    # Handle Bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        description = tool_input.get("description", "No description")

        # Log Bash commands
        log_dir = os.path.expanduser("~/.claude")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "bash-command-log.txt")
        with open(log_path, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {command} - {description}\n")

        # Block dangerous commands
        dangerous_patterns = ["rm -rf /", "dd if=/dev/zero", ":(){:|:&};:"]
        if any(pattern in command for pattern in dangerous_patterns):
            logger.log_operation(tool_name, tool_input, "blocked", ["Dangerous command"])
            print("Blocked: Dangerous command detected", file=sys.stderr)
            sys.exit(2)

        # Protect critical Claude files from deletion
        protected_files = [
            "/home/devcontainers/better-claude/.claude/settings.json",
            "/home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
        ]

        if "rm " in command or "unlink " in command:
            for protected_file in protected_files:
                if protected_file in command:
                    logger.log_operation(tool_name, tool_input, "blocked", ["Protected file"])
                    print(
                        f"Blocked: Cannot delete {protected_file} - critical Claude file is protected",
                        file=sys.stderr,
                    )
                    sys.exit(2)

    # Handle file modifications
    elif tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = tool_input.get("file_path", tool_input.get("path", ""))

        # Prevent recursive .claude directories
        if ".claude" in file_path:
            # Count occurrences of .claude in the path
            claude_count = file_path.count(".claude")
            if claude_count > 1:
                logger.log_operation(tool_name, tool_input, "blocked", ["Recursive .claude"])
                print(
                    f"Blocked: Cannot create recursive .claude directories in {file_path}",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Prevent new files in hook_handlers directory
        if tool_name in ["Write"]:  # Only block on file creation
            # Normalize path for comparison
            normalized_path = os.path.normpath(file_path)
            hook_handlers_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/hook_handlers",
            )

            # Check if trying to create new file in hook_handlers directory
            if (
                normalized_path.startswith(hook_handlers_dir + os.sep)
                or normalized_path == hook_handlers_dir
            ):
                logger.log_operation(tool_name, tool_input, "blocked", ["Hook handlers protected"])
                print(
                    "Blocked: Cannot create new files in hook_handlers directory",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Ensure test files are only created in the tests directory
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path)
            normalized_path = os.path.normpath(file_path)
            tests_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/tests",
            )

            # Check if it's a test file (starts with test_ or ends with _test.py)
            if filename.startswith("test_") or filename.endswith("_test.py"):
                # Ensure it's in the tests directory
                if not normalized_path.startswith(tests_dir + os.sep):
                    # Non-blocking warning instead of block
                    warnings.append({
                        "message": f"💡 Test files are typically placed in {tests_dir}",
                        "severity": "suggestion"
                    })

        # Ensure markdown files are only created in the docs directory
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path)
            normalized_path = os.path.normpath(file_path)
            docs_dir = os.path.normpath(
                "/home/devcontainers/better-claude/.claude/hooks/docs",
            )

            # Check if it's a markdown file (but allow README.md anywhere)
            if filename.endswith((".md", ".markdown")) and filename != "README.md":
                # Ensure it's in the docs directory
                if not normalized_path.startswith(docs_dir + os.sep):
                    # Non-blocking warning instead of block
                    warnings.append({
                        "message": f"💡 Documentation files are typically placed in {docs_dir}",
                        "severity": "suggestion"
                    })

        # Prevent backwards compatibility naming patterns
        if tool_name in ["Write"]:  # Only block on file creation
            filename = os.path.basename(file_path).lower()
            # Check for bad naming patterns (but allow .bak/.backup extensions)
            bad_patterns = [
                r"\benhanced\b",
                r"\badvanced\b",
                r"\bv2\b",
                r"\bv\d+\b",
                r"\bbackup\b",
            ]
            # Extract filename without extension
            name_without_ext = os.path.splitext(filename)[0]

            for pattern in bad_patterns:
                if re.search(pattern, name_without_ext):
                    logger.log_operation(tool_name, tool_input, "blocked", ["Bad naming pattern"])
                    print(
                        f"Blocked: Please use descriptive names instead of '{os.path.basename(file_path)}'. Avoid 'enhanced', 'advanced', 'v2', or 'backup' in filenames.",
                        file=sys.stderr,
                    )
                    sys.exit(2)

        # Block protected file modifications
        blocked_paths = [
            ".env",
            "package-lock.json",
            ".git/",
            "yarn.lock",
            "Gemfile.lock",
        ]

        # Special protection for critical Claude files - exact match required
        protected_files = [
            "/home/devcontainers/better-claude/.claude/settings.json",
            "/home/devcontainers/better-claude/.claude/hooks/hook_handler.py",
        ]

        normalized_file_path = os.path.normpath(file_path)
        for protected_file in protected_files:
            if normalized_file_path == os.path.normpath(protected_file):
                logger.log_operation(tool_name, tool_input, "blocked", ["Protected Claude file"])
                print(
                    f"Blocked: Cannot modify {file_path} - critical Claude file is protected",
                    file=sys.stderr,
                )
                sys.exit(2)

        if any(p in file_path for p in blocked_paths):
            logger.log_operation(tool_name, tool_input, "blocked", ["Protected file type"])
            print(
                f"Blocked: Cannot modify {file_path} - protected file",
                file=sys.stderr,
            )
            sys.exit(2)

    # Emit non-blocking warnings
    emit_warnings(warnings)
    
    # Log successful operation
    logger.log_operation(tool_name, tool_input, "allowed", [w["message"] for w in warnings])
    
    sys.exit(0)