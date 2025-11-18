"""
Security utilities for logging - prevents accidental secret exposure.

This module provides logging filters and utilities to ensure that sensitive
information (secrets, tokens, connection strings, passwords) is never
accidentally logged in plain text.

Author: Specify CLI Team
"""

import logging
import re
from typing import List, Pattern


class SecretRedactionFilter(logging.Filter):
    """
    Logging filter that redacts sensitive information from log records.
    
    This filter scans log messages and redacts common secret patterns:
    - Bearer tokens (Authorization: Bearer ...)
    - API keys (key=..., apikey=..., api_key=...)
    - Connection strings (Server=...;Password=...)
    - Password fields (password=..., pwd=...)
    - Secret values (secret=..., token=...)
    
    Usage:
        handler = logging.StreamHandler()
        handler.addFilter(SecretRedactionFilter())
        logger.addHandler(handler)
    """
    
    # Patterns for common secrets (case-insensitive)
    SECRET_PATTERNS: List[Pattern] = [
        # Bearer tokens
        re.compile(r'Bearer\s+[A-Za-z0-9._-]+', re.IGNORECASE),
        
        # API keys
        re.compile(r'(api[_-]?key|apikey)\s*[:=]\s*["\']?[\w-]+["\']?', re.IGNORECASE),
        
        # Passwords
        re.compile(r'(password|pwd)\s*[:=]\s*["\']?[^;,\s"\']+["\']?', re.IGNORECASE),
        
        # Secrets and tokens
        re.compile(r'(secret|token)\s*[:=]\s*["\']?[\w-]+["\']?', re.IGNORECASE),
        
        # Connection strings with password
        re.compile(r'(Password|Pwd)\s*=\s*[^;]+', re.IGNORECASE),
        
        # Authorization header values
        re.compile(r"'Authorization':\s*['\"]Bearer\s+[^'\"]+['\"]", re.IGNORECASE),
    ]
    
    REDACTION_TEXT = "***REDACTED***"
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record - redacts secrets from message.
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always allow the record, just modify it)
        """
        if hasattr(record, 'msg'):
            # Redact secrets from main message
            if isinstance(record.msg, str):
                record.msg = self._redact_secrets(record.msg)
            
            # Redact secrets from arguments (if any)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._redact_value(v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(self._redact_value(v) for v in record.args)
        
        return True
    
    def _redact_secrets(self, text: str) -> str:
        """
        Redact secrets from text using regex patterns.
        
        Args:
            text: Text that may contain secrets
            
        Returns:
            Text with secrets redacted
        """
        redacted = text
        for pattern in self.SECRET_PATTERNS:
            redacted = pattern.sub(self.REDACTION_TEXT, redacted)
        return redacted
    
    def _redact_value(self, value):
        """
        Redact secrets from individual value.
        
        Args:
            value: Value to check for secrets
            
        Returns:
            Original value or redacted string
        """
        if isinstance(value, str):
            return self._redact_secrets(value)
        return value


def configure_secure_logging(logger: logging.Logger) -> None:
    """
    Configure logger with secret redaction filter.
    
    Adds SecretRedactionFilter to all handlers of the specified logger
    to prevent accidental secret exposure in logs.
    
    Args:
        logger: Logger to configure
        
    Example:
        import logging
        from specify_cli.validation.secure_logging import configure_secure_logging
        
        logger = logging.getLogger(__name__)
        configure_secure_logging(logger)
    """
    redaction_filter = SecretRedactionFilter()
    
    # Add filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(redaction_filter)
    
    # If no handlers, add to logger itself (will apply to all future handlers)
    if not logger.handlers:
        logger.addFilter(redaction_filter)


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret string, showing only first/last characters.
    
    Useful for debugging or displaying partial secrets to users
    without exposing the full value.
    
    Args:
        secret: Secret string to mask
        visible_chars: Number of characters to show at start/end (default: 4)
        
    Returns:
        Masked string (e.g., "abcd****wxyz")
        
    Example:
        >>> mask_secret("my-secret-api-key-12345", visible_chars=4)
        'my-s****************2345'
    """
    if not secret or len(secret) <= visible_chars * 2:
        return "***MASKED***"
    
    visible = visible_chars
    return f"{secret[:visible]}{'*' * (len(secret) - visible * 2)}{secret[-visible:]}"


def is_sensitive_key(key: str) -> bool:
    """
    Check if a configuration key name suggests sensitive data.
    
    Detects common naming patterns for secrets, passwords, keys, tokens, etc.
    
    Args:
        key: Configuration key name
        
    Returns:
        True if key name suggests sensitive data
        
    Example:
        >>> is_sensitive_key("DATABASE_PASSWORD")
        True
        >>> is_sensitive_key("DATABASE_HOST")
        False
    """
    sensitive_keywords = [
        'password', 'pwd', 'secret', 'token', 'key', 'apikey', 'api_key',
        'connectionstring', 'connection_string', 'credential', 'auth',
        'bearer', 'authorization', 'private', 'sensitive'
    ]
    
    key_lower = key.lower()
    return any(keyword in key_lower for keyword in sensitive_keywords)


# Example usage and testing
if __name__ == "__main__":
    # Configure logging with redaction
    import logging
    
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("test")
    configure_secure_logging(logger)
    
    # Test cases - secrets should be redacted
    logger.info("Testing with Bearer token: Bearer abc123xyz789")
    logger.info("API key: apikey=super-secret-key-12345")
    logger.info("Password: password=myP@ssw0rd!")
    logger.info("Connection string: Server=db.example.com;Password=secret123;")
    logger.info("Headers: {'Authorization': 'Bearer my-token-value'}")
    
    # Test masking
    print(mask_secret("my-very-long-api-key-12345", visible_chars=4))
    print(is_sensitive_key("DATABASE_PASSWORD"))
    print(is_sensitive_key("DATABASE_HOST"))
