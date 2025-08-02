#!/usr/bin/env python3
"""Anti-pattern detection and validation logic."""

import ast
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ValidationIssue:
    """Represents a validation issue found in code."""

    category: str
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    line: int
    code_snippet: str
    pattern: Optional[str] = None


class PatternValidator(ABC):
    """Base class for pattern validators."""

    @abstractmethod
    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate content and return found issues."""

    def is_in_comment(self, content: str, match_start: int, line_text: str) -> bool:
        """Check if a match is within a comment."""
        # Get the actual line that contains the match
        line_start = content.rfind("\n", 0, match_start) + 1
        line_end = content.find("\n", match_start)
        if line_end == -1:
            line_end = len(content)
        
        # Get the exact line containing the match
        actual_line = content[line_start:line_end]
        
        # Calculate position within the line
        relative_pos = match_start - line_start
        
        # Check for single-line comment
        comment_pos = actual_line.find("#")
        if comment_pos != -1 and comment_pos < relative_pos:
            return True

        # Check for multi-line comment/string
        before_match = content[:match_start]
        triple_quotes = ['"""', "'''"]
        for quote in triple_quotes:
            # Count the number of occurrences before the match
            count = before_match.count(quote)
            # If odd number, we're inside a multi-line string
            if count % 2 == 1:
                return True

        return False


class SecurityPatternValidator(PatternValidator):
    """Validates security-related anti-patterns."""

    # Python patterns
    PYTHON_PATTERNS = [
        # Exposed secrets
        (
            r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([A-Za-z0-9+/]{20,})["\']',
            "CRITICAL: Exposed API key detected! Never commit secrets to code.",
        ),
        (
            r'(?i)aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*["\']([A-Z0-9]{20})["\']',
            "CRITICAL: AWS Access Key exposed!",
        ),
        (
            r'(?i)github[_-]?token\s*[:=]\s*["\']ghp_[A-Za-z0-9]{36}["\']',
            "CRITICAL: GitHub token exposed!",
        ),
        (
            r"mongodb\+srv://[^:]+:[^@]+@[^/\s]+",
            "CRITICAL: MongoDB connection string with credentials exposed!",
        ),
        # SQL injection - more comprehensive patterns
        (
            r"(SELECT|INSERT|UPDATE|DELETE).*?\+.*?(?:request|params|input|user_id|user_input)",
            "CRITICAL: SQL injection vulnerability via string concatenation!",
        ),
        (
            r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\{[^}]*(?:request|params|input|user|id)\b',
            "CRITICAL: SQL injection vulnerability via f-string!",
        ),
        (
            r'["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?["\'].*?%.*?(?:request|params|input|user)',
            "CRITICAL: SQL injection vulnerability via string formatting!",
        ),
        # Command injection - broader patterns
        (
            r"os\.system\s*\([^)]*[fF]?[\"'].*?\{[^}]*\}",
            "CRITICAL: Command injection vulnerability via os.system with string interpolation!",
        ),
        (
            r"os\.system\s*\([^)]*(?:request|params|input|user)",
            "CRITICAL: Command injection vulnerability via os.system!",
        ),
        (
            r"subprocess.*shell\s*=\s*True.*(?:request|params|input|user)",
            "CRITICAL: Command injection vulnerability via subprocess!",
        ),
        # eval() - more comprehensive
        (
            r"eval\s*\([^)]*(?:request|params|input|body|query|user|expression|expr)\b",
            "CRITICAL: Code injection vulnerability via eval!",
        ),
        (
            r"exec\s*\([^)]*(?:request|params|input|body|query|user)",
            "CRITICAL: Code injection vulnerability via exec!",
        ),
        # Path traversal - more specific patterns to avoid false positives
        (
            r"open\s*\(\s*(?:request\.|params\.|input\.|user_input|[^)]*\.get\(|flask\.request|request\[)",
            "CRITICAL: Path traversal vulnerability!",
        ),
        (
            r"with\s+open\s*\(\s*(?:request\.|params\.|input\.|user_input|[^)]*\.get\(|flask\.request|request\[)",
            "CRITICAL: Path traversal vulnerability in file opening!",
        ),
        # Also catch variables that come from user input
        (
            r"(?:file_path|filename|path)\s*=\s*(?:request\.|params\.|input\.|user_input|[^=]*\.get\()[^)]*\).*open\s*\(\s*(?:file_path|filename|path)",
            "CRITICAL: Path traversal - using user input for file operations!",
        ),
        # Hardcoded passwords and secrets
        (
            r'(?i)password\s*[:=]\s*["\'][^"\']+["\']',
            "WARNING: Hardcoded password detected. Use environment variables!",
        ),
        (
            r'(?i)(secret|jwt[_-]?secret|secret[_-]?key)\s*[:=]\s*["\'][^"\']+["\']',
            "CRITICAL: Hardcoded secret key detected!",
        ),
    ]

    # JavaScript/TypeScript patterns
    JS_PATTERNS = [
        # Exposed secrets
        (
            r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([A-Za-z0-9+/]{20,})["\']',
            "CRITICAL: Exposed API key detected! Never commit secrets to code.",
        ),
        (
            r'(?i)process\.env\.[A-Z_]+\s*\|\|\s*["\'][^"\']+["\']',
            "WARNING: Hardcoded fallback for environment variable. Use proper config management.",
        ),
        # eval() usage
        (
            r"\beval\s*\([^)]*(?:request|req|params|body|query)",
            "CRITICAL: eval() with user input - code injection vulnerability!",
        ),
        # innerHTML with user input
        (
            r"\.innerHTML\s*=.*(?:request|req|params|body|query|user)",
            "CRITICAL: innerHTML with user input - XSS vulnerability!",
        ),
        # SQL injection in template literals
        (
            r"`[^`]*(?:SELECT|INSERT|UPDATE|DELETE)[^`]*\$\{[^}]*(?:request|req|params|body|query)",
            "CRITICAL: SQL injection via template literal!",
        ),
        # Command injection
        (
            r"(?:exec|execSync|spawn|spawnSync)\s*\([^)]*(?:request|req|params|body|query)",
            "CRITICAL: Command injection vulnerability!",
        ),
        # Unsafe regex
        (
            r"new\s+RegExp\s*\([^)]*(?:request|req|params|body|query)",
            "CRITICAL: ReDoS vulnerability - unsafe regex with user input!",
        ),
        # CORS wildcard
        (
            r'Access-Control-Allow-Origin["\']?\s*:\s*["\'][*]["\']',
            "WARNING: CORS wildcard (*) allows any origin!",
        ),
        # Disabled CSRF
        (
            r"csrf\s*:\s*false",
            "WARNING: CSRF protection disabled!",
        ),
        # JWT secret hardcoded
        (
            r'(?:jwt|jsonwebtoken)\.sign\([^,]+,\s*["\'][^"\']+["\']',
            "CRITICAL: Hardcoded JWT secret!",
        ),
    ]

    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate content for security issues."""
        issues: List[ValidationIssue] = []
        lines = content.split("\n")
        ext = Path(file_path).suffix.lower()

        # Select patterns based on file type
        if ext == ".py":
            patterns = self.PYTHON_PATTERNS
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            patterns = self.JS_PATTERNS
        else:
            return issues

        for pattern, message in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_no = content[: match.start()].count("\n") + 1
                line_text = lines[line_no - 1] if line_no <= len(lines) else ""

                # Skip if in comment
                if self.is_in_comment(content, match.start(), line_text):
                    continue

                # Skip if it's in a pattern definition (inside quotes)
                if any(q in line_text for q in ['r"', "r'", '"""', "'''", '"', "'"]):
                    # Check if match is inside quotes
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    relative_pos = match.start() - line_start
                    # Simple check: count quotes before match position
                    before_match = line_text[:relative_pos]
                    if (
                        before_match.count('"') % 2 == 1
                        or before_match.count("'") % 2 == 1
                    ):
                        continue

                # Skip if it's in a pattern definition
                if ext == ".py" and ('r"' in line_text or "r'" in line_text):
                    continue

                severity = "CRITICAL" if "CRITICAL" in message else "WARNING"
                issues.append(
                    ValidationIssue(
                        category="Security",
                        severity=severity,
                        message=message,
                        line=line_no,
                        code_snippet=match.group()[:100],
                        pattern=pattern,
                    ),
                )

        return issues


class DataLossPatternValidator(PatternValidator):
    """Validates data loss anti-patterns."""

    PATTERNS = [
        (
            r'shutil\.rmtree\s*\([^)]*["\']/',
            "CRITICAL: Deleting from root directory!",
        ),
        (
            r"DROP\s+DATABASE",
            "CRITICAL: Dropping entire database!",
        ),
        (
            r"TRUNCATE\s+TABLE",
            "CRITICAL: Truncating table without backup!",
        ),
        (
            r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",
            "CRITICAL: DELETE without WHERE clause - data loss risk!",
        ),
        (
            r"rm\s+-rf\s+/",
            "CRITICAL: Recursive force delete from root!",
        ),
    ]

    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate content for data loss risks."""
        issues = []
        lines = content.split("\n")

        for pattern, message in self.PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_no = content[: match.start()].count("\n") + 1
                line_text = lines[line_no - 1] if line_no <= len(lines) else ""

                # Skip if in comment
                if self.is_in_comment(content, match.start(), line_text):
                    continue

                # Skip if it's in a pattern definition (inside quotes)
                if any(q in line_text for q in ['r"', "r'", '"""', "'''", '"', "'"]):
                    # Check if match is inside quotes
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    relative_pos = match.start() - line_start
                    # Simple check: count quotes before match position
                    before_match = line_text[:relative_pos]
                    if (
                        before_match.count('"') % 2 == 1
                        or before_match.count("'") % 2 == 1
                    ):
                        continue

                issues.append(
                    ValidationIssue(
                        category="Data Loss",
                        severity="CRITICAL",
                        message=message,
                        line=line_no,
                        code_snippet=match.group()[:100],
                        pattern=pattern,
                    ),
                )

        return issues


class PerformancePatternValidator(PatternValidator):
    """Validates performance anti-patterns."""

    PYTHON_PATTERNS = [
        (
            r"while\s+True\s*:(?!.*break)",
            "WARNING: Potential infinite loop detected!",
        ),
        (
            r"time\.sleep\(.*?\).*async\s+def",
            "WARNING: time.sleep in async code (use asyncio.sleep)!",
        ),
    ]

    JS_PATTERNS = [
        # document.write
        (
            r"document\.write\s*\(",
            "WARNING: document.write blocks parsing and is deprecated!",
        ),
        # Synchronous XHR
        (
            r"XMLHttpRequest.*async\s*:\s*false",
            "WARNING: Synchronous XMLHttpRequest is deprecated and blocks!",
        ),
        # Large inline scripts
        (
            r"<script[^>]*>[^<]{10000,}</script>",
            "WARNING: Large inline script blocks parsing!",
        ),
        # Missing await in async function
        (
            r"async\s+(?:function|\([^)]*\)\s*=>)[^{]*\{[^}]*(?:fetch|axios|Promise)[^}]*(?!await)[^}]*\}",
            "WARNING: Async operation without await!",
        ),
        # Array operations in loops
        (
            r"for\s*\([^)]+\)\s*\{[^}]*\.push\(",
            "WARNING: Consider using map/filter instead of push in loops!",
        ),
    ]

    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate content for performance issues."""
        issues: List[ValidationIssue] = []
        lines = content.split("\n")
        ext = Path(file_path).suffix.lower()

        # Select patterns based on file type
        if ext == ".py":
            patterns = self.PYTHON_PATTERNS
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            patterns = self.JS_PATTERNS
        else:
            return issues

        for pattern, message in patterns:
            matches = re.finditer(
                pattern,
                content,
                re.IGNORECASE | re.MULTILINE | re.DOTALL,
            )
            for match in matches:
                line_no = content[: match.start()].count("\n") + 1
                line_text = lines[line_no - 1] if line_no <= len(lines) else ""

                # Skip if in comment
                if self.is_in_comment(content, match.start(), line_text):
                    continue

                # Skip if it's in a pattern definition (inside quotes)
                if any(q in line_text for q in ['r"', "r'", '"""', "'''", '"', "'"]):
                    # Check if match is inside quotes
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    relative_pos = match.start() - line_start
                    # Simple check: count quotes before match position
                    before_match = line_text[:relative_pos]
                    if (
                        before_match.count('"') % 2 == 1
                        or before_match.count("'") % 2 == 1
                    ):
                        continue

                issues.append(
                    ValidationIssue(
                        category="Performance",
                        severity="WARNING",
                        message=message,
                        line=line_no,
                        code_snippet=match.group()[:100],
                        pattern=pattern,
                    ),
                )

        return issues


class ReactPatternValidator(PatternValidator):
    """Validates React-specific anti-patterns."""

    PATTERNS = [
        # Direct state mutation
        (
            r"this\.state\.[a-zA-Z_]+\s*=",
            "CRITICAL: Direct state mutation in React! Use setState!",
        ),
        (
            r"state\.[a-zA-Z_]+\s*=(?!=)",
            "CRITICAL: Direct state mutation! Use setState or state setter!",
        ),
        # Missing key in list
        (
            r"\.map\s*\([^)]*\)\s*=>\s*[^}]*<[^>]+>(?![^}]*key\s*=)",
            "WARNING: Missing key prop in list rendering!",
        ),
        # Unsafe dangerouslySetInnerHTML
        (
            r"dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*[^}]*(?:request|req|params|body|query|user)",
            "CRITICAL: XSS vulnerability via dangerouslySetInnerHTML!",
        ),
        # useEffect without dependencies
        (
            r"useEffect\s*\(\s*\([^)]*\)\s*=>\s*\{[^}]+\}\s*\)",
            "WARNING: useEffect without dependency array causes infinite re-renders!",
        ),
        # Binding in render
        (
            r"(?:onClick|onChange|onSubmit)\s*=\s*\{[^}]*\.bind\s*\(",
            "WARNING: Binding in render creates new function every render!",
        ),
    ]

    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate React code."""
        ext = Path(file_path).suffix.lower()
        if ext not in [".jsx", ".tsx", ".js", ".ts"]:
            return []

        # Quick check if this is likely React code
        if not any(
            indicator in content for indicator in ["React", "react", "jsx", "tsx"]
        ):
            return []

        issues = []
        lines = content.split("\n")

        for pattern, message in self.PATTERNS:
            matches = re.finditer(
                pattern,
                content,
                re.IGNORECASE | re.MULTILINE | re.DOTALL,
            )
            for match in matches:
                line_no = content[: match.start()].count("\n") + 1
                line_text = lines[line_no - 1] if line_no <= len(lines) else ""

                # Skip if in comment
                if self.is_in_comment(content, match.start(), line_text):
                    continue

                # Skip if it's in a pattern definition (inside quotes)
                if any(q in line_text for q in ['r"', "r'", '"""', "'''", '"', "'"]):
                    # Check if match is inside quotes
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    relative_pos = match.start() - line_start
                    # Simple check: count quotes before match position
                    before_match = line_text[:relative_pos]
                    if (
                        before_match.count('"') % 2 == 1
                        or before_match.count("'") % 2 == 1
                    ):
                        continue

                severity = "CRITICAL" if "CRITICAL" in message else "WARNING"
                issues.append(
                    ValidationIssue(
                        category="React",
                        severity=severity,
                        message=message,
                        line=line_no,
                        code_snippet=match.group()[:100],
                        pattern=pattern,
                    ),
                )

        return issues


class FileSizeValidator(PatternValidator):
    """Validates file size and complexity."""

    MAX_LINES = 1000
    MAX_FUNCTION_LINES = 50
    MAX_CLASS_LINES = 200

    def validate(self, content: str, file_path: str) -> List[ValidationIssue]:
        """Validate file size and complexity."""
        issues = []
        lines = content.split("\n")

        # Check total file size
        if len(lines) > self.MAX_LINES:
            issues.append(
                ValidationIssue(
                    category="File Size",
                    severity="WARNING",
                    message=f"Large file warning: {len(lines)} lines (max recommended: {self.MAX_LINES})",
                    line=1,
                    code_snippet=f"Total lines: {len(lines)}",
                ),
            )

        # For Python files, check function/class sizes
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.end_lineno is None or node.lineno is None:
                            continue
                        func_lines = node.end_lineno - node.lineno + 1
                        if func_lines > self.MAX_FUNCTION_LINES:
                            issues.append(
                                ValidationIssue(
                                    category="Complexity",
                                    severity="WARNING",
                                    message=f"Function '{node.name}' is too long: {func_lines} lines (max recommended: {self.MAX_FUNCTION_LINES})",
                                    line=node.lineno,
                                    code_snippet=f"def {node.name}(...)",
                                ),
                            )
                    elif isinstance(node, ast.ClassDef):
                        if node.end_lineno is None or node.lineno is None:
                            continue
                        class_lines = node.end_lineno - node.lineno + 1
                        if class_lines > self.MAX_CLASS_LINES:
                            issues.append(
                                ValidationIssue(
                                    category="Complexity",
                                    severity="WARNING",
                                    message=f"Class '{node.name}' is too long: {class_lines} lines (max recommended: {self.MAX_CLASS_LINES})",
                                    line=node.lineno,
                                    code_snippet=f"class {node.name}(...)",
                                ),
                            )
            except SyntaxError:
                pass  # Syntax errors will be caught by diagnostics

        return issues


def validate_file(file_path: str, content: str) -> Tuple[List[ValidationIssue], bool]:
    """Validate a file and return issues and whether there are critical issues."""
    validators = [
        SecurityPatternValidator(),
        DataLossPatternValidator(),
        PerformancePatternValidator(),
        ReactPatternValidator(),
        FileSizeValidator(),
    ]

    all_issues = []
    for validator in validators:
        issues = validator.validate(content, file_path)
        all_issues.extend(issues)

    # Check for critical issues
    has_critical = any(issue.severity == "CRITICAL" for issue in all_issues)

    return all_issues, has_critical


def print_validation_report(issues: List[ValidationIssue], file_path: str) -> None:
    """Print a validation report to stderr."""
    if not issues:
        print("✅ No critical anti-patterns found", file=sys.stderr)
        return

    # Group by severity
    critical_issues = [i for i in issues if i.severity == "CRITICAL"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    if critical_issues:
        print("\n🚨 CRITICAL ANTI-PATTERNS DETECTED:", file=sys.stderr)
        print("─" * 50, file=sys.stderr)

        for issue in critical_issues:
            print(f"\n{issue.category} Issue at line {issue.line}:", file=sys.stderr)
            print(f"  {issue.message}", file=sys.stderr)
            print(f"  Code: {issue.code_snippet}", file=sys.stderr)

        print("\n─" * 50, file=sys.stderr)
        print("🛑 BLOCKING: These critical issues must be fixed!", file=sys.stderr)
        print("   Claude will be notified immediately.", file=sys.stderr)
        print("   📝 Note: Hooks can be temporarily disabled in", file=sys.stderr)
        print("      /home/devcontainers/better-claude/.claude/hooks/hook_handler.py\n", file=sys.stderr)

    if warnings and not critical_issues:
        print(f"⚠️  {len(warnings)} warnings detected but not critical", file=sys.stderr)
