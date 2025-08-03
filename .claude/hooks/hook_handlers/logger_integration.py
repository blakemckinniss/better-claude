#!/usr/bin/env python3
"""
Central logging integration for all hook handlers.
Provides consistent logging across all hooks with proper error handling.
"""

import sys
import json
import traceback
import time
import resource
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Add parent directory to path for hook_logger import
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from hook_logger import logger, HookLogger
except ImportError:
    # Fallback if logger can't be imported
    print("Warning: Could not import hook_logger", file=sys.stderr)
    logger = None
    HookLogger = None


class HookLoggerIntegration:
    """Integrates logging into hook handlers with consistent patterns."""
    
    # Performance tracking storage
    _performance_data = {}
    
    @staticmethod
    def _get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics."""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "memory_mb": usage.ru_maxrss / 1024,  # Convert to MB
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime
            }
        except Exception:
            return {}
    
    @staticmethod
    def log_hook_entry(event_data: Dict[str, Any], hook_name: str = None) -> Dict[str, Any]:
        """Log the entry into a hook handler."""
        if not logger:
            return event_data
        
        try:
            # Add hook name if not present
            if hook_name and "hook_event_name" not in event_data:
                event_data["hook_event_name"] = hook_name
            
            # Start performance tracking
            session_id = event_data.get("session_id", "unknown")
            hook_key = f"{session_id}_{hook_name}_{time.time()}"
            HookLoggerIntegration._performance_data[hook_key] = {
                "start_time": time.time(),
                "start_memory": HookLoggerIntegration._get_memory_usage()
            }
            event_data["_perf_key"] = hook_key
            
            # Log at INFO level
            return logger.log_info(event_data)
        except Exception as e:
            # Silent failure - don't break hooks due to logging
            return event_data
    
    @staticmethod
    def log_hook_exit(event_data: Dict[str, Any], exit_code: int = 0, 
                      result: Optional[Any] = None, error: Optional[str] = None) -> Dict[str, Any]:
        """Log the exit from a hook handler."""
        if not logger:
            return event_data
        
        try:
            # Add result information
            event_data["exit_code"] = exit_code
            if result is not None:
                event_data["result"] = result
            if error:
                event_data["error"] = error
            
            # Calculate performance metrics if we have a key
            perf_key = event_data.get("_perf_key")
            if perf_key and perf_key in HookLoggerIntegration._performance_data:
                perf_start = HookLoggerIntegration._performance_data[perf_key]
                end_time = time.time()
                end_memory = HookLoggerIntegration._get_memory_usage()
                
                # Calculate metrics
                execution_time = end_time - perf_start["start_time"]
                memory_delta = (end_memory.get("memory_mb", 0) - 
                              perf_start["start_memory"].get("memory_mb", 0))
                
                event_data["performance"] = {
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "memory_delta_mb": round(memory_delta, 2),
                    "cpu_time": round(end_memory.get("user_time", 0) - 
                                    perf_start["start_memory"].get("user_time", 0), 3)
                }
                
                # Clean up performance data
                del HookLoggerIntegration._performance_data[perf_key]
                del event_data["_perf_key"]
            
            # Choose log level based on exit code
            if exit_code == 0:
                return logger.log_info(event_data)
            elif exit_code == 2:
                return logger.log_warning(event_data)
            else:
                return logger.log_error(event_data)
        except Exception:
            return event_data
    
    @staticmethod
    def log_decision(event_data: Dict[str, Any], decision: str, 
                    reason: Optional[str] = None, level: int = None) -> Dict[str, Any]:
        """Log a decision made by a hook."""
        if not logger:
            return event_data
        
        try:
            event_data["decision"] = decision
            if reason:
                event_data["reason"] = reason
            
            # Default level based on decision
            if level is None:
                if decision in ["block", "deny"]:
                    level = HookLogger.WARNING
                else:
                    level = HookLogger.INFO
            
            return logger.log_hook_event(event_data, level)
        except Exception:
            return event_data
    
    @staticmethod
    def log_error(event_data: Dict[str, Any], error: Union[str, Exception]) -> Dict[str, Any]:
        """Log an error that occurred in a hook."""
        if not logger:
            return event_data
        
        try:
            if isinstance(error, Exception):
                event_data["error"] = str(error)
                event_data["error_type"] = type(error).__name__
                event_data["traceback"] = traceback.format_exc()
            else:
                event_data["error"] = error
            
            return logger.log_error(event_data)
        except Exception:
            return event_data
    
    @staticmethod
    def create_logged_handler(handler_func):
        """Decorator to add logging to a hook handler function."""
        def logged_wrapper(event_data: Dict[str, Any]) -> Any:
            # Log entry
            hook_name = handler_func.__name__.replace("handle_", "")
            HookLoggerIntegration.log_hook_entry(event_data, hook_name)
            
            try:
                # Call the actual handler
                result = handler_func(event_data)
                
                # Log exit based on result type
                if isinstance(result, int):
                    # Exit code
                    HookLoggerIntegration.log_hook_exit(event_data, result)
                elif isinstance(result, tuple) and len(result) == 2:
                    # (exit_code, output) pattern
                    exit_code, output = result
                    HookLoggerIntegration.log_hook_exit(event_data, exit_code, output)
                else:
                    # Other result
                    HookLoggerIntegration.log_hook_exit(event_data, 0, result)
                
                return result
                
            except Exception as e:
                # Log error
                HookLoggerIntegration.log_error(event_data, e)
                raise
        
        return logged_wrapper
    
    @staticmethod
    def log_warning(event_data: Dict[str, Any], warning: str) -> Dict[str, Any]:
        """Log a warning from a hook."""
        if not logger:
            return event_data
        
        try:
            event_data["warning"] = warning
            return logger.log_warning(event_data)
        except Exception:
            return event_data
    
    @staticmethod
    def log_metrics(event_data: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Log performance metrics from a hook."""
        if not logger:
            return event_data
        
        try:
            event_data["performance_metrics"] = metrics
            return logger.log_debug(event_data)
        except Exception:
            return event_data
    
    @staticmethod
    def get_performance_summary() -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        if not logger:
            return {}
        
        try:
            # Get logger metrics
            logger_metrics = logger.get_metrics()
            
            # Add current memory usage
            current_memory = HookLoggerIntegration._get_memory_usage()
            
            # Count active performance tracking entries
            active_hooks = len(HookLoggerIntegration._performance_data)
            
            return {
                "logger_metrics": logger_metrics,
                "current_memory_mb": current_memory.get("memory_mb", 0),
                "active_hooks": active_hooks,
                "timestamp": time.time()
            }
        except Exception:
            return {}
    
    @staticmethod
    def cleanup_stale_performance_data(max_age_seconds: int = 300):
        """Clean up old performance tracking data to prevent memory leaks."""
        try:
            current_time = time.time()
            stale_keys = []
            
            for key, data in HookLoggerIntegration._performance_data.items():
                if current_time - data["start_time"] > max_age_seconds:
                    stale_keys.append(key)
            
            for key in stale_keys:
                del HookLoggerIntegration._performance_data[key]
            
            return len(stale_keys)
        except Exception:
            return 0


# Export convenience instance
hook_logger = HookLoggerIntegration()