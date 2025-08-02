# Trigger Injection System

The trigger injection system automatically detects keywords in user prompts and suggests relevant MCP tools to use. This ensures that the appropriate tools are considered for each task.

## Features

### 1. **Keyword-Based Tool Detection**
- Analyzes user prompts for keywords associated with specific MCP tools
- Supports all available MCP tools including GitHub, ZEN, filesystem, web search, etc.

### 2. **Priority-Based Scoring System**
- Keywords have priority levels (0-10) indicating their importance
- Tools receive scores based on:
  - Keyword priority values
  - Number of keyword matches
  - Tool base priority
- Higher scores result in stronger recommendations

### 3. **Domain-Specific Keywords**
- Recognizes common task domains (fullstack dev, testing, DevOps, debugging)
- Suggests multiple relevant tools for domain-specific tasks
- Examples: "CI/CD" triggers GitHub + ZEN + filesystem tools

### 4. **Customizable Configuration**
- JSON-based configuration file for easy customization
- Add project-specific keywords and tool mappings
- Override default priorities and suggestions

## How It Works

When a user submits a prompt:

1. The system normalizes and analyzes the text
2. Matches keywords against configured patterns
3. Calculates relevance scores for each tool
4. Injects recommendations ranked by score

### Recommendation Levels

- 🔴 **CRITICAL** (score > 70): Tool is highly recommended
- 🟡 **IMPORTANT** (score > 50): Consider using this tool
- 🟢 **SUGGESTED** (score ≤ 50): Tool may be helpful

## Configuration

Create a `keyword_triggers.json` file in the `.claude/hooks/` directory:

```json
{
  "mcp_mappings": {
    "mcp__github__": {
      "name": "GitHub MCP",
      "priority": 8,
      "keywords": {
        "10": ["my-org github", "company repo"],
        "8": ["deploy to prod", "release branch"]
      }
    },
    "mcp__custom_tool__": {
      "name": "Custom Tool",
      "priority": 7,
      "keywords": {
        "9": ["custom keyword", "special term"],
        "5": ["general term"]
      }
    }
  },
  "domain_keywords": {
    "my_workflow": {
      "keywords": ["specific workflow", "company process"],
      "suggested_tools": ["mcp__github__", "mcp__custom_tool__"]
    }
  }
}
```

### Configuration Structure

- **mcp_mappings**: Tool-specific keyword mappings
  - **priority**: Base priority for the tool (1-10)
  - **keywords**: Object with priority levels as keys
    - Higher numbers = higher priority keywords

- **domain_keywords**: Multi-tool suggestions for domains
  - **keywords**: Phrases that trigger the domain
  - **suggested_tools**: List of tool IDs to suggest

## Examples

### Input: "Create a pull request on github"
```
🔴 CRITICAL: Keywords detected ("github", "pull request") [score: 100]
Use mcp__github__ (GitHub MCP). This tool is HIGHLY RECOMMENDED!
```

### Input: "Set up a CI/CD pipeline with github actions"
```
🔴 CRITICAL: Keywords detected ("github", "github actions", "ci/cd pipeline") [score: 100]
Use mcp__github__ (GitHub MCP). This tool is HIGHLY RECOMMENDED!

🟢 SUGGESTED: Keywords detected ("domain:ci/cd") [score: 50]
Use mcp__zen__ (ZEN Strategic AI). This tool may be helpful.
```

## Default Tool Coverage

- **GitHub MCP**: Pull requests, issues, commits, actions, workflows
- **ZEN Strategic AI**: Complex analysis, debugging, architecture, planning
- **File System**: File/folder operations, directory management
- **Web Search**: Documentation lookup, online research, content extraction
- **Browser Automation**: E2E testing, UI automation, screenshots
- **Context7**: Library documentation, framework guides
- **shadcn/ui**: UI components, Tailwind integration
- **Magic UI**: Animated components, special effects

## Testing

Run the test suite to verify keyword matching:

```bash
python .claude/hooks/tests/test_trigger_injection.py
```

This will test various prompts and show which tools are triggered.