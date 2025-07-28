# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimal project that appears to be primarily focused on Claude Code hooks configuration. The project uses Python-based hooks for various Claude Code events.

## Project Structure

```
.
├── .claude/
│   ├── hooks/          # Hook handler scripts
│   │   └── hook_handler.py
│   └── settings.json   # Claude Code settings and hook configuration
└── package-lock.json   # Empty npm lockfile
```

## Hook System

The project has extensive hook configuration for Claude Code events:
- **UserPromptSubmit**: Triggered when user submits a prompt
- **PreToolUse**: Triggered before tool usage (configured twice)
- **PostToolUse**: Triggered after tool usage
- **Notification**: Triggered for notifications
- **Stop**: Triggered when stopping

All hooks execute the same Python script: `python $CLAUDE_PROJECT_DIR/.claude/hooks/hook_handler.py`

## Environment Configuration

The project environment variables:
- `CLAUDE_PROJECT_DIR`: Used for referencing project paths in hooks

## Development Notes

- This appears to be a test or demonstration project for Claude Code hooks functionality
- No build system, tests, or application code is present
- All MCP servers are enabled for this project (`enableAllProjectMcpServers: true`)