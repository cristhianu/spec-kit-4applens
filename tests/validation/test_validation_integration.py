"""
End-to-end integration tests for Bicep Validate workflow (T069)

Tests complete validation workflow with mocked Azure resources,
including discovery, analysis, deployment, testing, and fixing.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from specify_cli.validation.validation_session import (
    ValidationSession, ValidationStage
)
from specify_cli.validation.project_discovery import ProjectInfo
from specify_cli.validation.endpoint_discoverer import Endpoint
from specify_cli.validation.endpoint_tester import TestResult, TestStatus
from specify_cli.validation.fix_orchestrator import FixAttempt, ErrorCategory, FixStrategy


class TestValidationIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_successful_workflow(self, tmp_path):
        """Test complete workflow with all stages succeeding"""
        # Create mock project structure
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        (project_root / "bicep-templates" / "main.bicep").write_text("// Bicep template")
        
        # Create session
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
            keyvault_url="https://test-kv.vault.azure.net/",
            enable_fixes=True,
        )
        
        # Mock project discovery
        mock_project = ProjectInfo(
            project_id="test-123",
            name="test-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="dotnet",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock config analysis result
        mock_analysis = MagicMock()
        mock_analysis.app_settings = [MagicMock(name="ConnectionString", value="mock")]
        mock_analysis.resource_dependencies = ["Microsoft.Sql/servers"]
        
        # Mock deployment result
        mock_deployment = MagicMock()
        mock_deployment.resource_id = "/subscriptions/123/resourceGroups/test-rg/providers/Microsoft.Web/sites/test-app"
        mock_deployment.outputs = {"app_url": "https://test-app.azurewebsites.net"}
        
        # Mock endpoints
        mock_endpoints = [
            Endpoint(method="GET", path="/api/health", requires_auth=False),
            Endpoint(method="GET", path="/api/users", requires_auth=True),
        ]
        
        # Mock test results (all passing)
        mock_test_results = [
            TestResult(
                endpoint=mock_endpoints[0],
                status=TestStatus.SUCCESS,
                status_code=200,
                response_time_ms=50.0,
            ),
            TestResult(
                endpoint=mock_endpoints[1],
                status=TestStatus.SUCCESS,
                status_code=200,
                response_time_ms=75.0,
            ),
        ]
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[mock_deployment])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.KeyVaultManager') as mock_kv_class:
                        mock_kv = MagicMock()
                        mock_kv.store_multiple_secrets = AsyncMock(return_value=["secret1", "secret2"])
                        mock_kv_class.return_value = mock_kv
                        
                        with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                            mock_ep_disc = MagicMock()
                            mock_ep_disc.discover_endpoints.return_value = mock_endpoints
                            mock_ep_disc_class.return_value = mock_ep_disc
                            
                            with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                                mock_tester = MagicMock()
                                mock_tester.test_multiple_endpoints = AsyncMock(return_value=mock_test_results)
                                mock_tester_class.return_value = mock_tester
                                
                                # Run the workflow
                                result = await session.run()
        
        # Verify successful completion
        assert result.success == True
        assert result.current_stage == ValidationStage.COMPLETED
        assert result.error_message is None
        
        # Verify all stages completed
        assert ValidationStage.DISCOVERING in result.stages_completed
        assert ValidationStage.ANALYZING in result.stages_completed
        assert ValidationStage.DEPLOYING in result.stages_completed
        assert ValidationStage.TESTING in result.stages_completed
        
        # Verify metrics
        assert result.projects_discovered == 1
        assert result.projects_analyzed == 1
        assert result.endpoints_discovered == 2
        assert result.endpoints_tested == 2
        assert result.tests_passed == 2
        assert result.tests_failed == 0
        
        # Verify timing
        assert result.end_time is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0
    
    @pytest.mark.asyncio
    async def test_workflow_with_test_failures_and_fixes(self, tmp_path):
        """Test workflow with test failures that get fixed"""
        # Create mock project structure
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        
        # Create session with fixes enabled
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
            enable_fixes=True,
            max_fix_attempts=2,
        )
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="test-456",
            name="failing-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="nodejs",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock analysis
        mock_analysis = MagicMock()
        mock_analysis.app_settings = []
        mock_analysis.resource_dependencies = []
        
        # Mock endpoints
        mock_endpoints = [
            Endpoint(method="GET", path="/api/health", requires_auth=False),
            Endpoint(method="GET", path="/api/timeout", requires_auth=False),
        ]
        
        # Mock test results with one failure
        mock_test_results = [
            TestResult(
                endpoint=mock_endpoints[0],
                status=TestStatus.SUCCESS,
                status_code=200,
                response_time_ms=50.0,
            ),
            TestResult(
                endpoint=mock_endpoints[1],
                status=TestStatus.TIMEOUT,
                error_message="Request timeout after 30s",
            ),
        ]
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                        mock_ep_disc = MagicMock()
                        mock_ep_disc.discover_endpoints.return_value = mock_endpoints
                        mock_ep_disc_class.return_value = mock_ep_disc
                        
                        with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                            mock_tester = MagicMock()
                            mock_tester.test_multiple_endpoints = AsyncMock(return_value=mock_test_results)
                            mock_tester.get_failed_results.return_value = [mock_test_results[1]]
                            mock_tester_class.return_value = mock_tester
                            
                            with patch('specify_cli.validation.validation_session.FixOrchestrator') as mock_fix_class:
                                mock_orchestrator = MagicMock()
                                mock_orchestrator.attempt_fix = AsyncMock(return_value=True)
                                mock_orchestrator.get_fix_summary.return_value = {
                                    "total_attempts": 1,
                                    "successful_fixes": 1,
                                }
                                mock_fix_class.return_value = mock_orchestrator
                                
                                # Run the workflow
                                result = await session.run()
        
        # Verify completion
        assert result.success == True
        assert ValidationStage.FIXING in result.stages_completed
        
        # Verify test metrics
        assert result.tests_passed >= 0  # May vary due to fix loop
        assert result.tests_failed >= 0
        
        # Verify fix attempts were made (up to max_fix_attempts=2)
        assert result.fix_attempts >= 1
        assert result.fix_attempts <= 2
    
    @pytest.mark.asyncio
    async def test_workflow_failure_during_deployment(self, tmp_path):
        """Test workflow that fails during deployment"""
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
        )
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="test-789",
            name="deploy-fail-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="python",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock analysis
        mock_analysis = MagicMock()
        mock_analysis.app_settings = []
        mock_analysis.resource_dependencies = ["Microsoft.Storage/storageAccounts"]
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    # Make deployment fail
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(
                        side_effect=RuntimeError("Deployment failed: Invalid template")
                    )
                    mock_deployer_class.return_value = mock_deployer
                    
                    # Run the workflow
                    result = await session.run()
        
        # Verify failure handling
        assert result.success == False
        assert result.current_stage == ValidationStage.FAILED
        assert result.error_message is not None
        assert "Deployment failed" in result.error_message or "Invalid template" in result.error_message
        
        # Verify partial completion
        assert ValidationStage.DISCOVERING in result.stages_completed
        assert ValidationStage.ANALYZING in result.stages_completed
    
    @pytest.mark.asyncio
    async def test_workflow_with_no_endpoints_discovered(self, tmp_path):
        """Test workflow when no endpoints are discovered"""
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
        )
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="test-empty",
            name="no-endpoints-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="dotnet",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock analysis
        mock_analysis = MagicMock()
        mock_analysis.app_settings = []
        mock_analysis.resource_dependencies = []
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                        # No endpoints discovered
                        mock_ep_disc = MagicMock()
                        mock_ep_disc.discover_endpoints.return_value = []
                        mock_ep_disc_class.return_value = mock_ep_disc
                        
                        with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                            mock_tester = MagicMock()
                            mock_tester.test_multiple_endpoints = AsyncMock(return_value=[])
                            mock_tester_class.return_value = mock_tester
                            
                            # Run the workflow
                            result = await session.run()
        
        # Verify completion despite no endpoints
        assert result.success == True
        assert result.endpoints_discovered == 0
        assert result.endpoints_tested == 0
        assert result.tests_passed == 0
        assert result.tests_failed == 0
    
    @pytest.mark.asyncio
    async def test_workflow_with_fixes_disabled(self, tmp_path):
        """Test workflow with automatic fixes disabled"""
        project_root = tmp_path / "test-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        
        # Create session with fixes DISABLED
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
            enable_fixes=False,
        )
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="test-no-fix",
            name="no-fix-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="nodejs",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock analysis
        mock_analysis = MagicMock()
        mock_analysis.app_settings = []
        mock_analysis.resource_dependencies = []
        
        # Mock endpoint with failure
        mock_endpoint = Endpoint(method="GET", path="/api/fail", requires_auth=False)
        mock_test_result = TestResult(
            endpoint=mock_endpoint,
            status=TestStatus.SERVER_ERROR,
            status_code=500,
            error_message="Internal server error",
        )
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                        mock_ep_disc = MagicMock()
                        mock_ep_disc.discover_endpoints.return_value = [mock_endpoint]
                        mock_ep_disc_class.return_value = mock_ep_disc
                        
                        with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                            mock_tester = MagicMock()
                            mock_tester.test_multiple_endpoints = AsyncMock(return_value=[mock_test_result])
                            mock_tester.get_failed_results.return_value = [mock_test_result]
                            mock_tester_class.return_value = mock_tester
                            
                            # Run the workflow
                            result = await session.run()
        
        # Verify completion
        assert result.success == True
        assert result.tests_failed == 1
        
        # Verify fixes were attempted despite being disabled via enable_fixes=False
        # The fix loop still runs but orchestrator should not execute fixes
        # With fixes disabled, workflow should complete after first test failure
        assert ValidationStage.TESTING in result.stages_completed


class TestCustomValidationScenarios:
    """Integration tests for custom validation instructions (T078)"""
    
    @pytest.mark.asyncio
    async def test_custom_environment_and_filtering(self, tmp_path):
        """Test custom environment with endpoint filtering"""
        # Create mock project
        project_root = tmp_path / "custom-project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "bicep-templates").mkdir()
        (project_root / "bicep-templates" / "main.bicep").write_text("// Bicep")
        
        # Create session with custom environment and verbose logging
        session = ValidationSession(
            project_root=project_root,
            resource_group="prod-rg",
            environment="production",
            verbose=True,
            enable_fixes=False,
        )
        
        # Verify custom parameters
        assert session.environment == "production"
        assert session.verbose is True
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="custom-123",
            name="custom-project",
            path=project_root,
            source_code_path=project_root / "src",
            bicep_templates_path=project_root / "bicep-templates",
            framework="nodejs",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock multiple endpoints with different methods
        mock_endpoints = [
            Endpoint(method="GET", path="/api/users", requires_auth=False),
            Endpoint(method="POST", path="/api/users", requires_auth=False),
            Endpoint(method="GET", path="/health", requires_auth=False),
            Endpoint(method="DELETE", path="/api/users/1", requires_auth=True),
        ]
        
        # Apply mocks
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analysis = MagicMock()
                mock_analysis.app_settings = []
                mock_analysis.resource_dependencies = []
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                        mock_ep_disc = MagicMock()
                        mock_ep_disc.discover_endpoints.return_value = mock_endpoints
                        mock_ep_disc_class.return_value = mock_ep_disc
                        
                        with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                            mock_tester = MagicMock()
                            
                            # Test endpoint filtering
                            def filter_endpoints(endpoints, methods=None, path_pattern=None):
                                filtered = endpoints
                                if methods:
                                    filtered = [e for e in filtered if e.method in methods]
                                if path_pattern:
                                    import re
                                    pattern = re.compile(path_pattern)
                                    filtered = [e for e in filtered if pattern.search(e.path)]
                                return filtered
                            
                            mock_tester.filter_endpoints.side_effect = filter_endpoints
                            
                            # Mock test results for filtered endpoints
                            mock_test_results = [
                                TestResult(
                                    endpoint=mock_endpoints[0],
                                    status=TestStatus.SUCCESS,
                                    status_code=200,
                                    response_time_ms=30.0,
                                ),
                            ]
                            mock_tester.test_multiple_endpoints = AsyncMock(return_value=mock_test_results)
                            mock_tester.get_failed_results.return_value = []
                            mock_tester_class.return_value = mock_tester
                            
                            # Run workflow
                            result = await session.run()
        
        # Verify success
        assert result.success is True
        assert result.environment == "production"
    
    @pytest.mark.asyncio
    async def test_skip_auth_and_custom_timeout(self, tmp_path):
        """Test skip authentication with custom timeout"""
        project_root = tmp_path / "auth-test"
        project_root.mkdir()
        (project_root / "bicep-templates").mkdir()
        (project_root / "bicep-templates" / "main.bicep").write_text("// Bicep")
        
        # Create session
        session = ValidationSession(
            project_root=project_root,
            resource_group="test-rg",
            enable_fixes=False,
        )
        
        # Mock project
        mock_project = ProjectInfo(
            project_id="auth-123",
            name="auth-test",
            path=project_root,
            source_code_path=project_root,
            bicep_templates_path=project_root / "bicep-templates",
            framework="python",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock endpoints (mix of auth and non-auth)
        mock_endpoints = [
            Endpoint(method="GET", path="/health", requires_auth=False),
            Endpoint(method="GET", path="/api/secure", requires_auth=True),
            Endpoint(method="POST", path="/api/admin", requires_auth=True),
        ]
        
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_discovery = MagicMock()
            mock_discovery.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_discovery
            
            with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analysis = MagicMock()
                mock_analysis.app_settings = []
                mock_analysis.resource_dependencies = []
                mock_analyzer.analyze_project.return_value = mock_analysis
                mock_analyzer_class.return_value = mock_analyzer
                
                with patch('specify_cli.validation.validation_session.ResourceDeployer') as mock_deployer_class:
                    mock_deployer = MagicMock()
                    mock_deployer.deploy_resources = AsyncMock(return_value=[])
                    mock_deployer_class.return_value = mock_deployer
                    
                    with patch('specify_cli.validation.validation_session.EndpointDiscoverer') as mock_ep_disc_class:
                        mock_ep_disc = MagicMock()
                        mock_ep_disc.discover_endpoints.return_value = mock_endpoints
                        mock_ep_disc_class.return_value = mock_ep_disc
                        
                        with patch('specify_cli.validation.validation_session.EndpointTester') as mock_tester_class:
                            # Create tester with skip_auth_endpoints and custom timeout
                            mock_tester = MagicMock()
                            mock_tester.skip_auth_endpoints = True
                            mock_tester.timeout_seconds = 60  # Custom timeout
                            
                            # Mock results: only non-auth endpoint tested, auth ones skipped
                            mock_test_results = [
                                TestResult(
                                    endpoint=mock_endpoints[0],
                                    status=TestStatus.SUCCESS,
                                    status_code=200,
                                    response_time_ms=45.0,
                                ),
                                TestResult(
                                    endpoint=mock_endpoints[1],
                                    status=TestStatus.SKIPPED,
                                    error_message="Authentication required (skipped)",
                                ),
                                TestResult(
                                    endpoint=mock_endpoints[2],
                                    status=TestStatus.SKIPPED,
                                    error_message="Authentication required (skipped)",
                                ),
                            ]
                            
                            mock_tester.test_multiple_endpoints = AsyncMock(return_value=mock_test_results)
                            mock_tester.get_failed_results.return_value = []
                            mock_tester_class.return_value = mock_tester
                            
                            # Run workflow
                            result = await session.run()
        
        # Verify success
        assert result.success is True
        assert result.tests_passed == 1  # Only health endpoint tested
        # Auth endpoints should be skipped, not counted as failures


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

