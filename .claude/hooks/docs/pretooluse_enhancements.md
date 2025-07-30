# PreToolUse Hook Enhancements

The enhanced PreToolUse hook provides intelligent warnings and suggestions while maintaining rapid development flow. It uses non-blocking warnings (stderr with exit code 0) for suggestions and only blocks (exit code 2) for critical issues.

## Key Features

### 1. Git-Aware Warnings
- Warns when editing/deleting files with uncommitted changes
- Helps prevent accidental loss of work
- Non-blocking to maintain development speed

```bash
⚠️ File 'src/main.py' has uncommitted changes - consider committing first
```

### 2. Modern Tool Suggestions
Suggests faster, modern alternatives to traditional Unix tools:
- `grep` → `rg` (ripgrep) - 10-100x faster
- `find` → `fd` - simpler and faster
- `cat` → `bat` - syntax highlighting

```bash
💡 Consider using 'rg' (ripgrep) instead - it's 10-100x faster
```

### 3. Intelligent Pattern Detection
Detects and warns about suspicious file patterns:
- Recursive paths (`/path/to/path/to/file`)
- Temporary files (`*.tmp`, `*.swp`)
- Mixed path separators
- Test files outside `tests/` directory

```bash
⚠️ Recursive path pattern detected - this might be unintentional
💡 Test files are typically placed in tests/
```

### 4. Dependency Impact Analysis
Warns when modifying files that are imported by many others:
- Analyzes Python/JS/TS imports
- Shows impact count for better decision making
- Helps prevent breaking changes

```bash
⚠️ File 'utils.py' is imported by 12 other files - changes may have wide impact
```

### 5. Enhanced Operation Logging
All operations are logged with structured data:
- Timestamp and session ID
- Operation type and target
- Git status of affected files
- Warnings issued

Logs are stored in `~/.claude/hooks/operation_logs/` as daily JSONL files.

### 6. Non-Blocking vs Blocking Behavior

**Non-blocking warnings (suggestions):**
- Test files outside `tests/` directory
- Documentation outside `docs/` directory
- Using older tools when modern alternatives exist
- Files with uncommitted changes

**Blocking errors (protection):**
- Critical Claude configuration files
- Protected file types (`.env`, `package-lock.json`)
- Dangerous commands (`rm -rf /`)
- Bad naming patterns (`enhanced`, `v2`, `backup`)

## Configuration

### Circuit Breaker Settings
Configure path restrictions in the PreToolUse.py file:

```python
# Paths that cannot be modified (read-only)
READ_ONLY_PATHS = [".claude/config"]

# Paths that cannot be accessed at all
NO_ACCESS_PATHS = ["secrets/", ".env"]

# Paths where new files cannot be created
WRITE_RESTRICTED_PATHS = [".claude/hooks/hook_handlers"]

# Paths that cannot be deleted
DELETE_PROTECTED_PATHS = [".claude/settings.json"]
```

### Disabling Features
To disable the circuit breaker entirely:
```python
CIRCUIT_BREAKER_ENABLED = False
```

## Usage Examples

### Example 1: Editing with Git Warning
```bash
$ claude edit src/main.py
⚠️ File 'src/main.py' has uncommitted changes - consider committing first
[Edit proceeds normally]
```

### Example 2: Modern Tool Suggestion
```bash
$ claude run "grep -r 'TODO' ."
💡 Consider using 'rg' (ripgrep) instead - it's 10-100x faster
[Command executes normally]
```

### Example 3: Dependency Warning
```bash
$ claude delete core/utils.py
⚠️ File 'core/utils.py' is imported by 8 other files
⚠️ Deleting 'core/utils.py' with uncommitted changes - consider committing first
[Deletion proceeds with warnings]
```

### Example 4: Blocked Operation
```bash
$ claude write .claude/settings.json
Blocked: Cannot modify .claude/settings.json - critical Claude file is protected
[Operation blocked]
```

## Benefits

1. **Safer Development**: Prevents accidental data loss and breaking changes
2. **Educational**: Teaches modern tool usage through suggestions
3. **Non-Intrusive**: Warnings don't block workflow for non-critical issues
4. **Audit Trail**: Complete operation history for debugging
5. **Smart Defaults**: Protects critical files while allowing flexibility

## Testing

Run the test suite to see all features in action:

```bash
python .claude/hooks/tests/test_pretooluse_enhancements.py
```

This will demonstrate:
- Git-aware warnings
- Tool suggestions
- Pattern detection
- Dependency analysis
- Logging functionality
- Blocking vs non-blocking behavior