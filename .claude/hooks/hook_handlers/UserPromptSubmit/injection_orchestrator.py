#!/usr/bin/env python3
"""Injection Orchestrator for coordinating context injections."""

import asyncio
import subprocess
import sys
from typing import Any, Dict, Optional

from UserPromptSubmit.ai_context_optimizer_optimized import \
    optimize_injection_sync
from UserPromptSubmit.code_intelligence import get_code_intelligence
from UserPromptSubmit.context_revival import get_context_revival_injection
from UserPromptSubmit.firecrawl_injection import get_firecrawl_injection
from UserPromptSubmit.git_injection import get_git_injection
from UserPromptSubmit.mcp_injector import get_mcp_injection
from UserPromptSubmit.project_intelligence import gather_project_intelligence
# Import security validator for credential scrubbing
from UserPromptSubmit.security_validator import scrub_credentials
from UserPromptSubmit.system_monitor import get_system_monitoring_injection
from UserPromptSubmit.unified_smart_advisor import get_smart_recommendations

from .circuit_breaker_manager import CircuitBreakerManager


class InjectionOrchestrator:
    """Orchestrates all context injections in parallel with token optimization."""
    
    def __init__(self, circuit_breaker_manager: CircuitBreakerManager):
        """Initialize injection orchestrator."""
        self.circuit_breaker_manager = circuit_breaker_manager
        self._context_cache = {}
        self._cache_ttl = 300  # 5 minute cache for context
        self._token_budget = 15000  # Token budget for context (75% of 200k limit)
    
    async def execute_injections(self, user_prompt: str, project_dir: str) -> str:
        """Execute all enabled injections in parallel and return combined context."""
        # Check cache first for token efficiency
        cache_key = self._get_cache_key(user_prompt, project_dir)
        cached_context = self._get_cached_context(cache_key)
        if cached_context:
            return cached_context
            
        enabled_injections = self.circuit_breaker_manager.get_enabled_injections()
        circuit_breakers = self.circuit_breaker_manager.get_circuit_breakers()
        
        # Create ALL tasks for true parallel execution
        all_tasks = []
        task_names = []
        
        # Add consolidated injectors wrapped in asyncio.to_thread for true parallelism
        if enabled_injections.get("unified_smart_advisor"):
            all_tasks.append(asyncio.to_thread(get_smart_recommendations, user_prompt))
            task_names.append("unified_smart_advisor")
        
        if enabled_injections.get("system_monitor"):
            # This is an async function, call directly without to_thread
            all_tasks.append(get_system_monitoring_injection(user_prompt, project_dir))
            task_names.append("system_monitor")
        
        if enabled_injections.get("project_intelligence"):
            all_tasks.append(asyncio.to_thread(gather_project_intelligence, project_dir))
            task_names.append("project_intelligence")
        
        if enabled_injections.get("code_intelligence"):
            all_tasks.append(asyncio.to_thread(get_code_intelligence, project_dir))
            task_names.append("code_intelligence")
        
        if enabled_injections.get("context_revival"):
            all_tasks.append(
                asyncio.to_thread(
                    get_context_revival_injection,
                    user_prompt,
                    project_dir,
                ),
            )
            task_names.append("context_revival")
        
        if enabled_injections.get("mcp"):
            all_tasks.append(asyncio.to_thread(get_mcp_injection, user_prompt))
            task_names.append("mcp")
        
        # Add native async injections
        if enabled_injections.get("git"):
            all_tasks.append(get_git_injection(project_dir))
            task_names.append("git")
        
        if enabled_injections.get("firecrawl"):
            all_tasks.append(get_firecrawl_injection(user_prompt, project_dir))
            task_names.append("firecrawl")
        
        # Execute ALL tasks in parallel with timeout enforcement
        results_dict = {}
        if all_tasks:
            try:
                # Apply 30-second timeout for all injection operations
                results = await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True),
                    timeout=30.0
                )
                
                # Create result dictionary mapping task names to results
                for name, result in zip(task_names, results):
                    if isinstance(result, Exception):
                        # Contract 2.2: Use exit code 2 for blocking errors
                        secure_error = scrub_credentials(str(result))
                        print(
                            f"Error: Failed in {name} injection: {secure_error}",
                            file=sys.stderr,
                        )
                        sys.exit(2)
                    else:
                        if result is None:
                            print(
                                f"Error: {name} injection returned None - expected valid content",
                                file=sys.stderr,
                            )
                            sys.exit(2)
                        results_dict[name] = result
                        
            except asyncio.TimeoutError:
                print(
                    "Error: Injection operations timed out after 30 seconds",
                    file=sys.stderr,
                )
                sys.exit(2)
            except Exception as e:
                secure_error = scrub_credentials(str(e))
                print(
                    f"Error: Injection orchestration failed: {secure_error}",
                    file=sys.stderr,
                )
                sys.exit(2)
        
        # Validate required injections
        self._validate_injection_results(results_dict, enabled_injections)
        
        # Build combined context with token optimization
        combined_context = self._build_combined_context(results_dict, enabled_injections, circuit_breakers, user_prompt)
        
        # Cache the result for future use
        self._cache_context(cache_key, combined_context)
        
        return combined_context
    
    def _validate_injection_results(self, results_dict: Dict[str, Any], enabled_injections: Dict[str, bool]):
        """Validate that all required injections produced results."""
        validation_map = [
            ("unified_smart_advisor", "unified_smart_advisor"),
            ("system_monitor", "system_monitor"),
            ("project_intelligence", "project_intelligence"),
            ("code_intelligence", "code_intelligence"),
            ("context_revival", "context_revival"),
            ("mcp", "mcp"),
            ("git", "git"),
            ("firecrawl", "firecrawl"),
        ]
        
        for result_key, enabled_key in validation_map:
            if enabled_injections.get(enabled_key) and results_dict.get(result_key) is None:
                print(
                    f"Error: {result_key} injection failed to produce content",
                    file=sys.stderr,
                )
                sys.exit(2)
    
    def _build_combined_context(
        self, 
        results_dict: Dict[str, Any], 
        enabled_injections: Dict[str, bool],
        circuit_breakers: Dict[str, bool],
        user_prompt: str
    ) -> str:
        """Build the combined context from all injection results."""
        # Build context only from enabled injections
        unified_advisor = (
            results_dict.get("unified_smart_advisor", "") 
            if enabled_injections.get("unified_smart_advisor") else ""
        )
        system_monitor = (
            results_dict.get("system_monitor", "") 
            if enabled_injections.get("system_monitor") else ""
        )
        project_intelligence = (
            self._format_project_intelligence(results_dict.get("project_intelligence", {}))
            if enabled_injections.get("project_intelligence") else ""
        )
        code_intelligence = (
            self._format_code_intelligence(results_dict.get("code_intelligence", ""))
            if enabled_injections.get("code_intelligence") else ""
        )
        context_revival = (
            results_dict.get("context_revival", "") 
            if enabled_injections.get("context_revival") else ""
        )
        mcp_recommendations = (
            results_dict.get("mcp", "") 
            if enabled_injections.get("mcp") else ""
        )
        git_injection = (
            results_dict.get("git", "") 
            if enabled_injections.get("git") else ""
        )
        firecrawl_context = (
            results_dict.get("firecrawl", "") 
            if enabled_injections.get("firecrawl") else ""
        )
        
        # Build additional context - combine all injections
        # Git injection goes early for foundational context, project intelligence provides tech context
        raw_context = (
            f"{git_injection}\n{project_intelligence}\n{code_intelligence}\n{context_revival}{system_monitor}{firecrawl_context}{unified_advisor}"
            f"{mcp_recommendations}"
        )
        
        # ALWAYS optimize context with AI - no env checks, fails loudly if API fails
        # This now includes: Gemini enhancement + static content + zen-pro
        if circuit_breakers["enhanced_ai_optimizer"]:
            try:
                additional_context = optimize_injection_sync(user_prompt, raw_context)
            except Exception as e:
                # Contract 2.2: Use exit code 2 for blocking errors
                secure_error = scrub_credentials(str(e))
                print(f"Error: AI optimization failed: {secure_error}", file=sys.stderr)
                sys.exit(2)
        else:
            # If circuit breaker is disabled, just use raw context (should not happen in production)
            print(
                "[AI_OPTIMIZER] WARNING - Circuit breaker disabled, using raw context",
                file=sys.stderr,
            )
            additional_context = raw_context
        
        return additional_context
    
    def _format_project_intelligence(self, intelligence_data: Dict[str, Any]) -> str:
        """Format project intelligence data for context injection."""
        if not intelligence_data:
            return ""
        
        # Build structured project context
        lines = ["## PROJECT INTELLIGENCE"]
        
        # Project basics
        project_type = intelligence_data.get("project_type", "unknown")
        project_scale = intelligence_data.get("project_scale", "unknown")
        confidence = intelligence_data.get("confidence_score", 0.0)
        
        lines.append(f"**Type**: {project_type} | **Scale**: {project_scale} | **Confidence**: {confidence:.1%}")
        
        # Tech stack overview
        tech_stack = intelligence_data.get("tech_stack", [])
        if tech_stack:
            lines.append(f"**Tech Stack**: {', '.join(tech_stack)}")
        
        # Frameworks
        frameworks = intelligence_data.get("frameworks", {})
        if frameworks:
            fw_info = [f"{name} ({version})" for name, version in frameworks.items()]
            lines.append(f"**Frameworks**: {', '.join(fw_info)}")
        
        # Build system
        build_system = intelligence_data.get("build_system", {})
        if build_system:
            build_tools = [tool for tool, enabled in build_system.items() 
                          if enabled and isinstance(enabled, bool)]
            if build_tools:
                lines.append(f"**Build**: {', '.join(build_tools)}")
        
        # Testing setup
        testing = intelligence_data.get("testing", {})
        if testing:
            test_tools = [tool for tool, enabled in testing.items() 
                         if enabled and isinstance(enabled, bool)]
            if test_tools:
                lines.append(f"**Testing**: {', '.join(test_tools)}")
        
        # Architecture patterns
        architecture = intelligence_data.get("architecture", {})
        if architecture:
            arch_patterns = [pattern for pattern, enabled in architecture.items() 
                           if enabled and isinstance(enabled, bool)]
            if arch_patterns:
                lines.append(f"**Architecture**: {', '.join(arch_patterns)}")
        
        # CI/CD
        cicd = intelligence_data.get("cicd", {})
        if cicd:
            cicd_tools = [tool for tool, enabled in cicd.items() 
                         if enabled and isinstance(enabled, bool)]
            if cicd_tools:
                lines.append(f"**CI/CD**: {', '.join(cicd_tools)}")
        
        # Dependencies health
        dependencies = intelligence_data.get("dependencies", {})
        dep_health = dependencies.get("health", "unknown")
        if dep_health != "unknown":
            total_deps = sum(len(deps) for _, deps in dependencies.items() 
                           if isinstance(deps, list))
            lines.append(f"**Dependencies**: {total_deps} total ({dep_health})")
        
        # Code conventions
        conventions = intelligence_data.get("conventions", {})
        if conventions:
            conv_tools = [tool for tool, enabled in conventions.items() 
                         if enabled and isinstance(enabled, bool)]
            if conv_tools:
                lines.append(f"**Code Standards**: {', '.join(conv_tools)}")
        
        return "\n".join(lines) + "\n"
    
    def _format_code_intelligence(self, intelligence_data: str) -> str:
        """Format code intelligence data for context injection."""
        if not intelligence_data or not intelligence_data.strip():
            return ""
        
        # Parse JSON intelligence data if it's a string
        try:
            import json
            if isinstance(intelligence_data, str):
                data = json.loads(intelligence_data)
            else:
                data = intelligence_data
        except (json.JSONDecodeError, TypeError):
            # If not JSON, treat as plain text
            return f"## CODE INTELLIGENCE\n{intelligence_data}\n"
        
        # Build structured code intelligence context
        lines = ["## CODE INTELLIGENCE"]
        
        # Diagnostics summary
        diagnostics = data.get("diagnostics", [])
        if diagnostics:
            error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
            warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
            if error_count > 0 or warning_count > 0:
                lines.append(f"**Issues**: {error_count} errors, {warning_count} warnings")
        
        # Symbol summary
        symbols = data.get("symbols", [])
        if symbols:
            functions = sum(1 for s in symbols if s.get("kind") == "function")
            classes = sum(1 for s in symbols if s.get("kind") == "class")
            methods = sum(1 for s in symbols if s.get("kind") == "method")
            lines.append(f"**Code Structure**: {classes} classes, {functions} functions, {methods} methods")
        
        # Complexity metrics
        complexity_metrics = data.get("complexity_metrics", {})
        if complexity_metrics:
            total_complexity = sum(m.get("cyclomatic", 0) for m in complexity_metrics.values())
            if total_complexity > 0:
                lines.append(f"**Complexity**: {total_complexity} total cyclomatic complexity")
        
        # Recent changes
        recent_changes = data.get("recent_changes", [])
        if recent_changes:
            lines.append(f"**Recent Changes**: {len(recent_changes)} files modified recently")
        
        # Test coverage
        test_coverage = data.get("test_coverage", {})
        if test_coverage:
            avg_coverage = sum(test_coverage.values()) / len(test_coverage) if test_coverage else 0
            lines.append(f"**Test Coverage**: {avg_coverage:.1f}% average")
        
        # Quality metrics
        quality_metrics = data.get("quality_metrics", {})
        if quality_metrics:
            loc_metrics = quality_metrics.get("loc_metrics", {})
            if loc_metrics:
                code_lines = loc_metrics.get("code_lines", 0)
                total_lines = loc_metrics.get("total_lines", 0)
                if total_lines > 0:
                    lines.append(f"**Code Size**: {code_lines} code lines ({total_lines} total)")
        
        return "\n".join(lines) + "\n"
    
    def _get_cache_key(self, user_prompt: str, project_dir: str) -> str:
        """Generate cache key from prompt hash and git state."""
        import hashlib
        prompt_hash = hashlib.md5(user_prompt.encode()).hexdigest()[:8]
        try:
            git_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=project_dir, 
                stderr=subprocess.DEVNULL
            ).decode().strip()[:8]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            git_hash = "nogit"
        return f"{prompt_hash}_{git_hash}"
    
    def _get_cached_context(self, cache_key: str) -> Optional[str]:
        """Get cached context if valid."""
        import time
        if cache_key in self._context_cache:
            context, timestamp = self._context_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return context
        return None
    
    def _cache_context(self, cache_key: str, context: str):
        """Cache context with cleanup."""
        import time
        now = time.time()
        self._context_cache[cache_key] = (context, now)
        
        # Cleanup old entries
        for cache_key_to_check, (_, timestamp) in list(self._context_cache.items()):
            if now - timestamp > self._cache_ttl:
                del self._context_cache[cache_key_to_check]
    
    def _estimate_token_count(self, text: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(text) // 4
    
    def _truncate_for_budget(self, context: str) -> str:
        """Truncate context to fit token budget."""
        estimated_tokens = self._estimate_token_count(context)
        if estimated_tokens <= self._token_budget:
            return context
            
        # Truncate to fit budget (keep most important parts)
        target_length = self._token_budget * 4  # Convert back to chars
        lines = context.split('\n')
        
        # Prioritize: git info, errors, recent changes
        priority_patterns = ['git', 'error', 'failed', 'recent', 'change']
        priority_lines = []
        other_lines = []
        
        for line in lines:
            if any(pattern in line.lower() for pattern in priority_patterns):
                priority_lines.append(line)
            else:
                other_lines.append(line)
        
        # Build truncated context
        result = '\n'.join(priority_lines)
        remaining_budget = target_length - len(result)
        
        if remaining_budget > 0 and other_lines:
            other_content = '\n'.join(other_lines)
            if len(other_content) <= remaining_budget:
                result += '\n' + other_content
            else:
                result += '\n' + other_content[:remaining_budget] + '...'
        
        return result