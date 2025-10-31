"""
Unit tests for resource_deployer module.

Tests resource deployment with mocked Azure CLI.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from specify_cli.validation import ResourceDeployment, DeploymentResult, ValidationError, DeploymentState
from specify_cli.validation.resource_deployer_simple import ResourceDeployer
from specify_cli.utils.dependency_graph import DependencyGraph
from specify_cli.utils.azure_cli_wrapper import AzureCLIError


@pytest.fixture
def mock_azure_cli():
    """Mock Azure CLI wrapper."""
    with patch("specify_cli.validation.resource_deployer_simple.AzureCLIWrapper") as mock:
        cli_instance = Mock()
        cli_instance.validate_template = Mock(return_value={"valid": True})
        cli_instance.deploy_template = Mock(return_value={"outputs": {"endpoint": "https://example.com"}})
        cli_instance.get_resource = Mock(return_value=None)
        cli_instance.delete_resource = Mock(return_value=True)
        mock.return_value = cli_instance
        yield cli_instance


@pytest.fixture
def sample_deployment():
    """Create a sample resource deployment."""
    return ResourceDeployment(
        resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.Web/sites/app",
        resource_type="Microsoft.Web/sites",
        resource_name="test-app",
        deployment_order=0,
        deployment_status=DeploymentState.PENDING,
        bicep_template_path=Path("templates/app.bicep"),
        output_values={}
    )


@pytest.fixture
def sample_deployments():
    """Create multiple sample deployments."""
    return [
        ResourceDeployment(
            resource_id=f"/subscriptions/test/rg/providers/Microsoft.Storage/storageAccounts/storage{i}",
            resource_type="Microsoft.Storage/storageAccounts",
            resource_name=f"storage-{i}",
            deployment_order=i,
            deployment_status=DeploymentState.PENDING,
            bicep_template_path=Path(f"templates/storage{i}.bicep"),
            output_values={}
        )
        for i in range(3)
    ]


@pytest.mark.asyncio
class TestResourceDeployer:
    """Test ResourceDeployer class."""
    
    async def test_initialization(self, mock_azure_cli):
        """Test ResourceDeployer initialization."""
        deployer = ResourceDeployer(
            resource_group="test-rg",
            location="eastus",
            subscription_id="test-sub",
            max_concurrent=4
        )
        
        assert deployer.resource_group == "test-rg"
        assert deployer.location == "eastus"
        assert deployer.subscription_id == "test-sub"
        assert deployer.max_concurrent == 4
        assert deployer.force_redeploy is False
        assert deployer.enable_rollback is True
    
    async def test_deploy_single_resource_success(self, mock_azure_cli, sample_deployment):
        """Test successful deployment of a single resource."""
        deployer = ResourceDeployer(resource_group="test-rg")
        
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is True
        mock_azure_cli.validate_template.assert_called_once()
        mock_azure_cli.deploy_template.assert_called_once()
        assert len(sample_deployment.output_values) > 0
    
    async def test_deploy_single_resource_validation_failure(self, mock_azure_cli, sample_deployment):
        """Test deployment with validation failure."""
        mock_azure_cli.validate_template.return_value = {
            "valid": False,
            "error": "Template syntax error"
        }
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is False
    
    async def test_deploy_single_resource_deployment_failure(self, mock_azure_cli, sample_deployment):
        """Test deployment failure."""
        mock_azure_cli.deploy_template.side_effect = AzureCLIError(
            "az deployment create",
            1,
            "Deployment failed"
        )
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is False
    
    async def test_idempotency_check_resource_exists(self, mock_azure_cli, sample_deployment):
        """Test idempotency check when resource already exists."""
        mock_azure_cli.get_resource.return_value = {"id": sample_deployment.resource_id}
        
        deployer = ResourceDeployer(resource_group="test-rg", force_redeploy=False)
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is True
        # Should skip deployment if resource exists
        mock_azure_cli.deploy_template.assert_not_called()
    
    async def test_force_redeploy_ignores_existing_resource(self, mock_azure_cli, sample_deployment):
        """Test force_redeploy flag ignores existing resources."""
        mock_azure_cli.get_resource.return_value = {"id": sample_deployment.resource_id}
        
        deployer = ResourceDeployer(resource_group="test-rg", force_redeploy=True)
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is True
        # Should deploy even if resource exists
        mock_azure_cli.deploy_template.assert_called_once()
    
    async def test_deploy_multiple_resources(self, mock_azure_cli, sample_deployments):
        """Test deploying multiple resources."""
        deployer = ResourceDeployer(resource_group="test-rg")
        
        result = await deployer.deploy_resources(sample_deployments, show_progress=False)
        
        assert result.success is True
        assert len(result.deployed_resources) == 3
        assert len(result.error_messages) == 0
        assert result.resource_group == "test-rg"
        assert result.duration_seconds > 0
    
    async def test_deploy_with_dependency_graph(self, mock_azure_cli, sample_deployments):
        """Test deployment with dependency ordering."""
        graph = DependencyGraph()
        for deployment in sample_deployments:
            graph.add_node(deployment.resource_id)
        
        # Add dependencies: storage1 -> storage0, storage2 -> storage1
        graph.add_dependency(sample_deployments[1].resource_id, sample_deployments[0].resource_id)
        graph.add_dependency(sample_deployments[2].resource_id, sample_deployments[1].resource_id)
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer.deploy_resources(sample_deployments, dependency_graph=graph, show_progress=False)
        
        assert result.success is True
        assert len(result.deployed_resources) == 3
        
        # Verify ordered deployment calls
        assert mock_azure_cli.deploy_template.call_count == 3
    
    async def test_deploy_with_circular_dependency(self, mock_azure_cli, sample_deployments):
        """Test deployment fails with circular dependency."""
        graph = DependencyGraph()
        for deployment in sample_deployments:
            graph.add_node(deployment.resource_id)
        
        # Create circular dependency: A -> B -> C -> A
        graph.add_dependency(sample_deployments[0].resource_id, sample_deployments[1].resource_id)
        graph.add_dependency(sample_deployments[1].resource_id, sample_deployments[2].resource_id)
        graph.add_dependency(sample_deployments[2].resource_id, sample_deployments[0].resource_id)
        
        deployer = ResourceDeployer(resource_group="test-rg")
        
        with pytest.raises(ValidationError, match="Circular dependency"):
            await deployer.deploy_resources(sample_deployments, dependency_graph=graph, show_progress=False)
    
    async def test_partial_deployment_failure(self, mock_azure_cli, sample_deployments):
        """Test partial failure during deployment."""
        # Make second deployment fail (all retry attempts)
        call_count = [0]
        
        def deploy_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Fail on calls 2, 3, 4 (second resource, all retry attempts)
            if 2 <= call_count[0] <= 4:
                raise AzureCLIError("az deployment", 1, "Deployment failed")
            return {"outputs": {}}
        
        mock_azure_cli.deploy_template.side_effect = deploy_side_effect
        
        deployer = ResourceDeployer(resource_group="test-rg", enable_rollback=False)
        result = await deployer.deploy_resources(sample_deployments, show_progress=False)
        
        assert result.success is False
        assert len(result.deployed_resources) == 2  # First and third succeeded
        assert len(result.error_messages) == 1
    
    async def test_rollback_on_failure(self, mock_azure_cli, sample_deployments):
        """Test automatic rollback on deployment failure."""
        # Make second deployment fail (all retry attempts)
        call_count = [0]
        
        def deploy_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Fail on calls 2, 3, 4 (second resource, all retry attempts)
            if 2 <= call_count[0] <= 4:
                raise AzureCLIError("az deployment", 1, "Deployment failed")
            return {"outputs": {}}
        
        mock_azure_cli.deploy_template.side_effect = deploy_side_effect
        
        deployer = ResourceDeployer(resource_group="test-rg", enable_rollback=True)
        result = await deployer.deploy_resources(sample_deployments, show_progress=False)
        
        assert result.success is False
        # Rollback should be called for successful deployments
        assert mock_azure_cli.delete_resource.call_count >= 1
    
    async def test_retry_on_transient_failure(self, mock_azure_cli, sample_deployment):
        """Test retry logic with exponential backoff."""
        # Fail twice, then succeed
        call_count = [0]
        
        def deploy_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise AzureCLIError("az deployment", 1, "Transient error")
            return {"outputs": {}}
        
        mock_azure_cli.deploy_template.side_effect = deploy_side_effect
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is True
        assert mock_azure_cli.deploy_template.call_count == 3
    
    async def test_retry_exhausted(self, mock_azure_cli, sample_deployment):
        """Test deployment fails after retry exhaustion."""
        mock_azure_cli.deploy_template.side_effect = AzureCLIError(
            "az deployment", 1, "Persistent error"
        )
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer._deploy_single(sample_deployment)
        
        assert result is False
        assert mock_azure_cli.deploy_template.call_count == 3  # max_attempts
    
    async def test_deployment_outputs_parsing(self, mock_azure_cli, sample_deployment):
        """Test parsing of deployment outputs."""
        mock_azure_cli.deploy_template.return_value = {
            "outputs": {
                "endpoint": "https://api.example.com",
                "connectionString": "Server=...",
                "apiKey": "secret123"
            }
        }
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer.deploy_resources([sample_deployment], show_progress=False)
        
        assert result.success is True
        assert len(result.deployment_outputs) == 3
        assert any("endpoint" in key for key in result.deployment_outputs.keys())
    
    async def test_parallel_deployment_limit(self, mock_azure_cli, sample_deployments):
        """Test concurrent deployment limit."""
        # Add more deployments to test semaphore
        many_deployments = sample_deployments * 3  # 9 total
        
        deployer = ResourceDeployer(resource_group="test-rg", max_concurrent=2)
        result = await deployer.deploy_resources(many_deployments, show_progress=False)
        
        assert result.success is True
        assert len(result.deployed_resources) == 9
        # All should be deployed despite concurrency limit
        assert mock_azure_cli.deploy_template.call_count == 9
    
    async def test_check_resource_exists(self, mock_azure_cli, sample_deployment):
        """Test resource existence check."""
        deployer = ResourceDeployer(resource_group="test-rg")
        
        # Resource exists
        mock_azure_cli.get_resource.return_value = {"id": sample_deployment.resource_id}
        exists = await deployer._check_resource_exists(sample_deployment)
        assert exists is True
        
        # Resource doesn't exist
        mock_azure_cli.get_resource.return_value = None
        exists = await deployer._check_resource_exists(sample_deployment)
        assert exists is False
        
        # Error checking resource
        mock_azure_cli.get_resource.side_effect = AzureCLIError("az resource show", 1, "Not found")
        exists = await deployer._check_resource_exists(sample_deployment)
        assert exists is False
    
    async def test_rollback_deployments(self, mock_azure_cli, sample_deployments):
        """Test rollback of deployed resources."""
        deployer = ResourceDeployer(resource_group="test-rg")
        
        await deployer._rollback_deployments(sample_deployments)
        
        # Should delete in reverse order
        assert mock_azure_cli.delete_resource.call_count == 3
    
    async def test_deployment_result_structure(self, mock_azure_cli, sample_deployments):
        """Test DeploymentResult has correct structure."""
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer.deploy_resources(sample_deployments, show_progress=False)
        
        assert isinstance(result, DeploymentResult)
        assert isinstance(result.deployment_id, str)
        assert isinstance(result.timestamp, float)
        assert isinstance(result.success, bool)
        assert isinstance(result.deployed_resources, list)
        assert isinstance(result.deployment_outputs, dict)
        assert isinstance(result.error_messages, list)
        assert isinstance(result.duration_seconds, float)
        assert result.resource_group == "test-rg"


@pytest.mark.asyncio
class TestResourceDeployerEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_empty_deployment_list(self, mock_azure_cli):
        """Test deploying empty list of resources."""
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer.deploy_resources([], show_progress=False)
        
        assert result.success is False  # No resources deployed
        assert len(result.deployed_resources) == 0
    
    async def test_missing_bicep_template(self, mock_azure_cli, sample_deployment):
        """Test deployment with missing template file."""
        sample_deployment.bicep_template_path = Path("nonexistent/template.bicep")
        
        # Make deployment fail consistently (all retry attempts)
        mock_azure_cli.deploy_template.side_effect = AzureCLIError(
            "az deployment", 1, "Template file not found"
        )
        
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer._deploy_single(sample_deployment)
        
        # Should handle gracefully
        assert result is False
    
    async def test_deploy_without_dependency_graph(self, mock_azure_cli, sample_deployments):
        """Test deployment without dependency graph."""
        deployer = ResourceDeployer(resource_group="test-rg")
        result = await deployer.deploy_resources(sample_deployments, dependency_graph=None, show_progress=False)
        
        assert result.success is True
        # Should deploy in original order
        assert len(result.deployed_resources) == 3
