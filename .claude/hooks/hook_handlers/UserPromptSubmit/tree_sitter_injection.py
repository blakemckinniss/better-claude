"""Tree-sitter MCP injection for enhanced AST-based code analysis.

This module analyzes prompts and injects tree-sitter tool recommendations,
queries, and strategies to help Claude leverage tree-sitter MCP effectively.
"""

import re
from typing import List, Tuple


class TreeSitterInjector:
    """Generates tree-sitter MCP recommendations based on prompt analysis."""
    
    def __init__(self):
        self.project_name = "better-claude"
        
        # Tree-sitter query templates by intent
        self.query_templates = {
            "find_functions": {
                "python": "(function_definition name: (identifier) @name) @func",
                "javascript": "(function_declaration name: (identifier) @name) @func",
                "typescript": "[(function_declaration name: (identifier) @name) (method_definition key: (property_identifier) @name)] @func",
                "go": "(function_declaration name: (identifier) @name) @func"
            },
            "find_classes": {
                "python": "(class_definition name: (identifier) @name) @class",
                "javascript": "(class_declaration name: (identifier) @name) @class",
                "typescript": "(class_declaration name: (identifier) @name) @class",
                "java": "(class_declaration name: (identifier) @name) @class"
            },
            "find_imports": {
                "python": "[(import_statement) (import_from_statement)] @import",
                "javascript": "[(import_statement) (export_statement)] @import",
                "go": "(import_declaration) @import",
                "rust": "(use_declaration) @import"
            },
            "find_error_handling": {
                "python": "(try_statement) @try",
                "javascript": "(try_statement) @try",
                "go": '(if_statement condition: (binary_expression left: (identifier) @err (#eq? @err "err"))) @error_check',
                "rust": "(match_expression) @match"
            },
            "find_tests": {
                "python": '(function_definition name: (identifier) @name (#match? @name "^test")) @test',
                "javascript": '(call_expression function: (identifier) @func (#match? @func "^(test|it|describe)")) @test',
                "go": '(function_declaration name: (identifier) @name (#match? @name "^Test")) @test',
                "rust": '#[test] @test_attr'
            },
            "find_todos": {
                "all": '(comment) @comment (#match? @comment "(TODO|FIXME|XXX|HACK|BUG)")'
            },
            "find_long_functions": {
                "all": '(function_definition body: (block) @body (#match? @body ".{500,}")) @long_func'
            },
            "find_nested_conditions": {
                "all": "(if_statement condition: (if_statement)) @nested"
            }
        }
        
        # Intent patterns
        self.intent_patterns = {
            "refactor": {
                "patterns": [r"refactor", r"improve", r"clean", r"optimize", r"restructure", r"simplify"],
                "suggested_queries": ["find_long_functions", "find_nested_conditions", "find_todos"],
                "tools": ["find_similar_code", "analyze_complexity", "get_symbols_overview"]
            },
            "debug": {
                "patterns": [r"debug", r"bug", r"error", r"issue", r"problem", r"fix", r"broken", r"failing"],
                "suggested_queries": ["find_error_handling", "find_functions", "find_tests"],
                "tools": ["find_symbol", "find_referencing_symbols", "get_dependencies"]
            },
            "implement": {
                "patterns": [r"implement", r"add", r"create", r"build", r"feature", r"new", r"develop"],
                "suggested_queries": ["find_classes", "find_functions", "find_imports"],
                "tools": ["get_symbols_overview", "find_similar_code", "get_file_contents"]
            },
            "analyze": {
                "patterns": [r"analyze", r"understand", r"explain", r"how does", r"what does", r"explore"],
                "suggested_queries": ["find_functions", "find_classes", "find_imports"],
                "tools": ["get_ast", "get_symbols_overview", "analyze_complexity"]
            },
            "test": {
                "patterns": [r"test", r"coverage", r"unit test", r"integration test", r"e2e", r"pytest", r"jest"],
                "suggested_queries": ["find_tests", "find_functions", "find_classes"],
                "tools": ["find_symbol", "find_referencing_symbols", "analyze_complexity"]
            },
            "navigate": {
                "patterns": [r"find", r"where", r"locate", r"search", r"go to", r"jump to", r"definition"],
                "suggested_queries": ["find_functions", "find_classes", "find_imports"],
                "tools": ["find_symbol", "find_referencing_symbols", "search_for_pattern"]
            }
        }
        
        # Language detection patterns
        self.language_patterns = {
            "python": r"\.py\b|python|def\s|class\s|import\s|from\s.*import|__init__|self\.|pip|pytest",
            "javascript": r"\.js\b|javascript|function\s|const\s|let\s|var\s|=>\s|npm|node|react",
            "typescript": r"\.ts\b|typescript|interface\s|type\s|:\s*\w+\s*=|enum\s|namespace"
        }
        
    def detect_intent(self, prompt: str) -> Tuple[str, float]:
        """Detect the primary intent from the prompt."""
        prompt_lower = prompt.lower()
        intent_scores = {}
        
        for intent, config in self.intent_patterns.items():
            score = 0
            for pattern in config["patterns"]:
                matches = len(re.findall(pattern, prompt_lower))
                score += matches
            
            if score > 0:
                intent_scores[intent] = score
                
        if not intent_scores:
            return "analyze", 0.5  # Default intent
            
        # Get highest scoring intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        confidence = best_intent[1] / sum(intent_scores.values()) if sum(intent_scores.values()) > 0 else 0
        
        return best_intent[0], confidence
        
    def detect_languages(self, prompt: str) -> List[str]:
        """Detect programming languages mentioned in the prompt."""
        detected = []
        
        for lang, pattern in self.language_patterns.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                detected.append(lang)
                
        # Default to Python if no language detected
        if not detected:
            detected = ["python"]
            
        return detected
        
    def extract_file_paths(self, prompt: str) -> List[str]:
        """Extract file paths mentioned in the prompt."""
        # Common file path patterns
        patterns = [
            r'(?:^|[\s"\'])([\w\-/]+\.(?:py|js|ts|go|rs|java|cpp|c|h))(?:$|[\s"\'])',
            r'(?:file|path):\s*([^\s]+)',
            r'in\s+([^\s]+\.(?:py|js|ts|go|rs|java|cpp|c|h))'
        ]
        
        files = []
        for pattern in patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            files.extend(matches)
            
        return list(set(files))  # Remove duplicates
        
    def extract_symbols(self, prompt: str) -> List[Tuple[str, str]]:
        """Extract function/class names mentioned in the prompt.
        
        Returns: List of (symbol_name, symbol_type) tuples
        """
        symbols = []
        
        # Function patterns
        func_patterns = [
            r'function\s+(\w+)',
            r'def\s+(\w+)',
            r'func\s+(\w+)',
            r'method\s+(\w+)',
            r'(\w+)\s*\(\s*\)\s*{',  # JS-style functions
            r'(\w+)\s+function',
            r'the\s+(\w+)\s+function',
        ]
        
        for pattern in func_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                symbols.append((match, "function"))
                
        # Class patterns
        class_patterns = [
            r'class\s+(\w+)',
            r'type\s+(\w+)',
            r'struct\s+(\w+)',
            r'interface\s+(\w+)',
            r'the\s+(\w+)\s+class',
        ]
        
        for pattern in class_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                symbols.append((match, "class"))
                
        return symbols
        
    def generate_tool_recommendations(self, intent: str, languages: List[str], files: List[str], symbols: List[Tuple[str, str]]) -> str:
        """Generate specific tree-sitter tool recommendations."""
        recommendations = []
        
        # Get tools for the intent
        intent_config = self.intent_patterns.get(intent, {})
        suggested_tools = intent_config.get("tools", [])
        
        # Tool-specific recommendations
        if "find_symbol" in suggested_tools and symbols:
            for symbol_name, symbol_type in symbols[:3]:  # Limit to first 3
                recommendations.append(
                    f'mcp__tree_sitter__find_symbol(name_path="{symbol_name}", '
                    f'include_body=True, depth=1)'
                )
                
        if "get_symbols_overview" in suggested_tools and files:
            for file_path in files[:2]:  # Limit to first 2 files
                recommendations.append(
                    f'mcp__tree_sitter__get_symbols_overview(relative_path="{file_path}")'
                )
                
        if "analyze_complexity" in suggested_tools:
            recommendations.append(
                'mcp__tree_sitter__analyze_complexity(project="better-claude", file_path=<target_file>)'
            )
            
        if "find_similar_code" in suggested_tools:
            recommendations.append(
                'mcp__tree_sitter__find_similar_code(project="better-claude", snippet=<code_snippet>, threshold=0.7)'
            )
            
        if "get_ast" in suggested_tools:
            recommendations.append(
                'mcp__tree_sitter__get_ast(project="better-claude", path=<file_path>, max_depth=3)'
            )
            
        return "\n".join(f"- {rec}" for rec in recommendations) if recommendations else ""
        
    def generate_queries(self, intent: str, languages: List[str]) -> str:
        """Generate tree-sitter queries based on intent and languages."""
        intent_config = self.intent_patterns.get(intent, {})
        suggested_queries = intent_config.get("suggested_queries", [])
        
        queries = []
        
        for query_type in suggested_queries:
            if query_type in self.query_templates:
                query_config = self.query_templates[query_type]
                
                # Get queries for detected languages
                for lang in languages:
                    if lang in query_config:
                        query = query_config[lang]
                        queries.append(f"{lang}: {query}")
                    elif "all" in query_config:
                        query = query_config["all"]
                        queries.append(f"{lang}: {query}")
                        
        return "\n".join(queries) if queries else ""
        
    def generate_workflow_suggestion(self, intent: str, confidence: float) -> str:
        """Generate a suggested workflow based on intent."""
        workflows = {
            "refactor": """1. Use get_symbols_overview to understand file structure
2. Run find_long_functions query to identify complexity
3. Use analyze_complexity for detailed metrics
4. Apply find_similar_code to detect duplication
5. Use find_referencing_symbols before making changes""",
            
            "debug": """1. Use find_symbol to locate the problematic function
2. Run find_referencing_symbols to trace usage
3. Check get_dependencies for import issues
4. Use get_ast to examine code structure
5. Search for error handling patterns nearby""",
            
            "implement": """1. Use get_symbols_overview on related files
2. Find similar implementations with find_similar_code
3. Check existing patterns with run_query
4. Use find_symbol to navigate to insertion points
5. Verify integration with find_referencing_symbols""",
            
            "analyze": """1. Start with get_symbols_overview for file structure
2. Use get_ast for detailed structural analysis
3. Run analyze_complexity on key functions
4. Use run_query for specific pattern searches
5. Check get_dependencies for relationships""",
            
            "test": """1. Use find_tests query to locate existing tests
2. Find functions to test with find_functions query
3. Check complexity with analyze_complexity
4. Use find_referencing_symbols for test coverage
5. Search for untested edge cases""",
            
            "navigate": """1. Use find_symbol with target name
2. Check find_referencing_symbols for usage
3. Use get_symbols_overview for context
4. Navigate with get_node_at_position
5. Explore relationships with get_dependencies"""
        }
        
        if intent in workflows and confidence > 0.7:
            return workflows[intent]
        return ""


def create_tree_sitter_injection(prompt: str) -> str:
    """Generate tree-sitter analysis injection for UserPromptSubmit hook."""
    injector = TreeSitterInjector()
    
    # Analyze prompt
    intent, confidence = injector.detect_intent(prompt)
    languages = injector.detect_languages(prompt)
    files = injector.extract_file_paths(prompt)
    symbols = injector.extract_symbols(prompt)
    
    # Build injection parts
    injection_parts = []
    
    # Intent and confidence
    injection_parts.append(
        f"<tree-sitter-analysis>\n"
        f"Intent: {intent} (confidence: {confidence:.2f})\n"
        f"Languages: {', '.join(languages)}\n"
    )
    
    # File and symbol context
    if files:
        injection_parts.append(f"Files mentioned: {', '.join(files)}")
    if symbols:
        symbol_list = ", ".join(f"{name} ({type_})" for name, type_ in symbols[:5])
        injection_parts.append(f"Symbols mentioned: {symbol_list}")
        
    injection_parts.append("</tree-sitter-analysis>")
    
    # Tool recommendations
    tool_recs = injector.generate_tool_recommendations(intent, languages, files, symbols)
    if tool_recs:
        injection_parts.append(
            f"\n<tree-sitter-tools>\n"
            f"Recommended tree-sitter MCP tools:\n{tool_recs}\n"
            f"</tree-sitter-tools>"
        )
        
    # Query suggestions
    queries = injector.generate_queries(intent, languages)
    if queries:
        injection_parts.append(
            f"\n<tree-sitter-queries>\n"
            f"Suggested tree-sitter queries:\n{queries}\n"
            f"</tree-sitter-queries>"
        )
        
    # Workflow suggestion
    workflow = injector.generate_workflow_suggestion(intent, confidence)
    if workflow:
        injection_parts.append(
            f"\n<tree-sitter-workflow>\n"
            f"Suggested workflow:\n{workflow}\n"
            f"</tree-sitter-workflow>"
        )
        
    # Advanced features hint
    if len(languages) > 1:
        injection_parts.append(
            "\n<tree-sitter-advanced>\n"
            "Multiple languages detected! Consider:\n"
            "- Cross-language pattern analysis\n"
            "- Consistent API design verification\n"
            "- Shared architectural patterns\n"
            "</tree-sitter-advanced>"
        )
        
    return "\n".join(injection_parts) + "\n" if injection_parts else ""


def get_tree_sitter_hints(prompt: str) -> str:
    """Generate contextual hints for tree-sitter usage."""
    hints = []
    
    # Pattern-based hints
    if re.search(r"structure|organization|architecture|layout", prompt, re.IGNORECASE):
        hints.append(
            "💡 Tree-sitter can map entire codebases:\n"
            "   - get_symbols_overview: File structure view\n"
            "   - analyze_project: Full project analysis\n"
            "   - get_ast: Deep structural insights"
        )
        
    if re.search(r"performance|slow|optimize|complexity", prompt, re.IGNORECASE):
        hints.append(
            "⚡ Tree-sitter complexity analysis:\n"
            "   - analyze_complexity: Beyond cyclomatic\n"
            "   - find_long_functions: Identify hotspots\n"
            "   - find_similar_code: Detect duplication"
        )
        
    if re.search(r"pattern|similar|duplicate|copy", prompt, re.IGNORECASE):
        hints.append(
            "🔍 Tree-sitter pattern matching:\n"
            "   - find_similar_code: Structural similarity\n"
            "   - run_query: Custom pattern search\n"
            "   - Cross-language pattern detection"
        )
        
    return "\n\n".join(hints) + "\n" if hints else ""


# Convenience functions for backward compatibility
def create_tree_sitter_enhanced_injection(prompt: str) -> str:
    """Alias for create_tree_sitter_injection."""
    return create_tree_sitter_injection(prompt)


def get_ast_navigation_hints(prompt: str) -> str:
    """Alias for get_tree_sitter_hints."""
    return get_tree_sitter_hints(prompt)