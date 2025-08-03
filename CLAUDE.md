CLAUDE.md

## TASK(...) 
- USE AS OFTEN AS POSSIBLE (as subagents.)

## MUST USE MODERN CLI COMMANDS (ASSUME INSTALLED)
  **Bash(** 
  rg (fast grep), fd (find fast), bat (color cat), fzf (fuzzy pick), zoxide (smart cd), lsd (pretty ls), sd (sed alt), jq (JSON CLI), yq (YAML CLI), mlr (CSV CLI), ctags (tag index), delta (diff view), tree (dir tree), tokei (code LOC), scc (LOC alt), exa (modern ls), dust (disk du), duf (disk df), procs (ps plus), hyperfine (bench), entr (watch run), xh (curl alt), dog (DNS dig), podman (containers), dive (layer view), trivy (vuln scan), tldr (examples) 
  **)**

### Feature Implementation Priority Rules
- IMMEDIATE EXECUTION: Launch parallel Tasks immediately upon feature requests
- NO CLARIFICATION: Skip asking what type of implementation unless absolutely critical
- PARALLEL BY DEFAULT: Always use 7-parallel-Task method for efficiency

### Context Optimization Rules
- Strip out all comments when reading code files for analysis
- Each task handles ONLY specified files or file types
- Task 7 combines small config/doc updates to prevent over-splitting

### Feature Implementation Guidelines
- **CRITICAL**: Make MINIMAL CHANGES to existing patterns and structures
- **CRITICAL**: Preserve existing naming conventions and file organization
- Follow project's established architecture and component patterns
- Use existing utility functions and avoid duplicating functionality

### PARALLEL BY DEFAULT
- **Multiple files**: `read_multiple_files` (ONE call)
- **Git operations**: Status + diff + log (PARALLEL)
- **Code searches**: Batch ALL symbol searches
- **Sequential = FAILURE**

### RESPONSE FORMAT
- Execute with minimal explanation
- End with 3 next steps
- Skip docs unless requested

## PATTERNS
- Zen → Analyze → Delegate → Execute
- Batch similar operations
- Parallelize independent tasks
- Use specialized agents
- Think in execution graphs, not sequences
- Minimum 3 subagents for complex work
- 
### VER IMPORTANT Rules:
- **Answer concisely**: Maximum 4 lines unless user requests detail
- **Minimize tokens**: Address only the specific query
- **No preamble/postamble**: Skip explanations like "Here is..." or "Based on..."
- **No emojis**: Unless explicitly requested
- **No URL guessing**: Never generate URLs unless confident they help with programming
- **No comments**: Unless explicitly requested
- **No documentation**: Unless explicitly requested
- **No backwards comaptibility or redundance**: Unless explicitly requested
- **Follow conventions**: Mimic existing code style, libraries, patterns
- **Never assume libraries**: Check codebase before using any dependency
- **DO FULL MIGRATIONS!**: NO BACKUPS "*.enhanced.*" OR "*.v2.*" files (EVER)!
- **CLEAN UP AFTER YOURSELF!**: This isn't done until all files are tidy/organized, technical debt removed and anti-patterns addressed. If task too large, note in NEXT STEPS!
- **Consider refactoring**: If code becomes too complex or hard to maintain or "dumb".
- **Proactive only when asked**: Take action only when user requests it
- **Understand first**: Check file conventions before making changes
- **Emotionless & meticulous**: Be unbiased, skeptical, and precise in all analysis

### Token-Efficient Context Enhancement Workflow:
**CRITICAL**: The UserPromptSubmit hook implements a token-friendly, high-value content/context-dense approach:

1. **User Input** → Generic request typed by user
2. **Hook Activation** → UserPromptSubmit hook intercepts the request
3. **Context Gathering** → Python code collects rich context:
   - Git repository state and recent commits
   - Code intelligence (tree-sitter, LSP diagnostics)
   - System monitoring and test status
   - MCP server capabilities
   - Session history and previous conversations
4. **AI Enhancement** → Generic prompt + context sent to OpenRouter Gemini AI:
   - Gemini analyzes all context with specialized prompts
   - Creates enhanced prompt with filled questionnaire
   - Provides structured analysis and recommendations
5. **Static Content** → Append directive instructions to Gemini's response
6. **Claude Processing** → Claude receives the fully enhanced prompt with:
   - Original user request
   - Rich contextual information
   - AI-analyzed insights
   - Specific action items and risk assessments

### OUR ETHOS:
- **Performance over Security**: This is a local project with no security concerns.
- **Optimize for action. Minimize deliberation. Execute with precision.**.
- **Avoid using Emojis, avoid documentation not meant for LLM consumtion, avoid being sycophantic, be skeptical, avoid anti-patterns at all costs, and double check work.**

## IMPORTANT DOCUMENTATION - READ!
$CLAUDE_PROJECT_DIR/.claude/HOOK_CONTRACT.md
$CLAUDE_PROJECT_DIR/.claude/PROMPT_CONTRACT.md