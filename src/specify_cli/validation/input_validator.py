"""
Input validation utilities for Bicep validate command

Validates project paths, Azure resource names, subscription IDs,
and other user inputs to prevent errors and security issues.
"""

import re
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class InputValidator:
    """Validates user inputs for the validate command"""
    
    # Azure naming conventions
    # https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules
    RESOURCE_GROUP_PATTERN = re.compile(r'^[\w\-\.\(\)]{1,90}$')
    SUBSCRIPTION_ID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    KEYVAULT_URL_PATTERN = re.compile(r'^https://[a-zA-Z0-9\-]{3,24}\.vault\.azure\.net/?$')
    ENVIRONMENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]{1,50}$')
    
    @staticmethod
    def validate_project_path(path: Path) -> Path:
        """
        Validate project path exists and is accessible
        
        Args:
            path: Project root path
            
        Returns:
            Resolved absolute path
            
        Raises:
            ValidationError: If path is invalid or inaccessible
        """
        try:
            resolved = path.resolve()
            
            if not resolved.exists():
                raise ValidationError(f"Project path does not exist: {path}")
            
            if not resolved.is_dir():
                raise ValidationError(f"Project path is not a directory: {path}")
            
            # Check read access
            if not resolved.stat().st_mode & 0o444:
                raise ValidationError(f"Project path is not readable: {path}")
            
            logger.debug(f"Validated project path: {resolved}")
            return resolved
            
        except PermissionError as e:
            raise ValidationError(f"Permission denied accessing project path: {path}") from e
        except Exception as e:
            raise ValidationError(f"Invalid project path: {path} - {e}") from e
    
    @staticmethod
    def validate_resource_group_name(name: str) -> str:
        """
        Validate Azure resource group name
        
        Args:
            name: Resource group name
            
        Returns:
            Validated name
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError("Resource group name cannot be empty")
        
        if len(name) > 90:
            raise ValidationError(f"Resource group name too long (max 90 chars): {name}")
        
        if not InputValidator.RESOURCE_GROUP_PATTERN.match(name):
            raise ValidationError(
                f"Invalid resource group name: {name}\n"
                "Must contain only alphanumerics, underscores, parentheses, hyphens, periods"
            )
        
        # Check for invalid endings
        if name.endswith('.'):
            raise ValidationError(f"Resource group name cannot end with period: {name}")
        
        logger.debug(f"Validated resource group name: {name}")
        return name
    
    @staticmethod
    def validate_subscription_id(subscription_id: str) -> str:
        """
        Validate Azure subscription ID (GUID format)
        
        Args:
            subscription_id: Subscription GUID
            
        Returns:
            Validated subscription ID
            
        Raises:
            ValidationError: If subscription ID is invalid
        """
        if not subscription_id:
            raise ValidationError("Subscription ID cannot be empty")
        
        if not InputValidator.SUBSCRIPTION_ID_PATTERN.match(subscription_id):
            raise ValidationError(
                f"Invalid subscription ID format: {subscription_id}\n"
                "Expected GUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )
        
        logger.debug(f"Validated subscription ID: {subscription_id}")
        return subscription_id
    
    @staticmethod
    def validate_keyvault_url(url: Optional[str]) -> Optional[str]:
        """
        Validate Azure Key Vault URL
        
        Args:
            url: Key Vault URL (optional)
            
        Returns:
            Validated URL or None
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            return None
        
        if not InputValidator.KEYVAULT_URL_PATTERN.match(url):
            raise ValidationError(
                f"Invalid Key Vault URL: {url}\n"
                "Expected format: https://<vault-name>.vault.azure.net/"
            )
        
        logger.debug(f"Validated Key Vault URL: {url}")
        return url
    
    @staticmethod
    def validate_environment_name(name: str) -> str:
        """
        Validate environment name
        
        Args:
            name: Environment name (e.g., dev, staging, production)
            
        Returns:
            Validated name
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError("Environment name cannot be empty")
        
        if len(name) > 50:
            raise ValidationError(f"Environment name too long (max 50 chars): {name}")
        
        if not InputValidator.ENVIRONMENT_NAME_PATTERN.match(name):
            raise ValidationError(
                f"Invalid environment name: {name}\n"
                "Must contain only alphanumerics, hyphens, underscores"
            )
        
        logger.debug(f"Validated environment name: {name}")
        return name
    
    @staticmethod
    def validate_http_methods(methods_str: Optional[str]) -> Optional[List[str]]:
        """
        Validate and parse HTTP methods string
        
        Args:
            methods_str: Comma-separated HTTP methods (e.g., "GET,POST,PUT")
            
        Returns:
            List of validated method names or None
            
        Raises:
            ValidationError: If methods are invalid
        """
        if not methods_str:
            return None
        
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        
        methods = [m.strip().upper() for m in methods_str.split(',')]
        
        invalid_methods = [m for m in methods if m not in valid_methods]
        if invalid_methods:
            raise ValidationError(
                f"Invalid HTTP methods: {', '.join(invalid_methods)}\n"
                f"Valid methods: {', '.join(sorted(valid_methods))}"
            )
        
        logger.debug(f"Validated HTTP methods: {methods}")
        return methods
    
    @staticmethod
    def validate_status_codes(codes_str: Optional[str]) -> Optional[List[int]]:
        """
        Validate and parse status codes string
        
        Args:
            codes_str: Comma-separated status codes (e.g., "200,201,204")
            
        Returns:
            List of validated status codes or None
            
        Raises:
            ValidationError: If status codes are invalid
        """
        if not codes_str:
            return None
        
        try:
            codes = [int(c.strip()) for c in codes_str.split(',')]
        except ValueError as e:
            raise ValidationError(f"Invalid status code format: {codes_str}") from e
        
        # Validate range (100-599 per HTTP spec)
        invalid_codes = [c for c in codes if c < 100 or c > 599]
        if invalid_codes:
            raise ValidationError(
                f"Status codes out of range (100-599): {', '.join(map(str, invalid_codes))}"
            )
        
        logger.debug(f"Validated status codes: {codes}")
        return codes
    
    @staticmethod
    def validate_timeout(timeout: Optional[int]) -> Optional[int]:
        """
        Validate timeout value
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Validated timeout or None
            
        Raises:
            ValidationError: If timeout is invalid
        """
        if timeout is None:
            return None
        
        if timeout <= 0:
            raise ValidationError(f"Timeout must be positive: {timeout}")
        
        if timeout > 600:  # 10 minutes max
            raise ValidationError(f"Timeout too large (max 600s): {timeout}")
        
        logger.debug(f"Validated timeout: {timeout}s")
        return timeout
    
    @staticmethod
    def validate_regex_pattern(pattern: Optional[str]) -> Optional[str]:
        """
        Validate regex pattern
        
        Args:
            pattern: Regex pattern string
            
        Returns:
            Validated pattern or None
            
        Raises:
            ValidationError: If pattern is invalid regex
        """
        if not pattern:
            return None
        
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern: {pattern} - {e}") from e
        
        logger.debug(f"Validated regex pattern: {pattern}")
        return pattern
    
    @staticmethod
    def validate_max_retries(retries: int) -> int:
        """
        Validate max retries value
        
        Args:
            retries: Maximum retry attempts
            
        Returns:
            Validated retries value
            
        Raises:
            ValidationError: If retries value is invalid
        """
        if retries < 0:
            raise ValidationError(f"Max retries cannot be negative: {retries}")
        
        if retries > 10:
            raise ValidationError(f"Max retries too large (max 10): {retries}")
        
        logger.debug(f"Validated max retries: {retries}")
        return retries
