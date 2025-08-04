#!/usr/bin/env python3
"""Batch operations optimizer for reducing redundant API calls and operations."""

import asyncio
import hashlib
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class BatchOperationCache:
    """Cache for batched operations to prevent redundant calls."""
    
    def __init__(self, ttl: int = 300):
        """Initialize batch cache with TTL in seconds."""
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
        self.pending_operations: Dict[str, asyncio.Future] = {}
    
    def get_cache_key(self, operation_name: str, *args, **kwargs) -> str:
        """Generate cache key for operation and parameters."""
        # Create deterministic hash from operation and parameters
        param_str = f"{operation_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    async def get_or_execute(
        self, 
        operation_name: str, 
        operation_func: Callable[..., T], 
        *args, 
        **kwargs
    ) -> T:
        """Get cached result or execute operation once for all concurrent requests."""
        cache_key = self.get_cache_key(operation_name, *args, **kwargs)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Check if operation is already pending
        if cache_key in self.pending_operations:
            # Wait for existing operation to complete
            return await self.pending_operations[cache_key]
        
        # Execute operation and cache for concurrent requests
        future = asyncio.create_task(self._execute_and_cache(
            cache_key, operation_func, *args, **kwargs
        ))
        self.pending_operations[cache_key] = future
        
        try:
            result = await future
            return result
        finally:
            # Remove from pending operations
            self.pending_operations.pop(cache_key, None)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if still valid."""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    async def _execute_and_cache(
        self, 
        cache_key: str, 
        operation_func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute operation and cache result."""
        if asyncio.iscoroutinefunction(operation_func):
            result = await operation_func(*args, **kwargs)
        else:
            result = operation_func(*args, **kwargs)
        
        # Cache result
        self.cache[cache_key] = (result, time.time())
        
        # Cleanup old entries
        self._cleanup_cache()
        
        return result
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        now = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def clear_cache(self):
        """Clear all cached results."""
        self.cache.clear()
        
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cached_items': len(self.cache),
            'pending_operations': len(self.pending_operations),
            'ttl_seconds': self.ttl,
        }


class OperationBatcher:
    """Batches similar operations to reduce overhead."""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.1):
        """Initialize operation batcher."""
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batches: Dict[str, List[Tuple[Any, asyncio.Future]]] = {}
        self.batch_timers: Dict[str, asyncio.Task] = {}
    
    async def add_to_batch(
        self, 
        batch_key: str, 
        item: Any, 
        batch_processor: Callable[[List[Any]], List[Any]]
    ) -> Any:
        """Add item to batch and return result when batch is processed."""
        # Create future for this item's result
        future = asyncio.get_event_loop().create_future()
        
        # Initialize batch if needed
        if batch_key not in self.batches:
            self.batches[batch_key] = []
        
        # Add item to batch
        self.batches[batch_key].append((item, future))
        
        # Check if batch is full
        if len(self.batches[batch_key]) >= self.batch_size:
            await self._process_batch(batch_key, batch_processor)
        else:
            # Set timer to process batch after timeout
            if batch_key not in self.batch_timers:
                self.batch_timers[batch_key] = asyncio.create_task(
                    self._batch_timeout_handler(batch_key, batch_processor)
                )
        
        return await future
    
    async def _batch_timeout_handler(
        self, 
        batch_key: str, 
        batch_processor: Callable[[List[Any]], List[Any]]
    ):
        """Handle batch timeout - process partial batch."""
        await asyncio.sleep(self.batch_timeout)
        if batch_key in self.batches and self.batches[batch_key]:
            await self._process_batch(batch_key, batch_processor)
    
    async def _process_batch(
        self, 
        batch_key: str, 
        batch_processor: Callable[[List[Any]], List[Any]]
    ):
        """Process a complete batch."""
        if batch_key not in self.batches:
            return
        
        batch_items = self.batches[batch_key]
        if not batch_items:
            return
        
        # Clear batch and timer
        self.batches[batch_key] = []
        if batch_key in self.batch_timers:
            self.batch_timers[batch_key].cancel()
            del self.batch_timers[batch_key]
        
        try:
            # Extract items and futures
            items = [item for item, _ in batch_items]
            futures = [future for _, future in batch_items]
            
            # Process batch
            if asyncio.iscoroutinefunction(batch_processor):
                results = await batch_processor(items)
            else:
                results = batch_processor(items)
            
            # Set results on futures
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
                    
        except Exception as e:
            # Set exception on all futures
            for _, future in batch_items:
                if not future.done():
                    future.set_exception(e)


# Global instances
_batch_cache = BatchOperationCache()
_operation_batcher = OperationBatcher()


def get_batch_cache() -> BatchOperationCache:
    """Get global batch cache instance."""
    return _batch_cache


def get_operation_batcher() -> OperationBatcher:
    """Get global operation batcher instance."""
    return _operation_batcher


async def cached_operation(
    operation_name: str, 
    operation_func: Callable[..., T], 
    *args, 
    **kwargs
) -> T:
    """Execute operation with caching to prevent duplicates."""
    return await _batch_cache.get_or_execute(
        operation_name, operation_func, *args, **kwargs
    )


async def batched_operation(
    batch_key: str,
    item: Any,
    batch_processor: Callable[[List[Any]], List[Any]]
) -> Any:
    """Add item to batch for processing."""
    return await _operation_batcher.add_to_batch(
        batch_key, item, batch_processor
    )