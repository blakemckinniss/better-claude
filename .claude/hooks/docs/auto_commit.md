# Auto-Commit Feature

The Stop hook now includes an auto-commit feature that automatically commits changes when a Claude Code session ends.

## How it Works

When the Stop hook is triggered (at the end of a Claude Code session), it will:

1. Check if auto-commit is enabled via the `CLAUDE_AUTO_COMMIT` environment variable
2. Check for any uncommitted changes using `git status`
3. If changes exist, stage all files with `git add -A`
4. Create a commit with an intelligent commit message
5. The commit message will use the first line of Claude's last response (if available)

## Configuration

### Enable Auto-Commit

Set the environment variable to enable auto-commit:

```bash
export CLAUDE_AUTO_COMMIT=true
```

Add this to your shell profile (`.bashrc`, `.zshrc`, etc.) to make it permanent:

```bash
echo 'export CLAUDE_AUTO_COMMIT=true' >> ~/.bashrc
```

### Disable Auto-Commit

To disable auto-commit (default behavior):

```bash
export CLAUDE_AUTO_COMMIT=false
# or simply unset it
unset CLAUDE_AUTO_COMMIT
```

## Commit Message Format

The auto-commit feature generates intelligent commit messages:

1. **With Claude's context**: Uses the first line of Claude's last response (truncated to 50 characters)
   - Format: `Auto-commit: [First line of Claude's response]`
   - Example: `Auto-commit: Fixed the duplicate .claude folder issue`

2. **Without context**: Falls back to timestamp
   - Format: `Auto-commit: Session ended at YYYY-MM-DD HH:MM:SS`
   - Example: `Auto-commit: Session ended at 2025-01-29 15:30:45`

## Safety Features

- **Non-blocking**: Auto-commit errors won't fail the hook or interrupt the session end
- **Project isolation**: Only commits changes in the current project directory
- **Status check**: Only attempts to commit if there are actual changes
- **Error logging**: Any auto-commit errors are logged to stderr for debugging

## Use Cases

1. **Continuous Integration**: Keep your repository always up-to-date
2. **Work tracking**: Automatically capture all changes made during Claude sessions
3. **Backup**: Ensure no work is lost between sessions
4. **Collaboration**: Team members can see changes immediately

## Troubleshooting

If auto-commit isn't working:

1. Check if the environment variable is set:
   ```bash
   echo $CLAUDE_AUTO_COMMIT
   ```

2. Ensure you have Git configured:
   ```bash
   git config user.name
   git config user.email
   ```

3. Check the hook logs in stderr output for any error messages

4. Verify Git is accessible from the hook environment:
   ```bash
   which git
   ```

## Security Considerations

- Auto-commit will stage ALL changes (`git add -A`)
- Ensure sensitive files are in `.gitignore`
- Review commits regularly if using auto-commit in production
- Consider using a separate branch for auto-commits

## Example Workflow

1. Enable auto-commit:
   ```bash
   export CLAUDE_AUTO_COMMIT=true
   ```

2. Work with Claude Code normally

3. When the session ends, changes are automatically committed

4. Review the commits:
   ```bash
   git log --oneline -5
   ```