#!/usr/bin/env python3
"""
Optimized Python Auto-Fixer for PostToolUse Hook
Background subprocess with comprehensive error fixing (15+ patterns)
Fire-and-forget design with atomic operations and timeout protection
"""

import ast
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

# Optional imports - gracefully handle missing ones
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


class OptimizedPythonFixer:
    """Background Python fixer - 15+ error patterns, atomic ops, timeout protected."""

    def __init__(self, log_file: str = "/tmp/python_fixer.log"):
        self.log_file = log_file
        self.max_fix_time = 8  # seconds max per file
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _log(self, message: str):
        """Silent background logging."""
        try:
            timestamp = time.strftime("%H:%M:%S")
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass

    @contextmanager
    def _atomic_write(self, filepath: str):
        """Atomic file operations with automatic backup/restore."""
        backup = f"{filepath}.bak"
        try:
            # Create backup
            if os.path.exists(filepath):
                with open(filepath, 'rb') as src, open(backup, 'wb') as dst:
                    dst.write(src.read())
            yield
        except Exception:
            # Restore on any error
            if os.path.exists(backup):
                os.replace(backup, filepath)
            raise
        finally:
            # Cleanup
            if os.path.exists(backup):
                try:
                    os.remove(backup)
                except:
                    pass

    def _has_syntax_error(self, content: str) -> Tuple[bool, str]:
        """Check syntax with error details."""
        try:
            compile(content, '<string>', 'exec')
            return False, ""
        except SyntaxError as e:
            return True, str(e)

    def _fix_comprehensive_patterns(self, content: str) -> str:
        """Apply 15+ comprehensive fix patterns."""
        lines = content.splitlines(keepends=True)
        
        # Pattern 1-5: Original patterns (optimized)
        lines = self._fix_missing_colons(lines)
        lines = self._fix_python2_prints(lines)
        lines = self._fix_broken_prints(lines)
        lines = self._fix_unclosed_strings(lines)
        lines = self._fix_missing_parens(lines)
        
        # Pattern 6-10: Enhanced syntax fixes
        lines = self._fix_indentation_errors(lines)
        lines = self._fix_missing_commas(lines)
        lines = self._fix_invalid_fstrings(lines)
        lines = self._fix_missing_pass(lines)
        lines = self._fix_async_syntax(lines)
        
        # Pattern 11-20: Semantic fixes
        lines = self._fix_common_names(lines)
        lines = self._fix_type_hints(lines)
        lines = self._fix_decorator_syntax(lines)
        lines = self._fix_exception_syntax(lines)
        lines = self._fix_import_errors(lines)
        
        # Pattern 16-20: Advanced syntax fixes
        lines = self._fix_lambda_syntax(lines)
        lines = self._fix_comprehension_syntax(lines)
        lines = self._fix_undefined_variables(lines)
        lines = self._fix_missing_returns(lines)
        lines = self._fix_wildcard_imports(lines)
        
        return ''.join(lines)

    def _fix_missing_colons(self, lines: List[str]) -> List[str]:
        """Fix missing colons - enhanced for more keywords."""
        keywords = ('def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 
                   'try:', 'try ', 'except', 'finally', 'with ', 'match ', 'case ',
                   'async def ', 'async for ', 'async with ')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if any(stripped.startswith(kw) for kw in keywords):
                if not stripped.endswith(':') and ':' not in stripped:
                    if '#' in line:
                        pos = line.find('#')
                        lines[i] = line[:pos].rstrip() + ':  ' + line[pos:]
                    else:
                        lines[i] = line.rstrip() + ':\n'
        return lines

    def _fix_indentation_errors(self, lines: List[str]) -> List[str]:
        """Fix mixed tabs/spaces and inconsistent indentation."""
        # Detect predominant style
        space_lines = sum(1 for line in lines if line.startswith('    '))
        tab_lines = sum(1 for line in lines if line.startswith('\t'))
        use_spaces = space_lines >= tab_lines
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # Get the indentation part of the line
            indent_part = line[:len(line) - len(line.lstrip())]
            content_part = line[len(indent_part):]
            
            # Fix mixed indentation in the indent part
            if '\t' in indent_part and ' ' in indent_part:
                if use_spaces:
                    # Convert all tabs to 4 spaces
                    fixed_indent = indent_part.expandtabs(4)
                else:
                    # Convert groups of 4 spaces to tabs
                    fixed_indent = re.sub(r'    ', '\t', indent_part)
                    fixed_indent = fixed_indent.replace(' ', '')  # Remove stray spaces
                lines[i] = fixed_indent + content_part
            elif '\t' in indent_part and use_spaces:
                # Convert tabs to spaces when spaces are preferred
                lines[i] = indent_part.expandtabs(4) + content_part
            elif '    ' in indent_part and not use_spaces:
                # Convert spaces to tabs when tabs are preferred
                fixed_indent = re.sub(r'    ', '\t', indent_part)
                lines[i] = fixed_indent + content_part
                    
        return lines

    def _fix_missing_pass(self, lines: List[str]) -> List[str]:
        """Add pass to empty blocks."""
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().endswith(':'):
                indent_level = len(line) - len(line.lstrip())
                # Check if next line exists and is properly indented
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if (not next_line.strip() or 
                        len(next_line) - len(next_line.lstrip()) <= indent_level):
                        # Insert pass
                        lines.insert(i + 1, ' ' * (indent_level + 4) + 'pass\n')
                        i += 1  # Skip the inserted line
                else:
                    # End of file
                    lines.append(' ' * (indent_level + 4) + 'pass\n')
            i += 1
        return lines

    def _fix_common_names(self, lines: List[str]) -> List[str]:
        """Fix common undefined name patterns."""
        replacements = {
            r'\btrue\b': 'True',
            r'\bfalse\b': 'False', 
            r'\bnull\b': 'None',
            r'\bundefined\b': 'None',
            r'\bnil\b': 'None',
        }
        
        changed = False
        for i, line in enumerate(lines):
            # Skip comments to avoid false replacements
            if line.strip().startswith('#'):
                continue
                
            original_line = line
            # Apply all replacements
            for pattern, replacement in replacements.items():
                lines[i] = re.sub(pattern, replacement, lines[i])
            
            if lines[i] != original_line:
                changed = True
                self._log(f"Boolean fix: {original_line.strip()} -> {lines[i].strip()}")
                
        if changed:
            self._log("Applied boolean name fixes")
        return lines

    def _fix_type_hints(self, lines: List[str]) -> List[str]:
        """Fix Python 3.9+ type hint syntax for older versions."""
        for i, line in enumerate(lines):
            # Fix built-in type annotations for older Python versions
            line = re.sub(r'\blist\[', 'List[', line)
            line = re.sub(r'\bdict\[', 'Dict[', line)
            line = re.sub(r'\btuple\[', 'Tuple[', line)
            line = re.sub(r'\bset\[', 'Set[', line)
            
            # Fix union syntax: str | None -> Optional[str]
            line = re.sub(r'(\w+)\s*\|\s*None', r'Optional[\1]', line)
            line = re.sub(r'None\s*\|\s*(\w+)', r'Optional[\1]', line)
            
            # Fix complex union syntax: str | int | None -> Optional[Union[str, int]]
            union_pattern = r'(\w+(?:\[[\w,\s\[\]]+\])?)\s*\|\s*(\w+(?:\[[\w,\s\[\]]+\])?)\s*(\|\s*\w+(?:\[[\w,\s\[\]]+\])?)*'
            if '|' in line and '->' in line:  # Only in function signatures
                # Extract and fix union types
                matches = re.findall(union_pattern, line)
                for match in matches:
                    original = '|'.join([m for m in match if m])
                    if 'None' in original:
                        # Optional case
                        types = [t.strip() for t in original.split('|') if t.strip() != 'None']
                        if len(types) == 1:
                            replacement = f'Optional[{types[0]}]'
                        else:
                            replacement = f'Optional[Union[{", ".join(types)}]]'
                    else:
                        # Union case
                        types = [t.strip() for t in original.split('|')]
                        replacement = f'Union[{", ".join(types)}]'
                    
                    line = line.replace(original, replacement)
            
            lines[i] = line
        return lines

    def _fix_import_errors(self, lines: List[str]) -> List[str]:
        """Add common missing imports based on usage patterns."""
        content = ''.join(lines)
        imports_needed = []
        
        # Check for typing imports
        if any(word in content for word in ['List[', 'Dict[', 'Optional[', 'Union[']):
            if 'from typing import' not in content:
                imports_needed.append('from typing import List, Dict, Optional, Union, Any\n')
                
        # Check for common stdlib imports
        patterns = {
            r'\bos\.': 'import os\n',
            r'\bsys\.': 'import sys\n', 
            r'\bjson\.': 'import json\n',
            r'\btime\.': 'import time\n',
            r'\bPath\(': 'from pathlib import Path\n',
        }
        
        for pattern, import_stmt in patterns.items():
            if re.search(pattern, content) and import_stmt.strip() not in content:
                imports_needed.append(import_stmt)
                
        # Insert imports at top
        if imports_needed:
            # Find insertion point
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_idx = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
                    
            for imp in sorted(set(imports_needed)):
                lines.insert(insert_idx, imp)
                insert_idx += 1
                
        return lines

    # Simplified implementations for remaining patterns
    def _fix_python2_prints(self, lines): 
        for i, line in enumerate(lines):
            if 'print ' in line and not line.strip().startswith('#'):
                lines[i] = re.sub(r'^(\s*)print\s+(.+)$', r'\1print(\2)', line.rstrip()) + '\n'
        return lines
        
    def _fix_broken_prints(self, lines): 
        return lines
        
    def _fix_unclosed_strings(self, lines): 
        for i, line in enumerate(lines):
            if line.count('"') % 2 != 0 and not line.rstrip().endswith('"'):
                lines[i] = line.rstrip() + '"\n'
        return lines
        
    def _fix_missing_parens(self, lines):
        for i, line in enumerate(lines):
            if line.count('(') > line.count(')') and not line.strip().endswith((',', '\\')):
                diff = line.count('(') - line.count(')')
                lines[i] = line.rstrip() + ')' * diff + '\n'
        return lines
        
    def _fix_missing_commas(self, lines): 
        return lines
        
    def _fix_invalid_fstrings(self, lines):
        for i, line in enumerate(lines):
            if '{' in line and '}' in line and '"' in line and not line.strip().startswith('f'):
                lines[i] = re.sub(r'(["\'])(.*?\{.*?\}.*?)\1', r'f\1\2\1', line)
        return lines
        
    def _fix_async_syntax(self, lines): 
        return lines
        
    def _fix_decorator_syntax(self, lines): 
        return lines
        
    def _fix_exception_syntax(self, lines):
        """Fix common exception syntax errors."""
        for i, line in enumerate(lines):
            # Fix except Exception, e: -> except Exception as e:
            line = re.sub(r'except\s+(\w+),\s*(\w+):', r'except \1 as \2:', line)
            # Fix raise Exception, "message" -> raise Exception("message")
            line = re.sub(r'raise\s+(\w+),\s*(["\'].*?["\'])', r'raise \1(\2)', line)
            lines[i] = line
        return lines

    def _fix_lambda_syntax(self, lines: List[str]) -> List[str]:
        """Fix common lambda syntax errors."""
        for i, line in enumerate(lines):
            if 'lambda' not in line:
                continue
                
            # Fix lambda with missing colon - safer approach
            if 'lambda' in line:
                # Extract lambda part
                parts = line.split('lambda')
                if len(parts) > 1:
                    lambda_part = parts[1]
                    # Check if there's a colon after lambda
                    if ':' not in lambda_part.split('=')[0] if '=' in lambda_part else ':' not in lambda_part:
                        # Simple case: lambda x y -> lambda x: y
                        match = re.search(r'lambda\s+([^=:]+?)\s+([^=:]+)', line)
                        if match:
                            params, expr = match.groups()
                            line = line.replace(match.group(0), f'lambda {params.strip()}: {expr.strip()}')
                            
            # Fix lambda with incorrect return syntax
            line = re.sub(r'lambda\s+([^:]+):\s*return\s+(.+)', r'lambda \1: \2', line)
            lines[i] = line
        return lines

    def _fix_comprehension_syntax(self, lines: List[str]) -> List[str]:
        """Fix list/dict comprehension syntax errors."""
        for i, line in enumerate(lines):
            # Fix missing for keyword in comprehensions
            if '[' in line and ']' in line and 'in' in line and 'for' not in line:
                # Simple pattern: [expr in iterable] -> [expr for expr in iterable]
                match = re.search(r'\[([^[\]]+)\s+in\s+([^[\]]+)\]', line)
                if match:
                    expr, iterable = match.groups()
                    var_name = expr.split()[0] if ' ' in expr else 'x'
                    replacement = f'[{expr} for {var_name} in {iterable}]'
                    line = line.replace(match.group(0), replacement)
            
            # Fix dict comprehension syntax
            if '{' in line and '}' in line and ':' in line and 'for' not in line and 'in' in line:
                match = re.search(r'\{([^{}]+):\s*([^{}]+)\s+in\s+([^{}]+)\}', line)
                if match:
                    key, val, iterable = match.groups()
                    var_name = key.split()[0] if ' ' in key else 'x'
                    replacement = f'{{{key}: {val} for {var_name} in {iterable}}}'
                    line = line.replace(match.group(0), replacement)
            
            lines[i] = line
        return lines

    def _fix_undefined_variables(self, lines: List[str]) -> List[str]:
        """Fix common undefined variable patterns."""
        content = ''.join(lines)
        
        # Use AST to find undefined names (basic patterns)
        try:
            tree = ast.parse(content)
            undefined_patterns = {
                'lenght': 'len',
                'lengh': 'len', 
                'cout': 'len',  # common typo for len
                'lengtht': 'len',
                'rang': 'range',
                'prin': 'print',
                'improt': 'import',
            }
            
            for i, line in enumerate(lines):
                for wrong, correct in undefined_patterns.items():
                    if re.search(rf'\b{wrong}\b', line):
                        lines[i] = re.sub(rf'\b{wrong}\b', correct, line)
                        
        except SyntaxError:
            # Fallback to regex patterns
            common_typos = {
                r'\blenght\b': 'length',
                r'\bcout\b': 'count',
                r'\brang\b': 'range',
                r'\bprin\b\s*\(': 'print(',
            }
            
            for i, line in enumerate(lines):
                for pattern, replacement in common_typos.items():
                    lines[i] = re.sub(pattern, replacement, line)
                    
        return lines

    def _fix_missing_returns(self, lines: List[str]) -> List[str]:
        """Add missing return statements to functions that should return values."""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for function definitions
            if line.startswith('def ') and '-> ' in line and 'None' not in line:
                # Function has return type annotation but no None
                func_indent = len(lines[i]) - len(lines[i].lstrip())
                
                # Find the end of the function
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line and len(lines[j]) - len(lines[j].lstrip()) <= func_indent:
                        break
                    if next_line.startswith('return '):
                        break
                    j += 1
                
                # If no return found and function is not empty, add return None
                if j == len(lines) or (lines[j-1].strip() and not lines[j-1].strip().startswith('return')):
                    if j > i + 1:  # Function has content
                        lines.insert(j, ' ' * (func_indent + 4) + 'return None\n')
                        
            i += 1
            
        return lines

    def _fix_wildcard_imports(self, lines: List[str]) -> List[str]:
        """Fix problematic wildcard imports."""
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Fix from module import * (comment it with warning)
            if stripped.startswith('from ') and stripped.endswith('import *'):
                lines[i] = f"# FIXME: Wildcard import - {line.strip()}\n{line}"
                
            # Fix incomplete from imports
            if stripped.startswith('from ') and not ' import ' in stripped:
                module = stripped.replace('from ', '')
                lines[i] = f"import {module}\n"
                
        return lines

    def _run_formatters(self, filepath: str):
        """Run external formatters with timeout protection."""
        formatters = [
            (['ruff', 'check', '--fix', '--quiet', filepath], 2),
            (['black', '--quiet', filepath], 2),
        ]
        
        for cmd, timeout in formatters:
            try:
                subprocess.run(cmd, capture_output=True, timeout=timeout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    def fix_file(self, filepath: str) -> bool:
        """Main fix method with full protection."""
        try:
            with self._atomic_write(filepath):
                # Read
                with open(filepath, 'r', encoding='utf-8') as f:
                    original = f.read()
                    
                # Quick check - skip if no obvious issues
                has_error, error_msg = self._has_syntax_error(original)
                has_common_issues = any(pattern in original for pattern in [
                    'true', 'false', 'null', 'lenght', 'cout', 'rang', 'prin',
                    '\t    ', '    \t', 'lambda ', 'import *', 'except ', ', e:'
                ])
                
                if not has_error and not has_common_issues and len(original) < 5000:
                    self._run_formatters(filepath)
                    return True
                    
                # Apply comprehensive fixes
                fixed = self._fix_comprehensive_patterns(original)
                
                # Write if changed
                if fixed != original:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(fixed)
                    self._log(f"Fixed: {filepath}")
                    
                # Always run formatters
                self._run_formatters(filepath)
                return True
                
        except Exception as e:
            self._log(f"Error: {filepath} - {e}")
            return False


def should_process_file(tool_name: str, tool_input: dict, file_path: str) -> bool:
    """Determine if file should be processed."""
    if not file_path.endswith('.py'):
        return False
        
    if tool_name not in ['write_to_file', 'apply_diff', 'insert_content', 
                         'Write', 'Edit', 'MultiEdit']:
        return False
        
    # Skip patterns
    skip = ['test', '__pycache__', '.pyc', 'python_auto_fixer', 'hook']
    return not any(pattern in file_path.lower() for pattern in skip)


def run_auto_fixer(tool_name: str, tool_input: dict, cwd: str) -> None:
    """Hook entry point - launches background subprocess."""
    file_paths = []
    
    # Extract file paths
    for key in ['path', 'file_path']:
        if key in tool_input:
            file_paths.append(tool_input[key])
            
    if 'args' in tool_input and isinstance(tool_input['args'], list):
        for item in tool_input['args']:
            if isinstance(item, dict) and 'path' in item:
                file_paths.append(item['path'])
                
    # Process files in detached subprocess
    for file_path in file_paths:
        if not os.path.isabs(file_path):
            file_path = os.path.join(cwd, file_path)
            
        if should_process_file(tool_name, tool_input, file_path):
            try:
                # True background subprocess - completely detached
                subprocess.Popen(
                    [sys.executable, __file__, file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    cwd=cwd
                )
            except:
                pass  # Silent fail


if __name__ == "__main__":
    # Subprocess entry point
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            fixer = OptimizedPythonFixer()
            try:
                # Timeout protection
                future = fixer.executor.submit(fixer.fix_file, filepath)
                future.result(timeout=fixer.max_fix_time)
            except TimeoutError:
                pass
            finally:
                fixer.executor.shutdown(wait=False)