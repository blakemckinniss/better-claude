# Context Revival System Documentation

## Overview

The Context Revival System is an intelligent conversation history injection mechanism that automatically retrieves and injects relevant historical context into user prompts. It analyzes user queries to determine when historical context would be beneficial and provides that context to improve AI responses.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Context Revival System                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Context Revival │  │ Context Manager │  │ Session State   │ │
│  │ Hook            │  │                 │  │                 │ │
│  │ (Analyzer)      │  │ (Storage/Query) │  │ (Session Track) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Context Entry   │  │ Circuit Breaker │  │ Context Cache   │ │
│  │ (Data Model)    │  │ (Reliability)   │  │ (Performance)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ SQLite Database │  │ FTS Index       │  │ Configuration   │ │
│  │ (Persistence)   │  │ (Search)        │  │ (Settings)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
User Prompt
     ↓
┌─────────────────┐
│ ContextRevival  │ ← Configuration
│ Analyzer        │
└─────────────────┘
     ↓ (triggers?)
┌─────────────────┐
│ Context Manager │ ← Cache
│ Query System    │
└─────────────────┘
     ↓
┌─────────────────┐
│ SQLite + FTS    │ → Circuit Breaker
│ Database        │
└─────────────────┘
     ↓
┌─────────────────┐
│ Context         │
│ Formatter       │
└─────────────────┘
     ↓
Enhanced Prompt with Context
```

## Component Specifications

### 1. ContextRevivalHook

**Purpose**: Main orchestrator that analyzes prompts and coordinates context retrieval.

**Key Methods**:
- `generate_context_injection(prompt)`: Main entry point for context revival
- `extract_file_context(prompt)`: Extracts mentioned files from prompts
- `get_health_status()`: Returns system health information

**Configuration Path**: `context_revival_config.json`

### 2. ContextRevivalAnalyzer 

**Purpose**: Analyzes user prompts to determine if context revival would be beneficial.

**Analysis Criteria**:
- **Trigger Keywords**: "similar", "before", "previous", "like", "remember"
- **Error Indicators**: "error", "bug", "issue", "problem", "failed"
- **Success Indicators**: "worked", "success", "fixed"  
- **Pattern Matching**: Regex patterns for different context types
- **File Mentions**: Detection of file paths and extensions
- **Prompt Complexity**: Longer prompts are more likely to benefit

**Confidence Scoring**:
- Trigger keywords: +0.15 per keyword
- Pattern matches: +0.2 per pattern type
- Error indicators: +0.3 (higher confidence)
- Success indicators: +0.2
- File mentions: +0.1 per file (max 0.2)
- Complex prompts: +0.1 for >20 words

**Threshold**: Context is retrieved when confidence ≥ 0.3

### 3. ContextManager

**Purpose**: Handles storage, retrieval, and management of conversation contexts.

**Core Features**:
- **SQLite Database**: Persistent storage with WAL mode
- **Full-Text Search**: SQLite FTS5 for efficient text queries
- **Connection Pooling**: Thread-safe database connections
- **Circuit Breaker**: Reliability pattern for database operations
- **Caching**: In-memory LRU cache with TTL
- **Compression**: zlib compression for large contexts

**Database Schema**:
```sql
CREATE TABLE contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_prompt TEXT NOT NULL,
    context_data TEXT NOT NULL,
    files_involved TEXT,  -- JSON array
    timestamp DATETIME NOT NULL,
    outcome TEXT DEFAULT 'unknown',
    metadata TEXT,  -- JSON object
    relevance_score REAL DEFAULT 0.0,
    compressed BOOLEAN DEFAULT 0,
    hash TEXT UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Relevance Scoring Weights**:
- Recency: 0.3 (newer contexts preferred)
- Text Relevance: 0.4 (keyword overlap)
- Outcome Success: 0.2 (successful outcomes preferred)
- File Overlap: 0.1 (matching files involved)

### 4. ContextFormatter

**Purpose**: Formats retrieved contexts for injection into prompts.

**Features**:
- **Token Management**: Respects max_context_tokens limit (default: 2000)
- **Priority Sorting**: By relevance score and recency
- **Rich Formatting**: Includes metadata, outcome indicators, time information
- **Content Truncation**: Automatically truncates long contexts

**Output Format**:
```xml
<context-revival confidence="0.75">
<!-- Triggered by: error-related: error, debug -->

## Context 1/3 ✅ (2h ago)
**Relevance:** 0.85 | **Session:** transcript_20250102_14
**Prompt:** How to fix the login error...
**Files:** auth.py, login.js
**Context:**
Fixed the authentication issue by updating the session timeout...
**Metadata:** tools_used: Edit, outcome_reason: successful fix

## Context 2/3 🟡 (1d ago)
...
</context-revival>
```

### 5. CircuitBreaker

**Purpose**: Implements the circuit breaker pattern for database reliability.

**States**:
- **CLOSED**: Normal operation
- **OPEN**: All requests fail fast
- **HALF_OPEN**: Limited requests allowed for testing

**Configuration**:
- Failure threshold: 5 failures
- Recovery timeout: 300 seconds (5 minutes)  
- Half-open max calls: 3 attempts

## Integration Points

### Hook Integration

The Context Revival system integrates with the Claude hooks system through:

1. **UserPromptSubmit Hook**: Analyzes and enhances prompts before submission
2. **PostToolUse Hook**: Can store context based on tool usage outcomes
3. **Session Tracking**: Integrates with session state management

### File Locations

```
.claude/hooks/
├── hook_handlers/
│   └── UserPromptSubmit/
│       ├── context_revival.py          # Main hook implementation
│       ├── context_manager.py          # Storage and retrieval
│       ├── session_state.py           # Session management
│       └── context_revival_config.json # Configuration
└── context_revival/
    ├── context_revival.db             # SQLite database
    └── logs/                          # System logs
```

## Configuration Guide

### Basic Configuration (context_revival_config.json)

```json
{
  "database": {
    "filename": "context_revival.db",
    "timeout": 30.0,
    "wal_mode": true
  },
  "storage": {
    "max_context_age_days": 30,
    "compression_enabled": true,
    "max_context_length": 10000
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
  },
  "injection": {
    "max_context_tokens": 2000,
    "include_file_context": true
  },
  "triggers": {
    "keywords": ["similar", "before", "previous", "like", "remember"],
    "error_indicators": ["error", "bug", "issue", "problem"],
    "success_indicators": ["worked", "success", "fixed"],
    "file_extensions": [".py", ".js", ".ts", ".jsx", ".tsx"]
  },
  "performance": {
    "max_query_time_ms": 500,
    "cache_size": 100,
    "cache_ttl": 3600
  },
  "logging": {
    "level": "INFO"
  }
}
```

### Tuning Guidelines

**For High-Volume Usage**:
- Increase `cache_size` to 500-1000
- Reduce `cache_ttl` to 1800 (30 min)
- Increase `relevance_threshold` to 0.4

**For Development/Debugging**:
- Set `logging.level` to "DEBUG"
- Reduce `max_context_age_days` to 7
- Set `max_results` to 3-5

**For Performance-Critical**:
- Disable compression: `compression_enabled: false`
- Reduce `max_query_time_ms` to 200
- Increase `relevance_threshold` to 0.5

## Usage Patterns

### Automatic Triggering

The system automatically triggers on prompts containing:

1. **Error Resolution**: "Why is this failing?", "Debug this error"
2. **Pattern Seeking**: "How did I solve this before?", "Similar to previous issue"
3. **Implementation Reference**: "Like the login component", "Same approach as before"
4. **File-Specific Queries**: Mentions of specific files or extensions

### Manual Testing

```bash
# Test context revival directly
python3 context_revival.py "How to fix authentication error in login.py?"

# Test with hook system
echo '{"prompt": "Similar error as before with database connection"}' | python3 context_revival.py
```

### Health Monitoring

```python
from context_revival import get_context_revival_hook

hook = get_context_revival_hook()
health = hook.get_health_status()

print(f"System enabled: {health['enabled']}")
print(f"Contexts retrieved: {health['stats']['contexts_retrieved']}")
print(f"Average retrieval time: {health['stats']['total_retrieval_time']}")
```

## Performance Characteristics

### Benchmarks

**Context Retrieval Performance**:
- Small database (<1000 contexts): 5-20ms
- Medium database (1000-10000 contexts): 20-100ms  
- Large database (>10000 contexts): 100-500ms

**Memory Usage**:
- Base system: ~5MB
- Per 1000 cached contexts: ~2MB
- SQLite database: ~1MB per 1000 contexts

**Disk Storage**:
- Uncompressed: ~2KB per context entry
- Compressed: ~500B per context entry (75% reduction)

### Optimization Strategies

1. **Caching**: Aggressive caching of frequent queries
2. **Indexing**: FTS5 indexes on prompt and context text
3. **Compression**: zlib compression for large contexts
4. **Circuit Breaker**: Fails fast on database issues
5. **Connection Pooling**: Reuses database connections
6. **Background Cleanup**: Removes old contexts automatically

## Troubleshooting Guide

### Common Issues

**1. Context Revival Not Triggering**
- Check confidence score with debug logging
- Verify trigger keywords in configuration
- Ensure prompt complexity meets threshold

**2. No Relevant Contexts Found**  
- Check database contents: `sqlite3 context_revival.db "SELECT COUNT(*) FROM contexts"`
- Verify relevance threshold not too high
- Check if contexts have expired (max_context_age_days)

**3. Performance Issues**
- Monitor query time with logging
- Check circuit breaker state
- Clear cache if memory pressure: `hook.cache.clear()`

**4. Database Errors**
- Check file permissions on database directory
- Verify SQLite version supports FTS5
- Check disk space availability

### Debug Commands

```bash
# Check database schema
sqlite3 .claude/hooks/context_revival/context_revival.db ".schema"

# View recent contexts
sqlite3 .claude/hooks/context_revival/context_revival.db "SELECT * FROM contexts ORDER BY timestamp DESC LIMIT 5"

# Test FTS search
sqlite3 .claude/hooks/context_revival/context_revival.db "SELECT * FROM contexts_fts WHERE contexts_fts MATCH 'error login'"

# Check system health
python3 -c "from context_revival import get_context_revival_hook; print(get_context_revival_hook().get_health_status())"
```

### Log Analysis

**Enable Debug Logging**:
```json
{
  "logging": {
    "level": "DEBUG",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

**Key Log Messages**:
- `Context revival triggered: <reasons>` - System activated
- `Retrieved X contexts in Ys` - Performance metrics
- `Context revival not triggered (confidence: X)` - Below threshold
- `Slow context retrieval: Xs` - Performance warning

## Security Considerations

### Data Privacy

- **Local Storage**: All contexts stored locally in SQLite
- **No Network Calls**: System operates entirely offline
- **Session Isolation**: Contexts tagged by session ID
- **Automatic Cleanup**: Old contexts automatically removed

### Access Control

- **File Permissions**: Database readable only by user
- **Path Validation**: Input sanitization for file paths
- **Circuit Breaker**: Prevents resource exhaustion attacks

### Sensitive Data Handling

- **No Credential Storage**: Avoids storing API keys or passwords
- **Content Filtering**: Can be configured to exclude sensitive file types
- **Compression**: Optional compression obscures content slightly

## Future Enhancements

### Planned Features

1. **Semantic Search**: Vector embeddings for better relevance
2. **Context Categories**: Automatic categorization of context types
3. **Multi-Project Support**: Context sharing across related projects
4. **Export/Import**: Backup and restore context databases
5. **Analytics**: Usage patterns and effectiveness metrics

### Extension Points

1. **Custom Analyzers**: Plugin system for domain-specific analysis
2. **External Storage**: Support for remote context storage
3. **Integration APIs**: REST API for external tool integration
4. **Machine Learning**: ML-based relevance scoring

## API Reference

### Public Functions

```python
# Main entry point
get_context_revival_injection(prompt: str, project_dir: Optional[str] = None) -> str

# Get hook instance
get_context_revival_hook(project_dir: Optional[str] = None) -> ContextRevivalHook

# Context storage
store_conversation_context(user_prompt: str, context_data: str, 
                          files_involved: List[str] = None,
                          outcome: str = "unknown") -> Optional[int]

# Context retrieval  
retrieve_relevant_context(query: str, files_involved: List[str] = None,
                         max_results: int = 5) -> List[ContextEntry]
```

### ContextEntry Data Model

```python
@dataclass
class ContextEntry:
    id: Optional[int] = None
    session_id: str = ""
    user_prompt: str = ""
    context_data: str = ""
    files_involved: List[str] = None
    timestamp: datetime = None
    outcome: str = "unknown"  # success, failure, partial
    metadata: Dict[str, Any] = None
    relevance_score: float = 0.0
    compressed: bool = False
```

## Migration Guide

### From Legacy Systems

If migrating from previous context systems:

1. **Export Data**: Extract contexts from existing system
2. **Schema Mapping**: Map fields to ContextEntry structure  
3. **Bulk Import**: Use `store_context()` for batch insertion
4. **Configuration**: Update trigger keywords and thresholds
5. **Testing**: Verify retrieval performance and accuracy

### Version Compatibility

- **Database Schema**: Automatic migrations handled
- **Configuration**: Backward compatible with defaults
- **API**: Semantic versioning for breaking changes

This documentation provides a comprehensive overview of the Context Revival System architecture, configuration, and usage patterns for both users and developers.