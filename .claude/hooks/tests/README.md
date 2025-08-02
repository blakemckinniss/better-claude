# SessionStart Hook .gitignore Verification

This directory contains verification tools to ensure the SessionStart hook properly respects .gitignore rules.

## Files

### `sessionstart_gitignore_verification.py`
Comprehensive verification script that creates a temporary git repository with various files and .gitignore patterns, then verifies that all SessionStart hook functions correctly exclude ignored files.

**Features:**
- Creates test environment with tracked and ignored files
- Tests all major SessionStart hook functions:
  - `get_git_tracked_files()`
  - `is_gitignored()`
  - `get_project_structure()`
  - `get_readme_content()`
  - `get_project_metadata()`
  - `gather_session_context()`
- Verifies glob pattern handling (*.bak, etc.)
- Cleans up after testing

**Usage:**
```bash
# Run verification
python3 sessionstart_gitignore_verification.py

# Run with verbose output
python3 sessionstart_gitignore_verification.py --verbose

# Show help
python3 sessionstart_gitignore_verification.py --help
```

### `../scripts/run_sessionstart_gitignore_verification.sh`
Shell script wrapper that provides colored output and better error handling.

**Usage:**
```bash
# Run verification with colored output
.claude/hooks/scripts/run_sessionstart_gitignore_verification.sh

# Run with verbose mode
.claude/hooks/scripts/run_sessionstart_gitignore_verification.sh --verbose

# Show help
.claude/hooks/scripts/run_sessionstart_gitignore_verification.sh --help
```

## Test Coverage

The verification script tests the following scenarios:

### File Tracking
- ✅ Only git-tracked files are included in operations
- ✅ Ignored files are properly excluded
- ✅ .gitignore itself is included when tracked

### .gitignore Patterns
- ✅ Environment files (`.env`, `.env.*`)
- ✅ Dependencies (`node_modules/`)
- ✅ Python cache (`__pycache__/`, `*.pyc`)
- ✅ Build outputs (`dist/`, `build/`)
- ✅ OS files (`.DS_Store`)
- ✅ Temporary files (`*.tmp`, `*.bak`)
- ✅ Logs (`logs/`)
- ✅ IDE files (`.vscode/`, `.idea/`)
- ✅ Coverage (`coverage/`)

### Function-Specific Tests
- ✅ `get_git_tracked_files()` - Returns only tracked files
- ✅ `is_gitignored()` - Correctly identifies ignored files
- ✅ `get_project_structure()` - Only includes directories with tracked files
- ✅ `get_readme_content()` - Reads tracked README, ignores others
- ✅ `get_project_metadata()` - Only processes tracked config files
- ✅ `gather_session_context()` - Complete context excludes ignored files

## Expected Results

When all tests pass, you should see:
```
🎉 ALL VERIFICATIONS PASSED (6/6)
✅ SessionStart hook properly respects .gitignore rules
```

## Troubleshooting

If verification fails:

1. **Import Error**: Ensure the SessionStart module can be imported from the hook_handlers directory
2. **Git Issues**: Verify git is properly installed and configured
3. **Permission Issues**: Ensure the script has execute permissions
4. **Path Issues**: Run from the project root directory

## Integration

This verification can be integrated into CI/CD pipelines or run as part of hook development testing to ensure .gitignore compliance is maintained.