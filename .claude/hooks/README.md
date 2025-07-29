# Claude Hooks System

This directory contains the hooks system for Claude Code, allowing customization of behavior at various points in the execution lifecycle.

## Configuration

### Environment Variables

The hooks system uses environment variables for configuration. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then update the `PROJECT_DIR` path to match your local environment:

```bash
PROJECT_DIR=/path/to/your/better-claude/
```

This ensures that paths (like the agents directory) work correctly regardless of your system setup.

## Available Hooks

- **UserPromptSubmit**: Processes user prompts before execution
  - `zen_injection.py`: Injects Zen consultation for complex tasks and agent selection
  - `smart_filter.py`: Intelligently determines when to invoke Zen assistance

## Agents

The `.claude/agents/` directory contains specialized agent definitions that can be delegated to for specific tasks:

- `code-refactorer`: Improves code structure and readability
- `content-writer`: Creates compelling, informative content
- `frontend-designer`: Converts designs to technical specifications
- `prd-writer`: Creates Product Requirements Documents
- `project-task-planner`: Creates development task lists from PRDs
- `security-auditor`: Performs comprehensive security audits
- `vibe-coding-coach`: Builds apps through conversational guidance