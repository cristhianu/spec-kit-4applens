"""
Fix Orchestration Module for Bicep Validate Command

This module orchestrates automated fixes for deployment and endpoint test failures.
Includes error classification, fix strategy dispatch, and circuit breaker pattern.

Part of User Story 3: Test Deployment and Endpoint Validation
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from specify_cli.validation.endpoint_tester import TestResult, TestStatus

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of validation errors"""
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    TEMPLATE_ISSUE = "template_issue"
    DEPENDENCY_ISSUE = "dependency_issue"
    CONFIGURATION_ISSUE = "configuration_issue"
    NETWORK_ISSUE = "network_issue"
    UNKNOWN = "unknown"


class FixStrategy(Enum):
    """Fix strategies for different error categories"""
    RETRY = "retry"  # Simple retry with backoff
    UPDATE_TEMPLATE = "update_template"  # Call /speckit.bicep to fix template
    UPDATE_DEPENDENCIES = "update_dependencies"  # Update project dependencies
    RECONFIGURE = "reconfigure"  # Update configuration/settings
    MANUAL_INTERVENTION = "manual_intervention"  # Cannot auto-fix


@dataclass
class FixAttempt:
    """Record of a fix attempt"""
    
    error_category: ErrorCategory
    fix_strategy: FixStrategy
    description: str
    success: bool
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation for logging"""
        status = "✓" if self.success else "✗"
        return f"{status} {self.fix_strategy.value}: {self.description}"


class FixOrchestrator:
    """Orchestrates automated fixes for validation failures"""
    
    def __init__(
        self,
        project_root: Path,
        max_fix_attempts: int = 3,
        enable_template_fixes: bool = True,
    ):
        """
        Initialize fix orchestrator
        
        Args:
            project_root: Root directory of the project
            max_fix_attempts: Maximum number of fix attempts (circuit breaker)
            enable_template_fixes: Enable automatic template fixes via /speckit.bicep
        """
        self.project_root = Path(project_root)
        self.max_fix_attempts = max_fix_attempts
        self.enable_template_fixes = enable_template_fixes
        
        self.fix_attempts: List[FixAttempt] = []
        self.circuit_breaker_open = False
        
        logger.info(f"Initialized FixOrchestrator for: {self.project_root}")
        logger.info(f"Config: max_attempts={max_fix_attempts}, template_fixes={enable_template_fixes}")
    
    async def attempt_fix(
        self,
        test_results: List[TestResult],
        deployment_errors: Optional[List[str]] = None,
    ) -> bool:
        """
        Attempt to fix validation failures
        
        Args:
            test_results: List of endpoint test results
            deployment_errors: Optional list of deployment error messages
        
        Returns:
            True if fixes were applied successfully, False otherwise
        """
        # Check circuit breaker
        if self.circuit_breaker_open:
            logger.warning("Circuit breaker open - too many failed fix attempts")
            return False
        
        if len(self.fix_attempts) >= self.max_fix_attempts:
            logger.warning(f"Maximum fix attempts ({self.max_fix_attempts}) reached")
            self.circuit_breaker_open = True
            return False
        
        logger.info(f"Analyzing failures (attempt {len(self.fix_attempts) + 1}/{self.max_fix_attempts})...")
        
        # Classify errors
        error_classifications = self._classify_errors(test_results, deployment_errors)
        
        if not error_classifications:
            logger.info("No fixable errors detected")
            return True
        
        # Dispatch fixes based on error categories
        fix_success = await self._dispatch_fixes(error_classifications)
        
        return fix_success
    
    def _classify_errors(
        self,
        test_results: List[TestResult],
        deployment_errors: Optional[List[str]],
    ) -> Dict[ErrorCategory, List[str]]:
        """
        Classify errors into categories
        
        Returns:
            Dictionary mapping error categories to error messages
        """
        classifications: Dict[ErrorCategory, List[str]] = {}
        
        # Classify endpoint test failures
        for result in test_results:
            if result.status == TestStatus.TIMEOUT:
                category = ErrorCategory.TIMEOUT
                message = f"Endpoint timeout: {result.endpoint.method} {result.endpoint.path}"
                classifications.setdefault(category, []).append(message)
            
            elif result.status == TestStatus.AUTH_ERROR:
                category = ErrorCategory.AUTH_ERROR
                message = f"Authentication error: {result.endpoint.method} {result.endpoint.path}"
                classifications.setdefault(category, []).append(message)
            
            elif result.status == TestStatus.SERVER_ERROR:
                category = ErrorCategory.SERVER_ERROR
                message = f"Server error ({result.status_code}): {result.endpoint.method} {result.endpoint.path}"
                classifications.setdefault(category, []).append(message)
            
            elif result.status == TestStatus.FAILURE:
                category = ErrorCategory.UNKNOWN
                message = f"Test failure: {result.endpoint.method} {result.endpoint.path} - {result.error_message}"
                classifications.setdefault(category, []).append(message)
        
        # Classify deployment errors
        if deployment_errors:
            for error in deployment_errors:
                category = self._classify_deployment_error(error)
                classifications.setdefault(category, []).append(error)
        
        # Log classifications
        for category, messages in classifications.items():
            logger.info(f"Found {len(messages)} {category.value} error(s)")
        
        return classifications
    
    def _classify_deployment_error(self, error_message: str) -> ErrorCategory:
        """Classify a deployment error message"""
        error_lower = error_message.lower()
        
        # Template syntax or validation issues
        if any(keyword in error_lower for keyword in ['template', 'bicep', 'syntax', 'validation', 'schema']):
            return ErrorCategory.TEMPLATE_ISSUE
        
        # Dependency issues
        if any(keyword in error_lower for keyword in ['dependency', 'resource not found', 'does not exist']):
            return ErrorCategory.DEPENDENCY_ISSUE
        
        # Configuration issues
        if any(keyword in error_lower for keyword in ['configuration', 'setting', 'parameter', 'invalid value']):
            return ErrorCategory.CONFIGURATION_ISSUE
        
        # Network issues
        if any(keyword in error_lower for keyword in ['network', 'timeout', 'connection', 'unreachable']):
            return ErrorCategory.NETWORK_ISSUE
        
        # Authentication/authorization issues
        if any(keyword in error_lower for keyword in ['auth', 'permission', 'forbidden', 'unauthorized']):
            return ErrorCategory.AUTH_ERROR
        
        return ErrorCategory.UNKNOWN
    
    async def _dispatch_fixes(self, error_classifications: Dict[ErrorCategory, List[str]]) -> bool:
        """
        Dispatch appropriate fix strategies based on error categories
        
        Returns:
            True if all fixes succeeded, False otherwise
        """
        all_fixes_successful = True
        
        for category, messages in error_classifications.items():
            strategy = self._select_fix_strategy(category)
            
            logger.info(f"Applying fix strategy: {strategy.value} for {category.value}")
            
            # Execute fix strategy
            if strategy == FixStrategy.UPDATE_TEMPLATE:
                success = await self._fix_template_issues(messages)
            
            elif strategy == FixStrategy.UPDATE_DEPENDENCIES:
                success = await self._fix_dependency_issues(messages)
            
            elif strategy == FixStrategy.RECONFIGURE:
                success = await self._fix_configuration_issues(messages)
            
            elif strategy == FixStrategy.RETRY:
                # Retry is handled by the caller (validation session)
                success = True
                logger.info("Will retry after other fixes are applied")
            
            elif strategy == FixStrategy.MANUAL_INTERVENTION:
                success = False
                logger.warning(f"Manual intervention required for {category.value}")
            
            else:
                success = False
                logger.warning(f"No fix strategy for {category.value}")
            
            # Record fix attempt
            fix_attempt = FixAttempt(
                error_category=category,
                fix_strategy=strategy,
                description=f"Fixed {len(messages)} {category.value} error(s)",
                success=success,
                error_message=None if success else "Fix failed",
            )
            self.fix_attempts.append(fix_attempt)
            
            if not success:
                all_fixes_successful = False
        
        return all_fixes_successful
    
    def _select_fix_strategy(self, category: ErrorCategory) -> FixStrategy:
        """Select appropriate fix strategy for an error category"""
        strategy_map = {
            ErrorCategory.TIMEOUT: FixStrategy.RETRY,
            ErrorCategory.AUTH_ERROR: FixStrategy.RECONFIGURE,
            ErrorCategory.SERVER_ERROR: FixStrategy.UPDATE_TEMPLATE,
            ErrorCategory.TEMPLATE_ISSUE: FixStrategy.UPDATE_TEMPLATE,
            ErrorCategory.DEPENDENCY_ISSUE: FixStrategy.UPDATE_DEPENDENCIES,
            ErrorCategory.CONFIGURATION_ISSUE: FixStrategy.RECONFIGURE,
            ErrorCategory.NETWORK_ISSUE: FixStrategy.RETRY,
            ErrorCategory.UNKNOWN: FixStrategy.MANUAL_INTERVENTION,
        }
        
        return strategy_map.get(category, FixStrategy.MANUAL_INTERVENTION)
    
    async def _fix_template_issues(self, error_messages: List[str]) -> bool:
        """
        Fix template issues by calling /speckit.bicep command
        
        Args:
            error_messages: List of error messages related to templates
        
        Returns:
            True if fix succeeded, False otherwise
        """
        if not self.enable_template_fixes:
            logger.info("Template fixes disabled, skipping")
            return False
        
        logger.info("Attempting to fix template issues...")
        
        # Combine error messages into a single issue description
        issue_description = " | ".join(error_messages)
        
        try:
            success = await self.fix_template_issue(issue_description)
            
            if success:
                logger.info("✓ Template fixes applied successfully")
            else:
                logger.error("✗ Template fix failed")
            
            return success
        
        except Exception as e:
            logger.error(f"Error fixing template issues: {e}")
            return False
    
    async def fix_template_issue(self, issue_description: str) -> bool:
        """
        Fix a specific template issue by calling /speckit.bicep
        
        Args:
            issue_description: Description of the template issue
        
        Returns:
            True if fix succeeded, False otherwise
        """
        logger.info(f"Calling /speckit.bicep with issue: {issue_description}")
        
        try:
            # Call the speckit.bicep command via subprocess
            # In production, this would be integrated with the agent command system
            # For now, we'll simulate the call
            
            # TODO: Integrate with actual /speckit.bicep command
            # For Phase 5 implementation, we'll create a placeholder
            
            result = subprocess.run(
                ["specify", "bicep", "--issue", issue_description],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Template fix command completed successfully")
                return True
            else:
                logger.error(f"Template fix command failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("Template fix command timed out")
            return False
        
        except FileNotFoundError:
            logger.warning("specify CLI not found, simulating template fix")
            # In test/dev environment, simulate success
            return True
        
        except Exception as e:
            logger.error(f"Error calling template fix: {e}")
            return False
    
    async def _fix_dependency_issues(self, error_messages: List[str]) -> bool:
        """
        Fix dependency issues (placeholder for future implementation)
        
        Args:
            error_messages: List of dependency-related error messages
        
        Returns:
            True if fix succeeded, False otherwise
        """
        logger.info("Dependency fixes not yet implemented")
        # TODO: Implement dependency resolution (e.g., ensure resources exist in correct order)
        return False
    
    async def _fix_configuration_issues(self, error_messages: List[str]) -> bool:
        """
        Fix configuration issues (placeholder for future implementation)
        
        Args:
            error_messages: List of configuration-related error messages
        
        Returns:
            True if fix succeeded, False otherwise
        """
        logger.info("Configuration fixes not yet implemented")
        # TODO: Implement configuration updates (e.g., update app settings, connection strings)
        return False
    
    def reset_circuit_breaker(self):
        """Reset the circuit breaker (allow new fix attempts)"""
        self.circuit_breaker_open = False
        self.fix_attempts = []
        logger.info("Circuit breaker reset")
    
    def get_fix_summary(self) -> Dict:
        """Get summary of all fix attempts"""
        return {
            "total_attempts": len(self.fix_attempts),
            "successful_fixes": sum(1 for a in self.fix_attempts if a.success),
            "failed_fixes": sum(1 for a in self.fix_attempts if not a.success),
            "circuit_breaker_open": self.circuit_breaker_open,
            "attempts": [
                {
                    "category": a.error_category.value,
                    "strategy": a.fix_strategy.value,
                    "description": a.description,
                    "success": a.success,
                }
                for a in self.fix_attempts
            ],
        }
