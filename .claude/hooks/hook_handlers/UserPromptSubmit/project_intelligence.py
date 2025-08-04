"""
Project Intelligence Module

Gathers comprehensive project context by analyzing configuration files,
dependencies, architecture patterns, and development setup.
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Comprehensive project analysis results."""
    project_type: str
    frameworks: Dict[str, str]
    build_system: Dict[str, Any]
    testing: Dict[str, Any]
    architecture: Dict[str, Any]
    dependencies: Dict[str, List[str]]
    cicd: Dict[str, Any]
    conventions: Dict[str, Any]
    tech_stack: List[str]
    project_scale: str
    confidence_score: float


class ProjectIntelligenceGatherer:
    """Analyzes project structure and gathers intelligence for context enhancement."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.context = ProjectContext(
            project_type="unknown",
            frameworks={},
            build_system={},
            testing={},
            architecture={},
            dependencies={"main": [], "dev": [], "peer": []},
            cicd={},
            conventions={},
            tech_stack=[],
            project_scale="small",
            confidence_score=0.0
        )
    
    def gather_intelligence(self) -> Dict[str, Any]:
        """Main entry point to gather all project intelligence."""
        try:
            self._detect_project_type()
            self._analyze_frameworks()
            self._analyze_build_system()
            self._analyze_testing_setup()
            self._analyze_architecture()
            self._analyze_dependencies()
            self._analyze_cicd()
            self._analyze_conventions()
            self._calculate_project_scale()
            self._calculate_confidence()
            
            return asdict(self.context)
        except Exception as e:
            logger.error(f"Error gathering project intelligence: {e}")
            return asdict(self.context)
    
    def _detect_project_type(self):
        """Detect project type from configuration files and structure."""
        type_indicators = {
            "web_app": ["package.json", "src/index.html", "public/index.html", "app.py", "main.py", "server.py"],
            "cli_tool": ["setup.py", "pyproject.toml", "Cargo.toml", "main.go", "cmd/"],
            "library": ["setup.py", "pyproject.toml", "lib/", "src/lib/", "Cargo.toml"],
            "api_service": ["requirements.txt", "app.py", "main.py", "server.py", "api/", "routes/"],
            "mobile_app": ["package.json", "android/", "ios/", "pubspec.yaml", "Podfile"],
            "desktop_app": ["package.json", "main.js", "Cargo.toml", "setup.py"],
            "data_project": ["jupyter/", "notebooks/", "data/", "requirements.txt", "environment.yml"],
            "infrastructure": ["terraform/", "ansible/", "docker-compose.yml", "k8s/", "helm/"]
        }
        
        scores = {}
        for project_type, indicators in type_indicators.items():
            score = sum(1 for indicator in indicators if self._file_exists(indicator))
            if score > 0:
                scores[project_type] = score
        
        if scores:
            self.context.project_type = max(scores, key=scores.get)
        
        # Additional heuristics
        if self._file_exists("package.json"):
            package_json = self._read_json("package.json")
            if package_json:
                scripts = package_json.get("scripts", {})
                if "start" in scripts and "build" in scripts:
                    self.context.project_type = "web_app"
                elif "test" in scripts and not "start" in scripts:
                    self.context.project_type = "library"
    
    def _analyze_frameworks(self):
        """Identify frameworks and their versions."""
        # JavaScript/TypeScript frameworks
        if self._file_exists("package.json"):
            package_json = self._read_json("package.json")
            if package_json:
                deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
                
                framework_patterns = {
                    "react": ["react", "@types/react"],
                    "vue": ["vue", "@vue/cli"],
                    "angular": ["@angular/core", "@angular/cli"],
                    "next": ["next"],
                    "nuxt": ["nuxt"],
                    "svelte": ["svelte"],
                    "express": ["express"],
                    "fastify": ["fastify"],
                    "nestjs": ["@nestjs/core"]
                }
                
                for framework, patterns in framework_patterns.items():
                    for pattern in patterns:
                        if pattern in deps:
                            self.context.frameworks[framework] = deps[pattern]
                            break
        
        # Python frameworks
        requirements_files = ["requirements.txt", "pyproject.toml", "Pipfile"]
        for req_file in requirements_files:
            if self._file_exists(req_file):
                content = self._read_file(req_file)
                if content:
                    python_frameworks = {
                        "django": r"django[>=<~]*([\d.]+)",
                        "flask": r"flask[>=<~]*([\d.]+)",
                        "fastapi": r"fastapi[>=<~]*([\d.]+)",
                        "tornado": r"tornado[>=<~]*([\d.]+)",
                        "pyramid": r"pyramid[>=<~]*([\d.]+)",
                        "sanic": r"sanic[>=<~]*([\d.]+)"
                    }
                    
                    for framework, pattern in python_frameworks.items():
                        match = re.search(pattern, content.lower())
                        if match:
                            self.context.frameworks[framework] = match.group(1) if match.group(1) else "unknown"
        
        # Add to tech stack
        self.context.tech_stack.extend(self.context.frameworks.keys())
    
    def _analyze_build_system(self):
        """Analyze build system configuration."""
        build_systems = {
            "npm": "package.json",
            "yarn": "yarn.lock",
            "pnpm": "pnpm-lock.yaml",
            "pip": "requirements.txt",
            "poetry": "pyproject.toml",
            "pipenv": "Pipfile",
            "cargo": "Cargo.toml",
            "go": "go.mod",
            "maven": "pom.xml",
            "gradle": "build.gradle",
            "make": "Makefile",
            "cmake": "CMakeLists.txt"
        }
        
        for build_system, config_file in build_systems.items():
            if self._file_exists(config_file):
                self.context.build_system[build_system] = True
                
                # Get version info if available
                if build_system == "npm" and self._file_exists("package.json"):
                    package_json = self._read_json("package.json")
                    if package_json:
                        self.context.build_system["npm_version"] = package_json.get("engines", {}).get("npm")
                        self.context.build_system["node_version"] = package_json.get("engines", {}).get("node")
                        self.context.build_system["scripts"] = list(package_json.get("scripts", {}).keys())
    
    def _analyze_testing_setup(self):
        """Analyze testing framework and configuration."""
        # JavaScript testing
        if self._file_exists("package.json"):
            package_json = self._read_json("package.json")
            if package_json:
                deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
                
                test_frameworks = {
                    "jest": "jest",
                    "mocha": "mocha",
                    "jasmine": "jasmine",
                    "cypress": "cypress",
                    "playwright": "playwright",
                    "vitest": "vitest"
                }
                
                for framework, package in test_frameworks.items():
                    if package in deps:
                        self.context.testing[framework] = deps[package]
        
        # Python testing
        python_test_files = ["pytest.ini", "tox.ini", "setup.cfg"]
        for test_file in python_test_files:
            if self._file_exists(test_file):
                self.context.testing["pytest"] = True
        
        # Test directories
        test_dirs = ["test/", "tests/", "__tests__/", "spec/"]
        for test_dir in test_dirs:
            if self._dir_exists(test_dir):
                self.context.testing[f"has_{test_dir.rstrip('/')}"] = True
        
        # Coverage configuration
        coverage_files = [".coveragerc", "coverage.json", "jest.config.js", "jest.config.json"]
        for coverage_file in coverage_files:
            if self._file_exists(coverage_file):
                self.context.testing["coverage_configured"] = True
                break
    
    def _analyze_architecture(self):
        """Analyze architectural patterns and structure."""
        # Directory structure analysis
        common_patterns = {
            "mvc": ["models/", "views/", "controllers/"],
            "clean_architecture": ["domain/", "infrastructure/", "application/"],
            "hexagonal": ["adapters/", "ports/", "domain/"],
            "microservices": ["services/", "api-gateway/", "docker-compose.yml"],
            "monorepo": ["packages/", "apps/", "libs/"],
            "component_based": ["components/", "src/components/"],
            "modular": ["modules/", "src/modules/"]
        }
        
        for pattern, indicators in common_patterns.items():
            score = sum(1 for indicator in indicators if self._dir_exists(indicator))
            if score >= len(indicators) * 0.6:  # 60% match threshold
                self.context.architecture[pattern] = True
        
        # Framework-specific patterns
        if "django" in self.context.frameworks:
            django_patterns = ["models.py", "views.py", "urls.py", "admin.py"]
            if any(self._file_exists(f"*/{pattern}") for pattern in django_patterns):
                self.context.architecture["django_app_structure"] = True
        
        if "react" in self.context.frameworks:
            react_patterns = ["src/components/", "src/hooks/", "src/context/"]
            if any(self._dir_exists(pattern) for pattern in react_patterns):
                self.context.architecture["react_component_structure"] = True
    
    def _analyze_dependencies(self):
        """Analyze project dependencies."""
        # Node.js dependencies
        if self._file_exists("package.json"):
            package_json = self._read_json("package.json")
            if package_json:
                self.context.dependencies["main"] = list(package_json.get("dependencies", {}).keys())
                self.context.dependencies["dev"] = list(package_json.get("devDependencies", {}).keys())
                self.context.dependencies["peer"] = list(package_json.get("peerDependencies", {}).keys())
        
        # Python dependencies
        if self._file_exists("requirements.txt"):
            content = self._read_file("requirements.txt")
            if content:
                deps = [line.split("==")[0].split(">=")[0].split("~=")[0].strip() 
                       for line in content.split("\n") 
                       if line.strip() and not line.startswith("#")]
                self.context.dependencies["main"].extend(deps)
        
        # Analyze dependency health
        total_deps = sum(len(deps) for deps in self.context.dependencies.values())
        if total_deps > 100:
            self.context.dependencies["health"] = "heavy"
        elif total_deps > 50:
            self.context.dependencies["health"] = "moderate"
        else:
            self.context.dependencies["health"] = "light"
    
    def _analyze_cicd(self):
        """Analyze CI/CD configuration."""
        cicd_indicators = {
            "github_actions": ".github/workflows/",
            "gitlab_ci": ".gitlab-ci.yml",
            "jenkins": "Jenkinsfile",
            "travis": ".travis.yml",
            "circle_ci": ".circleci/config.yml",
            "azure_pipelines": "azure-pipelines.yml",
            "docker": "Dockerfile",
            "docker_compose": "docker-compose.yml",
            "kubernetes": "k8s/",
            "helm": "charts/"
        }
        
        for system, indicator in cicd_indicators.items():
            if self._file_exists(indicator) or self._dir_exists(indicator):
                self.context.cicd[system] = True
        
        # Analyze GitHub Actions workflows
        if self._dir_exists(".github/workflows/"):
            workflow_files = self._list_files(".github/workflows/", "*.yml", "*.yaml")
            self.context.cicd["github_workflows"] = len(workflow_files)
    
    def _analyze_conventions(self):
        """Analyze code conventions and standards."""
        # Linting and formatting
        lint_configs = {
            "eslint": [".eslintrc.js", ".eslintrc.json", ".eslintrc.yml"],
            "prettier": [".prettierrc", ".prettierrc.json", ".prettierrc.yml"],
            "black": ["pyproject.toml", "setup.cfg"],
            "flake8": [".flake8", "setup.cfg", "tox.ini"],
            "pylint": [".pylintrc", "pylint.cfg"],
            "editorconfig": [".editorconfig"],
            "gitignore": [".gitignore"]
        }
        
        for tool, configs in lint_configs.items():
            if any(self._file_exists(config) for config in configs):
                self.context.conventions[tool] = True
        
        # TypeScript configuration
        if self._file_exists("tsconfig.json"):
            self.context.conventions["typescript"] = True
            self.context.tech_stack.append("typescript")
        
        # Pre-commit hooks
        if self._file_exists(".pre-commit-config.yaml"):
            self.context.conventions["pre_commit"] = True
    
    def _calculate_project_scale(self):
        """Estimate project scale based on various indicators."""
        scale_indicators = {
            "lines_of_code": self._estimate_loc(),
            "file_count": self._count_files(),
            "dependency_count": sum(len(deps) for deps in self.context.dependencies.values()),
            "has_tests": bool(self.context.testing),
            "has_ci": bool(self.context.cicd),
            "framework_count": len(self.context.frameworks)
        }
        
        score = 0
        if scale_indicators["lines_of_code"] > 10000:
            score += 3
        elif scale_indicators["lines_of_code"] > 1000:
            score += 2
        elif scale_indicators["lines_of_code"] > 100:
            score += 1
        
        if scale_indicators["file_count"] > 100:
            score += 2
        elif scale_indicators["file_count"] > 20:
            score += 1
        
        if scale_indicators["dependency_count"] > 50:
            score += 2
        elif scale_indicators["dependency_count"] > 10:
            score += 1
        
        if scale_indicators["has_tests"]:
            score += 1
        if scale_indicators["has_ci"]:
            score += 1
        if scale_indicators["framework_count"] > 2:
            score += 1
        
        if score >= 7:
            self.context.project_scale = "enterprise"
        elif score >= 4:
            self.context.project_scale = "medium"
        else:
            self.context.project_scale = "small"
    
    def _calculate_confidence(self):
        """Calculate confidence score for the analysis."""
        indicators_found = 0
        total_indicators = 8
        
        if self.context.project_type != "unknown":
            indicators_found += 1
        if self.context.frameworks:
            indicators_found += 1
        if self.context.build_system:
            indicators_found += 1
        if self.context.testing:
            indicators_found += 1
        if self.context.architecture:
            indicators_found += 1
        if any(self.context.dependencies.values()):
            indicators_found += 1
        if self.context.cicd:
            indicators_found += 1
        if self.context.conventions:
            indicators_found += 1
        
        self.context.confidence_score = indicators_found / total_indicators
    
    # Helper methods
    def _file_exists(self, path: str) -> bool:
        """Check if file exists, supporting wildcards."""
        if "*" in path:
            return bool(list(self.root_path.glob(path)))
        return (self.root_path / path).exists()
    
    def _dir_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return (self.root_path / path).is_dir()
    
    def _read_file(self, path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            return (self.root_path / path).read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Could not read {path}: {e}")
            return None
    
    def _read_json(self, path: str) -> Optional[Dict]:
        """Read JSON file safely."""
        content = self._read_file(path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.debug(f"Could not parse JSON from {path}: {e}")
        return None
    
    def _list_files(self, directory: str, *patterns: str) -> List[str]:
        """List files matching patterns in directory."""
        try:
            dir_path = self.root_path / directory
            if not dir_path.is_dir():
                return []
            
            files = []
            for pattern in patterns:
                files.extend([str(f) for f in dir_path.glob(pattern)])
            return files
        except Exception:
            return []
    
    def _estimate_loc(self) -> int:
        """Estimate lines of code (rough approximation)."""
        try:
            # Simple estimation based on common source file patterns
            patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", 
                       "**/*.go", "**/*.rs", "**/*.java", "**/*.cpp", "**/*.c"]
            
            total_lines = 0
            for pattern in patterns:
                for file_path in self.root_path.glob(pattern):
                    if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                        try:
                            content = file_path.read_text(encoding='utf-8')
                            total_lines += len([line for line in content.split('\n') if line.strip()])
                        except Exception:
                            continue
            
            return total_lines
        except Exception:
            return 0
    
    def _count_files(self) -> int:
        """Count total source files."""
        try:
            patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", 
                       "**/*.go", "**/*.rs", "**/*.java", "**/*.cpp", "**/*.c"]
            
            files = set()
            for pattern in patterns:
                for file_path in self.root_path.glob(pattern):
                    if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                        files.add(str(file_path))
            
            return len(files)
        except Exception:
            return 0


def gather_project_intelligence(root_path: str) -> Dict[str, Any]:
    """Main function to gather project intelligence."""
    gatherer = ProjectIntelligenceGatherer(root_path)
    return gatherer.gather_intelligence()


if __name__ == "__main__":
    # Test the module
    import sys
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    intelligence = gather_project_intelligence(root_path)
    print(json.dumps(intelligence, indent=2))