#!/usr/bin/env python3
import os
import subprocess
import sys


def handle(data):
    """Handle PostToolUse hook events."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Initialize file_path to avoid unbound errors
    file_path = ""

    # Handle post-file modifications
    if tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = tool_input.get("file_path", tool_input.get("path", ""))

        # Auto-format TypeScript/JavaScript files
        if file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            if os.path.exists("package.json"):
                try:
                    result = subprocess.run(
                        ["npx", "prettier", "--write", file_path],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        print(
                            f"Prettier formatting failed: {result.stderr}",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                except Exception as e:
                    print(f"Failed to run prettier: {e}", file=sys.stderr)
                    sys.exit(1)

            # Check for JavaScript/TypeScript anti-patterns
            print(
                "\n🔍 Checking for JavaScript/TypeScript anti-patterns...",
                file=sys.stderr,
            )

            try:
                with open(file_path) as f:
                    content = f.read()

                js_antipatterns_found = False
                js_critical_antipatterns = []
                lines = content.split("\n")

                # JavaScript/TypeScript Security anti-patterns
                js_security_patterns = [
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

                # JavaScript/TypeScript Performance anti-patterns
                js_perf_patterns = [
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

                # React-specific anti-patterns
                react_patterns = [
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

                # Check all JavaScript/TypeScript patterns
                for patterns, category in [
                    (js_security_patterns, "Security"),
                    (js_perf_patterns, "Performance"),
                    (react_patterns, "React"),
                ]:
                    for pattern, message in patterns:
                        import re

                        matches = re.finditer(
                            pattern,
                            content,
                            re.IGNORECASE | re.MULTILINE | re.DOTALL,
                        )
                        for match in matches:
                            line_no = content[: match.start()].count("\n") + 1
                            # Skip if it's in a comment
                            line_text = (
                                lines[line_no - 1] if line_no <= len(lines) else ""
                            )
                            if "//" in line_text and line_text.index(
                                "//",
                            ) < match.start() - content.rfind("\n", 0, match.start()):
                                continue
                            # Skip if it's in a multi-line comment
                            before_match = content[: match.start()]
                            if (
                                "/*" in before_match
                                and "*/" not in before_match[before_match.rfind("/*") :]
                            ):
                                continue

                            js_antipatterns_found = True
                            if "CRITICAL" in message:
                                js_critical_antipatterns.append(
                                    {
                                        "category": category,
                                        "message": message,
                                        "line": line_no,
                                        "code": match.group()[:100],  # First 100 chars
                                    },
                                )

                # Report JavaScript/TypeScript critical anti-patterns
                if js_critical_antipatterns:
                    print(
                        "\n🚨 CRITICAL JAVASCRIPT/TYPESCRIPT ANTI-PATTERNS DETECTED:",
                        file=sys.stderr,
                    )
                    print("─" * 50, file=sys.stderr)

                    for issue in js_critical_antipatterns:
                        print(
                            f"\n{issue['category']} Issue at line {issue['line']}:",
                            file=sys.stderr,
                        )
                        print(f"  {issue['message']}", file=sys.stderr)
                        print(f"  Code: {issue['code']}", file=sys.stderr)

                    print("\n─" * 50, file=sys.stderr)
                    print(
                        "🛑 BLOCKING: These critical JavaScript/TypeScript issues must be fixed!",
                        file=sys.stderr,
                    )
                    print("   Claude will be notified immediately.\n", file=sys.stderr)

                    # Exit with code 2 for critical issues
                    sys.exit(2)
                elif js_antipatterns_found:
                    print(
                        "⚠️  Some JavaScript/TypeScript anti-patterns detected but not critical",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "✅ No critical JavaScript/TypeScript anti-patterns found",
                        file=sys.stderr,
                    )

            except Exception as e:
                print(
                    f"Warning: Failed to check JS/TS anti-patterns: {e}",
                    file=sys.stderr,
                )

        # Auto-format Python files
        elif file_path.endswith(".py"):
            # List of formatters to run in order
            formatters = [
                # autoflake: removes unused imports and variables
                [
                    "autoflake",
                    "--in-place",
                    "--remove-all-unused-imports",
                    "--remove-unused-variables",
                    file_path,
                ],
                # absolufy-imports: converts relative imports to absolute
                ["absolufy-imports", "--application-directories", ".", file_path],
                # isort: sorts and organizes imports
                ["isort", file_path],
                # flynt: converts old string formatting to f-strings
                ["flynt", "--line-length", "88", "--transform-concats", file_path],
                # pyupgrade: upgrades syntax to newer Python versions
                ["pyupgrade", "--py38-plus", file_path],
                # docformatter: formats docstrings to PEP 257
                [
                    "docformatter",
                    "--in-place",
                    "--wrap-summaries",
                    "88",
                    "--wrap-descriptions",
                    "88",
                    file_path,
                ],
                # add-trailing-comma: adds trailing commas for better diffs
                ["add-trailing-comma", "--py36-plus", file_path],
                # ssort: sorts class members
                ["ssort", file_path],
                # black: code formatter
                ["black", file_path],
                # ruff: linter and formatter (with fixes)
                ["ruff", "check", "--fix", file_path],
                # ruff format: additional formatting
                ["ruff", "format", file_path],
                # refurb: additional code modernization
                ["refurb", "--write", file_path],
            ]

            for formatter_cmd in formatters:
                try:
                    # Check if the tool is available
                    tool_name = formatter_cmd[0]
                    check_result = subprocess.run(
                        ["which", tool_name],
                        capture_output=True,
                        text=True,
                    )
                    if check_result.returncode != 0:
                        print(
                            f"Warning: {tool_name} not found, skipping",
                            file=sys.stderr,
                        )
                        continue

                    # Run the formatter
                    result = subprocess.run(
                        formatter_cmd,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        # Some tools may return non-zero for warnings, log but don't fail
                        print(
                            f"Warning from {tool_name}: {result.stderr}",
                            file=sys.stderr,
                        )
                except Exception as e:
                    print(f"Failed to run {formatter_cmd[0]}: {e}", file=sys.stderr)
                    # Continue with other formatters even if one fails
                    continue

            # After all formatters, run comprehensive diagnostics
            print(f"\n🔍 Running diagnostics on {file_path}...", file=sys.stderr)

            diagnostics_found = False
            all_diagnostics = []

            # 1. Run mypy for type checking
            try:
                mypy_result = subprocess.run(
                    [
                        "mypy",
                        "--no-error-summary",
                        "--show-error-codes",
                        "--show-column-numbers",
                        file_path,
                    ],
                    capture_output=True,
                    text=True,
                )
                if mypy_result.returncode != 0 and mypy_result.stdout.strip():
                    diagnostics_found = True
                    all_diagnostics.append(
                        ("MyPy Type Errors", mypy_result.stdout.strip()),
                    )
            except Exception as e:
                print(f"Warning: Failed to run mypy: {e}", file=sys.stderr)

            # 2. Run pylint for code quality and errors
            try:
                pylint_result = subprocess.run(
                    ["pylint", "--errors-only", "--output-format=parseable", file_path],
                    capture_output=True,
                    text=True,
                )
                if pylint_result.returncode != 0 and pylint_result.stdout.strip():
                    diagnostics_found = True
                    all_diagnostics.append(
                        ("PyLint Errors", pylint_result.stdout.strip()),
                    )
            except Exception as e:
                print(f"Warning: Failed to run pylint: {e}", file=sys.stderr)

            # 3. Run ruff for additional checks
            try:
                ruff_result = subprocess.run(
                    ["ruff", "check", "--output-format=text", file_path],
                    capture_output=True,
                    text=True,
                )
                if ruff_result.returncode != 0 and ruff_result.stdout.strip():
                    # Filter out fixable issues since we already ran ruff --fix
                    lines = ruff_result.stdout.strip().split("\n")
                    non_fixable = [
                        line for line in lines if "[*]" not in line and line.strip()
                    ]
                    if non_fixable:
                        diagnostics_found = True
                        all_diagnostics.append(("Ruff Errors", "\n".join(non_fixable)))
            except Exception as e:
                print(f"Warning: Failed to run ruff: {e}", file=sys.stderr)

            # 4. Check for asyncio issues (the specific error mentioned)
            try:
                import ast
                import re

                with open(file_path) as f:
                    content = f.read()

                # Parse the AST to find async issues
                try:
                    tree = ast.parse(content)

                    class AsyncChecker(ast.NodeVisitor):
                        def __init__(self):
                            self.issues = []

                        def visit_Call(self, node):
                            # Check for common asyncio mistakes
                            if isinstance(node.func, ast.Attribute):
                                if node.func.attr in [
                                    "create_task",
                                    "ensure_future",
                                    "gather",
                                    "wait",
                                ]:
                                    # These functions expect coroutines or futures
                                    for arg in node.args:
                                        if isinstance(arg, ast.Call):
                                            # Check if it's not an async call
                                            func_name = None
                                            if isinstance(arg.func, ast.Name):
                                                func_name = arg.func.id
                                            elif isinstance(arg.func, ast.Attribute):
                                                func_name = arg.func.attr

                                            if func_name:
                                                line_no = arg.lineno
                                                self.issues.append(
                                                    f"Line {line_no}: Possible issue - {node.func.attr}() expects a coroutine, but {func_name}() might not be async",
                                                )
                            self.generic_visit(node)

                    checker = AsyncChecker()
                    checker.visit(tree)

                    if checker.issues:
                        diagnostics_found = True
                        all_diagnostics.append(
                            ("Async/Await Issues", "\n".join(checker.issues)),
                        )

                except SyntaxError as e:
                    diagnostics_found = True
                    all_diagnostics.append(
                        ("Syntax Error", f"Line {e.lineno}: {e.msg}"),
                    )

            except Exception as e:
                print(f"Warning: Failed to check async issues: {e}", file=sys.stderr)

            # 5. Check for unbound variables (original check)
            try:
                # Pattern to find potential unbound variables
                unbound_issues = []
                lines = content.split("\n")

                # Look for common patterns that indicate possibly unbound variables
                for i, line in enumerate(lines, 1):
                    # Check for variables used in except blocks that might not be defined
                    if "except" in line and "as" in line:
                        # Next few lines might reference the exception variable outside the block
                        pass

                    # Check for variables that might not be initialized in all paths
                    if re.search(r"if .* in locals\(\)", line):
                        var_match = re.search(r'"(\w+)" (?:not )?in locals\(\)', line)
                        if var_match:
                            var_name = var_match.group(1)
                            unbound_issues.append(
                                f"Line {i}: Variable '{var_name}' might not be defined in all code paths",
                            )

                if unbound_issues:
                    diagnostics_found = True
                    all_diagnostics.append(
                        ("Possibly Unbound Variables", "\n".join(unbound_issues)),
                    )

            except Exception as e:
                print(
                    f"Warning: Failed to check unbound variables: {e}",
                    file=sys.stderr,
                )

            # Report all diagnostics if any were found
            if diagnostics_found:
                print("\n❌ Diagnostics found in modified file:", file=sys.stderr)
                print(f"   File: {file_path}\n", file=sys.stderr)

                for diagnostic_type, diagnostic_content in all_diagnostics:
                    print(f"📋 {diagnostic_type}:", file=sys.stderr)
                    print("─" * 50, file=sys.stderr)
                    print(diagnostic_content, file=sys.stderr)
                    print(f"{'─' * 50}\n", file=sys.stderr)

                print(
                    "💡 Recommendation: Fix these issues before continuing.",
                    file=sys.stderr,
                )
                print(
                    "   Claude will be notified of these diagnostics.\n",
                    file=sys.stderr,
                )

                # Exit with code 2 to notify Claude
                sys.exit(2)
            else:
                print(f"✅ No diagnostics found in {file_path}", file=sys.stderr)

            # 6. Check for critical anti-patterns
            print("\n🔍 Checking for critical anti-patterns...", file=sys.stderr)

            # Skip anti-pattern checks on the PostToolUse.py file itself
            if file_path.endswith("PostToolUse.py"):
                print(
                    "✅ Skipping anti-pattern checks on PostToolUse.py itself",
                    file=sys.stderr,
                )
                sys.exit(0)

            antipatterns_found = False
            critical_antipatterns = []

            # Read file content for anti-pattern checking
            try:
                import re

                with open(file_path) as f:
                    content = f.read()
                lines = content.split("\n")
            except Exception as e:
                print(
                    f"Warning: Failed to read file for anti-pattern check: {e}",
                    file=sys.stderr,
                )
                sys.exit(0)

            # Security anti-patterns
            security_patterns = [
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
                # SQL injection
                (
                    r"(SELECT|INSERT|UPDATE|DELETE).*?\+.*?(?:request|params|input)",
                    "CRITICAL: SQL injection vulnerability via string concatenation!",
                ),
                (
                    r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE).*?\{.*?(?:request|params|input)',
                    "CRITICAL: SQL injection vulnerability via f-string!",
                ),
                # Command injection
                (
                    r"os\.system\s*\([^)]*(?:request|params|input)",
                    "CRITICAL: Command injection vulnerability via os.system!",
                ),
                (
                    r"subprocess.*shell\s*=\s*True.*(?:request|params|input)",
                    "CRITICAL: Command injection vulnerability via subprocess!",
                ),
                (
                    r"eval\s*\([^)]*(?:request|params|input)",
                    "CRITICAL: Code injection vulnerability via eval!",
                ),
                # Path traversal
                (
                    r"open\s*\([^)]*(?:request|params|input)",
                    "CRITICAL: Path traversal vulnerability!",
                ),
                # Hardcoded passwords
                (
                    r'(?i)password\s*[:=]\s*["\'][^"\']+["\']',
                    "WARNING: Hardcoded password detected. Use environment variables!",
                ),
            ]

            # Data loss anti-patterns
            data_loss_patterns = [
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
                    "CRITICAL: DELETE without WHERE clause!",
                ),
                (
                    r"rm\s+-rf\s+/",
                    "CRITICAL: Recursive force delete from root!",
                ),
            ]

            # Performance anti-patterns
            perf_patterns = [
                (
                    r"while\s+True\s*:(?!.*break)",
                    "WARNING: Potential infinite loop detected!",
                ),
                (
                    r"time\.sleep\(.*?\).*async\s+def",
                    "WARNING: time.sleep in async code (use asyncio.sleep)!",
                ),
            ]

            # Check all patterns
            for patterns, category in [
                (security_patterns, "Security"),
                (data_loss_patterns, "Data Loss"),
                (perf_patterns, "Performance"),
            ]:
                for pattern, message in patterns:
                    matches = re.finditer(
                        pattern,
                        content,
                        re.IGNORECASE | re.MULTILINE,
                    )
                    for match in matches:
                        line_no = content[: match.start()].count("\n") + 1
                        # Skip if it's in a string literal (pattern definition)
                        line_text = lines[line_no - 1] if line_no <= len(lines) else ""
                        if 'r"' in line_text or "r'" in line_text or '"""' in line_text:
                            continue
                        # Skip if it's in a comment
                        if "#" in line_text and line_text.index(
                            "#",
                        ) < match.start() - content.rfind("\n", 0, match.start()):
                            continue

                        antipatterns_found = True
                        if "CRITICAL" in message:
                            critical_antipatterns.append(
                                {
                                    "category": category,
                                    "message": message,
                                    "line": line_no,
                                    "code": match.group()[:100],  # First 100 chars
                                },
                            )

            # Check for large files
            if len(lines) > 1000:
                antipatterns_found = True
                print(f"⚠️  Large file warning: {len(lines)} lines", file=sys.stderr)

            # Report critical anti-patterns
            if critical_antipatterns:
                print("\n🚨 CRITICAL ANTI-PATTERNS DETECTED:", file=sys.stderr)
                print("─" * 50, file=sys.stderr)

                for issue in critical_antipatterns:
                    print(
                        f"\n{issue['category']} Issue at line {issue['line']}:",
                        file=sys.stderr,
                    )
                    print(f"  {issue['message']}", file=sys.stderr)
                    print(f"  Code: {issue['code']}", file=sys.stderr)

                print("\n─" * 50, file=sys.stderr)
                print(
                    "🛑 BLOCKING: These critical issues must be fixed!",
                    file=sys.stderr,
                )
                print("   Claude will be notified immediately.\n", file=sys.stderr)

                # Exit with code 2 for critical issues
                sys.exit(2)
            elif antipatterns_found:
                print(
                    "⚠️  Some anti-patterns detected but not critical",
                    file=sys.stderr,
                )
            else:
                print("✅ No critical anti-patterns found", file=sys.stderr)

    sys.exit(0)
