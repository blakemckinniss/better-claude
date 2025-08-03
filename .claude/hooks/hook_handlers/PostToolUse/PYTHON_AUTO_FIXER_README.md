# Python Auto-Fixer for PostToolUse Hook

## Overview

The Python Auto-Fixer is a multi-layered automatic error correction system that runs as part of the PostToolUse hook. It specifically targets and fixes syntax errors that commonly occur when Claude inserts or modifies Python code.

## Key Features

### 1. Syntax Error Recovery
- **Targeted Fixes**: Specifically handles known Claude error patterns (e.g., broken print statements)
- **Parso Integration**: Uses Jedi's parser for advanced error recovery
- **Pre-formatter Execution**: Runs BEFORE other formatters to ensure valid syntax

### 2. Multi-Layer Approach
The fixer applies corrections in this order:
1. **Targeted Pattern Fixes**: Known Claude-specific errors
2. **Parso Error Recovery**: AST-based error correction
3. **Ruff Linting**: Auto-fixes common issues
4. **Black Formatting**: Code style standardization
5. **LibCST Processing**: Concrete syntax tree preservation
6. **autopep8**: Final PEP8 compliance

### 3. Safe Operation
- Only processes Python files (`.py`)
- Skips test files and itself
- Gracefully handles missing dependencies
- Preserves original code when fixes fail

## Integration Details

### Location
```
.claude/hooks/hook_handlers/PostToolUse/python_auto_fixer.py
```

### Hook Integration
The auto-fixer is integrated into the PostToolUse handler at:
```python
# In PostToolUse/__init__.py
from PostToolUse.python_auto_fixer import run_auto_fixer

# Runs BEFORE other formatters
if ext == ".py":
    run_auto_fixer(tool_name, tool_input, cwd)
```

### Removed Duplicates
To avoid duplicate functionality, the following were removed from `formatters.py`:
- Black formatter (lines 123-124)
- Ruff check with --fix (lines 125-126)
- Ruff format (lines 127-128)

These are now handled by `python_auto_fixer.py` with better error recovery.

## Common Fixed Patterns

### 1. Broken Print Statements
```python
# Claude might produce:
print("
📝 Note: Message", file=sys.stderr)

# Auto-fixer corrects to:
print("📝 Note: Message", file=sys.stderr)
```

### 2. Unclosed String Literals
```python
# Claude might produce:
message = "Hello world

# Auto-fixer corrects to:
message = "Hello world"
```

### 3. Missing Quotes in Function Calls
```python
# Claude might produce:
func("arg1, "arg2")

# Auto-fixer corrects to:
func("arg1", "arg2")
```

## Dependencies

### Required (Core Functionality)
- Python 3.8+
- Standard library modules

### Optional (Enhanced Features)
- `parso`: For AST-based error recovery
- `libcst`: For concrete syntax tree processing
- `autopep8`: For PEP8 compliance
- `black`: For code formatting
- `ruff`: For linting and fixes

Install optional dependencies:
```bash
pip install parso libcst autopep8 black ruff
```

## Configuration

The auto-fixer respects the existing PostToolUse configuration in:
```
.claude/hooks/hook_handlers/PostToolUse/config.yaml
```

## Debugging

To debug the auto-fixer:
1. Run manually: `python python_auto_fixer.py <file.py>`
2. Check verbose output for detailed processing steps
3. Look for the 🔧 emoji in Claude's output

## Performance Impact

- Minimal overhead for files without syntax errors
- Syntax error fixing typically adds <100ms
- Full formatting chain adds 200-500ms depending on file size

## Future Improvements

1. **Pattern Library**: Expand known error patterns
2. **Machine Learning**: Learn from fixed errors
3. **Language Support**: Extend to other languages
4. **IDE Integration**: Direct VS Code integration
5. **Metrics**: Track most common errors

## Troubleshooting

### Auto-fixer not running
- Check if PostToolUse hooks are enabled
- Verify file has `.py` extension
- Ensure not a test file

### Fixes not applied
- Some syntax errors may be too complex
- Check for nested quote issues
- Verify dependencies are installed

### Performance issues
- Large files may take longer
- Consider disabling some layers
- Check for infinite loop patterns

## Contributing

To add new error patterns:
1. Add pattern detection in `_apply_targeted_fixes()`
2. Test with real-world examples
3. Ensure no false positives
4. Document the pattern

## Related Files

- `.claude/hooks/hook_handlers/PostToolUse/__init__.py` - Main integration
- `.claude/hooks/hook_handlers/PostToolUse/formatters.py` - Other formatters
- `.claude/hooks/hook_handlers/PostToolUse/config.yaml` - Configuration