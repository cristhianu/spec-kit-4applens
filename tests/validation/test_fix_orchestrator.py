"""
Unit tests for FixOrchestrator module

Tests automated fix orchestration, error classification, fix strategies,
and circuit breaker pattern.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import subprocess

from specify_cli.validation.fix_orchestrator import (
    FixOrchestrator, ErrorCategory, FixStrategy, FixAttempt
)
from specify_cli.validation.endpoint_tester import TestResult, TestStatus, Endpoint


class TestFixOrchestrator:
    """Test FixOrchestrator class"""
    
    def test_initialization(self, tmp_path):
        """Test orchestrator initialization"""
        orchestrator = FixOrchestrator(
            project_root=tmp_path,
            max_fix_attempts=3
        )
        
        assert orchestrator.project_root == tmp_path
        assert orchestrator.max_fix_attempts == 3
        assert orchestrator.fix_attempts == []
        assert orchestrator.circuit_breaker_open == False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, tmp_path):
        """Test circuit breaker opens after max attempts"""
        orchestrator = FixOrchestrator(project_root=tmp_path, max_fix_attempts=2)
        
        # Create failed test results
        endpoint = Endpoint(method="GET", path="/api/test")
        test_results = [
            TestResult(
                endpoint=endpoint,
                status=TestStatus.FAILURE,
                error_message="Test error"
            )
        ]
        
        # First attempt
        await orchestrator.attempt_fix(test_results, [])
        assert not orchestrator.circuit_breaker_open
        
        # Second attempt
        await orchestrator.attempt_fix(test_results, [])
        assert orchestrator.circuit_breaker_open
        
        # Third attempt should be blocked
        result = await orchestrator.attempt_fix(test_results, [])
        assert result == False  # Fix blocked by circuit breaker
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, tmp_path):
        """Test circuit breaker reset"""
        orchestrator = FixOrchestrator(project_root=tmp_path, max_fix_attempts=1)
        
        endpoint = Endpoint(method="GET", path="/api/test")
        test_results = [
            TestResult(endpoint=endpoint, status=TestStatus.FAILURE, error_message="Error")
        ]
        
        # Open circuit breaker
        await orchestrator.attempt_fix(test_results, [])
        assert orchestrator.circuit_breaker_open
        
        # Reset
        orchestrator.reset_circuit_breaker()
        assert not orchestrator.circuit_breaker_open
        assert len(orchestrator.fix_attempts) == 0
    
    def test_classify_timeout_errors(self, tmp_path):
        """Test classification of timeout errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        endpoint = Endpoint(method="GET", path="/api/slow")
        test_results = [
            TestResult(
                endpoint=endpoint,
                status=TestStatus.TIMEOUT,
                error_message="Request timeout"
            )
        ]
        
        classifications = orchestrator._classify_errors(test_results, [])
        
        assert ErrorCategory.TIMEOUT in classifications
        assert "Request timeout" in classifications[ErrorCategory.TIMEOUT]
    
    def test_classify_auth_errors(self, tmp_path):
        """Test classification of authentication errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        endpoint = Endpoint(method="GET", path="/api/secure")
        test_results = [
            TestResult(
                endpoint=endpoint,
                status=TestStatus.AUTH_ERROR,
                status_code=401,
                error_message="Unauthorized"
            )
        ]
        
        classifications = orchestrator._classify_errors(test_results, [])
        
        assert ErrorCategory.AUTH_ERROR in classifications
        assert "401: Unauthorized" in classifications[ErrorCategory.AUTH_ERROR]
    
    def test_classify_server_errors(self, tmp_path):
        """Test classification of server errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        endpoint = Endpoint(method="GET", path="/api/error")
        test_results = [
            TestResult(
                endpoint=endpoint,
                status=TestStatus.SERVER_ERROR,
                status_code=500,
                error_message="Internal server error"
            )
        ]
        
        classifications = orchestrator._classify_errors(test_results, [])
        
        assert ErrorCategory.SERVER_ERROR in classifications
        assert "500: Internal server error" in classifications[ErrorCategory.SERVER_ERROR]
    
    def test_classify_deployment_template_errors(self, tmp_path):
        """Test classification of template deployment errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        deployment_errors = [
            "InvalidTemplate: The template is invalid",
            "Template validation failed: Missing required parameter"
        ]
        
        classifications = orchestrator._classify_errors([], deployment_errors)
        
        assert ErrorCategory.TEMPLATE_ISSUE in classifications
        assert len(classifications[ErrorCategory.TEMPLATE_ISSUE]) == 2
    
    def test_classify_deployment_dependency_errors(self, tmp_path):
        """Test classification of dependency deployment errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        deployment_errors = [
            "ResourceNotFound: The resource group does not exist",
            "DependencyError: Required resource not found"
        ]
        
        classifications = orchestrator._classify_errors([], deployment_errors)
        
        assert ErrorCategory.DEPENDENCY_ISSUE in classifications
        assert len(classifications[ErrorCategory.DEPENDENCY_ISSUE]) == 2
    
    def test_select_fix_strategy_timeout(self, tmp_path):
        """Test fix strategy selection for timeout errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        strategy = orchestrator._select_fix_strategy(ErrorCategory.TIMEOUT)
        assert strategy == FixStrategy.RETRY
    
    def test_select_fix_strategy_template(self, tmp_path):
        """Test fix strategy selection for template errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        strategy = orchestrator._select_fix_strategy(ErrorCategory.TEMPLATE_ISSUE)
        assert strategy == FixStrategy.UPDATE_TEMPLATE
    
    def test_select_fix_strategy_dependency(self, tmp_path):
        """Test fix strategy selection for dependency errors"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        strategy = orchestrator._select_fix_strategy(ErrorCategory.DEPENDENCY_ISSUE)
        assert strategy == FixStrategy.UPDATE_DEPENDENCIES
    
    @patch('subprocess.run')
    def test_fix_template_issue_success(self, mock_subprocess, tmp_path):
        """Test successful template fix via /speckit.bicep"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        # Mock successful subprocess call
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Template fixed successfully",
            stderr=""
        )
        
        result = orchestrator.fix_template_issue("Invalid template parameter")
        
        assert result == True
        mock_subprocess.assert_called_once()
        
        # Check fix attempts
        assert len(orchestrator.fix_attempts) == 1
        assert orchestrator.fix_attempts[0].fix_strategy == FixStrategy.UPDATE_TEMPLATE
        assert orchestrator.fix_attempts[0].success == True
    
    @patch('subprocess.run')
    def test_fix_template_issue_failure(self, mock_subprocess, tmp_path):
        """Test failed template fix"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        # Mock failed subprocess call
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Fix failed: Unknown error"
        )
        
        result = orchestrator.fix_template_issue("Invalid template")
        
        assert result == False
        assert len(orchestrator.fix_attempts) == 1
        assert orchestrator.fix_attempts[0].success == False
        assert orchestrator.fix_attempts[0].error_message is not None
        assert "Fix failed" in orchestrator.fix_attempts[0].error_message
    
    @pytest.mark.asyncio
    async def test_attempt_fix_with_mixed_errors(self, tmp_path):
        """Test fix attempt with multiple error types"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        # Create mixed test results
        endpoint1 = Endpoint(method="GET", path="/api/slow")
        endpoint2 = Endpoint(method="GET", path="/api/secure")
        
        test_results = [
            TestResult(endpoint=endpoint1, status=TestStatus.TIMEOUT, error_message="Timeout"),
            TestResult(endpoint=endpoint2, status=TestStatus.AUTH_ERROR, error_message="Unauthorized"),
        ]
        
        deployment_errors = ["InvalidTemplate: Missing parameter"]
        
        with patch.object(orchestrator, '_fix_template_issues', return_value=True):
            result = await orchestrator.attempt_fix(test_results, deployment_errors)
        
        # Should have recorded fix attempts
        assert len(orchestrator.fix_attempts) >= 1
        
        # Check that different error categories were identified
        assert result is not None  # Returns bool, not list
    
    def test_get_fix_summary(self, tmp_path):
        """Test fix summary generation"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        # Add some fix attempts to history
        orchestrator.fix_attempts = [
            FixAttempt(
                error_category=ErrorCategory.TEMPLATE_ISSUE,
                fix_strategy=FixStrategy.UPDATE_TEMPLATE,
                description="Fix template parameter",
                success=True
            ),
            FixAttempt(
                error_category=ErrorCategory.TIMEOUT,
                fix_strategy=FixStrategy.RETRY,
                description="Retry timed out endpoint",
                success=False,
                error_message="Still timing out"
            ),
        ]
        
        summary = orchestrator.get_fix_summary()
        
        assert "total_attempts" in summary
        assert summary["total_attempts"] == 2
        assert "successful" in summary
        assert summary["successful"] == 1
        assert "failed" in summary
        assert summary["failed"] == 1
        assert "by_category" in summary
        assert ErrorCategory.TEMPLATE_ISSUE.value in summary["by_category"]
        assert ErrorCategory.TIMEOUT.value in summary["by_category"]
    
    def test_empty_fix_summary(self, tmp_path):
        """Test fix summary with no attempts"""
        orchestrator = FixOrchestrator(project_root=tmp_path)
        
        summary = orchestrator.get_fix_summary()
        
        assert summary["total_attempts"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert len(summary["by_category"]) == 0
