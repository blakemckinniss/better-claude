#!/usr/bin/env python3
"""Context Revival Hook - Intelligently injects relevant historical context.

This hook analyzes user prompts to determine when historical context would be
beneficial and retrieves relevant context using the Context Manager.
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union


# Define fallback types for when imports fail
class _FallbackContextEntry:
    """Fallback ContextEntry for when imports fail."""
    def __init__(self):
        self.timestamp = None
        self.relevance_score = 0.0
        self.session_id = ""
        self.user_prompt = ""
        self.files_involved = []
        self.context_data = ""
        self.outcome = "unknown"
        self.metadata = {}

# Import the Context Manager and related modules
if TYPE_CHECKING:
    # Type checking imports - these are only used for static analysis
    try:
        from .context_manager import ContextEntry, ContextManager, get_context_manager
        from .session_state import SessionState
    except ImportError:
        from context_manager import ContextEntry, ContextManager, get_context_manager
        from session_state import SessionState

# Runtime imports with fallbacks
try:
    from .context_manager import ContextEntry, ContextManager, get_context_manager
    from .session_state import SessionState
except ImportError:
    try:
        from context_manager import ContextEntry, ContextManager, get_context_manager
        from session_state import SessionState
    except ImportError as e:
        print(f"Context revival import error: {e}", file=sys.stderr)
        # Provide fallback functionality with proper types
        ContextManager = None
        ContextEntry = _FallbackContextEntry  # Use fallback class instead of None
        get_context_manager = None
        SessionState = None

# Create a type alias that works with both real and fallback types
ContextEntryType = Union[ContextEntry, _FallbackContextEntry]


class ContextRevivalAnalyzer:
    """Analyzes user prompts to determine context revival needs."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.trigger_keywords = set(config["triggers"]["keywords"])
        self.error_indicators = set(config["triggers"]["error_indicators"])
        self.success_indicators = set(config["triggers"]["success_indicators"])
        self.relevant_extensions = set(config["triggers"]["file_extensions"])
        
        # Context type patterns
        self.patterns = {
            "error_context": [
                r"\b(?:error|bug|issue|problem|failed|broken|exception)\b",
                r"\b(?:debug|troubleshoot|diagnose)\b",
                r"\b(?:why.*(?:not work|fail|break))\b"
            ],
            "implementation_context": [
                r"\b(?:how to|implement|create|build|make)\b",
                r"\b(?:similar|like|same as|example)\b",
                r"\b(?:before|previous|earlier|last time)\b"
            ],
            "pattern_context": [
                r"\b(?:pattern|recurring|again|repeat)\b",
                r"\b(?:best practice|convention|standard)\b",
                r"\b(?:approach|strategy|method)\b"
            ],
            "file_context": [
                r"\b(?:file|module|component|class|function)\b.*\b(?:structure|organization)\b",
                r"\b(?:related|connected|dependent|import)\b",
                r"\b(?:refactor|reorganize|restructure)\b"
            ]
        }
    
    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt to determine if context revival is beneficial."""
        if not prompt:
            return {"should_retrieve": False, "confidence": 0.0, "reasons": []}
        
        prompt_lower = prompt.lower()
        analysis = {
            "should_retrieve": False,
            "confidence": 0.0,
            "reasons": [],
            "context_types": [],
            "keywords_found": [],
            "estimated_relevance": 0.0
        }
        
        # Check for trigger keywords
        found_keywords = []
        for keyword in self.trigger_keywords:
            if keyword in prompt_lower:
                found_keywords.append(keyword)
                analysis["confidence"] += 0.15
        
        if found_keywords:
            analysis["keywords_found"] = found_keywords
            analysis["reasons"].append(f"Contains trigger keywords: {', '.join(found_keywords[:3])}")
        
        # Check for context type patterns
        for context_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    analysis["context_types"].append(context_type)
                    analysis["confidence"] += 0.2
                    analysis["reasons"].append(f"Matches {context_type} pattern")
                    break
        
        # Check for error indicators (higher confidence)
        error_indicators_found = [ind for ind in self.error_indicators if ind in prompt_lower]
        if error_indicators_found:
            analysis["confidence"] += 0.3
            analysis["reasons"].append(f"Error-related: {', '.join(error_indicators_found[:2])}")
        
        # Check for success indicators (moderate confidence)  
        success_indicators_found = [ind for ind in self.success_indicators if ind in prompt_lower]
        if success_indicators_found:
            analysis["confidence"] += 0.2
            analysis["reasons"].append(f"Success-related: {', '.join(success_indicators_found[:2])}")
        
        # Check if prompt mentions files or code
        file_mentions = len(re.findall(r'\b\w+\.[a-zA-Z]+\b', prompt))
        if file_mentions > 0:
            analysis["confidence"] += min(0.2, file_mentions * 0.1)
            analysis["reasons"].append(f"Mentions {file_mentions} files")
        
        # Check prompt complexity (longer prompts more likely to benefit)
        word_count = len(prompt.split())
        if word_count > 20:
            analysis["confidence"] += 0.1
            analysis["reasons"].append("Complex/detailed prompt")
        
        # Determine if we should retrieve context
        analysis["should_retrieve"] = analysis["confidence"] >= 0.3
        analysis["estimated_relevance"] = min(analysis["confidence"], 1.0)
        
        return analysis


class ContextFormatter:
    """Formats retrieved context for injection."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_tokens = config["injection"]["max_context_tokens"]
        self.include_file_context = config["injection"]["include_file_context"]
    
    def format_contexts(self, contexts: List[ContextEntryType], analysis: Dict[str, Any]) -> str:
        """Format contexts for injection."""
        if not contexts:
            return ""
        
        # Sort by relevance and recency
        sorted_contexts = sorted(
            contexts, 
            key=lambda x: (x.relevance_score, x.timestamp), 
            reverse=True
        )
        
        formatted_parts = []
        token_estimate = 0
        
        for i, context in enumerate(sorted_contexts):
            if token_estimate >= self.max_tokens:
                break
            
            context_section = self._format_single_context(context, i + 1, len(sorted_contexts))
            section_tokens = len(context_section.split()) * 1.3  # Rough token estimate
            
            if token_estimate + section_tokens > self.max_tokens and formatted_parts:
                break
            
            formatted_parts.append(context_section)
            token_estimate += section_tokens
        
        if not formatted_parts:
            return ""
        
        # Build header
        confidence = analysis.get("confidence", 0.0)
        reasons = analysis.get("reasons", [])
        
        header = f"<context-revival confidence=\"{confidence:.2f}\">\n"
        if reasons:
            header += f"<!-- Triggered by: {', '.join(reasons[:3])} -->\n"
        
        # Combine all parts
        context_body = "\n".join(formatted_parts)
        footer = "</context-revival>\n"
        
        return header + context_body + footer
    
    def _format_single_context(self, context: ContextEntryType, index: int, total: int) -> str:
        """Format a single context entry."""
        # Time formatting
        time_ago = self._format_time_ago(context.timestamp)
        
        # Outcome indicator
        outcome_indicator = {
            "success": "✅",
            "partial": "🟡", 
            "failure": "❌",
            "unknown": "❓"
        }.get(context.outcome, "❓")
        
        parts = []
        
        # Context header
        parts.append(f"## Context {index}/{total} {outcome_indicator} ({time_ago})")
        parts.append(f"**Relevance:** {context.relevance_score:.2f} | **Session:** {context.session_id}")
        
        # User prompt (truncated if long)
        prompt = context.user_prompt[:200] + "..." if len(context.user_prompt) > 200 else context.user_prompt
        parts.append(f"**Prompt:** {prompt}")
        
        # Files involved
        if context.files_involved and self.include_file_context:
            files_display = ", ".join(context.files_involved[:5])
            if len(context.files_involved) > 5:
                files_display += f" (+{len(context.files_involved) - 5} more)"
            parts.append(f"**Files:** {files_display}")
        
        # Context data (truncated)
        context_data = context.context_data[:800] + "..." if len(context.context_data) > 800 else context.context_data
        parts.append(f"**Context:**\n{context_data}")
        
        # Metadata if available
        if context.metadata:
            relevant_metadata = {k: v for k, v in context.metadata.items() 
                               if k in ["tools_used", "outcome_reason", "duration"]}
            if relevant_metadata:
                metadata_str = ", ".join(f"{k}: {v}" for k, v in relevant_metadata.items())
                parts.append(f"**Metadata:** {metadata_str}")
        
        return "\n".join(parts) + "\n"
    
    def _format_time_ago(self, timestamp) -> str:
        """Format timestamp as 'time ago' string."""
        try:
            from datetime import datetime
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
            delta = now - timestamp
            
            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours}h ago"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes}m ago"
            else:
                return "just now"
        except Exception:
            return "unknown time"


class ContextRevivalHook:
    """Main context revival hook implementation."""
    
    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = project_dir or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        
        # Handle placeholder
        if self.project_dir == "$CLAUDE_PROJECT_DIR" or not os.path.isdir(self.project_dir):
            self.project_dir = os.getcwd()
        
        # Load configuration
        config_path = Path(__file__).parent / "context_revival_config.json"
        self.config = self._load_config(config_path)
        
        # Setup logging first
        self.logger = self._setup_logging()
        
        # Initialize components
        self.analyzer = ContextRevivalAnalyzer(self.config)
        self.formatter = ContextFormatter(self.config)
        
        # Initialize context manager if available
        self.context_manager = None
        if ContextManager and get_context_manager:
            try:
                self.context_manager = get_context_manager(self.project_dir)
                if self.context_manager:
                    self.logger.info("Context manager initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize context manager: {e}")
                self.context_manager = None
        
        # Performance tracking
        self.stats = {
            "contexts_retrieved": 0,
            "total_retrieval_time": 0.0,
            "cache_hits": 0,
            "errors": 0
        }
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration with fallbacks."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Config load error: {e}, using defaults", file=sys.stderr)
            return {
                "retrieval": {"max_results": 5, "relevance_threshold": 0.3},
                "injection": {"max_context_tokens": 2000, "include_file_context": True},
                "triggers": {
                    "keywords": ["similar", "before", "previous", "like", "remember"],
                    "error_indicators": ["error", "bug", "issue", "problem"],
                    "success_indicators": ["worked", "success", "fixed"],
                    "file_extensions": [".py", ".js", ".ts"]
                },
                "performance": {"max_query_time_ms": 500},
                "logging": {"level": "INFO"}
            }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging."""
        logger = logging.getLogger("ContextRevival")
        level = getattr(logging, self.config["logging"]["level"], logging.INFO)
        logger.setLevel(level)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                self.config["logging"].get("format", 
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def extract_file_context(self, prompt: str) -> List[str]:
        """Extract mentioned files from prompt for context filtering."""
        files = []
        
        # Extract file paths and names
        file_patterns = [
            r'\b[\w\-\.]+\.[a-zA-Z]{1,4}\b',  # filename.ext
            r'[\w\-\./]+/[\w\-\.]+\.[a-zA-Z]{1,4}',  # path/filename.ext
            r'[\w\-\./]+\.py|\.js|\.ts|\.jsx|\.tsx|\.go|\.rs|\.java'  # specific extensions
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, prompt)
            files.extend(matches)
        
        # Filter by relevant extensions
        relevant_files = []
        for file in files:
            if any(file.endswith(ext) for ext in self.config["triggers"]["file_extensions"]):
                relevant_files.append(file)
        
        return list(set(relevant_files))  # Remove duplicates
    
    def retrieve_contexts(self, prompt: str, analysis: Dict[str, Any]) -> List[ContextEntryType]:
        """Retrieve relevant contexts with performance monitoring."""
        if not self.context_manager:
            return []
        
        start_time = time.time()
        max_query_time = self.config["performance"]["max_query_time_ms"] / 1000.0
        
        try:
            # Extract file context
            files_involved = self.extract_file_context(prompt)
            
            # Retrieve contexts with timeout protection
            contexts = []
            try:
                # Create query from prompt (clean up for better matching)
                query_words = re.findall(r'\b\w+\b', prompt.lower())
                # Remove common words and context-specific words that might not match
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'when', 'where', 'why', 'can', 'could', 'should', 'would', 'will', 'like', 'before', 'previous', 'again', 'similar', 'same', 'debug', 'fix'}
                meaningful_words = [w for w in query_words if w not in stop_words and len(w) > 2]
                
                if meaningful_words:
                    # Try multiple query strategies
                    queries_to_try = [
                        ' '.join(meaningful_words[:5]),  # Main query
                        ' '.join(meaningful_words[:3]),  # Shorter query  
                        ' OR '.join(meaningful_words[:5])  # OR query for broader matching
                    ]
                    
                    all_contexts = []
                    for search_query in queries_to_try:
                        if search_query and search_query not in [q for q in queries_to_try[:queries_to_try.index(search_query)]]:
                            self.logger.debug(f"Trying search query: '{search_query}'")
                            try:
                                query_contexts = self.context_manager.retrieve_relevant_contexts(
                                    search_query, 
                                    files_involved, 
                                    self.config["retrieval"]["max_results"]
                                )
                                all_contexts.extend(query_contexts)
                                if query_contexts:
                                    self.logger.debug(f"Query '{search_query}' found {len(query_contexts)} contexts")
                                    break  # Use first successful query
                            except Exception as e:
                                self.logger.debug(f"Query '{search_query}' failed: {e}")
                                continue
                    
                    # Remove duplicates and sort by relevance
                    seen_contexts = set()
                    contexts = []
                    for ctx in all_contexts:
                        ctx_key = (ctx.session_id, ctx.timestamp, ctx.user_prompt[:50])  # Create unique key
                        if ctx_key not in seen_contexts:
                            seen_contexts.add(ctx_key)
                            contexts.append(ctx)
                    
                    # Apply relevance threshold
                    relevance_threshold = self.config["retrieval"]["relevance_threshold"]
                    contexts = [ctx for ctx in contexts if ctx.relevance_score >= relevance_threshold]
                    
                    # Sort by relevance score
                    contexts.sort(key=lambda x: x.relevance_score, reverse=True)
                    
                    # Limit results
                    contexts = contexts[:self.config["retrieval"]["max_results"]]
            
            except Exception as e:
                self.logger.warning(f"Context retrieval failed: {e}")
                contexts = []
            
            elapsed = time.time() - start_time
            self.stats["contexts_retrieved"] += len(contexts)
            self.stats["total_retrieval_time"] += elapsed
            
            if elapsed > max_query_time:
                self.logger.warning(f"Context retrieval took {elapsed:.2f}s (exceeds {max_query_time:.2f}s limit)")
            
            self.logger.debug(f"Retrieved {len(contexts)} contexts in {elapsed:.2f}s")
            return contexts
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Context retrieval error: {e}")
            return []
    
    def generate_context_injection(self, prompt: str) -> str:
        """Main entry point for context revival."""
        if not prompt.strip():
            return ""
        
        try:
            # Analyze prompt for context needs
            analysis = self.analyzer.analyze_prompt(prompt)
            
            if not analysis["should_retrieve"]:
                self.logger.debug(f"Skipping context retrieval (confidence: {analysis['confidence']:.2f})")
                return ""
            
            self.logger.debug(f"Context retrieval triggered: {analysis['reasons']}")
            
            # Retrieve relevant contexts
            contexts = self.retrieve_contexts(prompt, analysis)
            
            if not contexts:
                self.logger.debug("No relevant contexts found")
                return ""
            
            # Format contexts for injection
            try:
                injection = self.formatter.format_contexts(contexts, analysis)
                if injection:
                    self.logger.info(f"Generated context injection with {len(contexts)} contexts")
                    return injection
                else:
                    self.logger.debug("No context injection generated")
                    return ""
                    
            except Exception as e:
                self.logger.error(f"Context formatting error: {e}")
                return ""
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Context revival error: {e}")
            return ""
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health and performance stats."""
        return {
            "context_manager_available": self.context_manager is not None,
            "stats": self.stats.copy(),
            "avg_retrieval_time": (
                self.stats["total_retrieval_time"] / max(1, self.stats["contexts_retrieved"])
            ),
            "config": {
                "max_results": self.config["retrieval"]["max_results"],
                "max_tokens": self.config["injection"]["max_context_tokens"],
                "relevance_threshold": self.config["retrieval"]["relevance_threshold"]
            }
        }


def get_context_revival_hook(project_dir: Optional[str] = None) -> ContextRevivalHook:
    """Factory function to get context revival hook instance."""
    return ContextRevivalHook(project_dir)


def get_context_revival_injection(prompt: str, project_dir: Optional[str] = None) -> str:
    """Main entry point for context revival injection."""
    try:
        hook = get_context_revival_hook(project_dir)
        return hook.generate_context_injection(prompt)
    except Exception as e:
        print(f"Context revival failed: {e}", file=sys.stderr)
        return ""


# Hook entry point for the Claude system
def apply_hook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply context revival to user prompt."""
    if not data or "userMessage" not in data:
        return data
    
    user_message = data["userMessage"]
    if not user_message or "text" not in user_message:
        return data
    
    try:
        prompt = user_message["text"]
        context_injection = get_context_revival_injection(prompt)
        
        if context_injection:
            # Prepend context to the user message
            user_message["text"] = context_injection + "\n" + prompt
        
        return data
        
    except Exception as e:
        print(f"Context revival hook error: {e}", file=sys.stderr)
        return data