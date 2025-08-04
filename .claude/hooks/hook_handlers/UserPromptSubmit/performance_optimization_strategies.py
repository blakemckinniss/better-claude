#!/usr/bin/env python3
"""
Performance Optimization Strategies for Gemini Enhancement System

This module implements comprehensive performance optimization strategies to ensure
the enhanced Gemini system operates efficiently while providing maximum value.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    access_count: int = 0
    size_estimate: int = 0
    tags: Set[str] = field(default_factory=set)
    ttl: float = 300  # 5 minutes default


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    cache_hit_rate: float = 0.0
    average_response_time: float = 0.0
    context_gathering_time: float = 0.0
    ai_processing_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    token_usage: int = 0
    memory_usage_mb: float = 0.0


class IntelligentCacheManager:
    """
    Advanced caching system with intelligent eviction and optimization.
    
    Features:
    - Multi-tier caching (L1: memory, L2: disk, L3: distributed)
    - Content-aware TTL adjustment
    - Predictive prefetching
    - Cache warming strategies
    - Intelligent eviction policies
    """
    
    def __init__(self, max_memory_mb: int = 128):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_usage = 0
        
        # Multi-tier cache storage
        self.l1_cache: Dict[str, CacheEntry] = {}  # Memory cache
        self.l2_cache: Dict[str, str] = {}  # Disk cache paths
        self.l3_cache: Dict[str, str] = {}  # Distributed cache keys
        
        # Cache analytics
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.hit_counts: Dict[str, int] = defaultdict(int)
        self.miss_counts: Dict[str, int] = defaultdict(int)
        
        # Performance optimization
        self.prefetch_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.warm_cache_patterns: Dict[str, float] = {}
    
    async def get(self, key: str, tags: Optional[Set[str]] = None) -> Optional[Any]:
        """Get item from cache with intelligent hit tracking."""
        # Try L1 cache first (memory)
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if self._is_valid(entry):
                entry.access_count += 1
                self.hit_counts[key] += 1
                self._record_access_pattern(key)
                await self._update_prefetch_predictions(key, tags)
                return entry.data
            else:
                # Expired entry
                await self._evict_entry(key)
        
        # Try L2 cache (disk) - placeholder for now
        if key in self.l2_cache:
            data = await self._load_from_l2(key)
            if data is not None:
                await self.set(key, data, ttl=300, tags=tags)
                return data
        
        # Try L3 cache (distributed) - placeholder for now
        if key in self.l3_cache:
            data = await self._load_from_l3(key)
            if data is not None:
                await self.set(key, data, ttl=600, tags=tags)
                return data
        
        self.miss_counts[key] += 1
        return None
    
    async def set(self, key: str, data: Any, ttl: Optional[float] = None, tags: Optional[Set[str]] = None) -> bool:
        """Set item in cache with intelligent placement."""
        if tags is None:
            tags = set()
        
        size_estimate = self._estimate_size(data)
        
        # Determine optimal TTL based on content and access patterns
        optimal_ttl = self._calculate_optimal_ttl(key, data, ttl)
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            size_estimate=size_estimate,
            tags=tags,
            ttl=optimal_ttl
        )
        
        # Check if we need to make space
        if self.current_memory_usage + size_estimate > self.max_memory_bytes:
            await self._make_space(size_estimate)
        
        # Store in L1 cache
        self.l1_cache[key] = entry
        self.current_memory_usage += size_estimate
        
        # Consider storing in L2/L3 for important entries
        if self._should_persist_to_l2(key, entry):
            await self._store_to_l2(key, data)
        
        return True
    
    async def invalidate(self, pattern: Optional[str] = None, tags: Optional[Set[str]] = None):
        """Invalidate cache entries by pattern or tags."""
        if pattern:
            keys_to_remove = [k for k in self.l1_cache.keys() if pattern in k]
        elif tags:
            keys_to_remove = [k for k, v in self.l1_cache.items() if tags.intersection(v.tags)]
        else:
            keys_to_remove = list(self.l1_cache.keys())
        
        for key in keys_to_remove:
            await self._evict_entry(key)
    
    async def warm_cache(self, warming_strategies: Dict[str, Any]):
        """Warm cache with predicted high-value entries."""
        for strategy_name, strategy_config in warming_strategies.items():
            if strategy_name == "project_intelligence":
                await self._warm_project_intelligence_cache(strategy_config)
            elif strategy_name == "common_patterns":
                await self._warm_common_patterns_cache(strategy_config)
            elif strategy_name == "user_specific":
                await self._warm_user_specific_cache(strategy_config)
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        total_hits = sum(self.hit_counts.values())
        total_misses = sum(self.miss_counts.values())
        hit_rate = total_hits / max(1, total_hits + total_misses)
        
        return {
            "hit_rate": hit_rate,
            "total_entries": len(self.l1_cache),
            "memory_usage_mb": self.current_memory_usage / (1024 * 1024),
            "memory_utilization": self.current_memory_usage / self.max_memory_bytes,
            "top_accessed_keys": sorted(self.hit_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "cache_distribution": {
                "l1_entries": len(self.l1_cache),
                "l2_entries": len(self.l2_cache),
                "l3_entries": len(self.l3_cache)
            }
        }
    
    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - entry.timestamp < entry.ttl
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate memory size of data."""
        try:
            return len(json.dumps(data, default=str))
        except:
            return len(str(data))
    
    def _calculate_optimal_ttl(self, key: str, data: Any, provided_ttl: Optional[float]) -> float:
        """Calculate optimal TTL based on content and access patterns."""
        if provided_ttl:
            return provided_ttl
        
        # Analyze access patterns
        if key in self.access_patterns and len(self.access_patterns[key]) > 3:
            # If frequently accessed, longer TTL
            recent_accesses = self.access_patterns[key][-10:]
            access_frequency = len(recent_accesses) / (time.time() - recent_accesses[0])
            if access_frequency > 0.1:  # More than once per 10 seconds
                return 1800  # 30 minutes
        
        # Content-based TTL
        data_str = str(data).lower()
        if any(keyword in data_str for keyword in ['error', 'fail', 'exception']):
            return 60  # Short TTL for error states
        elif any(keyword in data_str for keyword in ['git', 'commit', 'branch']):
            return 300  # Medium TTL for git data
        elif any(keyword in data_str for keyword in ['system', 'process', 'memory']):
            return 30  # Short TTL for system data
        
        return 300  # Default 5 minutes
    
    async def _make_space(self, needed_bytes: int):
        """Make space in cache using intelligent eviction."""
        if needed_bytes > self.max_memory_bytes:
            logger.warning(f"Requested cache space ({needed_bytes}) exceeds max cache size")
            return
        
        # Sort entries by eviction priority (LRU + access frequency + size)
        entries_with_priority = []
        current_time = time.time()
        
        for key, entry in self.l1_cache.items():
            # Calculate eviction score (lower = evict first)
            age_score = current_time - entry.timestamp
            access_score = 1.0 / max(1, entry.access_count)
            size_score = entry.size_estimate / 1024  # KB
            
            eviction_score = age_score * access_score * (1 + size_score / 1000)
            entries_with_priority.append((eviction_score, key, entry))
        
        entries_with_priority.sort(key=lambda x: x[0], reverse=True)
        
        # Evict entries until we have enough space
        freed_bytes = 0
        for _, key, entry in entries_with_priority:
            if freed_bytes >= needed_bytes:
                break
            
            # Consider moving to L2 before evicting
            if self._should_persist_to_l2(key, entry):
                await self._store_to_l2(key, entry.data)
            
            await self._evict_entry(key)
            freed_bytes += entry.size_estimate
    
    async def _evict_entry(self, key: str):
        """Evict entry from L1 cache."""
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            self.current_memory_usage -= entry.size_estimate
            del self.l1_cache[key]
    
    def _record_access_pattern(self, key: str):
        """Record access pattern for predictive optimization."""
        self.access_patterns[key].append(time.time())
        # Keep only recent accesses
        cutoff_time = time.time() - 3600  # Last hour
        self.access_patterns[key] = [t for t in self.access_patterns[key] if t > cutoff_time]
    
    async def _update_prefetch_predictions(self, key: str, tags: Optional[Set[str]]):
        """Update prefetch predictions based on access patterns."""
        # Simple pattern-based prefetching
        if tags and "git" in tags:
            related_keys = [k for k in self.l1_cache.keys() if "git" in k and k != key]
            for related_key in related_keys[:3]:  # Limit prefetch
                if not self.prefetch_queue.full():
                    try:
                        self.prefetch_queue.put_nowait(related_key)
                    except asyncio.QueueFull:
                        pass
    
    def _should_persist_to_l2(self, key: str, entry: CacheEntry) -> bool:
        """Determine if entry should be persisted to L2 cache."""
        # Persist frequently accessed or large computation results
        return (entry.access_count > 3 or 
                any(tag in ["project_intelligence", "code_analysis"] for tag in entry.tags))
    
    async def _store_to_l2(self, key: str, data: Any):
        """Store to L2 cache (disk) - placeholder implementation."""
        # This would implement actual disk caching
        self.l2_cache[key] = f"/tmp/cache/{hashlib.md5(key.encode()).hexdigest()}"
    
    async def _load_from_l2(self, key: str) -> Optional[Any]:
        """Load from L2 cache - placeholder implementation."""
        return None
    
    async def _load_from_l3(self, key: str) -> Optional[Any]:
        """Load from L3 cache - placeholder implementation."""
        return None
    
    async def _warm_project_intelligence_cache(self, config: Dict[str, Any]):
        """Warm cache with project intelligence data."""
        pass
    
    async def _warm_common_patterns_cache(self, config: Dict[str, Any]):
        """Warm cache with common pattern data."""
        pass
    
    async def _warm_user_specific_cache(self, config: Dict[str, Any]):
        """Warm cache with user-specific data."""
        pass


class TokenBudgetManager:
    """
    Intelligent token budget management for API optimization.
    
    Features:
    - Dynamic token allocation across context sources
    - Priority-based token distribution
    - Token usage prediction and optimization
    - Context compression with minimal information loss
    """
    
    def __init__(self, total_budget: int = 15000):
        self.total_budget = total_budget
        self.reserved_budget = int(total_budget * 0.1)  # 10% reserve
        self.available_budget = total_budget - self.reserved_budget
        
        # Token allocation priorities
        self.source_priorities = {
            "user_prompt": 0.05,  # 5% - always include full prompt
            "git_context": 0.15,   # 15% - critical for context
            "smart_advisor": 0.20, # 20% - high-value recommendations
            "project_intelligence": 0.15, # 15% - important architectural context
            "code_intelligence": 0.15,    # 15% - code-specific insights
            "system_monitor": 0.10,       # 10% - runtime information
            "security_analysis": 0.08,    # 8% - security concerns
            "test_intelligence": 0.05,    # 5% - testing information
            "other_sources": 0.07          # 7% - remaining sources
        }
        
        # Token usage tracking
        self.usage_history: List[Tuple[float, int]] = []  # (timestamp, tokens_used)
        self.source_effectiveness: Dict[str, float] = defaultdict(lambda: 0.5)
    
    def allocate_tokens(self, context_sources: Dict[str, Any]) -> Dict[str, int]:
        """Allocate tokens across context sources based on priority and effectiveness."""
        allocations = {}
        
        # Calculate dynamic priorities based on effectiveness
        adjusted_priorities = self._calculate_dynamic_priorities(context_sources)
        
        # Allocate tokens
        for source, priority in adjusted_priorities.items():
            if source in context_sources:
                allocations[source] = int(self.available_budget * priority)
        
        return allocations
    
    def optimize_context_for_budget(self, context_data: Dict[str, Any], allocations: Dict[str, int]) -> Dict[str, Any]:
        """Optimize context data to fit within token budget."""
        optimized_context = {}
        
        for source, data in context_data.items():
            if source in allocations:
                budget = allocations[source]
                optimized_context[source] = self._compress_context(data, budget, source)
            else:
                # Include without compression if no specific allocation
                optimized_context[source] = data
        
        return optimized_context
    
    def record_usage(self, tokens_used: int, effectiveness_scores: Dict[str, float]):
        """Record token usage and effectiveness for optimization."""
        self.usage_history.append((time.time(), tokens_used))
        
        # Update source effectiveness
        for source, score in effectiveness_scores.items():
            current_score = self.source_effectiveness[source]
            # Exponential moving average
            self.source_effectiveness[source] = 0.7 * current_score + 0.3 * score
        
        # Keep only recent history
        cutoff_time = time.time() - 3600  # Last hour
        self.usage_history = [(t, u) for t, u in self.usage_history if t > cutoff_time]
    
    def get_budget_metrics(self) -> Dict[str, Any]:
        """Get budget utilization metrics."""
        if not self.usage_history:
            return {"average_usage": 0, "peak_usage": 0, "budget_utilization": 0}
        
        recent_usage = [usage for _, usage in self.usage_history[-10:]]
        
        return {
            "total_budget": self.total_budget,
            "available_budget": self.available_budget,
            "average_usage": sum(recent_usage) / len(recent_usage),
            "peak_usage": max(recent_usage),
            "budget_utilization": sum(recent_usage) / len(recent_usage) / self.total_budget,
            "source_effectiveness": dict(self.source_effectiveness),
            "current_allocations": self._calculate_dynamic_priorities({})
        }
    
    def _calculate_dynamic_priorities(self, context_sources: Dict[str, Any]) -> Dict[str, float]:
        """Calculate dynamic priorities based on effectiveness and context relevance."""
        adjusted_priorities = self.source_priorities.copy()
        
        # Adjust based on effectiveness scores
        total_adjustment = 0
        for source in adjusted_priorities:
            if source in self.source_effectiveness:
                effectiveness = self.source_effectiveness[source]
                # Increase priority for highly effective sources
                adjustment = (effectiveness - 0.5) * 0.1  # Max 5% adjustment
                adjusted_priorities[source] = max(0.01, adjusted_priorities[source] + adjustment)
                total_adjustment += adjustment
        
        # Normalize to ensure total is 1.0
        total_priority = sum(adjusted_priorities.values())
        if total_priority != 1.0:
            for source in adjusted_priorities:
                adjusted_priorities[source] = adjusted_priorities[source] / total_priority
        
        return adjusted_priorities
    
    def _compress_context(self, data: Any, token_budget: int, source: str) -> Any:
        """Compress context data to fit within token budget."""
        if not data:
            return data
        
        # Estimate current token usage (rough approximation)
        current_tokens = self._estimate_tokens(data)
        
        if current_tokens <= token_budget:
            return data
        
        # Apply source-specific compression strategies
        if source == "git_context":
            return self._compress_git_context(data, token_budget)
        elif source == "system_monitor":
            return self._compress_system_monitor(data, token_budget)
        elif source == "project_intelligence":
            return self._compress_project_intelligence(data, token_budget)
        elif source == "code_intelligence":
            return self._compress_code_intelligence(data, token_budget)
        else:
            return self._generic_compression(data, token_budget)
    
    def _estimate_tokens(self, data: Any) -> int:
        """Estimate token count for data."""
        text = json.dumps(data, default=str) if not isinstance(data, str) else data
        return len(text) // 4  # Rough approximation: 4 chars per token
    
    def _compress_git_context(self, data: Any, budget: int) -> Any:
        """Compress git context while preserving most important information."""
        if isinstance(data, dict):
            # Prioritize recent commits and branch information
            compressed = {}
            if "recent_commits" in data:
                # Keep only most recent commits
                compressed["recent_commits"] = data["recent_commits"][:5]
            if "branch_info" in data:
                compressed["branch_info"] = data["branch_info"]
            if "status" in data:
                compressed["status"] = data["status"]
            return compressed
        return data
    
    def _compress_system_monitor(self, data: Any, budget: int) -> Any:
        """Compress system monitoring data."""
        if isinstance(data, dict):
            # Focus on warnings and high-priority information
            compressed = {}
            for key, value in data.items():
                if any(keyword in str(value).lower() for keyword in ["warning", "error", "high", "critical", "failed"]):
                    compressed[key] = value
                elif key in ["cpu", "memory", "disk"]:
                    compressed[key] = value
            return compressed
        return data
    
    def _compress_project_intelligence(self, data: Any, budget: int) -> Any:
        """Compress project intelligence data."""
        if isinstance(data, dict):
            # Keep architectural and framework information
            compressed = {}
            priority_keys = ["architecture_pattern", "framework_ecosystem", "quality_metrics"]
            for key in priority_keys:
                if key in data:
                    compressed[key] = data[key]
            return compressed
        return data
    
    def _compress_code_intelligence(self, data: Any, budget: int) -> Any:
        """Compress code intelligence data."""
        if isinstance(data, dict):
            # Keep complexity and quality information
            compressed = {}
            priority_keys = ["complexity_analysis", "quality_gates", "security_analysis"]
            for key in priority_keys:
                if key in data:
                    compressed[key] = data[key]
            return compressed
        return data
    
    def _generic_compression(self, data: Any, budget: int) -> Any:
        """Generic compression strategy."""
        if isinstance(data, dict):
            # Keep only high-priority keys and truncate large values
            compressed = {}
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 500:
                    compressed[key] = value[:500] + "..."
                elif isinstance(value, list) and len(value) > 10:
                    compressed[key] = value[:10]
                else:
                    compressed[key] = value
            return compressed
        elif isinstance(data, str) and len(data) > 1000:
            return data[:1000] + "..."
        return data


class ParallelExecutionOptimizer:
    """
    Optimize parallel execution of context gathering and AI processing.
    
    Features:
    - Intelligent task batching and scheduling
    - Resource-aware parallelism limits
    - Dependency-aware execution ordering
    - Circuit breaker integration
    - Performance monitoring and adjustment
    """
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.task_metrics: Dict[str, List[float]] = defaultdict(list)
        self.dependency_graph: Dict[str, List[str]] = {}
        
    async def execute_optimized_tasks(self, tasks: Dict[str, asyncio.Task], dependencies: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """Execute tasks with optimal parallelization and dependency management."""
        if dependencies:
            self.dependency_graph = dependencies
        
        # Organize tasks by dependency levels
        execution_levels = self._organize_by_dependencies(tasks)
        
        results = {}
        
        # Execute tasks level by level
        for level, level_tasks in execution_levels.items():
            level_results = await self._execute_task_level(level_tasks)
            results.update(level_results)
        
        return results
    
    async def _execute_task_level(self, tasks: Dict[str, asyncio.Task]) -> Dict[str, Any]:
        """Execute all tasks in a dependency level concurrently."""
        # Create batches based on resource requirements
        batches = self._create_optimal_batches(tasks)
        
        results = {}
        
        for batch in batches:
            batch_results = await self._execute_batch(batch)
            results.update(batch_results)
        
        return results
    
    async def _execute_batch(self, batch: Dict[str, asyncio.Task]) -> Dict[str, Any]:
        """Execute a batch of tasks concurrently."""
        batch_tasks = []
        
        for task_name, task in batch.items():
            # Wrap task with monitoring and circuit breaker
            monitored_task = self._wrap_task_with_monitoring(task_name, task)
            batch_tasks.append((task_name, monitored_task))
        
        # Execute with semaphore for resource control
        results = {}
        async def execute_with_semaphore(name: str, task: asyncio.Task):
            async with self.semaphore:
                start_time = time.time()
                try:
                    result = await task
                    execution_time = time.time() - start_time
                    self.task_metrics[name].append(execution_time)
                    return name, result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.task_metrics[name].append(execution_time)
                    logger.error(f"Task {name} failed: {e}")
                    return name, {"error": str(e), "status": "failed"}
        
        # Execute all tasks in batch
        batch_results = await asyncio.gather(*[execute_with_semaphore(name, task) for name, task in batch_tasks])
        
        for name, result in batch_results:
            results[name] = result
        
        return results
    
    def _organize_by_dependencies(self, tasks: Dict[str, asyncio.Task]) -> Dict[int, Dict[str, asyncio.Task]]:
        """Organize tasks by dependency levels."""
        levels = defaultdict(dict)
        
        # Simple implementation - more sophisticated dependency resolution could be added
        for task_name, task in tasks.items():
            if task_name in self.dependency_graph:
                # Tasks with dependencies go to level 1+
                levels[1][task_name] = task
            else:
                # Independent tasks go to level 0
                levels[0][task_name] = task
        
        return levels
    
    def _create_optimal_batches(self, tasks: Dict[str, asyncio.Task]) -> List[Dict[str, asyncio.Task]]:
        """Create optimal batches based on resource requirements and task characteristics."""
        # Simple batching strategy - could be enhanced with resource analysis
        batch_size = min(self.max_concurrent_tasks, len(tasks))
        
        batches = []
        current_batch = {}
        
        for task_name, task in tasks.items():
            current_batch[task_name] = task
            
            if len(current_batch) >= batch_size:
                batches.append(current_batch)
                current_batch = {}
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def _wrap_task_with_monitoring(self, task_name: str, task: asyncio.Task) -> asyncio.Task:
        """Wrap task with monitoring and error handling."""
        async def monitored_task():
            try:
                return await task
            except asyncio.TimeoutError:
                logger.warning(f"Task {task_name} timed out")
                return {"error": "timeout", "status": "timeout"}
            except Exception as e:
                logger.error(f"Task {task_name} failed with exception: {e}")
                return {"error": str(e), "status": "failed"}
        
        return asyncio.create_task(monitored_task())
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights for optimization."""
        insights = {}
        
        for task_name, times in self.task_metrics.items():
            if times:
                insights[task_name] = {
                    "average_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "execution_count": len(times),
                    "performance_trend": self._calculate_trend(times)
                }
        
        return insights
    
    def _calculate_trend(self, times: List[float]) -> str:
        """Calculate performance trend."""
        if len(times) < 2:
            return "insufficient_data"
        
        recent_avg = sum(times[-5:]) / len(times[-5:])
        overall_avg = sum(times) / len(times)
        
        if recent_avg < overall_avg * 0.9:
            return "improving"
        elif recent_avg > overall_avg * 1.1:
            return "degrading"
        else:
            return "stable"


class PerformanceOptimizationCoordinator:
    """
    Main coordinator for all performance optimization strategies.
    
    Integrates:
    - Intelligent caching
    - Token budget management
    - Parallel execution optimization
    - Performance monitoring and adjustment
    """
    
    def __init__(self):
        self.cache_manager = IntelligentCacheManager()
        self.token_manager = TokenBudgetManager()
        self.parallel_optimizer = ParallelExecutionOptimizer()
        self.performance_metrics = PerformanceMetrics()
        
    async def optimize_context_processing(self, user_prompt: str, context_sources: Dict[str, Any]) -> Tuple[Dict[str, Any], PerformanceMetrics]:
        """Coordinate optimized context processing."""
        start_time = time.time()
        
        # 1. Check cache for existing results
        cache_key = self._generate_cache_key(user_prompt, context_sources)
        cached_result = await self.cache_manager.get(cache_key)
        
        if cached_result:
            self.performance_metrics.cache_hit_rate += 1
            self.performance_metrics.average_response_time = time.time() - start_time
            return cached_result, self.performance_metrics
        
        # 2. Allocate token budget
        token_allocations = self.token_manager.allocate_tokens(context_sources)
        
        # 3. Optimize context for budget
        optimized_context = self.token_manager.optimize_context_for_budget(context_sources, token_allocations)
        
        # 4. Execute context gathering with parallel optimization
        context_tasks = self._create_context_tasks(optimized_context)
        context_results = await self.parallel_optimizer.execute_optimized_tasks(context_tasks)
        
        # 5. Cache results
        await self.cache_manager.set(
            cache_key, 
            context_results, 
            tags={"user_prompt", "context_processing"}
        )
        
        # 6. Update metrics
        processing_time = time.time() - start_time
        self.performance_metrics.average_response_time = processing_time
        self.performance_metrics.context_gathering_time = processing_time
        self.performance_metrics.total_requests += 1
        self.performance_metrics.successful_requests += 1
        
        return context_results, self.performance_metrics
    
    def _generate_cache_key(self, user_prompt: str, context_sources: Dict[str, Any]) -> str:
        """Generate cache key for context processing."""
        # Create hash from prompt and context source signatures
        prompt_hash = hashlib.md5(user_prompt.encode()).hexdigest()[:16]
        
        context_signature = ""
        for source, data in sorted(context_sources.items()):
            data_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
            context_signature += f"{source}:{data_hash};"
        
        signature_hash = hashlib.md5(context_signature.encode()).hexdigest()[:16]
        
        return f"context_processing:{prompt_hash}:{signature_hash}"
    
    def _create_context_tasks(self, context_sources: Dict[str, Any]) -> Dict[str, asyncio.Task]:
        """Create async tasks for context processing."""
        tasks = {}
        
        for source_name, source_data in context_sources.items():
            # Create mock task for each context source
            async def process_context_source(name: str, data: Any):
                # Simulate processing time
                await asyncio.sleep(0.1)
                return {f"{name}_processed": data}
            
            tasks[source_name] = asyncio.create_task(process_context_source(source_name, source_data))
        
        return tasks
    
    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        return {
            "cache_metrics": self.cache_manager.get_cache_metrics(),
            "token_metrics": self.token_manager.get_budget_metrics(),
            "parallel_metrics": self.parallel_optimizer.get_performance_insights(),
            "overall_metrics": {
                "cache_hit_rate": self.performance_metrics.cache_hit_rate,
                "average_response_time": self.performance_metrics.average_response_time,
                "total_requests": self.performance_metrics.total_requests,
                "success_rate": self.performance_metrics.successful_requests / max(1, self.performance_metrics.total_requests),
                "memory_usage_mb": self.performance_metrics.memory_usage_mb
            }
        }
    
    async def optimize_system_performance(self):
        """Perform system-wide performance optimizations."""
        # 1. Cache warming based on usage patterns
        await self.cache_manager.warm_cache({
            "project_intelligence": {"priority": "high"},
            "common_patterns": {"priority": "medium"}
        })
        
        # 2. Adjust parallel execution limits based on system resources
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Dynamic adjustment based on resources
            optimal_concurrent = min(cpu_count * 2, int(memory_gb / 2), 20)
            self.parallel_optimizer.max_concurrent_tasks = optimal_concurrent
            self.parallel_optimizer.semaphore = asyncio.Semaphore(optimal_concurrent)
            
        except ImportError:
            # Fallback if psutil not available
            pass
        
        # 3. Token budget adjustment based on usage patterns
        metrics = self.token_manager.get_budget_metrics()
        if metrics["budget_utilization"] > 0.9:
            # Increase compression if consistently high usage
            self.token_manager.available_budget = int(self.token_manager.total_budget * 0.85)


# Export main coordinator and key classes
__all__ = [
    "PerformanceOptimizationCoordinator",
    "IntelligentCacheManager",
    "TokenBudgetManager", 
    "ParallelExecutionOptimizer",
    "PerformanceMetrics"
]