#!/usr/bin/env python3
"""
Focused logging components for the HookLogger refactoring.
Each component handles a specific responsibility.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict


class ContentAbridger:
    """Handles content truncation and abridging operations."""
    
    # Configuration constants
    MAX_STRING_LENGTH = 1000
    MAX_ARRAY_ITEMS = 20
    MAX_OBJECT_DEPTH = 5
    
    def __init__(self):
        self.abridged_count = 0
    
    def abridge_value(self, value: Any, depth: int = 0) -> Any:
        """Abridge large values to prevent log overflow."""
        if depth > self.MAX_OBJECT_DEPTH:
            return f"<TRUNCATED: max depth {self.MAX_OBJECT_DEPTH} exceeded>"
        
        if isinstance(value, str):
            if len(value) > self.MAX_STRING_LENGTH:
                self.abridged_count += 1
                hash_val = hashlib.md5(value.encode()).hexdigest()[:8]
                return f"{value[:self.MAX_STRING_LENGTH]}... <TRUNCATED: {len(value)} chars, hash: {hash_val}>"
            return value
        
        elif isinstance(value, (list, tuple)):
            if len(value) > self.MAX_ARRAY_ITEMS:
                self.abridged_count += 1
                abridged = [self.abridge_value(v, depth + 1) for v in value[:self.MAX_ARRAY_ITEMS]]
                return abridged + [f"... <TRUNCATED: {len(value) - self.MAX_ARRAY_ITEMS} more items>"]
            return [self.abridge_value(v, depth + 1) for v in value]
        
        elif isinstance(value, dict):
            abridged = {}
            for k, v in list(value.items())[:self.MAX_ARRAY_ITEMS]:
                abridged[k] = self.abridge_value(v, depth + 1)
            if len(value) > self.MAX_ARRAY_ITEMS:
                self.abridged_count += 1
                abridged["__truncated__"] = f"{len(value) - self.MAX_ARRAY_ITEMS} more items"
            return abridged
        
        elif isinstance(value, (int, float, bool, type(None))):
            return value
        
        else:
            # For other types, convert to string and abridge
            str_val = str(value)
            return self.abridge_value(str_val, depth)
    
    def get_abridged_count(self) -> int:
        """Get the total number of abridged items."""
        return self.abridged_count


class LogRotator:
    """Handles log file rotation based on size limits."""
    
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB per log file
    MAX_LOG_FILES = 100
    
    def rotate_if_needed(self, log_file: Path, directory: Path) -> Path:
        """Rotate log file if it exceeds size limit."""
        if log_file.exists() and log_file.stat().st_size > self.MAX_LOG_FILE_SIZE:
            rotation_index = 1
            while True:
                rotated_file = directory / f"{log_file.stem}.{rotation_index}.jsonl"
                if not rotated_file.exists():
                    log_file.rename(rotated_file)
                    break
                rotation_index += 1
                if rotation_index > self.MAX_LOG_FILES:
                    self._cleanup_old_files(directory)
                    break
        
        return log_file
    
    def _cleanup_old_files(self, directory: Path):
        """Clean up old log files when limit is reached."""
        log_files = sorted(directory.glob("*.jsonl*"), key=lambda f: f.stat().st_mtime)
        if len(log_files) > self.MAX_LOG_FILES:
            for old_file in log_files[:len(log_files) - self.MAX_LOG_FILES]:
                old_file.unlink()


class LogCleaner:
    """Handles comprehensive log cleanup operations."""
    
    MAX_LOG_AGE_DAYS = 7
    MAX_TOTAL_SIZE_MB = 500
    CLEANUP_INTERVAL_HOURS = 6
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.hooks_dir = base_dir / "hooks"
        self.system_dir = base_dir / "system"
        self.errors_dir = base_dir / "errors"
        
        self.last_cleanup = datetime.now()
        self.cleanup_state_file = base_dir / ".cleanup_state"
        self._load_cleanup_state()
    
    def cleanup_if_needed(self):
        """Run cleanup if needed based on interval."""
        if self._should_run_cleanup():
            self._comprehensive_cleanup()
    
    def _should_run_cleanup(self) -> bool:
        """Check if cleanup should run based on interval."""
        hours_since_cleanup = (datetime.now() - self.last_cleanup).total_seconds() / 3600
        return hours_since_cleanup >= self.CLEANUP_INTERVAL_HOURS
    
    def _load_cleanup_state(self):
        """Load last cleanup timestamp from state file."""
        if self.cleanup_state_file.exists():
            try:
                with open(self.cleanup_state_file, 'r') as f:
                    state = json.load(f)
                    self.last_cleanup = datetime.fromisoformat(
                        state.get('last_cleanup', datetime.now().isoformat())
                    )
            except Exception:
                pass
    
    def _save_cleanup_state(self):
        """Save cleanup timestamp to state file."""
        try:
            with open(self.cleanup_state_file, 'w') as f:
                json.dump({'last_cleanup': self.last_cleanup.isoformat()}, f)
        except Exception:
            pass
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of all files in directory tree."""
        total_size = 0
        for path in directory.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size
    
    def _comprehensive_cleanup(self):
        """Perform comprehensive log cleanup based on age and size limits."""
        try:
            cleanup_stats = {
                'deleted_files': 0,
                'deleted_bytes': 0,
                'start_time': datetime.now().isoformat()
            }
            
            # Age-based cleanup
            cutoff_date = datetime.now() - timedelta(days=self.MAX_LOG_AGE_DAYS)
            
            for base_dir in [self.hooks_dir, self.system_dir, self.errors_dir]:
                if not base_dir.exists():
                    continue
                    
                for log_file in base_dir.rglob('*.jsonl*'):
                    if log_file.is_file():
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            file_size = log_file.stat().st_size
                            log_file.unlink()
                            cleanup_stats['deleted_files'] += 1
                            cleanup_stats['deleted_bytes'] += file_size
                
                # Also clean up .log files (human-readable logs)
                for log_file in base_dir.rglob('*.log'):
                    if log_file.is_file():
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            file_size = log_file.stat().st_size
                            log_file.unlink()
                            cleanup_stats['deleted_files'] += 1
                            cleanup_stats['deleted_bytes'] += file_size
            
            # Size-based cleanup
            total_size_mb = self._get_directory_size(self.base_dir) / (1024 * 1024)
            
            if total_size_mb > self.MAX_TOTAL_SIZE_MB:
                all_logs = []
                for base_dir in [self.hooks_dir, self.system_dir, self.errors_dir]:
                    if base_dir.exists():
                        all_logs.extend(base_dir.rglob('*.jsonl*'))
                        all_logs.extend(base_dir.rglob('*.log'))
                
                all_logs = sorted(
                    [f for f in all_logs if f.is_file()],
                    key=lambda f: f.stat().st_mtime
                )
                
                # Delete oldest files until under size limit
                for log_file in all_logs:
                    if total_size_mb <= self.MAX_TOTAL_SIZE_MB:
                        break
                    
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    cleanup_stats['deleted_files'] += 1
                    cleanup_stats['deleted_bytes'] += file_size
                    total_size_mb -= file_size / (1024 * 1024)
            
            # Clean up empty directories
            for base_dir in [self.hooks_dir, self.system_dir]:
                if base_dir.exists():
                    for dir_path in sorted(base_dir.rglob('*'), reverse=True):
                        if dir_path.is_dir() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
            
            # Update cleanup state
            self.last_cleanup = datetime.now()
            self._save_cleanup_state()
            
            return cleanup_stats
                
        except Exception as e:
            return {'error': f"Cleanup failed: {str(e)}"}


class MetricsCollector:
    """Handles performance metrics collection and reporting."""
    
    def __init__(self):
        self.metrics = {
            "total_logs": 0,
            "errors_count": 0,
            "start_time": time.time()
        }
    
    def increment_total_logs(self):
        """Increment the total log counter."""
        self.metrics["total_logs"] += 1
    
    def increment_errors(self):
        """Increment the error counter."""
        self.metrics["errors_count"] += 1
    
    def reset_start_time(self):
        """Reset the start time for session tracking."""
        self.metrics["start_time"] = time.time()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics for log entries."""
        return {
            "log_number": self.metrics["total_logs"],
            "session_duration": time.time() - self.metrics["start_time"]
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics including computed values."""
        runtime_seconds = time.time() - self.metrics["start_time"]
        return {
            **self.metrics,
            "runtime_seconds": runtime_seconds,
            "logs_per_second": self.metrics["total_logs"] / max(1, runtime_seconds)
        }