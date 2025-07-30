# AI Context Optimization Improvements

## Overview

The AI context optimizer has been refactored to properly utilize system prompts for better separation between instructions and user content. This addresses the issue where all questions were incorrectly generating AI assistant role definitions.

## Key Improvements

### 1. System/User Prompt Separation

**Before:**
```python
data = {
    "messages": [{"role": "user", "content": prompt}],  # Everything mixed together
}
```

**After:**
```python
messages = [
    {"role": "system", "content": system_prompt},  # Instructions to the AI
    {"role": "user", "content": user_prompt}       # Actual data to process
]
```

### 2. Context-Aware Processing

The optimizer now intelligently detects:
- Whether the user is asking for AI role creation vs regular questions
- What types of context are present (Git, MCP tools, Web search, etc.)
- Which context types are relevant to the user's question

### 3. Dynamic System Prompts

For **regular questions**:
- System prompt instructs to extract only relevant information
- Explicitly prevents AI role creation
- Dynamically mentions available context types

For **role/agent requests**:
- System prompt focuses on role architecture
- Includes specific formatting requirements
- Emphasizes using real context data

### 4. Smart Context Detection

The optimizer identifies injected content types:
```python
has_firecrawl = "<firecrawl-context>" in raw_context
has_git = "git" in raw_context.lower() or "branch:" in raw_context.lower()
has_mcp = "<mcp-" in raw_context or "MCP_" in raw_context
has_tree_sitter = "<tree-sitter" in raw_context
has_zen = "<zen-" in raw_context
has_errors = any(word in raw_context.lower() for word in ["error", "fail", "critical", "warning"])
```

### 5. Improved Fallback Logic

When AI is unavailable, the rule-based fallback:
- Categorizes context into sections (git, mcp, errors, etc.)
- Only includes relevant sections based on the user's question
- Maintains the same role vs non-role distinction

## Examples

### Technical Question
**User:** "What are the advantages of React over Svelte?"

**System Prompt:** Instructs to extract relevant information only
**Result:** Clean, focused context without role definitions

### Role Request
**User:** "Create a specialized debugging agent role"

**System Prompt:** Instructs to create a properly formatted AI role
**Result:** Structured role definition with relevant context

## Configuration

The AI context optimization is controlled by:
1. Environment variable: `CLAUDE_AI_CONTEXT_OPTIMIZATION=true`
2. Circuit breaker in UserPromptSubmit.py: `"ai_optimization": True`

## Benefits

1. **Better Accuracy**: AI understands its task clearly through system prompts
2. **Context Relevance**: Only includes context that helps answer the question
3. **Flexibility**: Different optimization strategies for different request types
4. **Efficiency**: Reduced token usage by focusing on relevant information
5. **Fallback Robustness**: Rule-based fallback follows the same logic

## Future Improvements

1. Add more sophisticated context type detection
2. Implement context priority scoring
3. Add user preference learning
4. Support for custom optimization strategies