#!/usr/bin/env python3
"""Token efficiency optimizer for UserPromptSubmit hook."""

import hashlib
import os
import re
import time
from typing import Dict, List, Optional, Tuple


class TokenOptimizer:
    """Optimizes context for token efficiency while maintaining quality."""
    
    def __init__(self):
        """Initialize token optimizer."""
        self.token_budget = 15000  # 75% of 200k token limit for context
        self.cache = {}
        self.cache_ttl = 300  # 5 minute cache
        
        # Priority patterns for content preservation
        self.priority_patterns = [
            r'error|failed|exception',  # Errors (highest priority)
            r'git.*(?:commit|branch|status)',  # Git info
            r'test.*(?:failed|passed)',  # Test results
            r'performance|slow|timeout',  # Performance issues
            r'TODO|FIXME|XXX',  # Code markers
        ]
        
        # Redundant patterns to remove
        self.redundant_patterns = [
            r'Successfully.*\n',  # Success messages
            r'DEBUG:.*\n',  # Debug logs
            r'INFO:.*\n',  # Info logs
            r'\n\s*\n\s*\n',  # Multiple newlines
            r'#.*generated.*\n',  # Generated comments
        ]
    
    def optimize_context(self, raw_context: str, user_prompt: str) -> str:
        """Optimize context for token efficiency."""
        # Check cache first
        cache_key = self._get_cache_key(raw_context, user_prompt)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Estimate current token count
        current_tokens = self._estimate_tokens(raw_context)
        
        if current_tokens <= self.token_budget:
            # Under budget, minimal optimization
            optimized = self._minimal_optimization(raw_context)
        else:
            # Over budget, aggressive optimization
            optimized = self._aggressive_optimization(raw_context, user_prompt)
        
        # Cache result
        self._cache_result(cache_key, optimized)
        return optimized
    
    def _get_cache_key(self, context: str, prompt: str) -> str:
        """Generate cache key from content hash."""
        combined = f"{context[:1000]}{prompt}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Get cached optimization result if valid."""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
        return None
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache optimization result with cleanup."""
        now = time.time()
        self.cache[cache_key] = (result, now)
        
        # Cleanup old entries
        for key, (_, timestamp) in list(self.cache.items()):
            if now - timestamp > self.cache_ttl:
                del self.cache[key]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 4 chars per token)."""
        return len(text) // 4
    
    def _minimal_optimization(self, context: str) -> str:
        """Apply minimal optimizations when under budget."""
        # Remove redundant patterns
        optimized = context
        for pattern in self.redundant_patterns:
            optimized = re.sub(pattern, '', optimized, flags=re.MULTILINE)
        
        # Clean up whitespace
        optimized = re.sub(r'\n\s*\n', '\n', optimized)
        optimized = optimized.strip()
        
        return optimized
    
    def _aggressive_optimization(self, context: str, user_prompt: str) -> str:
        """Apply aggressive optimizations when over budget."""
        lines = context.split('\n')
        
        # Categorize lines by priority
        priority_lines = []
        normal_lines = []
        
        # Detect prompt-relevant terms
        prompt_terms = set(re.findall(r'\b\w{3,}\b', user_prompt.lower()))
        
        for line in lines:
            line_lower = line.lower()
            
            # Check priority patterns
            is_priority = any(re.search(pattern, line_lower) for pattern in self.priority_patterns)
            
            # Check prompt relevance
            line_terms = set(re.findall(r'\b\w{3,}\b', line_lower))
            is_relevant = bool(prompt_terms.intersection(line_terms))
            
            if is_priority or is_relevant:
                priority_lines.append(line)
            else:
                normal_lines.append(line)
        
        # Build optimized context within budget
        result_lines = priority_lines.copy()
        current_size = len('\n'.join(result_lines))
        target_size = self.token_budget * 4  # Convert tokens to chars
        
        # Add normal lines until budget exhausted
        for line in normal_lines:
            if current_size + len(line) + 1 < target_size:
                result_lines.append(line)
                current_size += len(line) + 1
            else:
                break
        
        # Final cleanup
        result = '\n'.join(result_lines)
        result = re.sub(r'\n\s*\n', '\n', result)
        result = result.strip()
        
        # Add truncation notice if needed
        if len(result) < len(context) * 0.8:
            result += '\n[Context truncated for token efficiency]'
        
        return result
    
    def get_optimization_stats(self) -> Dict[str, int]:
        """Get optimization statistics."""
        return {
            'cache_size': len(self.cache),
            'token_budget': self.token_budget,
            'cache_ttl': self.cache_ttl,
        }


# Global instance for reuse
_token_optimizer = None


def get_token_optimizer() -> TokenOptimizer:
    """Get or create global token optimizer instance."""
    global _token_optimizer
    if _token_optimizer is None:
        _token_optimizer = TokenOptimizer()
    return _token_optimizer


def optimize_for_tokens(raw_context: str, user_prompt: str) -> str:
    """Optimize context for token efficiency (convenience function)."""
    optimizer = get_token_optimizer()
    return optimizer.optimize_context(raw_context, user_prompt)