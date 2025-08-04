#!/usr/bin/env python3
"""Comprehensive Security Validation Module for UserPromptSubmit Hook.

This module addresses three critical security vulnerabilities:
1. Path Traversal Security Gap - Comprehensive path validation
2. Input Validation Weaknesses - Strict input sanitization 
3. API Key Exposure Risk - Credential protection and scrubbing

Security Framework: OWASP Top 10 compliance with defense-in-depth approach.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple


class SecurityValidator:
    """Comprehensive security validation for hook inputs and operations."""
    
    # Path traversal patterns (comprehensive detection)
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r'\.\.+[/\\]'),  # ../ or ..\
        re.compile(r'[/\\]\.\.+[/\\]'),  # /../ or \..\
        re.compile(r'[/\\]\.\.+$'),  # /.. or \.. at end
        re.compile(r'^\.\.+[/\\]'),  # ../ or ..\ at start
        re.compile(r'%2e%2e[/\\%]', re.IGNORECASE),  # URL encoded ..
        re.compile(r'\.{2,}'),  # Multiple dots
        re.compile(r'[/\\]{2,}'),  # Multiple slashes
    ]
    
    # Sensitive file patterns (expanded security coverage)
    SENSITIVE_PATTERNS = [
        # Environment and secrets
        ".env", ".env.local", ".env.production", ".env.staging",
        "secrets.json", "config.json", "credentials.json",
        
        # SSH and keys
        ".ssh/", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
        ".pem", ".key", ".cert", ".crt", ".p12", ".pfx",
        "private.key", "public.key", "keystore",
        
        # Authentication tokens
        "password", "passwd", "secret", "token", "api_key",
        "access_token", "refresh_token", "bearer_token",
        
        # Cloud provider credentials  
        ".aws/", ".azure/", ".gcloud/", "credentials",
        "serviceaccount.json", "azure-credentials.json",
        
        # Database credentials
        "database.yml", "db_config", "connection_string",
        
        # System files
        "/etc/", "/sys/", "/proc/", "/dev/", "/root/",
        "shadow", "sudoers", "hosts", "fstab",
        
        # Git internals
        ".git/config", ".git/credentials", ".git/hooks",
        
        # Application secrets
        "flask_secret", "django_secret", "jwt_secret",
        "encryption_key", "signing_key", "session_secret",
    ]
    
    # System directories (absolute path restrictions)
    SYSTEM_DIRECTORIES = [
        "/etc", "/sys", "/proc", "/dev", "/root", "/boot",
        "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/var/log",
        "/tmp", "/var/tmp", "/var/run", "/run",
    ]
    
    # Input validation patterns
    SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]{8,64}$')
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_./ ]{1,255}$')
    
    # API key patterns for credential scrubbing
    API_KEY_PATTERNS = [
        re.compile(r'sk-[a-zA-Z0-9]{20,}', re.IGNORECASE),  # OpenAI
        re.compile(r'AIza[a-zA-Z0-9_-]{35}', re.IGNORECASE),  # Google
        re.compile(r'ya29\.[a-zA-Z0-9_-]+', re.IGNORECASE),  # OAuth2
        re.compile(r'[a-zA-Z0-9]{32,}', re.IGNORECASE),  # Generic long tokens
        re.compile(r'Bearer\s+[a-zA-Z0-9\-_.~+/]+=*', re.IGNORECASE),  # Bearer tokens
        re.compile(r'["\']?[a-zA-Z0-9_-]{20,}["\']?'),  # Quoted tokens
    ]
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize security validator.
        
        Args:
            project_root: Optional project root directory for path validation
        """
        self.project_root = self._resolve_project_root(project_root)
        self.allowed_directories = self._get_allowed_directories()
        
    def _resolve_project_root(self, project_root: Optional[str]) -> str:
        """Resolve and validate project root directory."""
        if project_root:
            try:
                resolved = os.path.realpath(project_root)
                if os.path.isdir(resolved):
                    return resolved
            except (OSError, ValueError):
                pass
                
        # Fallback to current working directory
        return os.path.realpath(os.getcwd())
    
    def _get_allowed_directories(self) -> Set[str]:
        """Get set of allowed directories for file operations."""
        allowed = {self.project_root}
        
        # Add common development directories within project
        dev_dirs = [
            ".claude", "src", "lib", "docs", "tests", "scripts",
            "config", "data", "assets", "public", "static"
        ]
        
        for dirname in dev_dirs:
            dir_path = os.path.join(self.project_root, dirname)
            if os.path.isdir(dir_path):
                allowed.add(os.path.realpath(dir_path))
                
        return allowed
    
    def validate_path_security(self, path: str) -> Tuple[bool, str]:
        """Comprehensive path traversal and security validation.
        
        Args:
            path: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return True, ""  # Empty path is safe
            
        # Check for path traversal patterns
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path):
                return False, f"Path traversal detected: {path}"
        
        # Check for sensitive file patterns
        path_lower = path.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in path_lower:
                return False, f"Access to sensitive file blocked: {path}"
        
        # Resolve to absolute path and check bounds
        try:
            resolved_path = os.path.realpath(path)
            
            # Check if path is within allowed directories
            path_allowed = False
            for allowed_dir in self.allowed_directories:
                if resolved_path.startswith(allowed_dir + os.sep) or resolved_path == allowed_dir:
                    path_allowed = True
                    break
                    
            if not path_allowed:
                return False, f"Path outside allowed directories: {resolved_path}"
                
            # Check for system directories
            for sys_dir in self.SYSTEM_DIRECTORIES:
                if resolved_path.startswith(sys_dir):
                    return False, f"Access to system directory blocked: {resolved_path}"
                    
        except (OSError, ValueError) as e:
            return False, f"Path resolution failed: {e}"
            
        return True, ""
    
    def validate_input_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Comprehensive input validation with sanitization.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Tuple of (is_valid, sanitized_data, error_message)
        """
        try:
            # Check required fields
            required_fields = ["session_id", "transcript_path", "cwd", "hook_event_name"]
            for field in required_fields:
                if field not in data:
                    return False, None, f"Missing required field: {field}"
            
            # Validate hook event name
            if data["hook_event_name"] != "UserPromptSubmit":
                return False, None, f"Invalid hook event: {data['hook_event_name']}"
            
            # Validate session ID format
            session_id = data["session_id"]
            if not isinstance(session_id, str) or not self.SESSION_ID_PATTERN.match(session_id):
                return False, None, f"Invalid session_id format: {session_id}"
            
            # Validate transcript path
            transcript_path = data.get("transcript_path", "")
            if transcript_path:
                is_valid, error = self.validate_path_security(transcript_path)
                if not is_valid:
                    return False, None, f"transcript_path validation failed: {error}"
                
                # Check if file exists and is readable
                if not os.path.exists(transcript_path):
                    return False, None, f"transcript_path does not exist: {transcript_path}"
                
                if not os.access(transcript_path, os.R_OK):
                    return False, None, f"transcript_path not readable: {transcript_path}"
            
            # Validate current working directory
            cwd = data.get("cwd", "")
            if cwd:
                is_valid, error = self.validate_path_security(cwd)
                if not is_valid:
                    return False, None, f"cwd validation failed: {error}"
            
            # Validate prompt content (UserPromptSubmit specific)
            if "prompt" not in data:
                return False, None, "Missing required prompt field"
            
            prompt = data["prompt"]
            if not isinstance(prompt, str):
                return False, None, "Prompt must be string"
            
            # Sanitize prompt - remove shell metacharacters and control chars
            sanitized_prompt = self._sanitize_prompt(prompt)
            
            # Check length limits
            if len(sanitized_prompt) > 50000:  # 50KB limit
                return False, None, "Prompt exceeds maximum length (50KB)"
            
            # Create sanitized data copy
            sanitized_data = data.copy()
            sanitized_data["prompt"] = sanitized_prompt
            
            # Sanitize string fields
            for field in ["session_id", "transcript_path", "cwd", "hook_event_name"]:
                if field in sanitized_data and isinstance(sanitized_data[field], str):
                    sanitized_data[field] = self._sanitize_string_input(sanitized_data[field])
            
            return True, sanitized_data, ""
            
        except Exception as e:
            return False, None, f"Input validation error: {e}"
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize prompt content for security."""
        # Remove null bytes and control characters (except newlines, tabs)
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', prompt)
        
        # Remove shell metacharacters that could be dangerous
        dangerous_chars = ['`', '$', '|', '&', ';', '(', ')', '<', '>']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    def _sanitize_string_input(self, value: str) -> str:
        """Sanitize general string input."""
        # Remove null bytes and most control characters
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', value)
        return sanitized.strip()
    
    def scrub_credentials_from_text(self, text: str) -> str:
        """Remove API keys and credentials from text for safe logging.
        
        Args:
            text: Text that may contain credentials
            
        Returns:
            Text with credentials replaced by [REDACTED]
        """
        scrubbed = text
        
        for pattern in self.API_KEY_PATTERNS:
            scrubbed = pattern.sub('[REDACTED]', scrubbed)
        
        # Additional patterns for common credential formats
        credential_patterns = [
            (r'password["\s]*[:=]["\s]*[^"\s\n]+', 'password="[REDACTED]"'),
            (r'secret["\s]*[:=]["\s]*[^"\s\n]+', 'secret="[REDACTED]"'),
            (r'token["\s]*[:=]["\s]*[^"\s\n]+', 'token="[REDACTED]"'),
            (r'key["\s]*[:=]["\s]*[^"\s\n]+', 'key="[REDACTED]"'),
        ]
        
        for pattern, replacement in credential_patterns:
            scrubbed = re.sub(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        
        return scrubbed
    
    def scrub_credentials_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove credentials from dictionary data structure.
        
        Args:
            data: Dictionary that may contain credentials
            
        Returns:
            Dictionary with credentials redacted
        """
        scrubbed = {}
        credential_keys = {
            'password', 'secret', 'token', 'api_key', 'access_token', 
            'refresh_token', 'private_key', 'client_secret', 'bearer_token',
            'auth_token', 'session_token', 'oauth_token', 'jwt_token'
        }
        
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(cred_key in key_lower for cred_key in credential_keys):
                scrubbed[key] = '[REDACTED]'
            elif isinstance(value, str):
                scrubbed[key] = self.scrub_credentials_from_text(value)
            elif isinstance(value, dict):
                scrubbed[key] = self.scrub_credentials_from_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = [
                    self.scrub_credentials_from_text(item) if isinstance(item, str)
                    else self.scrub_credentials_from_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                scrubbed[key] = value
        
        return scrubbed
    
    def validate_environment_variables(self) -> List[str]:
        """Validate that required environment variables are set securely.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check for API keys in environment
        api_key_vars = [
            'OPENAI_API_KEY', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY',
            'OPENROUTER_API_KEY', 'CLAUDE_API_KEY'
        ]
        
        for var_name in api_key_vars:
            value = os.environ.get(var_name)
            if value:
                # Check if API key looks valid (basic format validation)
                if len(value) < 20:
                    warnings.append(f"{var_name} appears too short to be valid")
                elif value.startswith('test_') or value == 'dummy' or value == 'placeholder':
                    warnings.append(f"{var_name} appears to be a placeholder value")
                    
        return warnings
    
    def create_secure_error_message(self, error: Exception, context: str = "") -> str:
        """Create error message with credential scrubbing.
        
        Args:
            error: Exception object
            context: Additional context for the error
            
        Returns:
            Sanitized error message safe for logging
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        return self.scrub_credentials_from_text(error_msg)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events with proper credential scrubbing.
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
        """
        scrubbed_details = self.scrub_credentials_from_dict(details)
        
        # Log to stderr with security prefix
        log_entry = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "event_type": event_type,
            "details": scrubbed_details
        }
        
        print(f"[SECURITY] {json.dumps(log_entry)}", file=sys.stderr)


# Global security validator instance
_security_validator: Optional[SecurityValidator] = None


def get_security_validator(project_root: Optional[str] = None) -> SecurityValidator:
    """Get or create global security validator instance."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator(project_root)
    return _security_validator


def validate_path_security(path: str, project_root: Optional[str] = None) -> Tuple[bool, str]:
    """Validate path security using global validator."""
    validator = get_security_validator(project_root)
    return validator.validate_path_security(path)


def validate_input_data(data: Dict[str, Any], project_root: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Validate input data using global validator."""
    validator = get_security_validator(project_root)
    return validator.validate_input_data(data)


def scrub_credentials(text: str) -> str:
    """Scrub credentials from text using global validator."""
    validator = get_security_validator()
    return validator.scrub_credentials_from_text(text)