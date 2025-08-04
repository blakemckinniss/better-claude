#!/usr/bin/env python3
"""Secure Logging Configuration for UserPromptSubmit Hook.

This module provides secure logging capabilities with automatic credential scrubbing,
structured security event logging, and audit trail management.
"""

import datetime
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from UserPromptSubmit.security_validator import get_security_validator


class SecureLogger:
    """Secure logger with automatic credential scrubbing and security event tracking."""
    
    def __init__(self, name: str = "UserPromptSubmit", project_root: Optional[str] = None):
        """Initialize secure logger.
        
        Args:
            name: Logger name
            project_root: Project root directory for security validation
        """
        self.logger = logging.getLogger(name)
        self.security_validator = get_security_validator(project_root)
        self._configure_logging()
        
    def _configure_logging(self):
        """Configure logging with secure defaults."""
        if not self.logger.handlers:
            # Create stderr handler for hook logging
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(logging.INFO)
            
            # Create secure formatter
            formatter = SecureFormatter(
                fmt='[%(asctime)s] %(name)s:%(levelname)s - %(message)s',
                security_validator=self.security_validator
            )
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message with credential scrubbing."""
        secure_message = self.security_validator.scrub_credentials_from_text(message)
        secure_extra = self._scrub_extra_data(extra) if extra else None
        self.logger.info(secure_message, extra=secure_extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message with credential scrubbing."""
        secure_message = self.security_validator.scrub_credentials_from_text(message)
        secure_extra = self._scrub_extra_data(extra) if extra else None
        self.logger.warning(secure_message, extra=secure_extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message with credential scrubbing."""
        secure_message = self.security_validator.scrub_credentials_from_text(message)
        secure_extra = self._scrub_extra_data(extra) if extra else None
        self.logger.error(secure_message, extra=secure_extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message with credential scrubbing."""
        if os.environ.get("DEBUG_HOOKS"):
            secure_message = self.security_validator.scrub_credentials_from_text(message)
            secure_extra = self._scrub_extra_data(extra) if extra else None
            self.logger.debug(secure_message, extra=secure_extra)
    
    def security_event(self, event_type: str, details: Dict[str, Any], severity: str = "INFO"):
        """Log security event with structured format.
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        """
        scrubbed_details = self.security_validator.scrub_credentials_from_dict(details)
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": scrubbed_details,
            "session_id": details.get("session_id", "unknown"),
            "source": "UserPromptSubmit"
        }
        
        # Log structured security event
        security_message = f"[SECURITY] {json.dumps(log_entry)}"
        
        if severity == "CRITICAL":
            self.logger.critical(security_message)
        elif severity == "ERROR":
            self.logger.error(security_message)
        elif severity == "WARNING":
            self.logger.warning(security_message)
        else:
            self.logger.info(security_message)
    
    def performance_event(self, operation: str, duration: float, details: Optional[Dict[str, Any]] = None):
        """Log performance event with credential scrubbing.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
            details: Additional details dictionary
        """
        scrubbed_details = self._scrub_extra_data(details) if details else {}
        
        perf_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "details": scrubbed_details
        }
        
        log_level = "WARNING" if duration > 5.0 else "INFO"
        message = f"[PERFORMANCE] {json.dumps(perf_entry)}"
        
        if log_level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def audit_trail(self, action: str, user_context: Dict[str, Any], result: str):
        """Create audit trail entry.
        
        Args:
            action: Action performed
            user_context: User context information
            result: Action result
        """
        scrubbed_context = self.security_validator.scrub_credentials_from_dict(user_context)
        
        audit_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "user_context": scrubbed_context,
            "result": result,
            "source": "UserPromptSubmit"
        }
        
        message = f"[AUDIT] {json.dumps(audit_entry)}"
        self.logger.info(message)
    
    def _scrub_extra_data(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub credentials from extra logging data."""
        return self.security_validator.scrub_credentials_from_dict(extra)


class SecureFormatter(logging.Formatter):
    """Custom formatter that scrubs credentials from log messages."""
    
    def __init__(self, fmt: str, security_validator):
        """Initialize secure formatter.
        
        Args:
            fmt: Log format string
            security_validator: Security validator instance
        """
        super().__init__(fmt)
        self.security_validator = security_validator
    
    def format(self, record):
        """Format log record with credential scrubbing."""
        # Scrub credentials from the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.security_validator.scrub_credentials_from_text(record.msg)
        
        # Scrub credentials from args if present
        if hasattr(record, 'args') and record.args:
            scrubbed_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    scrubbed_args.append(self.security_validator.scrub_credentials_from_text(arg))
                else:
                    scrubbed_args.append(arg)
            record.args = tuple(scrubbed_args)
        
        return super().format(record)


# Global secure logger instance
_secure_logger: Optional[SecureLogger] = None


def get_secure_logger(name: str = "UserPromptSubmit", project_root: Optional[str] = None) -> SecureLogger:
    """Get or create global secure logger instance."""
    global _secure_logger
    if _secure_logger is None:
        _secure_logger = SecureLogger(name, project_root)
    return _secure_logger


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO"):
    """Log security event using global logger."""
    logger = get_secure_logger()
    logger.security_event(event_type, details, severity)


def log_performance_event(operation: str, duration: float, details: Optional[Dict[str, Any]] = None):
    """Log performance event using global logger."""
    logger = get_secure_logger()
    logger.performance_event(operation, duration, details)


def log_audit_trail(action: str, user_context: Dict[str, Any], result: str):
    """Create audit trail entry using global logger."""
    logger = get_secure_logger()
    logger.audit_trail(action, user_context, result)


def secure_print(message: str, file=sys.stderr):
    """Print message with credential scrubbing.
    
    Args:
        message: Message to print
        file: File to print to (default: stderr)
    """
    validator = get_security_validator()
    secure_message = validator.scrub_credentials_from_text(message)
    print(secure_message, file=file)