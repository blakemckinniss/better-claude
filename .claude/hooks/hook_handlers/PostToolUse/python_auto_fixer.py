#!/usr/bin/env python3
"""
Multi-layered Python auto-fixer for PostToolUse hooks.
Uses multiple parsing libraries to automatically fix syntax errors with minimal risk.
"""

import difflib
import os
import subprocess
import sys
from typing import List, Optional, Tuple

# Try to import parsing libraries - gracefully handle missing ones
try:
    import parso
    HAS_PARSO = True
except ImportError:
    HAS_PARSO = False

try:
    import libcst as cst
    HAS_LIBCST = True
except ImportError:
    HAS_LIBCST = False

try:
    import autopep8
    HAS_AUTOPEP8 = True
except ImportError:
    HAS_AUTOPEP8 = False


class PythonAutoFixer:
    """Multi-layered Python syntax and formatting fixer."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.original_content = None
        self.fixed_content = None

    def _log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is on."""
        if self.verbose:
            print(f"[{level}] {message}", file=sys.stderr)

    def _has_syntax_error(self, content: str) -> bool:
        """Check if content has syntax errors."""
        try:
            compile(content, '<string>', 'exec')
            return False
        except SyntaxError:
            return True

    def _apply_targeted_fixes(self, content: str) -> str:
        """Apply targeted fixes for known Claude error patterns."""
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Fix 1: Missing colons on function/class/if/for/while/try/except statements
            # Skip if already has colon or this is already fixed
            colon_keywords = ('def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'try:', 'try ', 'except', 'with ', 'match ', 'case ')
            if (stripped.startswith(colon_keywords) and
                ':' not in stripped and  # No colon anywhere in the line
                not line.strip().endswith(':')):
                # Add colon, but handle comments properly
                if '#' in line:
                    # Insert colon before the comment
                    comment_pos = line.find('#')
                    before_comment = line[:comment_pos].rstrip()
                    comment_part = line[comment_pos:]
                    fixed_line = before_comment + ':  ' + comment_part
                    fixed_lines.append(fixed_line)
                else:
                    # Add colon at end of line
                    if line.endswith('\n'):
                        fixed_lines.append(line.rstrip() + ':\n')
                    else:
                        fixed_lines.append(line.rstrip() + ':')
                self._log(f"Added missing colon to: {stripped}")
                i += 1
                continue

            # Fix 2: Python 2 style print statements
            if 'print ' in line and not line.strip().startswith('#'):
                import re
                # Match print followed by space and content (not print())
                match = re.match(r'^(\s*)print\s+(.+)$', line.rstrip())
                if match:
                    indent, content = match.groups()
                    # Convert to print() function
                    fixed_line = f'{indent}print({content})\n'
                    fixed_lines.append(fixed_line)
                    self._log("Converted Python 2 print to Python 3")
                    i += 1
                    continue

            # Fix 3: Broken print statements
            if 'print("' in line and line.strip().endswith('print("'):
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if '", file=sys.stderr)' in next_line:
                        # Extract content and merge
                        import re
                        match = re.search(r'^(.*?)", file=sys\.stderr\)', next_line)
                        if match:
                            content_part = match.group(1)
                            indent = len(line) - len(line.lstrip())
                            fixed_line = ' ' * indent + f'print("{content_part}", file=sys.stderr)\n'
                            fixed_lines.append(fixed_line)
                            i += 2  # Skip next line
                            self._log("Fixed broken print statement")
                            continue

            # Fix 4: Unclosed string literals at end of line
            if line.count('"') % 2 != 0 or line.count("'") % 2 != 0:
                # Simple fix: add closing quote
                if line.rstrip().endswith('"'):
                    pass  # Already has closing quote
                elif '"' in line and line.count('"') % 2 != 0:
                    fixed_lines.append(line.rstrip() + '"\n')
                    self._log("Added missing double quote")
                    i += 1
                    continue
                elif "'" in line and line.count("'") % 2 != 0:
                    fixed_lines.append(line.rstrip() + "'\n")
                    self._log("Added missing single quote")
                    i += 1
                    continue

            # Fix 5: Missing closing parentheses/brackets (simple cases)
            if (line.count('(') > line.count(')') and
                not line.strip().endswith((',', '\\', '('))):
                # Add missing closing parenthesis
                fixed_lines.append(line.rstrip() + ')\n')
                self._log("Added missing closing parenthesis")
                i += 1
                continue

            fixed_lines.append(line)
            i += 1

        result = ''.join(fixed_lines)

        # Always check for missing pass statements for empty blocks
        # This is critical for fixing empty function/if/for/try blocks
        result = self._add_missing_pass_statements(result)

        return result

    def _add_missing_pass_statements(self, content: str) -> str:
        """Add pass statements to empty code blocks."""
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check if this line ends with a colon (start of a block)
            if stripped.endswith(':'):
                indent_level = len(line) - len(line.lstrip())
                # Look ahead to see if there's a body
                j = i + 1
                has_body = False

                while j < len(lines):
                    next_line = lines[j]
                    next_stripped = next_line.strip()

                    # Skip empty lines and comments
                    if not next_stripped or next_stripped.startswith('#'):
                        j += 1
                        continue

                    next_indent = len(next_line) - len(next_line.lstrip())

                    # If next line is indented more, it's part of the block
                    if next_indent > indent_level:
                        has_body = True
                        break
                    else:
                        # Same or less indent means end of block
                        break

                fixed_lines.append(line)

                # If no body found, add pass statement
                if not has_body:
                    pass_indent = ' ' * (indent_level + 4)  # Standard 4-space indent
                    fixed_lines.append(pass_indent + 'pass\n')
                    self._log(f"Added pass statement for empty block")
            else:
                fixed_lines.append(line)

            i += 1

        return ''.join(fixed_lines)

    def _fix_with_parso(self, content: str) -> Optional[str]:
        """Use parso for error recovery and fixing."""
        if not HAS_PARSO:
            return None

        try:
            self._log("Attempting parso error recovery")
            # Parse with error recovery
            module = parso.parse(content, error_recovery=True)

            # Check if parso can parse it without syntax errors
            # If parso can parse it, the content might be valid
            if module:
                # Try to get the code back from parso
                try:
                    # Use parso's normalization
                    normalized = module.get_code()
                    if not self._has_syntax_error(normalized):
                        self._log("✓ Parso normalized code successfully")
                        return normalized
                except AttributeError:
                    # Fallback: if parso parsed successfully, content might be OK
                    pass

            # For error nodes, we'll rely on our targeted fixes
            # instead of trying to parse parso's error structure
            return None

        except Exception as e:
            self._log(f"Parso error: {e}", "WARNING")

        return None

    def _fix_with_libcst(self, content: str) -> Optional[str]:
        """Use libcst for CST-based fixes."""
        if not HAS_LIBCST or self._has_syntax_error(content):
            return None

        try:
            self._log("Attempting libcst formatting")
            tree = cst.parse_module(content)
            # LibCST preserves formatting but ensures valid syntax
            fixed = tree.code
            self._log("✓ LibCST formatting applied")
            return fixed
        except Exception as e:
            self._log(f"LibCST error: {e}", "WARNING")

        return None

    def _fix_with_autopep8(self, content: str) -> Optional[str]:
        """Use autopep8 for PEP8 fixes."""
        if not HAS_AUTOPEP8 or self._has_syntax_error(content):
            return None

        try:
            self._log("Applying autopep8 fixes")
            fixed = autopep8.fix_code(content, options={'aggressive': 1})
            self._log("✓ autopep8 formatting applied")
            return fixed
        except Exception as e:
            self._log(f"autopep8 error: {e}", "WARNING")

        return None

    def _fix_with_black(self, filepath: str) -> bool:
        """Run Black formatter on file."""
        try:
            result = subprocess.run(
                ["black", "--quiet", filepath],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._log("✓ Black formatting applied")
                return True
        except FileNotFoundError:
            self._log("Black not installed", "WARNING")
        except Exception as e:
            self._log(f"Black error: {e}", "WARNING")

        return False

    def _fix_with_ruff(self, filepath: str) -> bool:
        """Run Ruff linter with auto-fix on file."""
        try:
            result = subprocess.run(
                ["ruff", "check", "--fix", "--quiet", filepath],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._log("✓ Ruff fixes applied")
                return True
        except FileNotFoundError:
            self._log("Ruff not installed", "WARNING")
        except Exception as e:
            self._log(f"Ruff error: {e}", "WARNING")

        return False

    def fix_file(self, filepath: str) -> Tuple[bool, List[str]]:
        """
        Apply multi-layered fixes to a Python file.
        Returns (success, messages).
        """
        messages = []

        if not os.path.exists(filepath):
            return False, ["File not found"]

        try:
            # Read original content
            with open(filepath, 'r', encoding='utf-8') as f:
                self.original_content = f.read()

            # Check if file has syntax errors
            if not self._has_syntax_error(self.original_content):
                messages.append("No syntax errors detected")
                # Still run formatters
                self._fix_with_ruff(filepath)
                self._fix_with_black(filepath)
                return True, messages

            # Layer 1: Apply targeted fixes for known patterns
            content = self._apply_targeted_fixes(self.original_content)

            # Layer 2: Try parso for error recovery (only if we still have errors)
            if self._has_syntax_error(content) and HAS_PARSO:
                parso_fixed = self._fix_with_parso(content)
                if parso_fixed and not self._has_syntax_error(parso_fixed):
                    content = parso_fixed
                    messages.append("✓ Fixed with parso error recovery")

            # Check if we fixed the syntax errors
            if self._has_syntax_error(content):
                messages.append("⚠️ Could not fix all syntax errors")
                # Still write back our best attempt
            else:
                messages.append("✓ Syntax errors fixed")

            # Write back the content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Layer 3: Run external tools (only if syntax is valid)
            if not self._has_syntax_error(content):
                # Apply formatters in sequence
                self._fix_with_ruff(filepath)
                self._fix_with_black(filepath)

                # Re-read for final formatting passes
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Layer 4: LibCST for final touches
                if HAS_LIBCST:
                    libcst_fixed = self._fix_with_libcst(content)
                    if libcst_fixed:
                        content = libcst_fixed
                        messages.append("✓ Applied libcst formatting")

                # Layer 5: autopep8 for PEP8 compliance
                if HAS_AUTOPEP8:
                    autopep8_fixed = self._fix_with_autopep8(content)
                    if autopep8_fixed:
                        content = autopep8_fixed
                        messages.append("✓ Applied autopep8 formatting")

                # Write final content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Show diff if verbose
            if self.verbose and content != self.original_content:
                diff = difflib.unified_diff(
                    self.original_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile='original',
                    tofile='fixed'
                )
                self._log("\nChanges made:")
                for line in diff:
                    print(line, end='', file=sys.stderr)

            return True, messages

        except Exception as e:
            return False, [f"Error: {str(e)}"]


def should_process_file(tool_name: str, tool_input: dict, file_path: str) -> bool:
    """Determine if we should process this file."""
    # Only process Python files
    if not file_path.endswith('.py'):
        return False

    # Only process after write/edit operations
    if tool_name not in ['write_to_file', 'apply_diff', 'insert_content', 'Write', 'Edit', 'MultiEdit']:
        return False

    # Skip test files and this file itself
    if 'test' in file_path.lower() or 'python_auto_fixer.py' in file_path:
        return False

    return True


def run_auto_fixer(tool_name: str, tool_input: dict, cwd: str) -> None:
    """Run the auto-fixer on appropriate files."""
    # Extract file path
    file_path = None
    if 'path' in tool_input:
        file_path = tool_input['path']
    elif 'file_path' in tool_input:
        file_path = tool_input['file_path']
    elif 'args' in tool_input and isinstance(tool_input['args'], list):
        # Handle apply_diff format - can have multiple files
        for file_info in tool_input['args']:
            if 'path' in file_info:
                fp = file_info['path']
                if not os.path.isabs(fp):
                    fp = os.path.join(cwd, fp)
                if should_process_file(tool_name, tool_input, fp):
                    fixer = PythonAutoFixer(verbose=False)
                    success, messages = fixer.fix_file(fp)
                    if success and any('✓' in msg for msg in messages):
                        print(f"\n🔧 Auto-fixed Python issues in {os.path.basename(fp)}:")
                        for msg in messages:
                            if '✓' in msg or '⚠️' in msg:
                                print(f"   {msg}")
        return

    if not file_path:
        return

    # Make path absolute
    if not os.path.isabs(file_path):
        file_path = os.path.join(cwd, file_path)

    if not should_process_file(tool_name, tool_input, file_path):
        return

    # Wait a moment for file to be written
    import time
    time.sleep(0.1)

    # Check if file exists
    if not os.path.exists(file_path):
        return

    # Run the fixer
    fixer = PythonAutoFixer(verbose=False)
    success, messages = fixer.fix_file(file_path)

    if success and any('✓' in msg for msg in messages):
        print(f"\n🔧 Auto-fixed Python issues in {os.path.basename(file_path)}:")
        for msg in messages:
            if '✓' in msg or '⚠️' in msg:
                print(f"   {msg}")


if __name__ == '__main__':
    # Test mode
    if len(sys.argv) > 1:
        fixer = PythonAutoFixer(verbose=True)
        success, messages = fixer.fix_file(sys.argv[1])
        for msg in messages:
            print(msg)
        sys.exit(0 if success else 1)