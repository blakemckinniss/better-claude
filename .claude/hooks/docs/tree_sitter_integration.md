# Tree-Sitter MCP Integration Guide

This guide explains how to leverage tree-sitter MCP tools in your hook handlers for advanced AST-based code analysis.

## Overview

The tree-sitter MCP integration enhances your hook system with powerful AST (Abstract Syntax Tree) analysis capabilities that go beyond traditional text-based analysis:

- **Language-agnostic AST analysis** - Works across Python, JavaScript, Go, Rust, etc.
- **Semantic code search** - Find code by structure, not just text patterns
- **Cross-language pattern detection** - Identify similar patterns across different languages
- **Intelligent context extraction** - Get semantically related code, not just line-based context

## Integration with Hook System

The tree-sitter enhanced module is automatically integrated into the UserPromptSubmit hook. It provides:

1. **Intent Detection** - Analyzes user prompts to understand if they're refactoring, debugging, implementing, or analyzing code
2. **Language Detection** - Identifies programming languages mentioned in the prompt
3. **Query Suggestions** - Provides relevant tree-sitter queries based on the detected intent
4. **Navigation Hints** - Suggests appropriate tree-sitter tools for the task at hand

## Key Features

### 1. Semantic Code Search

Unlike text-based search, tree-sitter queries find code by its structure:

```python
# Find all error handling blocks
query = "(try_statement) @try"

# Find functions with specific naming patterns
query = '(function_definition name: (identifier) @name (#match? @name "^test"))'

# Find nested conditionals (code smell)
query = "(if_statement condition: (if_statement))"
```

### 2. Cross-Language Pattern Analysis

Detect similar patterns across different languages:

```python
# Find singleton patterns in Python, JavaScript, and Go
patterns = enhancer.find_cross_language_patterns("singleton")

# Find factory methods across languages
patterns = enhancer.find_cross_language_patterns("factory")

# Find error handling patterns
patterns = enhancer.find_cross_language_patterns("error_handling")
```

### 3. AST-Based Code Quality Analysis

Get deep structural insights:

```python
# Analyze code structure quality
quality = enhancer.analyze_code_structure_quality("src/main.py")
# Returns: max_ast_depth, node_type_distribution, structural_patterns, complexity_hotspots

# Get semantic context around a symbol
context = enhancer.get_symbol_context_window("src/main.py", "process_data", context_size=3)
# Returns: parent scope, sibling methods, dependencies
```

## Example Use Cases

### 1. Refactoring Detection

When a user mentions "refactor", "improve", "clean", or "optimize", the hook automatically suggests:
- Finding long functions with tree-sitter queries
- Detecting nested conditionals
- Identifying duplicate patterns using similarity analysis

### 2. Debugging Assistance

When debugging keywords are detected, the hook provides:
- Error handling pattern queries
- Null check detection queries
- Function call tracing queries

### 3. Multi-Language Projects

For projects with multiple languages, the hook:
- Detects all languages mentioned
- Suggests cross-language consistency checks
- Helps maintain architectural patterns across languages

## Available Tree-Sitter MCP Tools

The integration uses these tree-sitter MCP tools:

1. **find_symbol** - Navigate to functions, classes, methods by name
2. **get_ast** - Get full AST structure for deep analysis
3. **run_query** - Execute tree-sitter queries for semantic search
4. **find_similar_code** - Find structurally similar code patterns
5. **analyze_complexity** - Get complexity metrics beyond cyclomatic
6. **get_dependencies** - Analyze import relationships
7. **get_symbols_overview** - High-level file structure view

## How It Works

The tree-sitter injection module (`tree_sitter_injection.py`) analyzes user prompts and provides:

1. **Intent Detection** - Identifies what the user is trying to do (refactor, debug, implement, analyze, test, navigate)
2. **Language Detection** - Recognizes programming languages mentioned
3. **Symbol Extraction** - Finds function and class names mentioned
4. **File Path Extraction** - Identifies specific files referenced
5. **Tool Recommendations** - Suggests specific tree-sitter MCP tools with parameters
6. **Query Generation** - Provides language-specific tree-sitter queries
7. **Workflow Suggestions** - Offers step-by-step approaches for the detected intent

## Configuration

The tree-sitter injection is automatically integrated into the UserPromptSubmit hook. No additional configuration is needed - it will activate when appropriate based on the user's prompt

## Best Practices

1. **Use for Structural Analysis** - Tree-sitter excels at understanding code structure, not just text
2. **Combine with Existing Analyzers** - Tree-sitter complements, not replaces, existing code smell and dependency analyzers
3. **Language-Aware Queries** - Use language-specific queries for best results
4. **Performance Consideration** - AST analysis is more intensive than text search; use judiciously

## Example Hook Response

When a user asks about refactoring, the hook might inject:

```xml
<tree-sitter-intent>Detected intent: refactor</tree-sitter-intent>
<tree-sitter-languages>Detected languages: python, javascript</tree-sitter-languages>
<tree-sitter-queries>
Suggested tree-sitter queries for refactoring:
- Find long functions: (function_definition body: (block) @body (#match? @body ".{500,}"))
- Find nested conditionals: (if_statement condition: (if_statement))
- Find duplicate patterns: Use find_similar_code with threshold 0.8
</tree-sitter-queries>
<tree-sitter-cross-language>
Multiple languages detected. Tree-sitter can analyze patterns across languages:
- Consistent error handling patterns
- Similar architectural patterns (singleton, factory, etc.)
- Cross-language API consistency
</tree-sitter-cross-language>
```

This enhanced context helps Claude understand the codebase structure better and provide more accurate assistance.