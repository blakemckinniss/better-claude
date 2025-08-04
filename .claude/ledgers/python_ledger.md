# Python File Registry & Justification Ledger

This ledger enforces anti-debt by requiring documentation before Python file creation or renaming. All Python files must be registered here with proper justification.

## Registration Format
```
### filename.py
- **Purpose**: Brief description of file's responsibility
- **Justification**: Why this file needs to exist independently
- **Dependencies**: Key modules/files this interacts with
- **Anti-debt**: How this prevents code debt/duplication
```

---

## Core Hook System Files

### hook_handler.py
- **Purpose**: Main hook orchestration and routing system
- **Justification**: Central coordination point for all hook operations
- **Dependencies**: All hook_handlers modules, logging, config
- **Anti-debt**: Single entry point prevents scattered hook logic

### hook_logger.py
- **Purpose**: Centralized logging system for all hook operations
- **Justification**: Consistent logging interface across all hooks
- **Dependencies**: Standard logging, formatting utilities
- **Anti-debt**: Prevents duplicate logging implementations

### posttooluse_verification.py
- **Purpose**: Post-execution validation and verification system
- **Justification**: Ensures tool execution meets quality standards
- **Dependencies**: Hook handlers, validation modules
- **Anti-debt**: Centralized validation prevents scattered checks

## PreToolUse Hook Handlers

### command_validator.py
- **Purpose**: Validates command syntax and parameters before execution
- **Justification**: Prevents execution of malformed or dangerous commands
- **Dependencies**: regex, command parsing utilities
- **Anti-debt**: Single validation point prevents duplicate validation logic

### dependency_analyzer.py
- **Purpose**: Analyzes dependencies and potential conflicts before tool use
- **Justification**: Prevents dependency conflicts and circular imports
- **Dependencies**: AST parsing, import analysis
- **Anti-debt**: Centralized dependency analysis prevents scattered checks

### git_validator.py
- **Purpose**: Validates git operations and repository state
- **Justification**: Ensures git operations are safe and properly sequenced
- **Dependencies**: git commands, repository state checking
- **Anti-debt**: Single git validation point prevents inconsistent git handling

### operation_logger.py
- **Purpose**: Logs all tool operations with detailed context
- **Justification**: Provides audit trail and debugging information
- **Dependencies**: logging, operation context tracking
- **Anti-debt**: Centralized operation logging prevents scattered logging

### path_validator.py
- **Purpose**: Validates file paths and permissions before operations
- **Justification**: Prevents operations on invalid or restricted paths
- **Dependencies**: pathlib, permission checking
- **Anti-debt**: Single path validation prevents duplicate path logic

### pattern_detector.py
- **Purpose**: Detects potentially problematic patterns in tool usage
- **Justification**: Proactive detection of anti-patterns and issues
- **Dependencies**: pattern matching, heuristic analysis
- **Anti-debt**: Early pattern detection prevents accumulation of problems

### python_creation_blocker.py
- **Purpose**: Blocks Python file creation/rename without ledger registration
- **Justification**: Enforces documentation-first approach for Python files
- **Dependencies**: ledger parsing, file path analysis
- **Anti-debt**: Prevents undocumented Python files that become technical debt

### read_blocker.py
- **Purpose**: Blocks unnecessary read operations to conserve tokens
- **Justification**: Enforces token-efficient alternatives to Read tool
- **Dependencies**: command suggestion, token optimization
- **Anti-debt**: Prevents wasteful token usage patterns

## PostToolUse Hook Handlers

### context_capture.py
- **Purpose**: Captures execution context and results for analysis
- **Justification**: Provides rich context for post-execution analysis
- **Dependencies**: execution monitoring, context serialization
- **Anti-debt**: Centralized context capture prevents lost execution information

### diagnostics.py
- **Purpose**: Runs diagnostic checks after tool execution
- **Justification**: Identifies issues and potential improvements
- **Dependencies**: diagnostic utilities, health checks
- **Anti-debt**: Systematic diagnostics prevent undetected issues

### educational_feedback.py
- **Purpose**: Provides learning-focused feedback on tool usage
- **Justification**: Improves user understanding and tool usage patterns
- **Dependencies**: feedback generation, pattern analysis
- **Anti-debt**: Educational approach prevents repeated mistakes

### educational_feedback_enhanced.py
- **Purpose**: Enhanced version with deeper analysis capabilities
- **Justification**: Provides more sophisticated feedback and insights
- **Dependencies**: advanced analysis, ML-based insights
- **Anti-debt**: Sophisticated analysis prevents subtle issues

### educational_feedback_optimized.py
- **Purpose**: Performance-optimized version for high-frequency usage
- **Justification**: Maintains feedback quality while minimizing overhead
- **Dependencies**: optimized algorithms, caching
- **Anti-debt**: Performance optimization prevents feedback system becoming bottleneck

### feedback_service_layer.py
- **Purpose**: Service layer abstraction for feedback systems
- **Justification**: Provides clean interface between feedback components
- **Dependencies**: service abstractions, dependency injection
- **Anti-debt**: Service layer prevents tight coupling between feedback components

### formatters.py
- **Purpose**: Formats output and feedback for consistent presentation
- **Justification**: Ensures consistent, readable output across all feedback
- **Dependencies**: formatting utilities, template engines
- **Anti-debt**: Centralized formatting prevents inconsistent output styles

### performance_optimized_feedback.py
- **Purpose**: High-performance feedback system for production use
- **Justification**: Provides feedback without impacting system performance
- **Dependencies**: performance monitoring, efficient algorithms
- **Anti-debt**: Performance focus prevents feedback from becoming overhead

### performance_validation.py
- **Purpose**: Validates performance characteristics after tool execution
- **Justification**: Ensures operations meet performance requirements
- **Dependencies**: performance metrics, validation thresholds
- **Anti-debt**: Performance validation prevents performance regression

### python_auto_fixer.py
- **Purpose**: Automatically fixes common Python issues after execution
- **Justification**: Reduces manual intervention for common problems
- **Dependencies**: AST manipulation, code fixing utilities
- **Anti-debt**: Automatic fixing prevents accumulation of minor issues

### run_tests.py
- **Purpose**: Executes relevant tests after code changes
- **Justification**: Ensures changes don't break existing functionality
- **Dependencies**: test runners, test discovery
- **Anti-debt**: Automatic testing prevents undetected regressions

### session_tracker.py
- **Purpose**: Tracks session state and execution history
- **Justification**: Provides context for session-aware optimizations
- **Dependencies**: session management, state persistence
- **Anti-debt**: Session tracking prevents loss of important context

### test_educational_feedback.py
- **Purpose**: Tests for educational feedback system
- **Justification**: Ensures feedback system reliability and correctness
- **Dependencies**: pytest, feedback system components
- **Anti-debt**: Testing prevents feedback system regressions

### test_feedback.py
- **Purpose**: Core tests for feedback functionality
- **Justification**: Validates feedback system behavior
- **Dependencies**: pytest, mock utilities
- **Anti-debt**: Core testing prevents fundamental feedback issues

### test_framework.py
- **Purpose**: Testing framework and utilities for hook system
- **Justification**: Provides consistent testing approach across all hooks
- **Dependencies**: pytest, testing utilities
- **Anti-debt**: Unified testing framework prevents inconsistent test approaches

### test_performance.py
- **Purpose**: Performance tests for hook system components
- **Justification**: Ensures hook system doesn't degrade performance
- **Dependencies**: performance testing tools, benchmarking
- **Anti-debt**: Performance testing prevents performance debt accumulation

### test_shared_intelligence.py
- **Purpose**: Tests for shared intelligence system
- **Justification**: Validates cross-component intelligence sharing
- **Dependencies**: pytest, intelligence system components
- **Anti-debt**: Intelligence system testing prevents knowledge silos

### validators.py
- **Purpose**: Common validation utilities for post-execution checks
- **Justification**: Provides reusable validation logic across components
- **Dependencies**: validation libraries, check implementations
- **Anti-debt**: Shared validators prevent duplicate validation code

## SessionStart Hook Handlers

### context_gatherer.py
- **Purpose**: Gathers initial context at session start
- **Justification**: Provides rich initial context for optimal session behavior
- **Dependencies**: system monitoring, context collection
- **Anti-debt**: Rich initial context prevents suboptimal early decisions

### git_operations.py
- **Purpose**: Git-specific operations for session initialization
- **Justification**: Ensures proper git context at session start
- **Dependencies**: git commands, repository analysis
- **Anti-debt**: Proper git initialization prevents git-related issues

### output_formatters.py
- **Purpose**: Formats session start output and information
- **Justification**: Provides consistent, informative session start experience
- **Dependencies**: formatting utilities, template systems
- **Anti-debt**: Consistent formatting improves user experience

### performance_benchmark.py
- **Purpose**: Benchmarks system performance at session start
- **Justification**: Establishes performance baseline for optimization
- **Dependencies**: benchmarking tools, performance metrics
- **Anti-debt**: Performance baseline enables optimization decisions

### session_validator.py
- **Purpose**: Validates session state and requirements at startup
- **Justification**: Ensures session is properly configured before work begins
- **Dependencies**: validation utilities, system checks
- **Anti-debt**: Session validation prevents issues from improper setup

## UserPromptSubmit Hook Handlers

### ai_context_optimizer_optimized.py
- **Purpose**: Optimized AI context enhancement for user prompts
- **Justification**: Maximizes AI effectiveness while minimizing token usage
- **Dependencies**: AI services, context optimization algorithms
- **Anti-debt**: Context optimization prevents wasteful AI usage

### config_reloader.py
- **Purpose**: Reloads configuration when user submits prompts
- **Justification**: Ensures latest configuration is active for prompt processing
- **Dependencies**: configuration management, file watching
- **Anti-debt**: Dynamic config reloading prevents stale configuration issues

### context_manager.py
- **Purpose**: Manages context accumulation and optimization
- **Justification**: Provides intelligent context management for better responses
- **Dependencies**: context storage, optimization algorithms
- **Anti-debt**: Smart context management prevents context bloat

### context_revival.py
- **Purpose**: Revives and reconstructs lost or stale context
- **Justification**: Maintains context continuity across sessions
- **Dependencies**: context serialization, revival algorithms
- **Anti-debt**: Context revival prevents loss of important information

### firecrawl_injection.py
- **Purpose**: Injects web content via Firecrawl for enhanced context
- **Justification**: Provides real-time web information for better responses
- **Dependencies**: Firecrawl API, content processing
- **Anti-debt**: Real-time web data prevents outdated information issues

### git_injection.py
- **Purpose**: Injects git context into user prompt processing
- **Justification**: Provides repository context for code-related prompts
- **Dependencies**: git operations, context injection
- **Anti-debt**: Git context injection prevents uninformed code decisions

### http_session_manager.py
- **Purpose**: Manages HTTP sessions for external service integration
- **Justification**: Provides efficient, persistent connections to external services
- **Dependencies**: HTTP libraries, session management
- **Anti-debt**: Session management prevents connection overhead

### logging_config.py
- **Purpose**: Configures logging for user prompt processing
- **Justification**: Ensures proper logging during complex prompt processing
- **Dependencies**: logging configuration, format specifications
- **Anti-debt**: Proper logging configuration prevents debugging difficulties

### mcp_injector.py
- **Purpose**: Injects MCP (Model Context Protocol) data into prompts
- **Justification**: Enhances prompts with structured context data
- **Dependencies**: MCP protocols, data injection utilities
- **Anti-debt**: Structured context injection prevents context fragmentation

### path_utils.py
- **Purpose**: Path manipulation utilities for prompt processing
- **Justification**: Provides consistent path handling across prompt processing
- **Dependencies**: pathlib, path manipulation utilities
- **Anti-debt**: Centralized path utilities prevent path handling inconsistencies

### performance_monitor.py
- **Purpose**: Monitors performance during prompt processing
- **Justification**: Identifies performance bottlenecks in prompt enhancement
- **Dependencies**: performance monitoring, metrics collection
- **Anti-debt**: Performance monitoring prevents performance degradation

### session_state.py
- **Purpose**: Manages session state during prompt processing
- **Justification**: Maintains consistency and continuity across prompt processing
- **Dependencies**: state management, persistence utilities
- **Anti-debt**: Session state management prevents state inconsistencies

### static_content.py
- **Purpose**: Manages static content injection into enhanced prompts
- **Justification**: Provides consistent, reusable content for prompt enhancement
- **Dependencies**: content management, template systems
- **Anti-debt**: Static content management prevents content duplication

### system_monitor.py
- **Purpose**: Monitors system resources during prompt processing
- **Justification**: Ensures prompt processing doesn't overwhelm system
- **Dependencies**: system monitoring, resource tracking
- **Anti-debt**: System monitoring prevents resource exhaustion

### unified_smart_advisor.py
- **Purpose**: Provides intelligent advisory services for prompt enhancement
- **Justification**: Offers smart recommendations and optimizations
- **Dependencies**: AI services, recommendation engines
- **Anti-debt**: Smart advisory prevents suboptimal prompt handling

## Shared Intelligence System

### anti_pattern_detector.py
- **Purpose**: Detects anti-patterns across the entire hook system
- **Justification**: Proactive identification of systemic issues
- **Dependencies**: pattern analysis, machine learning
- **Anti-debt**: Anti-pattern detection prevents systemic debt accumulation

### intelligent_router.py
- **Purpose**: Intelligently routes operations to optimal handlers
- **Justification**: Ensures operations are handled by the most appropriate component
- **Dependencies**: routing logic, performance metrics
- **Anti-debt**: Intelligent routing prevents suboptimal operation handling

### performance_optimizer.py
- **Purpose**: Optimizes performance across the entire system
- **Justification**: Maintains system performance as complexity grows
- **Dependencies**: performance analysis, optimization algorithms
- **Anti-debt**: System-wide optimization prevents performance debt

### recommendation_engine.py
- **Purpose**: Provides recommendations for system improvements
- **Justification**: Guides system evolution and optimization
- **Dependencies**: analytics, recommendation algorithms
- **Anti-debt**: Recommendation system prevents stagnation and debt accumulation

## Other Essential Files

### logger_integration.py
- **Purpose**: Integrates logging across all hook components
- **Justification**: Provides unified logging strategy and implementation
- **Dependencies**: logging frameworks, integration utilities
- **Anti-debt**: Unified logging prevents fragmented logging approaches

### monitor_logging.py
- **Purpose**: Monitors logging system health and performance
- **Justification**: Ensures logging system remains effective and efficient
- **Dependencies**: monitoring tools, logging analysis
- **Anti-debt**: Logging monitoring prevents logging system degradation

### performance_metrics.py
- **Purpose**: Collects and analyzes performance metrics system-wide
- **Justification**: Provides data-driven insights for optimization
- **Dependencies**: metrics collection, analysis tools
- **Anti-debt**: Metrics collection enables informed optimization decisions

### performance_validation_report.py
- **Purpose**: Generates comprehensive performance validation reports
- **Justification**: Provides detailed performance analysis and recommendations
- **Dependencies**: reporting tools, validation frameworks
- **Anti-debt**: Performance reporting prevents performance issues from being ignored

### session_monitor.py
- **Purpose**: Monitors session health and behavior patterns
- **Justification**: Identifies session-level issues and optimization opportunities
- **Dependencies**: session tracking, monitoring utilities
- **Anti-debt**: Session monitoring prevents session-level problems

### test_performance.py
- **Purpose**: Performance testing for the entire hook system
- **Justification**: Validates system performance under various conditions
- **Dependencies**: performance testing frameworks, load testing
- **Anti-debt**: System performance testing prevents performance regressions

### test_production_validation.py
- **Purpose**: Production-level validation testing
- **Justification**: Ensures system meets production readiness standards
- **Dependencies**: production testing tools, validation frameworks
- **Anti-debt**: Production validation prevents production-specific issues

---

## Registration Rules

1. **All Python files must be registered** before creation or rename
2. **Purpose must be clear and specific** - avoid vague descriptions
3. **Justification must explain why file exists independently** - not just what it does
4. **Dependencies should list key interactions** - helps understand coupling
5. **Anti-debt explanation required** - how does this prevent technical debt?

## Exceptions

- `test_*.py` files in `.claude/tests/` are automatically allowed
- Files can be registered in batches if they serve related purposes
- Temporary files for experimentation should still be registered if they become permanent

## Maintenance

This ledger should be updated whenever:
- New Python files are added to the system
- Existing files are renamed or moved
- File purposes or responsibilities change significantly
- Anti-debt benefits are realized or modified