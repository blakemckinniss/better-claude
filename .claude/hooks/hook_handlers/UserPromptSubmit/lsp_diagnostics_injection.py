"""Language Server Protocol diagnostics injection for code quality awareness."""

import asyncio
import os
import json
import glob
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict


class LSPDiagnosticsAnalyzer:
    """Analyze diagnostics from various language servers and linters."""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.diagnostics = defaultdict(list)
        
    async def collect_all_diagnostics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Collect diagnostics from all available sources."""
        collectors = [
            self._collect_mypy_diagnostics(),
            self._collect_ruff_diagnostics(),
            self._collect_pyright_diagnostics(),
            self._collect_typescript_diagnostics(),
            self._collect_eslint_diagnostics(),
            self._collect_rust_diagnostics(),
        ]
        
        # Run all collectors in parallel
        await asyncio.gather(*collectors, return_exceptions=True)
                
        return dict(self.diagnostics)
    
    async def _collect_mypy_diagnostics(self):
        """Collect mypy type checking errors."""
        # Check for .mypy_cache
        mypy_cache = self.project_dir / '.mypy_cache'
        if mypy_cache.exists():
            # Try to run mypy for fresh results
            try:
                process = await asyncio.create_subprocess_exec(
                    'mypy', '--no-error-summary', '--show-column-numbers', '--show-error-codes', '.',
                    cwd=self.project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
                
                if stdout:
                    for line in stdout.decode().splitlines():
                        # Parse mypy output format: file.py:line:col: error: message [error-code]
                        match = re.match(r'^(.+?):(\d+):(\d+): (\w+): (.+?)(?:\s+\[(.+?)\])?$', line)
                        if match:
                            file_path, line_num, col, severity, message, code = match.groups()
                            self.diagnostics['mypy'].append({
                                'file': file_path,
                                'line': int(line_num),
                                'column': int(col),
                                'severity': severity,
                                'message': message,
                                'code': code or 'unknown',
                                'source': 'mypy'
                            })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    
    def _collect_ruff_diagnostics(self):
        """Collect ruff linting errors."""
        # Check for .ruff_cache or run ruff
        try:
            result = subprocess.run(
                ['ruff', 'check', '--output-format=json', '.'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        self.diagnostics['ruff'].append({
                            'file': issue.get('filename', ''),
                            'line': issue.get('location', {}).get('row', 0),
                            'column': issue.get('location', {}).get('column', 0),
                            'severity': 'error' if issue.get('fix') else 'warning',
                            'message': issue.get('message', ''),
                            'code': issue.get('code', 'unknown'),
                            'source': 'ruff'
                        })
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    for line in result.stdout.splitlines():
                        match = re.match(r'^(.+?):(\d+):(\d+): (\w+) (.+)$', line)
                        if match:
                            file_path, line_num, col, code, message = match.groups()
                            self.diagnostics['ruff'].append({
                                'file': file_path,
                                'line': int(line_num),
                                'column': int(col),
                                'severity': 'warning',
                                'message': f"{code}: {message}",
                                'code': code,
                                'source': 'ruff'
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def _collect_pyright_diagnostics(self):
        """Collect Pyright/Pylance diagnostics."""
        # Look for pyrightconfig.json or run pyright
        try:
            result = subprocess.run(
                ['pyright', '--outputjson'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for diag in data.get('generalDiagnostics', []):
                        self.diagnostics['pyright'].append({
                            'file': diag.get('file', ''),
                            'line': diag.get('range', {}).get('start', {}).get('line', 0) + 1,
                            'column': diag.get('range', {}).get('start', {}).get('character', 0) + 1,
                            'severity': diag.get('severity', 'error'),
                            'message': diag.get('message', ''),
                            'code': diag.get('rule', 'unknown'),
                            'source': 'pyright'
                        })
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def _collect_typescript_diagnostics(self):
        """Collect TypeScript compiler diagnostics."""
        # Check for tsconfig.json
        tsconfig = self.project_dir / 'tsconfig.json'
        if tsconfig.exists():
            try:
                result = subprocess.run(
                    ['tsc', '--noEmit', '--pretty', 'false'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.stdout:
                    # Parse TypeScript output
                    for line in result.stdout.splitlines():
                        # Format: file.ts(line,col): error TS1234: message
                        match = re.match(r'^(.+?)\((\d+),(\d+)\): (\w+) (TS\d+): (.+)$', line)
                        if match:
                            file_path, line_num, col, severity, code, message = match.groups()
                            self.diagnostics['typescript'].append({
                                'file': file_path,
                                'line': int(line_num),
                                'column': int(col),
                                'severity': severity.lower(),
                                'message': message,
                                'code': code,
                                'source': 'tsc'
                            })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    
    def _collect_eslint_diagnostics(self):
        """Collect ESLint diagnostics."""
        # Check for .eslintrc or run eslint
        eslintrc_files = list(self.project_dir.glob('.eslintrc*'))
        if eslintrc_files or (self.project_dir / 'package.json').exists():
            try:
                result = subprocess.run(
                    ['npx', 'eslint', '.', '--format=json'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.stdout:
                    try:
                        files = json.loads(result.stdout)
                        for file_data in files:
                            for msg in file_data.get('messages', []):
                                self.diagnostics['eslint'].append({
                                    'file': file_data.get('filePath', ''),
                                    'line': msg.get('line', 0),
                                    'column': msg.get('column', 0),
                                    'severity': 'error' if msg.get('severity', 0) == 2 else 'warning',
                                    'message': msg.get('message', ''),
                                    'code': msg.get('ruleId', 'unknown'),
                                    'source': 'eslint'
                                })
                    except json.JSONDecodeError:
                        pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    
    def _collect_rust_diagnostics(self):
        """Collect Rust compiler/clippy diagnostics."""
        # Check for Cargo.toml
        cargo_toml = self.project_dir / 'Cargo.toml'
        if cargo_toml.exists():
            try:
                # Try clippy first (more comprehensive)
                result = subprocess.run(
                    ['cargo', 'clippy', '--message-format=json', '--no-deps'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.stdout:
                    for line in result.stdout.splitlines():
                        try:
                            msg = json.loads(line)
                            if msg.get('reason') == 'compiler-message':
                                message = msg.get('message', {})
                                for span in message.get('spans', []):
                                    if span.get('is_primary'):
                                        self.diagnostics['rust'].append({
                                            'file': span.get('file_name', ''),
                                            'line': span.get('line_start', 0),
                                            'column': span.get('column_start', 0),
                                            'severity': message.get('level', 'warning'),
                                            'message': message.get('message', ''),
                                            'code': message.get('code', {}).get('code', 'unknown'),
                                            'source': 'clippy'
                                        })
                        except json.JSONDecodeError:
                            pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    
    def filter_diagnostics_for_prompt(self, prompt: str) -> Dict[str, List[Dict[str, Any]]]:
        """Filter diagnostics relevant to the user's prompt."""
        # Extract file paths mentioned in prompt
        file_pattern = r'["\']?([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)["\']?'
        mentioned_files = set(re.findall(file_pattern, prompt))
        
        # Keywords that suggest interest in diagnostics
        diagnostic_keywords = ['error', 'warning', 'type', 'lint', 'fix', 'issue', 'problem', 'diagnostic']
        wants_diagnostics = any(keyword in prompt.lower() for keyword in diagnostic_keywords)
        
        filtered = defaultdict(list)
        
        for source, diags in self.diagnostics.items():
            for diag in diags:
                # Include if file is mentioned or user wants diagnostics
                file_path = Path(diag['file'])
                if mentioned_files:
                    # Check if any mentioned file matches
                    for mentioned in mentioned_files:
                        if mentioned in str(file_path) or file_path.name == mentioned:
                            filtered[source].append(diag)
                            break
                elif wants_diagnostics and diag['severity'] in ['error', 'critical']:
                    # Include critical errors when diagnostics are wanted
                    filtered[source].append(diag)
        
        return dict(filtered)


async def get_lsp_diagnostics_injection(prompt: str, project_dir: str) -> str:
    """Create LSP diagnostics injection."""
    analyzer = LSPDiagnosticsAnalyzer(project_dir)
    
    try:
        # Collect all diagnostics
        await analyzer.collect_all_diagnostics()
        
        # Filter based on prompt
        filtered = analyzer.filter_diagnostics_for_prompt(prompt)
        
        if not filtered:
            # Check if we have any diagnostics at all
            total_count = sum(len(diags) for diags in analyzer.diagnostics.values())
            if total_count > 0:
                # Summary only
                error_count = sum(1 for diags in analyzer.diagnostics.values() 
                                for d in diags if d['severity'] == 'error')
                warning_count = total_count - error_count
                
                if error_count > 0:
                    return f"<lsp-diagnostics>🔴 {error_count} errors, {warning_count} warnings across codebase</lsp-diagnostics>\n"
            return ""
        
        # Format diagnostics
        injection_parts = ["<lsp-diagnostics>"]
        
        # Group by severity
        errors = []
        warnings = []
        
        for source, diags in filtered.items():
            for diag in diags[:10]:  # Limit to 10 per source
                entry = f"{diag['file']}:{diag['line']}:{diag['column']} - {diag['message']} [{diag['code']}]"
                if diag['severity'] == 'error':
                    errors.append(entry)
                else:
                    warnings.append(entry)
        
        if errors:
            injection_parts.append("❌ Errors:")
            injection_parts.extend(f"  {e}" for e in errors[:5])
            
        if warnings:
            injection_parts.append("⚠️ Warnings:")
            injection_parts.extend(f"  {w}" for w in warnings[:3])
            
        injection_parts.append("</lsp-diagnostics>")
        
        return "\n".join(injection_parts) + "\n"
        
    except Exception as e:
        # Don't let diagnostic errors break the hook
        return f"<!-- LSP diagnostics error: {str(e)} -->\n"