# LSP Diagnostics Integration in PostToolUse Hook

The PostToolUse hook now includes comprehensive LSP (Language Server Protocol) diagnostics that automatically check Python files for errors after modifications.

## Overview

When Claude modifies a Python file (via Edit, MultiEdit, or Write tools), the PostToolUse hook will:

1. **Format the code** using various Python formatters
2. **Run comprehensive diagnostics** using multiple tools
3. **Report any issues to Claude** via stderr with exit code 2

## Diagnostic Tools Used

### 1. MyPy - Type Checking
- Detects type errors and incompatible assignments
- Validates function signatures and return types
- Checks for undefined variables

### 2. PyLint - Code Quality
- Identifies undefined variables
- Detects variables used before assignment
- Finds other code quality issues (errors only mode)

### 3. Ruff - Fast Python Linter
- Additional linting checks
- Filters out auto-fixable issues (since we run `ruff --fix` first)

### 4. Custom AST Analysis
- **Asyncio Issues**: Detects when sync functions are passed to async contexts
- **Unbound Variables**: Finds variables that might not be defined in all code paths
- **Syntax Errors**: Catches Python syntax errors

## How It Works

1. After formatting a Python file, the hook runs all diagnostic tools
2. Each tool's output is collected and categorized
3. If any issues are found:
   - A detailed report is printed to stderr
   - The hook exits with code 2
   - Claude is notified and can see the diagnostics

## Example Output

```
🔍 Running diagnostics on /path/to/file.py...

❌ Diagnostics found in modified file:
   File: /path/to/file.py

📋 MyPy Type Errors:
──────────────────────────────────────────────────
file.py:31:12: error: Incompatible return value type (got "int", expected "str")
──────────────────────────────────────────────────

📋 PyLint Errors:
──────────────────────────────────────────────────
file.py:37: [E0602(undefined-variable)] Undefined variable 'some_condition'
──────────────────────────────────────────────────

📋 Async/Await Issues:
──────────────────────────────────────────────────
Line 23: Possible issue - create_task() expects a coroutine, but sync_function() might not be async
──────────────────────────────────────────────────

💡 Recommendation: Fix these issues before continuing.
   Claude will be notified of these diagnostics.
```

## Benefits

1. **Immediate Feedback**: Claude knows about errors right after making changes
2. **Comprehensive Coverage**: Multiple tools catch different types of issues
3. **Async/Await Detection**: Specifically catches the "asyncio.Future, coroutine or awaitable required" errors
4. **Type Safety**: MyPy ensures type correctness
5. **Code Quality**: PyLint and Ruff maintain code standards

## Configuration

The diagnostics run automatically on all Python files. No configuration is needed.

### Disabling Diagnostics

If needed, you can temporarily disable diagnostics by modifying the PostToolUse hook or removing it from your `.claude/settings.json`.

## Common Issues Detected

1. **Type Errors**
   - Incompatible return types
   - Incorrect parameter types
   - Unsupported operations

2. **Undefined Variables**
   - Using variables before definition
   - Typos in variable names
   - Missing imports

3. **Async/Await Issues**
   - Passing sync functions to async contexts
   - Not awaiting coroutines
   - Incorrect asyncio usage

4. **Possibly Unbound Variables**
   - Variables that might not be defined in all code paths
   - Variables defined only in try/except blocks

## Troubleshooting

If diagnostics are not working:

1. Ensure the required tools are installed:
   ```bash
   pip install mypy pylint ruff
   ```

2. Check that the PostToolUse hook is registered in `.claude/settings.json`

3. Verify the hook has execute permissions:
   ```bash
   chmod +x .claude/hooks/hook_handlers/PostToolUse.py
   ```

## Future Enhancements

- Support for other languages (JavaScript/TypeScript via ESLint)
- Integration with language servers (pylsp, pyright)
- Configurable diagnostic levels
- Project-specific diagnostic rules