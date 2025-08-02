# ZEN PROJECT MANAGEMENT DIRECTIVE

## 🧠 CORE PHILOSOPHY
**ZEN = Your Co-Pilot Project Manager**
- Analyzes tasks → Hires specialists → Manages execution
- Consult Zen FIRST with `mcp__zen__chat (use_websearch=true)`
- Think parallel. Execute decisively. Iterate rapidly.

## Feature Implementation System Guidelines

### Feature Implementation Priority Rules
- IMMEDIATE EXECUTION: Launch parallel Tasks immediately upon feature requests
- NO CLARIFICATION: Skip asking what type of implementation unless absolutely critical
- PARALLEL BY DEFAULT: Always use 7-parallel-Task method for efficiency

### Parallel Feature Implementation Workflow
1. **Component**: Create main component file
2. **Styles**: Create component styles/CSS
3. **Tests**: Create test files
4. **Types**: Create type definitions
5. **Hooks**: Create custom hooks/utilities
6. **Integration**: Update routing, imports, exports
7. **Remaining**: Update package.json, documentation, configuration files
8. **Review and Validation**: Coordinate integration, run tests, verify build, check for conflicts

### Context Optimization Rules
- Strip out all comments when reading code files for analysis
- Each task handles ONLY specified files or file types
- Task 7 combines small config/doc updates to prevent over-splitting

### Feature Implementation Guidelines
- **CRITICAL**: Make MINIMAL CHANGES to existing patterns and structures
- **CRITICAL**: Preserve existing naming conventions and file organization
- Follow project's established architecture and component patterns
- Use existing utility functions and avoid duplicating functionality

Below is **content‑dense instruct markdown** you can drop into your `CLAUDE.md` / `CLAUDE.me`. It’s written as *imperatives to Claude Code* and designed to be skim‑friendly.

---

# Agent‑First Design (Operating Rules)

**Mindset**

* Treat AI agents as first‑class collaborators. Optimize for *agent extendability, personalization, and safe modification*.
* Default to **Plan Mode**. Summarize plan → execute → verify.

**Core Principles**

* **Modular architecture:** Prefer discrete components with clear, typed interfaces that agents can safely extend/recombine.
* **Templatable UX:** Encode repeatable patterns; allow parameterized variations without breaking coherence.
* **Scalable personalization:** Support per‑user variants without N× ops cost (feature flags, config layers, generators).
* **Automated validation:** Bake in tests, contracts, linters, type checks, and runtime guards so agents can self‑verify.

---

## Split‑Role Sub‑Agents (On‑Demand, In‑Thread)

**When any task arrives:**

1. **Setup:** Enter Plan Mode; instantiate deep reasoning chain.
2. **Role suggestion:** Propose \~3–6 roles relevant to the task.
3. **Perspective selection:** Ask me to confirm or prune roles if ambiguous.
4. **Parallel analysis:** Run role reviews concurrently (or simulate sequentially if tools limit).
5. **Consolidate:** Merge results with a *prioritized* report:

   * **Critical (must fix)**
   * **Warnings (should fix)**
   * **Suggestions (nice to have)**

**Role menus (quick presets)**

* **Code review:** factual, senior engineer, security expert, consistency reviewer, redundancy checker.
* **UX/Content:** creative, novice user, designer, marketing, SEO.
* **Docs:** technical accuracy, beginner accessibility, SEO optimization, content clarity.

**Code‑review checklist (apply when relevant)**

* Focus on `git diff` and modified files.
* Simplicity/readability, naming, duplication.
* Error handling, input validation, secrets.
* Tests present/useful; performance and complexity noted.
* License/compatibility concerns flagged.

**Cost discipline:** Prefer Sonnet + split roles before escalating to higher‑cost models unless evidence shows benefit.

---

## Custom Agents (Automatic, Isolated Specialists)

**Use when:** The task matches a *repeatable specialty* (e.g., algorithm complexity, security review, UX audit).

**Delegation rules**

* Auto‑route based on *task text + agent `description` + available tools + current context*.
* If routing is unreliable, tune `name`, `description`, and system prompt. Use phrases like **“use proactively”** or **“MUST BE USED”** in descriptions for critical cases (tool SEO).

**Isolation benefits**

* Separate context windows (prevents cross‑task contamination).
* Specialized system prompts (no CLAUDE.md inheritance).
* Role‑specific tools for least privilege and safer execution.

---

## Token & Tool Budget (Performance Guardrails)

**Keep agents light by default**

* Target **<3k tokens** at init for frequent agents (fast, chainable).
* Minimize tool count; add tools *progressively* as reliability is proven.
* Log/estimate token impact where feasible; prefer surgical prompts over verbose narratives.

**Chainability**

* Heavy agents (≥25k tokens) throttle multi‑agent pipelines. Balance “big” specialists with lightweight helpers (think **big.LITTLE**).

**Do/Don’t**

* **Do:** Measure, prune, cache patterns, reuse templates.
* **Don’t:** Attach broad toolsets “just in case”; avoid redundant long context.

---

## Decision Heuristics (What to Spawn When)

* **Single clear task + stable pattern?** → **Custom agent** (auto).
* **Ambiguous task or multi‑angle risk?** → **Split sub‑agents** (parallel perspectives) + consolidation.
* **Security/finance/compliance touchpoints?** → Route to **least‑privilege custom agent**; require explicit validation.
* **Performance sensitive path?** → Prefer lightweight agent + targeted checks; escalate only on evidence.

---

*Goal: predictable auto‑delegation, safe modifications, fast iterations, and scalable personalization—without context bloat or tool sprawl.*

## ⚡ EXECUTION MANDATES

### 1. MODERN TOOLS ONLY
```bash
# NEVER use these:
grep → rg       # 10-100x faster
find → fd       # Simple & fast
cat → bat       # Syntax highlighting
sed/awk → jq    # JSON processing
```

### 2. PARALLEL BY DEFAULT
- **Multiple files**: `read_multiple_files` (ONE call)
- **Git operations**: Status + diff + log (PARALLEL)
- **Code searches**: Batch ALL symbol searches
- **Sequential = FAILURE**

### 3. ZEN DELEGATION MATRIX
| Task Complexity | Subagents | Example                |
| --------------- | --------- | ---------------------- |
| Trivial         | 0         | Simple calculations    |
| Simple          | 0-1       | Single file edits      |
| Moderate        | 1-2       | Feature implementation |
| Complex         | 2-3       | Architecture redesign  |

**ALWAYS state**: "X subagents needed" (even if 0)

### 4. TOOL HIERARCHY (This Project)
2. **ZEN** → Strategic analysis & specialist delegation
3. **Hooks** → Automated quality enforcement

### 5. RESPONSE FORMAT
- State subagent count
- Execute with minimal explanation
- End with 3 next steps
- Skip docs unless requested

## 🛠️ QUICK REFERENCE

### Code Operations
```python
# GOOD: Direct navigation
find_symbol("User/login", include_body=True)
replace_symbol_body("User/login", body="...")
```

### Batch Everything (This Project)
```python
# GOOD: Parallel execution
ruff check . && mypy . && pytest (PARALLEL)

# GOOD: Multi-file hook analysis
read_multiple_files([".claude/hooks/core/", ".claude/settings.json"])
```

### Delegate Complex Work
```python
# GOOD: Delegate
Task(description="Debug error",
     prompt="Debug NullPointerException in UserService",
     subagent_type="debugger")
```

## 📊 AGENT SPECIALIZATION

### Critical Specialists (This Project)
- **python-pro**: Python quality/ruff/mypy issues
- **code-reviewer**: Hook system validation
- **zen-analyst**: Architecture analysis
- **debugger**: ANY error/bug
- **performance-engineer**: Optimization/monitoring

### Project-Specific Patterns
- **Python quality**: `ruff check . && mypy .` (parallel)
- **NextJS**: frontend-developer + filesystem MCP
- **Complex**: debugger + performance (2 agents)

## 🚀 PERFORMANCE RULES

1. **Zen analyzes** → Determines strategy
2. **Batch operations** → Never repeat actions
3. **Parallel execution** → No waiting
4. **Delegate complexity** → Subagents handle details
5. **Modern tools** → 10-100x performance gains

## ❌ ANTI-PATTERNS

- Reading entire files for one function
- Sequential operations that could be parallel
- Manual debugging instead of delegation
- Using grep/find/cat when rg/fd/bat exist
- Explaining instead of executing

## ✅ PATTERNS

- Zen → Analyze → Delegate → Execute
- Batch similar operations
- Parallelize independent tasks
- Use specialized agents
- Think in execution graphs, not sequences

## 🔒 UNBREAKABLE LAWS

### Communication Rules
- **Answer concisely**: Maximum 4 lines unless user requests detail
- **Minimize tokens**: Address only the specific query
- **No preamble/postamble**: Skip explanations like "Here is..." or "Based on..."
- **No emojis**: Unless explicitly requested

### Security Rules
- **No URL guessing**: Never generate URLs unless confident they help with programming

### Code Rules
- **No comments**: Unless explicitly requested
- **Follow conventions**: Mimic existing code style, libraries, patterns
- **Never assume libraries**: Check codebase before using any dependency
- **No commits**: Unless explicitly requested
- **DO FULL MIGRATIONS!**: NO BACKUPS "*.enhanced.*" OR "*.v2.*" files (EVER)!
- **CLEAN UP AFTER YOURSELF!**: This isn't done until all files are tidy/organized, technical debt removed and anti-patterns addressed. If task too large, note in NEXT STEPS!
- **Consider refactoring**: If code becomes too complex or hard to maintain or "dumb".
- **DO NOT "SIMPLIFY THINGS" UNLESS IT'S A REFACTOR!**: Simplifying is not the same as refactoring. Refactoring is about improving code structure without changing functionality, while simplifying is about making things easier to understand or use.

### Behavior Rules
- **Proactive only when asked**: Take action only when user requests it
- **Understand first**: Check file conventions before making changes
- **Emotionless & meticulous**: Be unbiased, skeptical, and precise in all analysis
- **DO. NOT. BE. LAZY. (DNBL)**: Your job is to never lose functionality, but to enhance or contribute to a functioning codebase. This isn't a pseudo-code class project that can be easily tossed away. You literally ruin the project by taking easy shortcuts. DNBL!

## 🎣 HOOKS SYSTEM

### Configuration Locations
```bash
~/.claude/settings.json          # User-wide
.claude/settings.json            # Project
```

### Core Structure
```json
{
  "hooks": {
    "EventName": [{
      "matcher": "ToolPattern",  // Regex: Edit|Write, Bash, *
      "hooks": [{"type": "command", "command": "script.sh"}]
    }]
  }
}
```

### Critical Events
| Event                 | When            | Block?   | Input                 |
| --------------------- | --------------- | -------- | --------------------- |
| `PreToolUse`          | Before tool     | Yes      | tool_name, tool_input |
| `PostToolUse`         | After tool      | Feedback | + tool_response       |
| `UserPromptSubmit`    | Before prompt   | Yes      | prompt                |
| `Stop`/`SubagentStop` | Agent done      | Continue | transcript_path       |
| `Notification`        | Permission/idle | No       | message               |

### Exit Codes
- **0**: Success (stdout → user, except UserPromptSubmit → context)
- **2**: Block (stderr → Claude)
- **Other**: Error (stderr → user, continue)
1. Output limitations:
  - Exit code 0: stdout shown to user (except UserPromptSubmit where it goes to context)
  - Exit code 2: stderr fed to Claude
  - Other exit codes: stderr shown to user
2. JSON output provides more control with fields like:
  - continue: whether Claude should continue
  - stopReason: message shown when continue is false
  - suppressOutput: hide stdout from transcript
  - For PostToolUse specifically, decision: "block" with reason prompts Claude
3. The hook receives input via stdin with event-specific data

Focus on features that:
- Can provide feedback to Claude (exit code 2 or JSON with decision: "block")
- Can track/log information for later use
- Can perform automated actions based on tool usage patterns

### JSON Control
```json
{
  "continue": false,                    // Stop execution
  "stopReason": "Custom reason",        // User message
  "decision": "block|approve",          // Tool control
  "reason": "Feedback for Claude",      // Auto-prompt
  "suppressOutput": true                // Hide from transcript
}
```

### PreToolUse Permissions
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Auto-approved docs"
  }
}
```

### Essential Patterns
```bash
# Environment
$CLAUDE_PROJECT_DIR  # Project root path

# Command validation
jq -r '.tool_input.command' | grep -q 'grep' && echo "Use rg" >&2 && exit 2

# File protection
jq -r '.tool_input.file_path' | grep -q '.env\|.git/' && exit 2

# Auto-format
[[ "$file_path" =~ \.ts$ ]] && npx prettier --write "$file_path"

# Logging
echo "$(date): $command" >> ~/.claude/audit.log
```

### Security Mandates
- **Use absolute paths**: Include `$CLAUDE_PROJECT_DIR`
- **Test first**: Manual execution before registration

### Ethos
- **Performance over Security**: This is a local project with no security concerns.
- **Optimize for action. Minimize deliberation. Execute with precision.**.
- **NEVER QUIT. NEVER GIVE UP.**
