#!/usr/bin/env python3
"""
Service Layer Architecture for Educational Feedback System.

Implements clean architecture with separated concerns:
- Service Layer: Business logic and coordination
- Repository Layer: Data access and persistence
- Domain Layer: Core business entities and rules
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
import json
import time


@dataclass
class FeedbackContext:
    """Domain entity for feedback context."""
    session_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_response: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class FeedbackMessage:
    """Domain entity for feedback messages."""
    content: str
    feedback_type: str
    priority: int = 1  # 1=low, 2=medium, 3=high
    session_id: str = ""
    tool_name: str = ""


class SessionRepository(ABC):
    """Abstract repository for session data management."""
    
    @abstractmethod
    def get_warning_count(self, session_id: str, warning_type: str) -> int:
        pass
    
    @abstractmethod
    def increment_warning_count(self, session_id: str, warning_type: str) -> None:
        pass
    
    @abstractmethod
    def should_show_warning(self, session_id: str, warning_type: str) -> bool:
        pass


class InMemorySessionRepository(SessionRepository):
    """In-memory implementation of session repository."""
    
    def __init__(self):
        self._session_warnings = {}
    
    def get_warning_count(self, session_id: str, warning_type: str) -> int:
        return self._session_warnings.get(session_id, {}).get(warning_type, 0)
    
    def increment_warning_count(self, session_id: str, warning_type: str) -> None:
        if session_id not in self._session_warnings:
            self._session_warnings[session_id] = {}
        
        current_count = self._session_warnings[session_id].get(warning_type, 0)
        self._session_warnings[session_id][warning_type] = current_count + 1
    
    def should_show_warning(self, session_id: str, warning_type: str) -> bool:
        count = self.get_warning_count(session_id, warning_type)
        
        # Business rule: warning frequency logic
        if count == 0:
            return True
        elif count < 3:
            return True
        elif count < 10:
            return (count % 3 == 0)
        else:
            return (count % 10 == 0)


class FeedbackAnalyzer(ABC):
    """Abstract analyzer for different types of feedback."""
    
    @abstractmethod
    def analyze(self, context: FeedbackContext) -> Optional[FeedbackMessage]:
        pass


class ErrorFeedbackAnalyzer(FeedbackAnalyzer):
    """Analyzer for error-based feedback."""
    
    def analyze(self, context: FeedbackContext) -> Optional[FeedbackMessage]:
        if not context.tool_response or len(context.tool_response) < 10:
            return None
        
        response_lower = context.tool_response.lower()
        error_indicators = ["error:", "failed", "exception", "traceback"]
        
        if any(indicator in response_lower for indicator in error_indicators):
            return FeedbackMessage(
                content="📚 Error detected - consider debugging tools or breaking into smaller steps",
                feedback_type="error_learning",
                priority=2,
                session_id=context.session_id,
                tool_name=context.tool_name
            )
        
        return None


class LargeOutputFeedbackAnalyzer(FeedbackAnalyzer):
    """Analyzer for large output feedback."""
    
    def __init__(self, size_threshold: int = 5000):
        self.size_threshold = size_threshold
    
    def analyze(self, context: FeedbackContext) -> Optional[FeedbackMessage]:
        if not context.tool_response:
            return None
        
        if len(context.tool_response) > self.size_threshold:
            return FeedbackMessage(
                content="📊 Large output - consider pagination or filtering for better efficiency",
                feedback_type="large_output",
                priority=1,
                session_id=context.session_id,
                tool_name=context.tool_name
            )
        
        return None


class SuccessPatternAnalyzer(FeedbackAnalyzer):
    """Analyzer for success pattern feedback."""
    
    def analyze(self, context: FeedbackContext) -> Optional[FeedbackMessage]:
        if not context.tool_response:
            return None
        
        response_lower = context.tool_response.lower()
        success_indicators = ["successfully", "completed", "done"]
        
        if any(indicator in response_lower for indicator in success_indicators):
            # Only show occasionally for positive reinforcement
            if hash(context.session_id + context.tool_name) % 5 == 0:
                return FeedbackMessage(
                    content="✅ Success - consider documenting this approach for future reference",
                    feedback_type="success_pattern",
                    priority=1,
                    session_id=context.session_id,
                    tool_name=context.tool_name
                )
        
        return None


class FeedbackService:
    """Service layer for educational feedback management."""
    
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo
        self.analyzers: List[FeedbackAnalyzer] = [
            ErrorFeedbackAnalyzer(),
            LargeOutputFeedbackAnalyzer(),
            SuccessPatternAnalyzer(),
        ]
    
    def generate_feedback(self, context: FeedbackContext) -> Optional[FeedbackMessage]:
        """Generate feedback using registered analyzers."""
        
        # Run analyzers in priority order
        for analyzer in self.analyzers:
            try:
                message = analyzer.analyze(context)
                if message:
                    # Check if we should show this feedback
                    if self.session_repo.should_show_warning(
                        context.session_id, 
                        message.feedback_type
                    ):
                        # Mark as shown and return the message
                        self.session_repo.increment_warning_count(
                            context.session_id,
                            message.feedback_type
                        )
                        return message
            except Exception:
                # Continue with next analyzer if one fails
                continue
        
        return None
    
    def add_analyzer(self, analyzer: FeedbackAnalyzer) -> None:
        """Add a new feedback analyzer."""
        self.analyzers.append(analyzer)
    
    def remove_analyzer(self, analyzer_type: type) -> None:
        """Remove analyzers of a specific type."""
        self.analyzers = [a for a in self.analyzers if not isinstance(a, analyzer_type)]


class FeedbackController:
    """Controller layer for handling feedback requests."""
    
    def __init__(self, feedback_service: FeedbackService):
        self.feedback_service = feedback_service
    
    def handle_feedback_request(self, data: Dict[str, Any]) -> int:
        """Handle incoming feedback request."""
        try:
            # Extract and validate input data
            tool_name = data.get("tool_name", "")
            tool_input = data.get("tool_input", {})
            tool_response = data.get("tool_response", "")
            session_id = self._extract_session_id(data)
            
            if not tool_name:
                return 0
            
            # Create domain context
            context = FeedbackContext(
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_response=tool_response
            )
            
            # Generate feedback through service layer
            feedback_message = self.feedback_service.generate_feedback(context)
            
            if feedback_message:
                # Output feedback to stderr for Claude to see
                print(feedback_message.content, file=sys.stderr)
            
            return 0
            
        except Exception:
            # Fail gracefully without breaking the system
            return 0
    
    def _extract_session_id(self, data: Dict[str, Any]) -> str:
        """Extract session ID from request data."""
        return data.get('session_id', data.get('context', {}).get('session_id', 'default'))


# Factory function for creating the complete service layer
def create_feedback_system() -> FeedbackController:
    """Factory function to create configured feedback system."""
    session_repo = InMemorySessionRepository()
    feedback_service = FeedbackService(session_repo)
    controller = FeedbackController(feedback_service)
    return controller


# Global instance for performance
_feedback_controller = create_feedback_system()


def handle_service_layer_feedback(data: Dict[str, Any]) -> int:
    """Main entry point using service layer architecture."""
    return _feedback_controller.handle_feedback_request(data)


# For testing and direct execution
if __name__ == "__main__":
    import sys
    
    try:
        if not sys.stdin.isatty():
            event_data = json.loads(sys.stdin.read())
            exit_code = handle_service_layer_feedback(event_data)
            sys.exit(exit_code)
        else:
            print("Service Layer Educational Feedback System")
            sys.exit(0)
    except json.JSONDecodeError as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)