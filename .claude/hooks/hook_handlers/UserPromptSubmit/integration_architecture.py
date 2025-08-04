#!/usr/bin/env python3
"""
Integration Architecture for Gemini Enhancement System

This module defines how the comprehensive Gemini enhancement system integrates
with the existing UserPromptSubmit infrastructure while maintaining backward
compatibility and providing seamless upgrades.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from .ai_context_optimizer_optimized import OptimizedAIContextOptimizer
from .circuit_breaker_manager import CircuitBreakerManager
from .config import get_config
from .gemini_enhancement_architecture import (
    GeminiEnhancementArchitecture, enhanced_optimize_injection_with_ai)

logger = logging.getLogger(__name__)


class GeminiIntegrationManager:
    """
    Manages the integration between the existing system and the enhanced Gemini architecture.
    
    This class provides:
    1. Seamless migration from current system to enhanced system
    2. Feature flag management for gradual rollout
    3. Performance monitoring and fallback strategies
    4. Backward compatibility maintenance
    """
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.config = get_config()
        self.circuit_breaker = CircuitBreakerManager()
        
        # Initialize both systems for seamless migration
        self.legacy_optimizer = OptimizedAIContextOptimizer()
        self.enhanced_architecture = GeminiEnhancementArchitecture(project_dir)
        
        # Feature flags for gradual rollout
        self.feature_flags = {
            "enhanced_system_prompt": self._get_feature_flag("ENHANCED_SYSTEM_PROMPT", True),
            "structured_output": self._get_feature_flag("STRUCTURED_OUTPUT", True),
            "project_intelligence": self._get_feature_flag("PROJECT_INTELLIGENCE", True),
            "code_intelligence": self._get_feature_flag("CODE_INTELLIGENCE", True),
            "multimodal_processing": self._get_feature_flag("MULTIMODAL_PROCESSING", False),
            "advanced_context_sources": self._get_feature_flag("ADVANCED_CONTEXT_SOURCES", True),
            "performance_optimization": self._get_feature_flag("PERFORMANCE_OPTIMIZATION", True)
        }
    
    def _get_feature_flag(self, flag_name: str, default: bool) -> bool:
        """Get feature flag value from environment or config."""
        import os
        return os.environ.get(f"GEMINI_{flag_name}", str(default)).lower() == "true"
    
    async def optimize_context_with_enhanced_ai(self, user_prompt: str, raw_context: str) -> str:
        """
        Main entry point that intelligently routes between legacy and enhanced systems.
        
        This method:
        1. Analyzes the request complexity and context needs
        2. Determines the optimal processing path (legacy vs enhanced)
        3. Executes the optimization with appropriate fallback strategies
        4. Returns the enhanced prompt with structured insights
        """
        try:
            # Analyze request to determine processing strategy
            processing_strategy = await self._determine_processing_strategy(user_prompt, raw_context)
            
            if processing_strategy["use_enhanced"]:
                return await self._process_with_enhanced_system(user_prompt, raw_context, processing_strategy)
            else:
                return await self._process_with_legacy_system(user_prompt, raw_context)
                
        except Exception as e:
            logger.error(f"Enhanced AI optimization failed: {e}")
            # Always fallback to legacy system for reliability
            return await self._process_with_legacy_system(user_prompt, raw_context)
    
    async def _determine_processing_strategy(self, user_prompt: str, raw_context: str) -> Dict[str, Any]:
        """
        Intelligent strategy determination based on request characteristics.
        
        Considers:
        - Request complexity and scope
        - Available context richness
        - System performance and load
        - Feature flag configuration
        - Circuit breaker states
        """
        strategy = {
            "use_enhanced": False,
            "features_enabled": [],
            "fallback_reason": None,
            "confidence": 0.0
        }
        
        # Check circuit breakers first
        if not self.circuit_breaker.is_circuit_breaker_enabled("enhanced_ai_optimizer"):
            strategy["fallback_reason"] = "enhanced_ai_optimizer_circuit_breaker_disabled"
            return strategy
        
        # Analyze request complexity
        complexity_score = await self._analyze_request_complexity(user_prompt)
        context_richness = await self._analyze_context_richness(raw_context)
        
        # Determine if enhanced processing is beneficial
        enhancement_threshold = 0.3  # Minimum threshold for enhanced processing
        enhancement_score = (complexity_score * 0.6) + (context_richness * 0.4)
        
        if enhancement_score >= enhancement_threshold:
            strategy["use_enhanced"] = True
            strategy["confidence"] = enhancement_score
            
            # Determine which enhanced features to use
            if self.feature_flags["enhanced_system_prompt"] and complexity_score > 0.4:
                strategy["features_enabled"].append("enhanced_system_prompt")
            
            if self.feature_flags["structured_output"] and complexity_score > 0.5:
                strategy["features_enabled"].append("structured_output")
            
            if self.feature_flags["project_intelligence"] and context_richness > 0.6:
                strategy["features_enabled"].append("project_intelligence")
            
            if self.feature_flags["code_intelligence"] and self._is_code_related(user_prompt):
                strategy["features_enabled"].append("code_intelligence")
            
            if self.feature_flags["multimodal_processing"] and self._has_visual_indicators(user_prompt):
                strategy["features_enabled"].append("multimodal_processing")
            
            if self.feature_flags["advanced_context_sources"] and complexity_score > 0.7:
                strategy["features_enabled"].append("advanced_context_sources")
        else:
            strategy["fallback_reason"] = f"enhancement_score_too_low_{enhancement_score:.2f}"
        
        return strategy
    
    async def _analyze_request_complexity(self, user_prompt: str) -> float:
        """
        Analyze request complexity to determine if enhanced processing is needed.
        
        Factors:
        - Prompt length and structure
        - Technical terminology density
        - Multi-domain indicators
        - Ambiguity and context requirements
        """
        complexity_score = 0.0
        prompt_lower = user_prompt.lower()
        
        # Length complexity (longer prompts often need more context)
        length_score = min(len(user_prompt) / 500.0, 1.0)  # Normalize to max 1.0
        complexity_score += length_score * 0.2
        
        # Technical terminology density
        technical_terms = [
            'architecture', 'design', 'pattern', 'system', 'performance', 'optimize',
            'debug', 'error', 'exception', 'database', 'api', 'service', 'integration',
            'security', 'authentication', 'authorization', 'deployment', 'infrastructure',
            'scalability', 'maintainability', 'refactor', 'test', 'coverage'
        ]
        term_density = sum(1 for term in technical_terms if term in prompt_lower) / len(technical_terms)
        complexity_score += term_density * 0.3
        
        # Multi-domain indicators
        domains = {
            'frontend': ['ui', 'interface', 'component', 'react', 'vue', 'angular'],
            'backend': ['api', 'server', 'database', 'service', 'endpoint'],
            'devops': ['deploy', 'ci/cd', 'docker', 'kubernetes', 'pipeline'],
            'security': ['secure', 'auth', 'permission', 'vulnerability'],
            'data': ['database', 'query', 'model', 'schema', 'migration']
        }
        
        domains_mentioned = sum(1 for domain_terms in domains.values() 
                              if any(term in prompt_lower for term in domain_terms))
        domain_complexity = min(domains_mentioned / 3.0, 1.0)  # Multi-domain = complex
        complexity_score += domain_complexity * 0.3
        
        # Ambiguity indicators (questions, comparisons, open-ended requests)
        ambiguity_indicators = ['how', 'what', 'why', 'which', 'should', 'best', 'better', 'compare']
        ambiguity_score = sum(1 for indicator in ambiguity_indicators if indicator in prompt_lower.split())
        normalized_ambiguity = min(ambiguity_score / 5.0, 1.0)
        complexity_score += normalized_ambiguity * 0.2
        
        return min(complexity_score, 1.0)
    
    async def _analyze_context_richness(self, raw_context: str) -> float:
        """
        Analyze context richness to determine enhancement value.
        
        Rich context benefits more from enhanced processing that can synthesize
        and structure the information effectively.
        """
        if not raw_context:
            return 0.0
        
        richness_score = 0.0
        
        # Context volume (more context = potentially richer)
        volume_score = min(len(raw_context) / 10000.0, 1.0)  # Normalize to max 1.0
        richness_score += volume_score * 0.3
        
        # Context diversity (different types of information)
        context_types = [
            'git', 'system', 'test', 'error', 'performance', 'memory', 'cpu',
            'network', 'file', 'process', 'dependency', 'coverage', 'commit'
        ]
        diversity_score = sum(1 for ctx_type in context_types if ctx_type in raw_context.lower())
        normalized_diversity = min(diversity_score / len(context_types), 1.0)
        richness_score += normalized_diversity * 0.4
        
        # Structured information indicators
        structure_indicators = ['<', '>', '{', '}', '[', ']', ':', '|', '─', '•']
        structure_density = sum(raw_context.count(indicator) for indicator in structure_indicators)
        normalized_structure = min(structure_density / 100.0, 1.0)
        richness_score += normalized_structure * 0.3
        
        return min(richness_score, 1.0)
    
    def _is_code_related(self, user_prompt: str) -> bool:
        """Check if the prompt is code-related and would benefit from code intelligence."""
        code_indicators = [
            'code', 'function', 'method', 'class', 'variable', 'import', 'export',
            'debug', 'error', 'exception', 'bug', 'fix', 'implement', 'refactor',
            'test', 'unittest', 'integration', 'api', 'endpoint', 'database',
            'query', 'optimization', 'performance', 'memory', 'algorithm'
        ]
        return any(indicator in user_prompt.lower() for indicator in code_indicators)
    
    def _has_visual_indicators(self, user_prompt: str) -> bool:
        """Check if the prompt mentions visual elements that would benefit from multimodal processing."""
        visual_indicators = [
            'diagram', 'chart', 'graph', 'image', 'screenshot', 'ui', 'interface',
            'design', 'layout', 'wireframe', 'mockup', 'visualization', 'architecture'
        ]
        return any(indicator in user_prompt.lower() for indicator in visual_indicators)
    
    async def _process_with_enhanced_system(self, user_prompt: str, raw_context: str, strategy: Dict[str, Any]) -> str:
        """Process with the enhanced Gemini architecture system."""
        logger.info(f"Using enhanced system with features: {strategy['features_enabled']}")
        
        try:
            # Use the enhanced architecture for full processing
            result = await enhanced_optimize_injection_with_ai(user_prompt, raw_context, self.project_dir)
            
            # Add metadata about the enhancement
            enhancement_metadata = {
                "enhanced_processing": True,
                "features_used": strategy["features_enabled"],
                "confidence": strategy["confidence"],
                "processing_time": "enhanced"
            }
            
            return f"{result}\n\n<!-- Enhancement Metadata: {json.dumps(enhancement_metadata)} -->"
            
        except Exception as e:
            logger.error(f"Enhanced system processing failed: {e}")
            # Fallback to legacy system
            return await self._process_with_legacy_system(user_prompt, raw_context)
    
    async def _process_with_legacy_system(self, user_prompt: str, raw_context: str) -> str:
        """Process with the legacy optimization system."""
        logger.info("Using legacy optimization system")
        
        try:
            result = await self.legacy_optimizer.optimize_context_with_ai(user_prompt, raw_context)
            
            # Add minimal static content
            static_suffix = "\nThink optimal. Consult with ZEN whenever possible."
            return f"CONTEXT: {result}\n{static_suffix}"
            
        except Exception as e:
            logger.error(f"Legacy system processing failed: {e}")
            # Final fallback to raw context
            return raw_context


class MigrationManager:
    """
    Manages migration from the current system to the enhanced architecture.
    
    Provides:
    - Gradual feature rollout
    - A/B testing capabilities
    - Performance monitoring
    - Rollback strategies
    """
    
    def __init__(self):
        self.migration_phases = {
            "phase_1_enhanced_prompts": {"enabled": True, "rollout_percentage": 100},
            "phase_2_structured_output": {"enabled": True, "rollout_percentage": 100},
            "phase_3_intelligence_modules": {"enabled": True, "rollout_percentage": 80},
            "phase_4_multimodal_support": {"enabled": False, "rollout_percentage": 0},
            "phase_5_full_enhancement": {"enabled": False, "rollout_percentage": 0}
        }
    
    def should_use_feature(self, feature_name: str, user_hash: Optional[str] = None) -> bool:
        """Determine if a feature should be used based on rollout percentage."""
        if feature_name not in self.migration_phases:
            return False
        
        phase = self.migration_phases[feature_name]
        if not phase["enabled"]:
            return False
        
        rollout_percentage = phase["rollout_percentage"]
        if rollout_percentage >= 100:
            return True
        
        # Use user hash for consistent rollout (same user gets same experience)
        if user_hash:
            import hashlib
            hash_value = int(hashlib.md5(user_hash.encode()).hexdigest()[:8], 16)
            return (hash_value % 100) < rollout_percentage
        
        # Random rollout if no user hash
        import random
        return random.randint(1, 100) <= rollout_percentage
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and metrics."""
        return {
            "migration_phases": self.migration_phases,
            "overall_progress": self._calculate_overall_progress(),
            "next_phase": self._get_next_phase(),
            "rollback_ready": True
        }
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall migration progress percentage."""
        total_phases = len(self.migration_phases)
        completed_phases = sum(1 for phase in self.migration_phases.values() 
                             if phase["enabled"] and phase["rollout_percentage"] == 100)
        return (completed_phases / total_phases) * 100
    
    def _get_next_phase(self) -> Optional[str]:
        """Get the next phase to be rolled out."""
        for phase_name, phase_config in self.migration_phases.items():
            if not phase_config["enabled"] or phase_config["rollout_percentage"] < 100:
                return phase_name
        return None


# Updated integration function for backward compatibility
async def optimize_injection_with_enhanced_ai(user_prompt: str, raw_context: str, project_dir: str = ".") -> str:
    """
    Enhanced entry point that maintains backward compatibility while providing new capabilities.
    
    This function serves as the main integration point between the existing system
    and the enhanced Gemini architecture, providing intelligent routing and fallback strategies.
    """
    try:
        integration_manager = GeminiIntegrationManager(project_dir)
        return await integration_manager.optimize_context_with_enhanced_ai(user_prompt, raw_context)
    except Exception as e:
        logger.error(f"Integration manager failed: {e}")
        # Ultimate fallback to original system
        try:
            optimizer = OptimizedAIContextOptimizer()
            result = await optimizer.optimize_context_with_ai(user_prompt, raw_context)
            return f"CONTEXT: {result}\nThink optimal. Consult with ZEN whenever possible."
        except Exception as final_e:
            logger.error(f"All systems failed: {final_e}")
            return raw_context


# Performance monitoring and optimization
class PerformanceMonitor:
    """Monitor performance of the enhancement system."""
    
    def __init__(self):
        self.metrics = {
            "enhanced_requests": 0,
            "legacy_requests": 0,
            "enhancement_time": [],
            "legacy_time": [],
            "error_rate": 0.0,
            "fallback_rate": 0.0
        }
    
    def record_request(self, request_type: str, processing_time: float, success: bool):
        """Record request metrics for performance analysis."""
        if request_type == "enhanced":
            self.metrics["enhanced_requests"] += 1
            self.metrics["enhancement_time"].append(processing_time)
        else:
            self.metrics["legacy_requests"] += 1
            self.metrics["legacy_time"].append(processing_time)
        
        if not success:
            total_requests = self.metrics["enhanced_requests"] + self.metrics["legacy_requests"]
            self.metrics["error_rate"] = (self.metrics["error_rate"] * (total_requests - 1) + 1) / total_requests
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring and optimization."""
        return {
            "total_requests": self.metrics["enhanced_requests"] + self.metrics["legacy_requests"],
            "enhancement_adoption": self.metrics["enhanced_requests"] / max(1, self.metrics["enhanced_requests"] + self.metrics["legacy_requests"]),
            "average_enhancement_time": sum(self.metrics["enhancement_time"]) / max(1, len(self.metrics["enhancement_time"])),
            "average_legacy_time": sum(self.metrics["legacy_time"]) / max(1, len(self.metrics["legacy_time"])),
            "error_rate": self.metrics["error_rate"],
            "performance_improvement": self._calculate_performance_improvement()
        }
    
    def _calculate_performance_improvement(self) -> float:
        """Calculate performance improvement of enhanced system."""
        if not self.metrics["enhancement_time"] or not self.metrics["legacy_time"]:
            return 0.0
        
        avg_enhanced = sum(self.metrics["enhancement_time"]) / len(self.metrics["enhancement_time"])
        avg_legacy = sum(self.metrics["legacy_time"]) / len(self.metrics["legacy_time"])
        
        if avg_legacy == 0:
            return 0.0
        
        return (avg_legacy - avg_enhanced) / avg_legacy * 100  # Percentage improvement