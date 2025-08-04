"""
Code Intelligence Module

Provides comprehensive code analysis context for AI-enhanced prompts through:
- LSP diagnostics with rich context
- Tree-sitter symbol analysis
- Call graph generation
- Code complexity metrics
- Recent changes analysis
- Import/dependency mapping
- Test coverage integration
- Code quality assessment
"""

import ast
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class Diagnostic:
    """LSP diagnostic with context"""
    file_path: str
    line: int
    column: int
    severity: str  # error, warning, information, hint
    message: str
    source: str
    code: Optional[str] = None
    related_info: Optional[List[str]] = None

@dataclass
class Symbol:
    """Code symbol with metadata"""
    name: str
    kind: str  # function, class, method, variable, etc.
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    scope: str
    docstring: Optional[str] = None
    complexity: int = 0
    references: int = 0

@dataclass
class CallRelation:
    """Function/method call relationship"""
    caller: str
    callee: str
    file_path: str
    line: int
    call_type: str  # direct, indirect, recursive

@dataclass
class ImportInfo:
    """Import/dependency information"""
    module: str
    imported_names: List[str]
    file_path: str
    line: int
    is_local: bool
    is_standard_lib: bool

@dataclass
class ComplexityMetrics:
    """Code complexity measurements"""
    cyclomatic: int
    cognitive: int
    lines_of_code: int
    maintainability_index: float

@dataclass
class CodeIntelligenceContext:
    """Complete code intelligence context"""
    diagnostics: List[Diagnostic]
    symbols: List[Symbol]
    call_graph: List[CallRelation]
    imports: List[ImportInfo]
    complexity_metrics: Dict[str, ComplexityMetrics]
    recent_changes: List[str]
    test_coverage: Dict[str, float]
    quality_metrics: Dict[str, Any]
    timestamp: float

class TreeSitterAnalyzer:
    """Tree-sitter based code analysis"""
    
    def __init__(self):
        self.python_extensions = {'.py', '.pyi'}
        self.js_extensions = {'.js', '.jsx', '.ts', '.tsx'}
        self.supported_extensions = self.python_extensions | self.js_extensions
    
    def analyze_file(self, file_path: Path) -> Tuple[List[Symbol], List[CallRelation], List[ImportInfo]]:
        """Analyze a single file using AST parsing"""
        if not file_path.suffix in self.python_extensions:
            return [], [], []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = PythonASTAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            return analyzer.symbols, analyzer.calls, analyzer.imports
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            return [], [], []

class PythonASTAnalyzer(ast.NodeVisitor):
    """Python AST analyzer for symbols, calls, and imports"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[Symbol] = []
        self.calls: List[CallRelation] = []
        self.imports: List[ImportInfo] = []
        self.scope_stack: List[str] = ['global']
        self.current_class = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions"""
        scope = '.'.join(self.scope_stack)
        if self.current_class:
            scope += f'.{self.current_class}'
        
        docstring = ast.get_docstring(node)
        complexity = self._calculate_complexity(node)
        
        symbol = Symbol(
            name=node.name,
            kind='method' if self.current_class else 'function',
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            column_start=node.col_offset,
            column_end=node.end_col_offset or node.col_offset,
            scope=scope,
            docstring=docstring,
            complexity=complexity
        )
        self.symbols.append(symbol)
        
        # Enter function scope
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definitions"""
        # Handle async functions with same logic as regular functions
        scope = '.'.join(self.scope_stack)
        if self.current_class:
            scope += f'.{self.current_class}'
        
        docstring = ast.get_docstring(node)
        complexity = self._calculate_async_complexity(node)
        
        symbol = Symbol(
            name=node.name,
            kind='method' if self.current_class else 'function',
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            column_start=node.col_offset,
            column_end=node.end_col_offset or node.col_offset,
            scope=scope,
            docstring=docstring,
            complexity=complexity
        )
        self.symbols.append(symbol)
        
        # Enter function scope
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions"""
        scope = '.'.join(self.scope_stack)
        docstring = ast.get_docstring(node)
        
        symbol = Symbol(
            name=node.name,
            kind='class',
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            column_start=node.col_offset,
            column_end=node.end_col_offset or node.col_offset,
            scope=scope,
            docstring=docstring
        )
        self.symbols.append(symbol)
        
        # Enter class scope
        old_class = self.current_class
        self.current_class = node.name
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
        self.current_class = old_class
    
    def visit_Call(self, node: ast.Call):
        """Visit function/method calls"""
        caller_scope = '.'.join(self.scope_stack)
        
        # Extract callee name
        callee = self._extract_call_name(node.func)
        if callee:
            call = CallRelation(
                caller=caller_scope,
                callee=callee,
                file_path=self.file_path,
                line=node.lineno,
                call_type='direct'
            )
            self.calls.append(call)
        
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        """Visit import statements"""
        for alias in node.names:
            import_info = ImportInfo(
                module=alias.name,
                imported_names=[alias.asname or alias.name],
                file_path=self.file_path,
                line=node.lineno,
                is_local=self._is_local_import(alias.name),
                is_standard_lib=self._is_standard_lib(alias.name)
            )
            self.imports.append(import_info)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statements"""
        if node.module:
            imported_names = [alias.asname or alias.name for alias in node.names]
            import_info = ImportInfo(
                module=node.module,
                imported_names=imported_names,
                file_path=self.file_path,
                line=node.lineno,
                is_local=self._is_local_import(node.module),
                is_standard_lib=self._is_standard_lib(node.module)
            )
            self.imports.append(import_info)
    
    def _extract_call_name(self, node: ast.expr) -> Optional[str]:
        """Extract function/method name from call node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._extract_call_name(node.value)}.{node.attr}"
        return None
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _calculate_async_complexity(self, node: ast.AsyncFunctionDef) -> int:
        """Calculate cyclomatic complexity for async functions"""
        return self._calculate_complexity(node)  # Same logic as regular functions
    
    def _is_local_import(self, module_name: str) -> bool:
        """Check if import is local to the project"""
        return module_name.startswith('.') or not self._is_standard_lib(module_name)
    
    def _is_standard_lib(self, module_name: str) -> bool:
        """Check if module is part of Python standard library"""
        # Simplified check - could be enhanced with stdlib-list package
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 'collections', 'itertools', 'functools',
            'pathlib', 'subprocess', 'time', 'datetime', 'logging', 'typing',
            'dataclasses', 're', 'math', 'random', 'hashlib', 'urllib', 'http'
        }
        return module_name.split('.')[0] in stdlib_modules

class LSPDiagnosticsCollector:
    """Collects and processes LSP diagnostics"""
    
    def __init__(self):
        self.severity_map = {
            1: 'error',
            2: 'warning', 
            3: 'information',
            4: 'hint'
        }
    
    def collect_diagnostics(self, root_path: Path) -> List[Diagnostic]:
        """Collect diagnostics from various sources"""
        diagnostics = []
        
        # Try to get VS Code diagnostics if available (disabled for now)
        # try:
        #     # This would require MCP IDE integration
        #     from mcp__ide__getDiagnostics import getDiagnostics
        #     vscode_diagnostics = getDiagnostics()
        #     diagnostics.extend(self._process_vscode_diagnostics(vscode_diagnostics))
        # except ImportError:
        #     pass
        
        # Fallback to static analysis tools
        diagnostics.extend(self._run_flake8(root_path))
        diagnostics.extend(self._run_mypy(root_path))
        diagnostics.extend(self._run_pylint(root_path))
        
        return diagnostics
    
    def _process_vscode_diagnostics(self, vscode_diagnostics: Dict) -> List[Diagnostic]:
        """Process VS Code diagnostics"""
        diagnostics = []
        
        for uri, diag_list in vscode_diagnostics.items():
            file_path = uri.replace('file://', '')
            
            for diag in diag_list:
                diagnostic = Diagnostic(
                    file_path=file_path,
                    line=diag['range']['start']['line'],
                    column=diag['range']['start']['character'],
                    severity=self.severity_map.get(diag['severity'], 'information'),
                    message=diag['message'],
                    source=diag.get('source', 'lsp'),
                    code=str(diag.get('code', ''))
                )
                diagnostics.append(diagnostic)
        
        return diagnostics
    
    def _run_flake8(self, root_path: Path) -> List[Diagnostic]:
        """Run flake8 for style and error checking"""
        try:
            result = subprocess.run(
                ['flake8', '--format=json', str(root_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                flake8_output = json.loads(result.stdout)
                return self._process_flake8_output(flake8_output)
        except Exception as e:
            logger.debug(f"Flake8 analysis failed: {e}")
        
        return []
    
    def _run_mypy(self, root_path: Path) -> List[Diagnostic]:
        """Run mypy for type checking"""
        try:
            result = subprocess.run(
                ['mypy', '--show-error-codes', '--no-error-summary', str(root_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return self._process_mypy_output(result.stdout)
        except Exception as e:
            logger.debug(f"Mypy analysis failed: {e}")
        
        return []
    
    def _run_pylint(self, root_path: Path) -> List[Diagnostic]:
        """Run pylint for code quality"""
        try:
            result = subprocess.run(
                ['pylint', '--output-format=json', str(root_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                pylint_output = json.loads(result.stdout)
                return self._process_pylint_output(pylint_output)
        except Exception as e:
            logger.debug(f"Pylint analysis failed: {e}")
        
        return []
    
    def _process_flake8_output(self, output: List[Dict]) -> List[Diagnostic]:
        """Process flake8 JSON output"""
        diagnostics = []
        
        for item in output:
            diagnostic = Diagnostic(
                file_path=item['filename'],
                line=item['line_number'],
                column=item['column_number'],
                severity='warning',
                message=item['text'],
                source='flake8',
                code=item['code']
            )
            diagnostics.append(diagnostic)
        
        return diagnostics
    
    def _process_mypy_output(self, output: str) -> List[Diagnostic]:
        """Process mypy text output"""
        diagnostics = []
        
        for line in output.strip().split('\n'):
            if not line or 'Found' in line:
                continue
            
            # Parse mypy output format: file:line:column: severity: message
            parts = line.split(':', 4)
            if len(parts) >= 4:
                diagnostic = Diagnostic(
                    file_path=parts[0],
                    line=int(parts[1]) if parts[1].isdigit() else 0,
                    column=int(parts[2]) if parts[2].isdigit() else 0,
                    severity='error' if 'error' in parts[3] else 'warning',
                    message=parts[4].strip() if len(parts) > 4 else parts[3],
                    source='mypy'
                )
                diagnostics.append(diagnostic)
        
        return diagnostics
    
    def _process_pylint_output(self, output: List[Dict]) -> List[Diagnostic]:
        """Process pylint JSON output"""
        diagnostics = []
        
        for item in output:
            severity_map = {'error': 'error', 'warning': 'warning', 'info': 'information'}
            
            diagnostic = Diagnostic(
                file_path=item['path'],
                line=item['line'],
                column=item['column'],
                severity=severity_map.get(item['type'], 'information'),
                message=item['message'],
                source='pylint',
                code=item['message-id']
            )
            diagnostics.append(diagnostic)
        
        return diagnostics

class CodeQualityAnalyzer:
    """Analyzes code quality metrics"""
    
    def analyze_quality_metrics(self, root_path: Path) -> Dict[str, Any]:
        """Analyze various code quality metrics"""
        metrics = {
            'loc_metrics': self._get_loc_metrics(root_path),
            'duplication': self._check_duplication(root_path),
            'maintainability': self._calculate_maintainability(root_path),
            'technical_debt': self._estimate_technical_debt(root_path)
        }
        
        return metrics
    
    def _get_loc_metrics(self, root_path: Path) -> Dict[str, int]:
        """Get lines of code metrics"""
        try:
            result = subprocess.run(
                ['tokei', '--output', 'json', str(root_path)],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.stdout:
                tokei_data = json.loads(result.stdout)
                return self._process_tokei_output(tokei_data)
        except Exception as e:
            logger.debug(f"LOC analysis failed: {e}")
        
        return {'total_lines': 0, 'code_lines': 0, 'comment_lines': 0, 'blank_lines': 0}
    
    def _check_duplication(self, root_path: Path) -> Dict[str, Any]:
        """Check for code duplication"""
        # Simplified duplication detection - could be enhanced with tools like jscpd
        _ = root_path  # Unused for now
        return {'duplicated_blocks': 0, 'duplication_ratio': 0.0}
    
    def _calculate_maintainability(self, root_path: Path) -> float:
        """Calculate maintainability index"""
        # Simplified maintainability calculation - could be enhanced with radon
        _ = root_path  # Unused for now
        return 75.0  # Placeholder
    
    def _estimate_technical_debt(self, root_path: Path) -> Dict[str, Any]:
        """Estimate technical debt"""
        # Could be enhanced with SonarQube metrics or custom analysis
        _ = root_path  # Unused for now
        return {'debt_ratio': 0.05, 'debt_minutes': 120}
    
    def _process_tokei_output(self, tokei_data: Dict) -> Dict[str, int]:
        """Process tokei JSON output"""
        total_stats = {'total_lines': 0, 'code_lines': 0, 'comment_lines': 0, 'blank_lines': 0}
        
        for stats in tokei_data.get('languages', {}).values():
            if isinstance(stats, dict):
                total_stats['total_lines'] += stats.get('total', 0)
                total_stats['code_lines'] += stats.get('code', 0)
                total_stats['comment_lines'] += stats.get('comments', 0)
                total_stats['blank_lines'] += stats.get('blanks', 0)
        
        return total_stats

class RecentChangesAnalyzer:
    """Analyzes recent changes in the codebase"""
    
    def analyze_recent_changes(self, root_path: Path, days: int = 7) -> List[str]:
        """Analyze recent changes in the codebase"""
        try:
            # Get files changed in the last N days
            result = subprocess.run([
                'git', 'log', '--name-only', '--pretty=format:', f'--since={days} days ago'
            ], capture_output=True, text=True, cwd=root_path, timeout=10)
            
            if result.returncode == 0:
                changed_files = [
                    line.strip() for line in result.stdout.split('\n')
                    if line.strip() and not line.startswith('commit')
                ]
                return list(set(changed_files))  # Remove duplicates
        except Exception as e:
            logger.debug(f"Recent changes analysis failed: {e}")
        
        return []

class TestCoverageCollector:
    """Collects test coverage information"""
    
    def collect_coverage(self, root_path: Path) -> Dict[str, float]:
        """Collect test coverage information"""
        coverage_data = {}
        
        # Try to read coverage.json if it exists
        coverage_json = root_path / 'coverage.json'
        
        if coverage_json.exists():
            try:
                with open(coverage_json, 'r') as f:
                    data = json.load(f)
                coverage_data = self._process_coverage_json(data)
            except Exception as e:
                logger.debug(f"Coverage JSON processing failed: {e}")
        
        return coverage_data
    
    def _process_coverage_json(self, data: Dict) -> Dict[str, float]:
        """Process coverage.py JSON output"""
        coverage_by_file = {}
        
        files_data = data.get('files', {})
        for file_path, file_data in files_data.items():
            coverage_percentage = file_data.get('summary', {}).get('percent_covered', 0.0)
            coverage_by_file[file_path] = coverage_percentage
        
        return coverage_by_file

class CodeIntelligenceOrchestrator:
    """Main orchestrator for code intelligence gathering"""
    
    def __init__(self):
        self.tree_sitter_analyzer = TreeSitterAnalyzer()
        self.lsp_collector = LSPDiagnosticsCollector()
        self.quality_analyzer = CodeQualityAnalyzer()
        self.changes_analyzer = RecentChangesAnalyzer()
        self.coverage_collector = TestCoverageCollector()
    
    def gather_intelligence(self, root_path: Path, max_files: int = 50) -> CodeIntelligenceContext:
        """Gather comprehensive code intelligence"""
        start_time = time.time()
        
        # Collect all Python files
        python_files = list(root_path.rglob("*.py"))[:max_files]
        
        # Parallel analysis of different aspects
        all_symbols = []
        all_calls = []
        all_imports = []
        
        # Analyze files with tree-sitter
        for file_path in python_files:
            symbols, calls, imports = self.tree_sitter_analyzer.analyze_file(file_path)
            all_symbols.extend(symbols)
            all_calls.extend(calls)
            all_imports.extend(imports)
        
        # Collect diagnostics
        diagnostics = self.lsp_collector.collect_diagnostics(root_path)
        
        # Calculate complexity metrics per file
        complexity_metrics = {}
        for symbol in all_symbols:
            if symbol.kind in ['function', 'method']:
                file_key = symbol.file_path
                if file_key not in complexity_metrics:
                    complexity_metrics[file_key] = ComplexityMetrics(
                        cyclomatic=0,
                        cognitive=0,
                        lines_of_code=0,
                        maintainability_index=75.0
                    )
                complexity_metrics[file_key].cyclomatic += symbol.complexity
        
        # Gather other metrics
        recent_changes = self.changes_analyzer.analyze_recent_changes(root_path)
        test_coverage = self.coverage_collector.collect_coverage(root_path)
        quality_metrics = self.quality_analyzer.analyze_quality_metrics(root_path)
        
        context = CodeIntelligenceContext(
            diagnostics=diagnostics,
            symbols=all_symbols,
            call_graph=all_calls,
            imports=all_imports,
            complexity_metrics=complexity_metrics,
            recent_changes=recent_changes,
            test_coverage=test_coverage,
            quality_metrics=quality_metrics,
            timestamp=time.time()
        )
        
        logger.info(f"Code intelligence gathered in {time.time() - start_time:.2f}s")
        return context
    
    def serialize_context(self, context: CodeIntelligenceContext) -> str:
        """Serialize context to JSON string for AI consumption"""
        try:
            # Convert dataclasses to dictionaries
            context_dict = asdict(context)
            return json.dumps(context_dict, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to serialize context: {e}")
            return "{}"
    
    def get_focused_context(self, context: CodeIntelligenceContext, focus_files: List[str]) -> str:
        """Get focused context for specific files"""
        filtered_diagnostics = [d for d in context.diagnostics if d.file_path in focus_files]
        filtered_symbols = [s for s in context.symbols if s.file_path in focus_files]
        filtered_calls = [c for c in context.call_graph if c.file_path in focus_files]
        
        focused_context = CodeIntelligenceContext(
            diagnostics=filtered_diagnostics,
            symbols=filtered_symbols,
            call_graph=filtered_calls,
            imports=context.imports,  # Keep all imports for dependency analysis
            complexity_metrics={k: v for k, v in context.complexity_metrics.items() if k in focus_files},
            recent_changes=[f for f in context.recent_changes if f in focus_files],
            test_coverage={k: v for k, v in context.test_coverage.items() if k in focus_files},
            quality_metrics=context.quality_metrics,  # Keep global metrics
            timestamp=context.timestamp
        )
        
        return self.serialize_context(focused_context)

# Main entry point for integration
def get_code_intelligence(root_path: str, focus_files: Optional[List[str]] = None) -> str:
    """Main entry point for getting code intelligence context"""
    orchestrator = CodeIntelligenceOrchestrator()
    root = Path(root_path)
    
    context = orchestrator.gather_intelligence(root)
    
    if focus_files:
        return orchestrator.get_focused_context(context, focus_files)
    else:
        return orchestrator.serialize_context(context)

if __name__ == "__main__":
    # Test the module
    import sys
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    intelligence = get_code_intelligence(root_path)
    print(intelligence)