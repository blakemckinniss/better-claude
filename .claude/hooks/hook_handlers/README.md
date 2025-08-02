# Hook Handlers Directory

This directory contains the implementation modules for Claude Code hooks. All code in this directory MUST comply with the HOOK_CONTRACT.md.

## Directory Structure

```
hook_handlers/
├── HOOK_CONTRACT.md      # Governing rules and security requirements
├── README.md             # This file
├── pyproject.toml        # Python project configuration
├── hook_logger.py        # Logging utilities
├── Notification.py       # Notification event handler
├── PostToolUse.py        # Post tool use event handler
├── PreCompact.py         # Pre-compact event handler
├── PreToolUse.py         # Pre tool use event handler
├── SessionStart.py       # Session start event handler
├── Stop.py               # Stop event handler
├── SubagentStop.py       # Subagent stop event handler
└── UserPromptSubmit/     # User prompt submit handlers
    ├── __init__.py
    ├── agent_injector.py
    ├── ai_context_optimizer.py
    ├── code_smell_detector.py
    ├── content_injection.py
    ├── context_history_injection.py
    ├── dependency_graph.py
    ├── firecrawl_injection.py
    ├── git_injection.py
    ├── lsp_diagnostics_injection.py
    ├── mcp_injector.py
    ├── prefix_injection.py
    ├── runtime_monitoring_injection.py
    ├── session_state.py
    ├── smart_filter.py
    ├── suffix_injection.py
    ├── test_status_injection.py
    ├── tree_sitter_injection.py
    ├── trigger_injection.py
    └── zen_injection.py
```

## Security Requirements

⚠️ **CRITICAL**: All hook handlers execute with full system permissions. Before modifying ANY code in this directory, you MUST:

1. Read and understand HOOK_CONTRACT.md
2. Follow ALL security practices outlined in the contract
3. Never trust user input without validation
4. Always use proper error handling
5. Test thoroughly in a safe environment

## Development Guidelines

### Adding New Handlers

1. **Choose the appropriate event type** based on when your hook needs to run
2. **Follow the naming convention**: `EventName.py` or `EventName/module.py`
3. **Implement proper input validation** as shown in the contract
4. **Use appropriate exit codes**:
   - 0: Success
   - 2: Block action (where applicable)
   - Other: Non-blocking error
5. **Return structured JSON** when advanced control is needed

### Common Patterns

#### Basic Hook Handler Template
```python
#!/usr/bin/env python3
import json
import sys

# Load and validate input
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

# Extract event-specific data
hook_event = input_data.get("hook_event_name", "")
if hook_event != "ExpectedEventName":
    sys.exit(0)  # Not applicable, exit silently

# Your hook logic here
# ...

# Success
sys.exit(0)
```

#### Security Validation Example
```python
# Validate file paths
file_path = input_data.get("tool_input", {}).get("file_path", "")
if not file_path:
    sys.exit(0)  # No file path, not applicable

# Security checks
if ".." in file_path or file_path.startswith("/etc"):
    print("Security: Path traversal attempt blocked", file=sys.stderr)
    sys.exit(2)  # Block the action

# Skip sensitive files
sensitive_patterns = [".env", ".git/", "id_rsa", ".pem", ".key"]
if any(pattern in file_path for pattern in sensitive_patterns):
    print(f"Security: Sensitive file access blocked: {file_path}", file=sys.stderr)
    sys.exit(2)
```

## Testing

All handlers should include tests in the `/tests` directory. Run tests before deploying:

```bash
cd /home/devcontainers/better-claude/.claude/hooks
python -m pytest tests/
```

## Integration with Claude Code

Handlers are invoked automatically by Claude Code based on the configuration in `.claude/settings.json`. Example:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/hook_handler.py"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting

1. **Hook not firing**: Check matcher patterns in settings.json
2. **Unexpected behavior**: Run with `claude --debug` to see hook execution
3. **JSON errors**: Validate your JSON output format
4. **Permission errors**: Ensure scripts are executable (`chmod +x`)

## Important Notes

- Hooks run with a 60-second timeout by default
- All matching hooks run in parallel
- Environment variable `$CLAUDE_PROJECT_DIR` contains the project root
- Changes to hooks in settings files require Claude Code restart or `/hooks` review

---

**Remember**: With great power comes great responsibility. Hooks can access and modify any files your user can. Always prioritize security and test thoroughly.