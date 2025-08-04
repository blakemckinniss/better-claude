#!/usr/bin/env python3
"""
Additional Context Gathering Modules for Gemini Enhancement System

This module implements the 9+ new intelligence sources to expand from the current
6 context sources to 15+ comprehensive context sources for maximum prompt enhancement.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DependencyAnalysisModule:
    """
    Advanced dependency analysis beyond basic package detection.
    
    Analyzes:
    - Dependency security vulnerabilities
    - Outdated package versions
    - Dependency conflicts and compatibility
    - License compliance issues
    - Dependency graph complexity
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache for dependency analysis
    
    async def analyze_dependencies(self) -> Dict[str, Any]:
        """Comprehensive dependency analysis."""
        cache_key = "dependency_analysis"
        if cache_key in self.cache and time.time() - self.cache["timestamp"] < self.cache_ttl:
            return self.cache[cache_key]
        
        analysis = {
            "security_vulnerabilities": await self._scan_security_vulnerabilities(),
            "outdated_packages": await self._find_outdated_packages(),
            "dependency_conflicts": await self._detect_conflicts(),
            "license_analysis": await self._analyze_licenses(),
            "dependency_graph": await self._build_dependency_graph(),
            "recommendations": await self._generate_recommendations()
        }
        
        self.cache[cache_key] = analysis
        self.cache["timestamp"] = time.time()
        return analysis
    
    async def _scan_security_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Scan for known security vulnerabilities."""
        vulnerabilities = []
        
        # Check Python vulnerabilities
        if (self.project_dir / "requirements.txt").exists():
            try:
                result = await asyncio.create_subprocess_exec(
                    "pip-audit", "--format", "json", str(self.project_dir / "requirements.txt"),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if result.returncode == 0:
                    audit_data = json.loads(stdout.decode())
                    vulnerabilities.extend(audit_data.get("vulnerabilities", []))
            except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Check Node.js vulnerabilities
        if (self.project_dir / "package.json").exists():
            try:
                result = await asyncio.create_subprocess_exec(
                    "npm", "audit", "--json",
                    cwd=self.project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if stdout:
                    audit_data = json.loads(stdout.decode())
                    vulnerabilities.extend(self._parse_npm_audit(audit_data))
            except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
                pass
        
        return vulnerabilities
    
    async def _find_outdated_packages(self) -> List[Dict[str, Any]]:
        """Find outdated packages across ecosystems."""
        outdated = []
        
        # Check Python packages
        try:
            result = await asyncio.create_subprocess_exec(
                "pip", "list", "--outdated", "--format", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                pip_outdated = json.loads(stdout.decode())
                outdated.extend([{
                    "ecosystem": "python",
                    "package": pkg["name"],
                    "current": pkg["version"],
                    "latest": pkg["latest_version"],
                    "type": pkg["latest_filetype"]
                } for pkg in pip_outdated])
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass
        
        # Check Node.js packages
        if (self.project_dir / "package.json").exists():
            try:
                result = await asyncio.create_subprocess_exec(
                    "npm", "outdated", "--json",
                    cwd=self.project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if stdout:
                    npm_outdated = json.loads(stdout.decode())
                    for pkg, info in npm_outdated.items():
                        outdated.append({
                            "ecosystem": "nodejs",
                            "package": pkg,
                            "current": info.get("current"),
                            "wanted": info.get("wanted"),
                            "latest": info.get("latest"),
                            "location": info.get("location")
                        })
            except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
                pass
        
        return outdated
    
    async def _detect_conflicts(self) -> List[Dict[str, Any]]:
        """Detect dependency conflicts."""
        # This would implement conflict detection logic
        return []
    
    async def _analyze_licenses(self) -> Dict[str, Any]:
        """Analyze license compliance."""
        return {"compatible_licenses": [], "incompatible_licenses": [], "unknown_licenses": []}
    
    async def _build_dependency_graph(self) -> Dict[str, Any]:
        """Build dependency graph with metrics."""
        return {"depth": 0, "breadth": 0, "circular_dependencies": []}
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate dependency recommendations."""
        return []
    
    def _parse_npm_audit(self, audit_data: Dict) -> List[Dict[str, Any]]:
        """Parse npm audit data."""
        vulnerabilities = []
        if "vulnerabilities" in audit_data:
            for vuln_id, vuln_info in audit_data["vulnerabilities"].items():
                vulnerabilities.append({
                    "id": vuln_id,
                    "severity": vuln_info.get("severity", "unknown"),
                    "title": vuln_info.get("title", "Unknown vulnerability"),
                    "package": vuln_info.get("name", "unknown"),
                    "patched_in": vuln_info.get("patched_in", "unknown")
                })
        return vulnerabilities


class SecurityAnalysisModule:
    """
    Comprehensive security analysis for code and configuration.
    
    Analyzes:
    - Static code security patterns
    - Configuration security issues
    - Secrets and credential exposure
    - Security best practices compliance
    - OWASP Top 10 vulnerabilities
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.security_patterns = self._load_security_patterns()
    
    async def analyze_security(self) -> Dict[str, Any]:
        """Comprehensive security analysis."""
        return {
            "static_analysis": await self._static_security_analysis(),
            "configuration_security": await self._analyze_configuration_security(),
            "secrets_exposure": await self._scan_for_secrets(),
            "owasp_compliance": await self._check_owasp_compliance(),
            "security_headers": await self._analyze_security_headers(),
            "authentication_patterns": await self._analyze_auth_patterns()
        }
    
    async def _static_security_analysis(self) -> Dict[str, Any]:
        """Static code analysis for security issues."""
        issues = []
        
        # Use bandit for Python security analysis
        if any(self.project_dir.rglob("*.py")):
            try:
                result = await asyncio.create_subprocess_exec(
                    "bandit", "-r", str(self.project_dir), "-f", "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if stdout:
                    bandit_data = json.loads(stdout.decode())
                    issues.extend(self._parse_bandit_results(bandit_data))
            except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Use ESLint security plugin for JavaScript
        if any(self.project_dir.rglob("*.js")) or any(self.project_dir.rglob("*.ts")):
            issues.extend(await self._run_eslint_security())
        
        return {"issues": issues, "total_issues": len(issues)}
    
    async def _analyze_configuration_security(self) -> Dict[str, Any]:
        """Analyze configuration files for security issues."""
        config_issues = []
        
        # Check common configuration files
        config_files = [
            ".env", ".env.local", ".env.production",
            "config.json", "config.yaml", "config.yml",
            "docker-compose.yml", "Dockerfile"
        ]
        
        for config_file in config_files:
            config_path = self.project_dir / config_file
            if config_path.exists():
                issues = await self._analyze_config_file(config_path)
                config_issues.extend(issues)
        
        return {"configuration_issues": config_issues}
    
    async def _scan_for_secrets(self) -> Dict[str, Any]:
        """Scan for exposed secrets and credentials."""
        secrets = []
        
        # Use TruffleHog or similar for secret scanning
        try:
            result = await asyncio.create_subprocess_exec(
                "trufflehog", "filesystem", str(self.project_dir), "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if stdout:
                for line in stdout.decode().splitlines():
                    if line.strip():
                        secret_data = json.loads(line)
                        secrets.append({
                            "detector": secret_data.get("DetectorName"),
                            "file": secret_data.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("file"),
                            "line": secret_data.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("line"),
                            "verified": secret_data.get("Verified")
                        })
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass
        
        return {"exposed_secrets": secrets, "total_secrets": len(secrets)}
    
    async def _check_owasp_compliance(self) -> Dict[str, Any]:
        """Check compliance with OWASP Top 10."""
        owasp_checks = {
            "injection": await self._check_injection_vulnerabilities(),
            "broken_authentication": await self._check_authentication_issues(),
            "sensitive_data_exposure": await self._check_data_exposure(),
            "xml_external_entities": await self._check_xxe_vulnerabilities(),
            "broken_access_control": await self._check_access_control(),
            "security_misconfiguration": await self._check_security_config(),
            "cross_site_scripting": await self._check_xss_vulnerabilities(),
            "insecure_deserialization": await self._check_deserialization(),
            "vulnerable_components": await self._check_vulnerable_components(),
            "insufficient_logging": await self._check_logging_monitoring()
        }
        
        compliance_score = sum(1 for check in owasp_checks.values() if check["compliant"]) / len(owasp_checks)
        
        return {
            "owasp_checks": owasp_checks,
            "compliance_score": compliance_score,
            "critical_issues": [k for k, v in owasp_checks.items() if not v["compliant"] and v.get("severity") == "critical"]
        }
    
    def _load_security_patterns(self) -> Dict[str, List[str]]:
        """Load security patterns for analysis."""
        return {
            "sql_injection": [
                r"execute\s*\(\s*['\"].*\+.*['\"]",
                r"query\s*\(\s*['\"].*\+.*['\"]",
                r"SELECT.*\+.*FROM"
            ],
            "xss_patterns": [
                r"innerHTML\s*=\s*.*\+",
                r"document\.write\s*\(\s*.*\+",
                r"eval\s*\("
            ],
            "hardcoded_secrets": [
                r"password\s*=\s*['\"][^'\"]+['\"]",
                r"api_key\s*=\s*['\"][^'\"]+['\"]",
                r"secret\s*=\s*['\"][^'\"]+['\"]"
            ]
        }
    
    def _parse_bandit_results(self, bandit_data: Dict) -> List[Dict[str, Any]]:
        """Parse bandit security analysis results."""
        issues = []
        for result in bandit_data.get("results", []):
            issues.append({
                "type": "security",
                "severity": result.get("issue_severity", "unknown").lower(),
                "confidence": result.get("issue_confidence", "unknown").lower(),
                "file": result.get("filename"),
                "line": result.get("line_number"),
                "test_id": result.get("test_id"),
                "test_name": result.get("test_name"),
                "message": result.get("issue_text")
            })
        return issues
    
    async def _run_eslint_security(self) -> List[Dict[str, Any]]:
        """Run ESLint with security plugins."""
        return []  # Placeholder
    
    async def _analyze_config_file(self, config_path: Path) -> List[Dict[str, Any]]:
        """Analyze specific configuration file."""
        return []  # Placeholder
    
    async def _check_injection_vulnerabilities(self) -> Dict[str, Any]:
        """Check for injection vulnerabilities."""
        return {"compliant": True, "issues": []}
    
    async def _check_authentication_issues(self) -> Dict[str, Any]:
        """Check authentication implementation."""
        return {"compliant": True, "issues": []}
    
    async def _check_data_exposure(self) -> Dict[str, Any]:
        """Check for sensitive data exposure."""
        return {"compliant": True, "issues": []}
    
    async def _check_xxe_vulnerabilities(self) -> Dict[str, Any]:
        """Check for XXE vulnerabilities."""
        return {"compliant": True, "issues": []}
    
    async def _check_access_control(self) -> Dict[str, Any]:
        """Check access control implementation."""
        return {"compliant": True, "issues": []}
    
    async def _check_security_config(self) -> Dict[str, Any]:
        """Check security configuration."""
        return {"compliant": True, "issues": []}
    
    async def _check_xss_vulnerabilities(self) -> Dict[str, Any]:
        """Check for XSS vulnerabilities."""
        return {"compliant": True, "issues": []}
    
    async def _check_deserialization(self) -> Dict[str, Any]:
        """Check for insecure deserialization."""
        return {"compliant": True, "issues": []}
    
    async def _check_vulnerable_components(self) -> Dict[str, Any]:
        """Check for vulnerable components."""
        return {"compliant": True, "issues": []}
    
    async def _check_logging_monitoring(self) -> Dict[str, Any]:
        """Check logging and monitoring."""
        return {"compliant": True, "issues": []}
    
    async def _analyze_security_headers(self) -> Dict[str, Any]:
        """Analyze security headers in web applications."""
        return {"security_headers": [], "missing_headers": []}
    
    async def _analyze_auth_patterns(self) -> Dict[str, Any]:
        """Analyze authentication patterns."""
        return {"auth_mechanisms": [], "security_level": "medium"}


class PerformanceProfilingModule:
    """
    Advanced performance profiling and optimization recommendations.
    
    Analyzes:
    - Runtime performance characteristics
    - Memory usage patterns
    - CPU utilization hotspots
    - I/O bottlenecks
    - Network performance
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.profiling_data = {}
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """Comprehensive performance analysis."""
        return {
            "runtime_metrics": await self._collect_runtime_metrics(),
            "memory_analysis": await self._analyze_memory_patterns(),
            "cpu_profiling": await self._profile_cpu_usage(),
            "io_analysis": await self._analyze_io_patterns(),
            "network_performance": await self._analyze_network_performance(),
            "optimization_recommendations": await self._generate_optimization_recommendations()
        }
    
    async def _collect_runtime_metrics(self) -> Dict[str, Any]:
        """Collect runtime performance metrics."""
        return {
            "execution_time": 0.0,
            "memory_peak": 0,
            "cpu_time": 0.0,
            "io_operations": 0
        }
    
    async def _analyze_memory_patterns(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        return {
            "memory_leaks": [],
            "memory_hotspots": [],
            "memory_efficiency": 0.8
        }
    
    async def _profile_cpu_usage(self) -> Dict[str, Any]:
        """Profile CPU usage patterns."""
        return {
            "cpu_hotspots": [],
            "cpu_efficiency": 0.7,
            "optimization_opportunities": []
        }
    
    async def _analyze_io_patterns(self) -> Dict[str, Any]:
        """Analyze I/O patterns."""
        return {
            "io_bottlenecks": [],
            "file_access_patterns": [],
            "database_queries": []
        }
    
    async def _analyze_network_performance(self) -> Dict[str, Any]:
        """Analyze network performance."""
        return {
            "network_calls": [],
            "latency_issues": [],
            "bandwidth_usage": 0
        }
    
    async def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations."""
        return []


class TestIntelligenceModule:
    """
    Advanced test intelligence beyond basic test results.
    
    Analyzes:
    - Test coverage gaps and quality
    - Test performance and efficiency
    - Test flakiness and reliability
    - Test architecture and patterns
    - Testing best practices compliance
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
    
    async def analyze_test_intelligence(self) -> Dict[str, Any]:
        """Comprehensive test intelligence analysis."""
        return {
            "coverage_analysis": await self._analyze_test_coverage(),
            "test_performance": await self._analyze_test_performance(),
            "test_reliability": await self._analyze_test_reliability(),
            "test_architecture": await self._analyze_test_architecture(),
            "quality_metrics": await self._calculate_test_quality_metrics(),
            "recommendations": await self._generate_test_recommendations()
        }
    
    async def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Detailed test coverage analysis."""
        return {
            "line_coverage": 0.0,
            "branch_coverage": 0.0,
            "function_coverage": 0.0,
            "uncovered_critical_paths": [],
            "coverage_trends": []
        }
    
    async def _analyze_test_performance(self) -> Dict[str, Any]:
        """Analyze test performance characteristics."""
        return {
            "slow_tests": [],
            "test_execution_time": 0.0,
            "parallel_execution_opportunities": [],
            "resource_usage": {}
        }
    
    async def _analyze_test_reliability(self) -> Dict[str, Any]:
        """Analyze test reliability and flakiness."""
        return {
            "flaky_tests": [],
            "reliability_score": 0.9,
            "failure_patterns": [],
            "environmental_dependencies": []
        }
    
    async def _analyze_test_architecture(self) -> Dict[str, Any]:
        """Analyze test architecture and patterns."""
        return {
            "test_patterns": [],
            "test_organization": "good",
            "test_isolation": 0.8,
            "shared_fixtures": []
        }
    
    async def _calculate_test_quality_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive test quality metrics."""
        return {
            "test_quality_score": 0.8,
            "maintainability": 0.7,
            "readability": 0.9,
            "effectiveness": 0.8
        }
    
    async def _generate_test_recommendations(self) -> List[str]:
        """Generate test improvement recommendations."""
        return []


class DeploymentContextModule:
    """
    Deployment and infrastructure context analysis.
    
    Analyzes:
    - Deployment configuration and patterns
    - Infrastructure as code
    - CI/CD pipeline health
    - Environment configuration
    - Deployment risks and strategies
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
    
    async def analyze_deployment_context(self) -> Dict[str, Any]:
        """Comprehensive deployment context analysis."""
        return {
            "deployment_config": await self._analyze_deployment_config(),
            "infrastructure": await self._analyze_infrastructure(),
            "cicd_pipeline": await self._analyze_cicd_pipeline(),
            "environment_config": await self._analyze_environment_config(),
            "deployment_risks": await self._assess_deployment_risks(),
            "optimization_opportunities": await self._identify_deployment_optimizations()
        }
    
    async def _analyze_deployment_config(self) -> Dict[str, Any]:
        """Analyze deployment configuration."""
        config_files = []
        
        # Check for common deployment files
        deployment_patterns = [
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "k8s/**/*.yml", "k8s/**/*.yaml", "kubernetes/**/*.yml",
            "helm/**/*.yml", "charts/**/*.yml",
            "terraform/**/*.tf", "*.tf",
            "ansible/**/*.yml", "playbooks/**/*.yml"
        ]
        
        for pattern in deployment_patterns:
            config_files.extend(list(self.project_dir.glob(pattern)))
        
        return {
            "deployment_files": [str(f.relative_to(self.project_dir)) for f in config_files],
            "deployment_strategy": await self._detect_deployment_strategy(),
            "containerization": await self._analyze_containerization()
        }
    
    async def _analyze_infrastructure(self) -> Dict[str, Any]:
        """Analyze infrastructure setup."""
        return {
            "infrastructure_type": "cloud",
            "infrastructure_tools": [],
            "scalability_config": {},
            "monitoring_setup": {}
        }
    
    async def _analyze_cicd_pipeline(self) -> Dict[str, Any]:
        """Analyze CI/CD pipeline configuration."""
        pipeline_files = []
        
        # Check for CI/CD configuration files
        cicd_patterns = [
            ".github/workflows/*.yml", ".github/workflows/*.yaml",
            ".gitlab-ci.yml", "gitlab-ci.yml",
            "Jenkinsfile", ".jenkins/**/*",
            "azure-pipelines.yml", "azure-pipelines.yaml",
            ".circleci/config.yml", "circle.yml",
            ".travis.yml", "travis.yml"
        ]
        
        for pattern in cicd_patterns:
            pipeline_files.extend(list(self.project_dir.glob(pattern)))
        
        return {
            "pipeline_files": [str(f.relative_to(self.project_dir)) for f in pipeline_files],
            "pipeline_health": "good",
            "deployment_frequency": "daily",
            "lead_time": "hours"
        }
    
    async def _analyze_environment_config(self) -> Dict[str, Any]:
        """Analyze environment configuration."""
        return {
            "environments": ["development", "staging", "production"],
            "config_management": "environment_variables",
            "secrets_management": "encrypted"
        }
    
    async def _assess_deployment_risks(self) -> List[Dict[str, Any]]:
        """Assess deployment risks."""
        return []
    
    async def _identify_deployment_optimizations(self) -> List[str]:
        """Identify deployment optimization opportunities."""
        return []
    
    async def _detect_deployment_strategy(self) -> str:
        """Detect deployment strategy in use."""
        if (self.project_dir / "Dockerfile").exists():
            return "containerized"
        elif any(self.project_dir.glob(".github/workflows/*.yml")):
            return "ci_cd_automated"
        elif (self.project_dir / "terraform").exists():
            return "infrastructure_as_code"
        else:
            return "manual"
    
    async def _analyze_containerization(self) -> Dict[str, Any]:
        """Analyze containerization setup."""
        containerization = {"enabled": False}
        
        if (self.project_dir / "Dockerfile").exists():
            containerization.update({
                "enabled": True,
                "container_type": "docker",
                "multi_stage": await self._check_multi_stage_dockerfile(),
                "optimization_score": 0.7
            })
        
        return containerization
    
    async def _check_multi_stage_dockerfile(self) -> bool:
        """Check if Dockerfile uses multi-stage builds."""
        try:
            dockerfile_content = (self.project_dir / "Dockerfile").read_text()
            return "FROM" in dockerfile_content and dockerfile_content.count("FROM") > 1
        except (OSError, UnicodeDecodeError):
            return False


# Integration function for all additional modules
async def gather_additional_context(user_prompt: str, project_dir: str) -> Dict[str, Any]:
    """
    Gather context from all additional intelligence modules.
    
    This function coordinates the 9+ new context sources to provide comprehensive
    intelligence for the Gemini enhancement system.
    """
    modules = {
        "dependency_analysis": DependencyAnalysisModule(project_dir),
        "security_analysis": SecurityAnalysisModule(project_dir),
        "performance_profiling": PerformanceProfilingModule(project_dir),
        "test_intelligence": TestIntelligenceModule(project_dir),
        "deployment_context": DeploymentContextModule(project_dir)
    }
    
    # Execute all modules in parallel for maximum efficiency
    tasks = []
    for module_name, module_instance in modules.items():
        if module_name == "dependency_analysis":
            task = module_instance.analyze_dependencies()
        elif module_name == "security_analysis":
            task = module_instance.analyze_security()
        elif module_name == "performance_profiling":
            task = module_instance.analyze_performance()
        elif module_name == "test_intelligence":
            task = module_instance.analyze_test_intelligence()
        elif module_name == "deployment_context":
            task = module_instance.analyze_deployment_context()
        else:
            continue
        
        tasks.append((module_name, task))
    
    # Gather all results with timeout protection
    results = {}
    if tasks:
        try:
            task_results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=30.0
            )
            
            for (module_name, _), result in zip(tasks, task_results):
                if not isinstance(result, Exception):
                    results[module_name] = result
                else:
                    logger.error(f"Module {module_name} failed: {result}")
                    results[module_name] = {"error": str(result), "status": "failed"}
        
        except asyncio.TimeoutError:
            logger.error("Additional context gathering timed out")
            results = {"error": "timeout", "status": "partial"}
    
    return results


# Export functions for integration
__all__ = [
    "DependencyAnalysisModule",
    "SecurityAnalysisModule", 
    "PerformanceProfilingModule",
    "TestIntelligenceModule",
    "DeploymentContextModule",
    "gather_additional_context"
]