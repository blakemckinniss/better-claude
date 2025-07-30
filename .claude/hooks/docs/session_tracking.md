# Session Tracking for UserPromptSubmit Hook

## Overview

The UserPromptSubmit hook now includes intelligent session tracking to optimize context injection. This feature ensures that comprehensive context injections occur at strategic points during conversations, reducing context window pollution while keeping context fresh and relevant.

## How It Works

### Injection Triggers

Context injection happens when:

1. **First Prompt**: No user messages in the transcript yet
2. **After 5 Messages**: Every 6th message gets fresh context to prevent drift
3. **After Subagent**: When a subagent completes (SubagentStop hook)
4. **After Compact**: When context is compacted (PreCompact hook)
5. **Transcript Change**: When `/clear` is run or new conversation starts
6. **Session Start**: When Claude Code starts (SessionStart hook clears state)

### Session Lifecycle

1. **New Session**: SessionStart clears state, first prompt gets full context
2. **Messages 1-5**: After initial injection, next 5 messages get no additional context
3. **Message 6**: Automatic re-injection to refresh context
4. **Subagent/Compact**: Forces next prompt to get full context
5. **Reset**: `/clear` or restart creates new transcript, cycle repeats

## Implementation Details

### Key Functions

```python
def is_first_user_prompt(data):
    """Check if this is the first user prompt in the current session using provided transcript path."""
    # Uses data.get("transcript_path") to check transcript
    # Returns True for first prompt, False for subsequent prompts
```

### Injection Decision Logic

```python
# Simplified logic:
1. Check session state file for injection rules
2. If inject_next is True (forced injection) → inject
3. If messages_since_injection >= 5 → inject
4. If transcript changed → inject
5. If no user messages in transcript → inject
6. Otherwise → skip injection
```

### Session State Structure

```json
{
  "inject_next": false,           // Force injection on next prompt
  "messages_since_injection": 3,  // Count since last injection
  "last_transcript_path": "...",  // Track transcript changes
  "reason": "message_limit"       // Why injection is needed
}
```

### Hook Data Structure

The UserPromptSubmit hook receives data like:

```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
  "cwd": "/Users/...",
  "hook_event_name": "UserPromptSubmit",
  "userPrompt": "Write a function to calculate the factorial of a number"
}
```

### Circuit Breakers

The feature respects the existing injection circuit breakers. Even on first prompts, disabled injections won't run.

## Benefits

1. **Performance**: Reduces processing time for subsequent prompts
2. **Context Efficiency**: Prevents context window saturation with repetitive information
3. **Better Conversations**: Allows for more natural, continued dialogues without noise
4. **Automatic Management**: No user configuration needed - it just works

## Configuration

No configuration is required. The feature works automatically and integrates seamlessly with the existing hook system.

### Advantages of Smart Session Tracking

1. **Prevents Context Drift**: Regular re-injection keeps context fresh
2. **Handles All Scenarios**: `/clear`, subagents, compacts, restarts
3. **Configurable Limits**: Easy to adjust message count threshold
4. **Event-Driven**: Responds to important session events
5. **Graceful Degradation**: Falls back to safe behavior on errors

## Technical Notes

- Uses both transcript files and session state for robust tracking
- State stored in `.claude/hooks/session_state/` (gitignored)
- The feature is transparent to users and other hooks
- Session tracking adds minimal overhead (< 5ms)
- Gracefully handles file system errors
- Falls back to "inject" behavior on any error (safer)

## Configuration

### Modifying Injection Frequency

To change how often context is re-injected, modify the message limit in `session_state.py`:

```python
# Change from 5 to any number
if state["messages_since_injection"] >= 5:
```

## Future Enhancements

Potential improvements could include:
- User-configurable message limits
- Per-injection type preferences (e.g., always include git status)
- Smart context carry-over for specific scenarios
- Analytics on injection effectiveness
- Time-based injection (e.g., every 30 minutes)
- Detecting specific commands that should trigger full context