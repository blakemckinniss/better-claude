# Destructive Edit Protection

## Overview

After a critical incident where significant functionality was accidentally removed from UserPromptSubmit.py, we've implemented comprehensive safeguards to prevent destructive edits to files.

## Protection Mechanisms

### 1. File Size Reduction Detection

**What it does**: Blocks edits that would remove more than 50% of a file's content.

**Triggers**:
- Write operations that reduce file size by >50%
- Write operations that reduce line count by >50%
- Edit operations that replace >500 characters with <50% of the original

**Example blocked operation**:
```python
# Original file: 400 lines
# New content: 2 lines
# Result: BLOCKED - would remove 99% of content
```

### 2. Critical File Warnings

**What it does**: Warns when modifying files critical to the hooks system.

**Protected files**:
- `UserPromptSubmit.py`
- `hook_handler.py`
- `Guard.py`
- `SessionStart.py`
- `Stop.py`
- `SubagentStop.py`

**Behavior**: Shows warning but doesn't block (allows legitimate updates)

### 3. Technical Debt Prevention

**What it does**: Blocks creation of files with names suggesting legacy/backup code.

**Blocked keywords**:
- backup, v2, enhanced, legacy, old
- revised, new, copy, temp, tmp
- bak, orig, v3, v4, original
- renamed, deprecated, archived, obsolete
- draft, test, example, sample
- _old, _new, _backup, _legacy, _temp, _copy

## Implementation Details

### Location
- Primary logic: `/home/devcontainers/better-claude/.claude/hooks/hook_handlers/PreToolUse/__init__.py`
- Functions:
  - `check_file_size_reduction()` - Main destructive edit detection
  - `check_critical_file_modification()` - Critical file warnings
  - `check_technical_debt_filename()` - Technical debt prevention

### How It Works

1. **Before any file operation**, PreToolUse hook checks:
   - Is this a write/edit operation?
   - Does the file exist?
   - What's the current size/line count?

2. **For write operations**:
   - Calculate new size/line count
   - Compare with original
   - Block if reduction >50%

3. **For edit operations**:
   - Check old_string length
   - Check new_string length
   - Block if replacing >500 chars with <50% content

## Testing

Run the test suite:
```bash
python .claude/hooks/tests/test_destructive_edit_detection.py
```

Tests verify:
1. Large file reductions are blocked
2. Large edit replacements are blocked
3. Critical file modifications generate warnings

## Bypassing Protection

If you legitimately need to make large changes:

1. **Break into smaller edits**: Make incremental changes
2. **Use MultiEdit**: Multiple smaller edits in one operation
3. **Temporarily disable hooks**: Edit `hook_handler.py` (not recommended)
4. **Delete and recreate**: Remove the file first, then create new

## Error Messages

### Destructive Edit Blocked
```
❌ DESTRUCTIVE EDIT BLOCKED: This would remove 75% of file content
   File: /path/to/file.py
   Current: 400 lines (8,000 bytes)
   New: 100 lines (2,000 bytes)
   Action: Review your changes - this appears to delete significant functionality
   Hint: If you need to refactor, do it incrementally or explain the changes first
```

### Critical File Warning
```
⚠️ CRITICAL FILE: Modifying UserPromptSubmit.py - this controls core hook functionality
```

## Best Practices

1. **Make incremental changes**: Break large refactors into steps
2. **Document intentions**: Add comments explaining major changes
3. **Use version control**: Commit before major refactoring
4. **Test changes**: Run tests after modifications
5. **Review warnings**: Don't ignore critical file warnings

## Configuration

Currently hardcoded thresholds:
- File size reduction: 50%
- Line count reduction: 50%
- Edit size threshold: 500 characters
- Edit reduction threshold: 50%

Future enhancement: Make these configurable in `PreToolUse/config.py`

## Incident Prevention

This system prevents:
- Accidental file truncation
- Unintended mass deletions
- Loss of functionality during refactoring
- Creation of technical debt files
- Corruption of critical system files

## Limitations

Does not protect against:
- Gradual functionality removal (multiple small edits)
- Logic errors that don't change file size
- Syntax errors or breaking changes
- Malicious but size-preserving edits

## Future Enhancements

1. **AST-based analysis**: Detect function/class removal
2. **Backup creation**: Auto-backup before large changes
3. **Rollback capability**: Undo destructive changes
4. **Configurable thresholds**: Per-project settings
5. **ML-based detection**: Learn normal vs destructive patterns