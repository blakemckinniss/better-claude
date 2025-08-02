# PostToolUse Hook - Context Capture System

The PostToolUse hook captures tool usage outcomes and stores them as context for future revival, creating a feedback loop where successful patterns and encountered issues are preserved for future reference.

## Features

### 1. Context Capture (`context_capture.py`)

The context capture system analyzes tool responses to determine success/failure outcomes and extracts meaningful context:

#### Tool Outcome Analysis
- **Outcome Classification**: Classifies tool usage as `success`, `partial_success`, `failure`, or `unknown`
- **Error Pattern Detection**: Identifies common error patterns (file not found, permission denied, syntax errors, etc.)
- **Success Pattern Recognition**: Recognizes success indicators in tool responses
- **File Tracking**: Extracts files involved in operations from tool inputs and responses

#### Supported Tools
- **Built-in Tools**: `Bash`, `Edit`, `MultiEdit`, `Write`, `Read`, `Grep`, `Glob`
- **MCP Filesystem**: `mcp__filesystem__write_file`, `mcp__filesystem__edit_file`, etc.
- **Extensible**: Easy to add support for new tools

#### Context Storage
- Integrates with the Context Manager to store captured contexts
- Compresses large context data automatically
- Includes metadata about tool type, outcome, files involved
- Generates representative user prompts for context indexing

### 2. Integration with PostToolUse Pipeline

The context capture runs as the first step in the PostToolUse hook:

```
PostToolUse Hook Flow:
1. Context Capture (for all tools)
2. File Modification Processing (for file-modifying tools)
   - Formatters
   - Validators  
   - Diagnostics
```

### 3. Performance Features

- **Non-blocking**: Context capture failures don't block tool execution
- **Efficient**: Only captures meaningful contexts (skips trivial responses)
- **Smart Filtering**: Avoids capturing repetitive or low-value operations
- **Circuit Breaker**: Protects against database failures

## Usage Examples

### Automatic Context Capture

Context is automatically captured when tools are used:

```python
# When Claude runs: Bash command "ls -la"
# Context captured:
{
    "user_prompt": "Execute command: ls -la",
    "outcome": "success", 
    "files_involved": [],
    "context_data": "Tool: Bash\nOutcome: success\nCommand: ls -la\n...",
    "metadata": {"tool_name": "Bash", "command_type": "inspection"}
}
```

### Context Retrieval

Stored contexts can be retrieved for future reference:

```python
from context_manager import get_context_manager

cm = get_context_manager()
contexts = cm.retrieve_relevant_contexts("bash command error", max_results=5)

# Returns relevant contexts with:
# - Error patterns from failed bash commands
# - Successful command patterns
# - File operations that encountered issues
```

## Configuration

Context capture is configured through the Context Manager settings:

```json
{
  "storage": {
    "max_context_age_days": 30,
    "compression_enabled": true
  },
  "retrieval": {
    "max_results": 10,
    "relevance_threshold": 0.3,
    "scoring_weights": {
      "recency": 0.3,
      "relevance": 0.4, 
      "outcome_success": 0.2,
      "file_overlap": 0.1
    }
  }
}
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/devcontainers/better-claude/.claude/hooks/hook_handlers/PostToolUse
python3 test_context_capture.py
```

This tests:
- Various tool scenarios (success/failure)
- Context capture accuracy
- Context retrieval functionality
- Health monitoring

## Architecture

### Classes

1. **`ToolOutcomeAnalyzer`**: Analyzes tool responses to extract outcomes and patterns
2. **`ContextCaptureHandler`**: Main handler for capturing tool usage context
3. **`ToolOutcome`**: Data structure representing analyzed tool outcome

### Key Methods

- `analyze_tool_outcome()`: Main analysis method that classifies outcomes
- `capture_tool_context()`: Captures and stores context from tool interactions
- `should_capture_context()`: Determines if context should be captured
- `handle_context_capture()`: Entry point for hook integration

## Benefits

1. **Learning from Experience**: Successful patterns are preserved and can be referenced
2. **Error Prevention**: Common failure patterns are captured and can be avoided
3. **Context Continuity**: Tool usage patterns across sessions are maintained
4. **Debugging Aid**: Failed operations are documented with full context
5. **Performance Insights**: Track which tools and patterns work best

## Integration with Context Revival

The captured contexts feed into the Context Revival system in UserPromptSubmit:

1. **PostToolUse** captures outcomes → stores in Context Manager
2. **UserPromptSubmit** retrieves relevant contexts → injects into prompts
3. **Claude** receives enriched context → makes better decisions

This creates a complete feedback loop for continuous improvement of tool usage patterns.