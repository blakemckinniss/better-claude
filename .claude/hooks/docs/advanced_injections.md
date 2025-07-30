# Advanced Context Injections for Better Claude

## Overview

The UserPromptSubmit hook system now includes powerful new injections that provide Claude with real-time awareness of system state, test results, and intelligently optimized context.

## New Injection Modules

### 1. AI Context Optimizer (`ai_context_optimizer.py`)

Uses AI to intelligently filter and prioritize all context data before sending to Claude.

**Features:**
- Multi-provider support (OpenRouter, OpenAI, Anthropic, Ollama)
- Intelligent prioritization based on user intent
- Automatic fallback to rule-based optimization
- 3-second timeout to prevent delays

**Enable with:**
```bash
export CLAUDE_AI_CONTEXT_OPTIMIZATION=true
export OPENROUTER_API_KEY=your_key_here  # Or other provider
```

### 2. Runtime Monitoring (`runtime_monitoring_injection.py`)

Provides real-time system resource awareness.

**Monitors:**
- CPU and memory usage (system and process level)
- Disk I/O and space
- Network connectivity to GitHub, PyPI, NPM
- Heavy processes (language servers, IDEs, dev tools)
- Recently modified files (last 5 minutes)

**Example output:**
```
<runtime-monitoring>
⚠️ HIGH CPU: 85.2%
⚠️ UNREACHABLE: PyPI
Recent activity: src/api/handler.py, tests/test_api.py
</runtime-monitoring>
```

### 3. Test Status Injection (`test_status_injection.py`)

Analyzes test results and coverage data from multiple frameworks.

**Supports:**
- **pytest**: JSON reports, JUnit XML
- **Jest**: jest-results.json
- **Coverage**: Python (coverage.py), JavaScript (lcov, NYC)
- **CI/CD**: GitHub Actions, GitLab CI, Jenkins detection

**Example output:**
```
<test-status>
✅ PYTEST: 142/150 passed
  Recent failures:
  - test_authentication_edge_case
❌ JEST: 89/102 passed
🟡 Python coverage: 76.5%
  Low coverage files:
  - handlers.py: 45%
  - utils.py: 52%
</test-status>
```

## How It Works

1. **Collection Phase**: All injection modules gather their data in parallel
2. **Combination Phase**: Raw context is assembled from all sources
3. **Optimization Phase** (if enabled): AI analyzes and restructures the context
4. **Injection Phase**: Optimized context is added to the user's prompt

## Configuration

### Environment Variables

```bash
# Enable AI optimization (default: false)
CLAUDE_AI_CONTEXT_OPTIMIZATION=true

# API Keys (at least one required for AI optimization)
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Local AI with Ollama

For free, private AI optimization:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2

# The system will automatically use it when available
```

## Best Practices

1. **Enable AI optimization for complex tasks** - It significantly improves context relevance
2. **Use OpenRouter for free tier** - Models like `google/gemini-2.0-flash-exp:free` work well
3. **Monitor injection size** - Check logs if prompts seem slow
4. **Disable unnecessary injections** - Comment out modules in UserPromptSubmit.py if not needed

## Future Enhancements

Planned injections include:
- Language Server Protocol diagnostics
- Docker container states
- Database schema analysis
- API endpoint health checks
- Security vulnerability scanning
- Distributed tracing integration

## Troubleshooting

### AI Optimization Not Working

1. Check environment variable is set: `echo $CLAUDE_AI_CONTEXT_OPTIMIZATION`
2. Verify API key is valid: Check provider dashboard
3. Test Ollama locally: `curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"Hi"}'`

### High Resource Usage

- Runtime monitoring may show warnings - this is normal during builds
- Disable runtime monitoring if it's too noisy

### Test Status Not Showing

- Ensure test result files are in standard locations
- Supported formats: pytest-json, JUnit XML, Jest results, coverage.json