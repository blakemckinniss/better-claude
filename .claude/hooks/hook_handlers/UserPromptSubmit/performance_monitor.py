"""Performance monitoring utilities for UserPromptSubmit hook."""

import functools
import time
from typing import Any, Callable, Dict


class PerformanceMonitor:
    """Simple performance monitoring for hook operations."""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}

    def start_timer(self, operation: str) -> float:
        """Start timing an operation."""
        return time.perf_counter()

    def end_timer(self, operation: str, start_time: float) -> float:
        """End timing an operation and return duration."""
        duration = time.perf_counter() - start_time
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
        return duration


def monitor_performance(func: Callable) -> Callable:
    """Decorator for monitoring function performance."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            if duration > 0.5:  # Log slow operations
                print(f"[PERF] Slow operation {func.__name__}: {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"[PERF] Failed {func.__name__} after {duration:.3f}s: {e}")
            raise

    return wrapper


def cleanup_performance_monitoring() -> None:
    """Clean up performance monitoring resources."""
    # Placeholder for cleanup operations
