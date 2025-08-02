#!/usr/bin/env python3
"""Context Manager for conversation context storage, retrieval, and management."""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from session_state import SessionState


@dataclass
class ContextEntry:
    """Represents a stored context entry."""
    id: Optional[int] = None
    session_id: str = ""
    user_prompt: str = ""
    context_data: str = ""
    files_involved: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    outcome: str = "unknown"  # success, failure, partial
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: float = 0.0
    compressed: bool = False
    
    def __post_init__(self):
        if self.files_involved is None:
            self.files_involved = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class CircuitBreaker:
    """Circuit breaker pattern for database operations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300, 
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    self.half_open_calls = 0
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            if self.state == "HALF_OPEN":
                if self.half_open_calls >= self.half_open_max_calls:
                    raise Exception("Circuit breaker HALF_OPEN limit exceeded")
                self.half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (self.last_failure_time is not None and
                time.time() - self.last_failure_time > self.recovery_timeout)
    
    def _on_success(self):
        """Handle successful operation."""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.half_open_calls = 0
    
    def _on_failure(self):
        """Handle failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"


class ContextManager:
    """Main orchestrator for context operations with SQLite storage."""
    
    def __init__(self, project_dir: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize the context manager."""
        self.project_dir = project_dir or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        
        # Handle placeholder
        if self.project_dir == "$CLAUDE_PROJECT_DIR" or not os.path.isdir(self.project_dir):
            self.project_dir = os.getcwd()
        
        # Setup paths
        self.context_dir = Path(self.project_dir) / ".claude" / "hooks" / "context_revival"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        if config_path is None:
            config_file_path = Path(__file__).parent / "context_revival_config.json"
        else:
            config_file_path = Path(config_path)
        self.config = self._load_config(config_file_path)
        
        # Database setup
        self.db_path = self.context_dir / self.config["database"]["filename"]
        self.connection_pool = {}
        self.pool_lock = threading.Lock()
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config["circuit_breaker"]["failure_threshold"],
            recovery_timeout=self.config["circuit_breaker"]["recovery_timeout"],
            half_open_max_calls=self.config["circuit_breaker"]["half_open_max_calls"]
        )
        
        # Session integration
        self.session_state = SessionState(self.project_dir)
        
        # Cache
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_lock = threading.Lock()
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize database
        self._init_database()
        
        # Start background tasks
        self._last_cleanup = time.time()
        
        self.logger.info("Context Manager initialized")
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default config if file missing or invalid
            return {
                "database": {"filename": "context_revival.db", "timeout": 30.0},
                "storage": {"max_context_age_days": 30, "compression_enabled": True},
                "retrieval": {"max_results": 10, "relevance_threshold": 0.3},
                "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
                "performance": {"cache_size": 100, "cache_ttl": 3600},
                "logging": {"level": "INFO"}
            }
    
    def _setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger("ContextManager")
        level = getattr(logging, self.config["logging"]["level"], logging.INFO)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                self.config["logging"].get("format", 
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with connection pooling."""
        thread_id = threading.get_ident()
        
        with self.pool_lock:
            if thread_id not in self.connection_pool:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=self.config["database"]["timeout"],
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                if self.config["database"].get("wal_mode", True):
                    conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                self.connection_pool[thread_id] = conn
        
        try:
            yield self.connection_pool[thread_id]
        except Exception as e:
            self.connection_pool[thread_id].rollback()
            raise e
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        schema = """
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_prompt TEXT NOT NULL,
            context_data TEXT NOT NULL,
            files_involved TEXT,  -- JSON array
            timestamp DATETIME NOT NULL,
            outcome TEXT DEFAULT 'unknown',
            metadata TEXT,  -- JSON object
            relevance_score REAL DEFAULT 0.0,
            compressed BOOLEAN DEFAULT 0,
            hash TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_contexts_session ON contexts(session_id);
        CREATE INDEX IF NOT EXISTS idx_contexts_timestamp ON contexts(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_contexts_outcome ON contexts(outcome);
        CREATE INDEX IF NOT EXISTS idx_contexts_hash ON contexts(hash);
        CREATE INDEX IF NOT EXISTS idx_contexts_relevance ON contexts(relevance_score DESC);
        
        CREATE VIRTUAL TABLE IF NOT EXISTS contexts_fts USING fts5(
            user_prompt, context_data, files_involved,
            content='contexts',
            content_rowid='id'
        );
        
        CREATE TRIGGER IF NOT EXISTS contexts_fts_insert AFTER INSERT ON contexts BEGIN
            INSERT INTO contexts_fts(rowid, user_prompt, context_data, files_involved)
            VALUES (new.id, new.user_prompt, new.context_data, new.files_involved);
        END;
        
        CREATE TRIGGER IF NOT EXISTS contexts_fts_delete AFTER DELETE ON contexts BEGIN
            DELETE FROM contexts_fts WHERE rowid = old.id;
        END;
        
        CREATE TRIGGER IF NOT EXISTS contexts_fts_update AFTER UPDATE ON contexts BEGIN
            DELETE FROM contexts_fts WHERE rowid = old.id;
            INSERT INTO contexts_fts(rowid, user_prompt, context_data, files_involved)
            VALUES (new.id, new.user_prompt, new.context_data, new.files_involved);
        END;
        """
        
        try:
            with self.get_connection() as conn:
                conn.executescript(schema)
                conn.commit()
            self.logger.info("Database schema initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_context(self, user_prompt: str, context_data: str,
                     files_involved: Optional[List[str]] = None, outcome: str = "unknown",
                     metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Store a new context entry."""
        if not user_prompt or not context_data:
            return None
        
        # Create context entry
        entry = ContextEntry(
            session_id=self._get_current_session_id(),
            user_prompt=user_prompt,
            context_data=context_data,
            files_involved=files_involved or [],
            outcome=outcome,
            metadata=metadata or {}
        )
        
        # Compress if enabled and data is large
        if (self.config["storage"]["compression_enabled"] and 
            len(context_data) > 1024):
            entry.context_data = zlib.compress(context_data.encode()).hex()
            entry.compressed = True
        
        # Generate hash for deduplication
        content_hash = hashlib.md5(
            f"{user_prompt}{context_data}".encode()
        ).hexdigest()
        
        try:
            return self.circuit_breaker.call(self._store_context_db, entry, content_hash)
        except Exception as e:
            self.logger.error(f"Failed to store context: {e}")
            return None
    
    def _store_context_db(self, entry: ContextEntry, content_hash: str) -> int:
        """Internal method to store context in database."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO contexts 
                (session_id, user_prompt, context_data, files_involved, 
                 timestamp, outcome, metadata, compressed, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.session_id,
                entry.user_prompt,
                entry.context_data,
                json.dumps(entry.files_involved),
                entry.timestamp.isoformat() if entry.timestamp else datetime.now().isoformat(),
                entry.outcome,
                json.dumps(entry.metadata),
                entry.compressed,
                content_hash
            ))
            conn.commit()
            return cursor.lastrowid
    
    def retrieve_relevant_contexts(self, query: str, files_involved: Optional[List[str]] = None,
                                 max_results: Optional[int] = None) -> List[ContextEntry]:
        """Retrieve contexts relevant to the query."""
        max_results = max_results or self.config["retrieval"]["max_results"]
        
        # Check cache first
        cache_key = f"{query}:{':'.join(sorted(files_involved or []))}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result[:max_results]
        
        try:
            contexts = self.circuit_breaker.call(
                self._retrieve_contexts_db, query, files_involved, max_results
            )
            self._store_in_cache(cache_key, contexts)
            return contexts
        except Exception as e:
            self.logger.error(f"Failed to retrieve contexts: {e}")
            return []
    
    def _retrieve_contexts_db(self, query: str, files_involved: List[str], 
                            max_results: int) -> List[ContextEntry]:
        """Internal method to retrieve contexts from database."""
        with self.get_connection() as conn:
            # Use FTS for text search
            sql = """
                SELECT c.*, rank
                FROM contexts c
                JOIN (
                    SELECT rowid, rank
                    FROM contexts_fts
                    WHERE contexts_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                ) fts ON c.id = fts.rowid
                WHERE datetime(c.timestamp) > datetime(?)
                ORDER BY 
                    CASE WHEN c.outcome = 'success' THEN 3
                         WHEN c.outcome = 'partial' THEN 2
                         ELSE 1 END DESC,
                    c.timestamp DESC,
                    fts.rank
                LIMIT ?
            """
            
            # Query within time window  
            cutoff_date = (datetime.now() - 
                          timedelta(days=self.config["storage"]["max_context_age_days"]))
            
            cursor = conn.execute(sql, (
                query,
                max_results * 2,  # Get more for filtering
                cutoff_date.isoformat(),
                max_results
            ))
            
            contexts = []
            for row in cursor:
                entry = self._row_to_context_entry(row)
                if entry:
                    # Calculate relevance score
                    entry.relevance_score = self._calculate_relevance(
                        entry, query, files_involved
                    )
                    if entry.relevance_score >= self.config["retrieval"]["relevance_threshold"]:
                        contexts.append(entry)
            
            return sorted(contexts, key=lambda x: x.relevance_score, reverse=True)[:max_results]
    
    def _row_to_context_entry(self, row) -> Optional[ContextEntry]:
        """Convert database row to ContextEntry."""
        try:
            context_data = row["context_data"]
            if row["compressed"]:
                context_data = zlib.decompress(bytes.fromhex(context_data)).decode()
            
            return ContextEntry(
                id=row["id"],
                session_id=row["session_id"],
                user_prompt=row["user_prompt"],
                context_data=context_data,
                files_involved=json.loads(row["files_involved"] or "[]"),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                outcome=row["outcome"],
                metadata=json.loads(row["metadata"] or "{}"),
                relevance_score=row["relevance_score"] if "relevance_score" in row.keys() else 0.0,
                compressed=bool(row["compressed"])
            )
        except Exception as e:
            self.logger.error(f"Error converting row to context entry: {e}")
            return None
    
    def _calculate_relevance(self, entry: ContextEntry, query: str,
                           files_involved: Optional[List[str]] = None) -> float:
        """Calculate relevance score for a context entry."""
        weights = self.config["retrieval"]["scoring_weights"]
        score = 0.0
        
        # Recency score (newer is better)
        if entry.timestamp is None:
            age_hours = 0
        else:
            age_hours = (datetime.now() - entry.timestamp).total_seconds() / 3600
        recency_score = max(0, 1 - (age_hours / (24 * 7)))  # Decay over a week
        score += recency_score * weights["recency"]
        
        # Text relevance (simple keyword matching)
        query_words = set(query.lower().split())
        prompt_words = set(entry.user_prompt.lower().split())
        context_words = set(entry.context_data.lower().split())
        
        prompt_overlap = len(query_words & prompt_words) / max(len(query_words), 1)
        context_overlap = len(query_words & context_words) / max(len(query_words), 1)
        relevance_score = max(prompt_overlap, context_overlap * 0.5)
        score += relevance_score * weights["relevance"]
        
        # Outcome success bonus
        outcome_score = {"success": 1.0, "partial": 0.5, "unknown": 0.3, "failure": 0.1}.get(
            entry.outcome, 0.1
        )
        score += outcome_score * weights["outcome_success"]
        
        # File overlap bonus
        if files_involved and entry.files_involved:
            file_overlap = len(set(files_involved) & set(entry.files_involved))
            file_score = file_overlap / max(len(files_involved), 1)
            score += file_score * weights["file_overlap"]
        
        return min(score, 1.0)
    
    def _get_current_session_id(self) -> str:
        """Get current session identifier."""
        state = self.session_state.get_state()
        transcript_path = state.get("last_transcript_path", "")
        
        if transcript_path:
            # Use transcript filename as session ID
            return Path(transcript_path).stem
        else:
            # Fallback to date-based session ID
            return datetime.now().strftime("%Y%m%d_%H")
    
    def _get_from_cache(self, key: str) -> Optional[List[ContextEntry]]:
        """Get result from cache if valid."""
        with self.cache_lock:
            if key in self.cache:
                timestamp = self.cache_timestamps.get(key, 0)
                if time.time() - timestamp < self.config["performance"]["cache_ttl"]:
                    return self.cache[key]
                else:
                    del self.cache[key]
                    del self.cache_timestamps[key]
        return None
    
    def _store_in_cache(self, key: str, value: List[ContextEntry]):
        """Store result in cache."""
        with self.cache_lock:
            # Implement LRU eviction
            if len(self.cache) >= self.config["performance"]["cache_size"]:
                oldest_key = min(self.cache_timestamps.keys(), 
                               key=lambda k: self.cache_timestamps[k])
                del self.cache[oldest_key]
                del self.cache_timestamps[oldest_key]
            
            self.cache[key] = value
            self.cache_timestamps[key] = time.time()
    
    def cleanup_old_contexts(self, days_old: Optional[int] = None) -> int:
        """Remove contexts older than specified days."""
        effective_days_old = days_old if days_old is not None else self.config["storage"]["max_context_age_days"]
        cutoff_date = datetime.now() - timedelta(days=effective_days_old)
        
        try:
            return self.circuit_breaker.call(self._cleanup_contexts_db, cutoff_date)
        except Exception as e:
            self.logger.error(f"Failed to cleanup contexts: {e}")
            return 0
    
    def _cleanup_contexts_db(self, cutoff_date: datetime) -> int:
        """Internal method to cleanup old contexts."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM contexts WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            conn.commit()
            deleted_count = cursor.rowcount
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            
            self.logger.info(f"Cleaned up {deleted_count} old contexts")
            return deleted_count
    
    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for a session."""
        session_id = session_id or self._get_current_session_id()
        
        try:
            return self.circuit_breaker.call(self._get_session_summary_db, session_id)
        except Exception as e:
            self.logger.error(f"Failed to get session summary: {e}")
            return {"error": str(e)}
    
    def _get_session_summary_db(self, session_id: str) -> Dict[str, Any]:
        """Internal method to get session summary."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_contexts,
                    COUNT(CASE WHEN outcome = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failed,
                    AVG(relevance_score) as avg_relevance,
                    MIN(timestamp) as first_context,
                    MAX(timestamp) as last_context
                FROM contexts 
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "session_id": session_id,
                    "total_contexts": row["total_contexts"],
                    "successful": row["successful"],
                    "failed": row["failed"],
                    "success_rate": (row["successful"] / max(row["total_contexts"], 1)) * 100,
                    "avg_relevance": round(row["avg_relevance"] or 0, 2),
                    "first_context": row["first_context"],
                    "last_context": row["last_context"]
                }
            return {"session_id": session_id, "total_contexts": 0}
    
    def update_context_outcome(self, context_id: int, outcome: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update the outcome of a stored context."""
        try:
            return self.circuit_breaker.call(
                self._update_context_outcome_db, context_id, outcome, metadata
            )
        except Exception as e:
            self.logger.error(f"Failed to update context outcome: {e}")
            return False
    
    def _update_context_outcome_db(self, context_id: int, outcome: str, 
                                  metadata: Optional[Dict[str, Any]]) -> bool:
        """Internal method to update context outcome."""
        with self.get_connection() as conn:
            if metadata:
                cursor = conn.execute("""
                    UPDATE contexts 
                    SET outcome = ?, metadata = ?
                    WHERE id = ?
                """, (outcome, json.dumps(metadata), context_id))
            else:
                cursor = conn.execute("""
                    UPDATE contexts 
                    SET outcome = ?
                    WHERE id = ?
                """, (outcome, context_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the context manager."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM contexts")
                total_contexts = cursor.fetchone()["count"]
                
                cursor = conn.execute("""
                    SELECT COUNT(*) as count FROM contexts 
                    WHERE timestamp > datetime('now', '-1 day')
                """)
                recent_contexts = cursor.fetchone()["count"]
            
            return {
                "status": "healthy",
                "circuit_breaker_state": self.circuit_breaker.state,
                "total_contexts": total_contexts,
                "recent_contexts": recent_contexts,
                "cache_size": len(self.cache),
                "database_path": str(self.db_path),
                "last_cleanup": self._last_cleanup
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state
            }
    
    def close(self):
        """Close all database connections and cleanup."""
        with self.pool_lock:
            for conn in self.connection_pool.values():
                try:
                    conn.close()
                except:
                    pass
            self.connection_pool.clear()
        
        self.logger.info("Context Manager closed")


# Convenience functions for hook integration
_context_manager_instance: Optional[ContextManager] = None

def get_context_manager(project_dir: Optional[str] = None) -> ContextManager:
    """Get a singleton context manager instance."""
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = ContextManager(project_dir)
    return _context_manager_instance


def store_conversation_context(user_prompt: str, context_data: str,
                             files_involved: Optional[List[str]] = None,
                             outcome: str = "unknown") -> Optional[int]:
    """Convenience function to store context from hooks."""
    try:
        cm = get_context_manager()
        return cm.store_context(user_prompt, context_data, files_involved, outcome)
    except Exception as e:
        logging.error(f"Failed to store conversation context: {e}")
        return None


def retrieve_relevant_context(query: str, files_involved: Optional[List[str]] = None,
                            max_results: int = 5) -> List[ContextEntry]:
    """Convenience function to retrieve relevant context."""
    try:
        cm = get_context_manager()
        return cm.retrieve_relevant_contexts(query, files_involved, max_results)
    except Exception as e:
        logging.error(f"Failed to retrieve relevant context: {e}")
        return []