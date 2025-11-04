"""
Resource deployer for Azure Bicep templates.

Handles deployment of Azure resources using Azure CLI, including
validation, parallel deployment, rollback, and progress reporting.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from specify_cli.validation import (
    ResourceDeployment,
    DeploymentResult,
    ValidationError,
)
from specify_cli.utils.azure_cli_wrapper import AzureCLIWrapper, AzureCLIError
from specify_cli.utils.dependency_graph import DependencyGraph
from specify_cli.utils.retry_policies import ExponentialBackoff, with_retry

logger = logging.getLogger(__name__)


class ResourceDeployer:
    """
    Deploys Azure resources from Bicep templates with dependency management.
    
    Features:
    - Topological sort for correct deployment order
    - Parallel deployment (max 4 concurrent)
    - Template validation before deployment
    - Automatic rollback on failure
    - Exponential backoff retry logic
    - Idempotency checks
    """
    
    def __init__(
        self,
        resource_group: str,
        location: str = "eastus",
        subscription_id: Optional[str] = None,
        max_concurrent: int = 4,
        enable_rollback: bool = True,
        force_redeploy: bool = False
    ):
        """
        Initialize resource deployer.
        
        Args:
            resource_group: Azure resource group name
            location: Azure region for deployment
            subscription_id: Optional Azure subscription ID
            max_concurrent: Maximum concurrent deployments (default 4)
            enable_rollback: Enable automatic rollback on failure
            force_redeploy: Force redeployment even if resource exists
        """
        self.resource_group = resource_group
        self.location = location
        self.subscription_id = subscription_id
        self.max_concurrent = max_concurrent
        self.enable_rollback = enable_rollback
        self.force_redeploy = force_redeploy
        
        self.cli = AzureCLIWrapper(subscription_id=subscription_id)
        self.retry_policy = ExponentialBackoff(
            base_delay=2.0,
            max_delay=60.0,
            max_attempts=3
        )
        
        self.deployed_resources: List[ResourceDeployment] = []
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(
            f"Initialized ResourceDeployer: rg={resource_group}, "
            f"location={location}, max_concurrent={max_concurrent}"
        )
    
    async def deploy_resources(
        self,
        deployments: List[ResourceDeployment],
        dependency_graph: Optional[DependencyGraph] = None
    ) -> List[DeploymentResult]:
        """
        Deploy multiple resources in correct dependency order.
        
        Args:
            deployments: List of resource deployments
            dependency_graph: Optional dependency graph for ordering
            
        Returns:
            List of deployment results
            
        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Starting deployment of {len(deployments)} resources")
        
        # Create deployment order
        if dependency_graph:
            try:
                ordered_ids = dependency_graph.get_ordered_resources()
                deployment_batches = dependency_graph.get_deployment_batches()
                logger.info(
                    f"Deployment order: {len(deployment_batches)} batches, "
                    f"{len(ordered_ids)} total resources"
                )
            except Exception as e:
                raise DeploymentError(f"Failed to create deployment order: {e}")
        else:
            # No dependencies - deploy all in parallel
            deployment_batches = [[d.resource_id for d in deployments]]
        
        # Create deployment lookup
        deployment_map = {d.resource_id: d for d in deployments}
        
        # Deploy in batches
        all_results = []
        
        try:
            for batch_num, batch in enumerate(deployment_batches, 1):
                logger.info(
                    f"Deploying batch {batch_num}/{len(deployment_batches)} "
                    f"with {len(batch)} resources"
                )
                
                # Deploy batch in parallel
                batch_deployments = [
                    deployment_map[resource_id]
                    for resource_id in batch
                    if resource_id in deployment_map
                ]
                
                batch_results = await self._deploy_batch(batch_deployments)
                all_results.extend(batch_results)
                
                # Check for failures
                failed = [r for r in batch_results if r.status != ValidationStatus.PASSED]
                if failed and self.enable_rollback:
                    logger.error(f"Batch {batch_num} had {len(failed)} failures")
                    await self._rollback_deployments()
                    raise DeploymentError(
                        f"Deployment failed in batch {batch_num}: "
                        f"{len(failed)} resources failed"
                    )
            
            logger.info(f"Deployment complete: {len(all_results)} resources deployed")
            return all_results
            
        except Exception as e:
            if self.enable_rollback:
                logger.error(f"Deployment failed: {e}. Starting rollback...")
                await self._rollback_deployments()
            raise
    
    async def _deploy_batch(
        self,
        deployments: List[ResourceDeployment]
    ) -> List[DeploymentResult]:
        """Deploy a batch of resources in parallel"""
        tasks = [
            self._deploy_single_resource(deployment)
            for deployment in deployments
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _deploy_single_resource(
        self,
        deployment: ResourceDeployment
    ) -> DeploymentResult:
        """
        Deploy a single resource with retry logic.
        
        Args:
            deployment: Resource deployment configuration
            
        Returns:
            Deployment result
        """
        async with self.semaphore:
            logger.info(f"Deploying: {deployment.resource_id}")
            
            try:
                # Update state
                deployment.state = DeploymentState.VALIDATING
                
                # Check if resource already exists (idempotency)
                if not self.force_redeploy:
                    exists = await self._check_resource_exists(deployment)
                    if exists:
                        logger.info(f"Resource already exists: {deployment.resource_id}")
                        return DeploymentResult(
                            resource_id=deployment.resource_id,
                            deployment_name=deployment.deployment_name,
                            status=ValidationStatus.PASSED,
                            message="Resource already exists (skipped)",
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            outputs={}
                        )
                
                # Validate template
                await self._validate_template(deployment)
                
                # Deploy with retry
                deployment.state = DeploymentState.DEPLOYING
                result = await self.retry_policy.execute_async(
                    self._execute_deployment,
                    deployment
                )
                
                deployment.state = DeploymentState.SUCCEEDED
                self.deployed_resources.append(deployment)
                
                logger.info(f"Deployment succeeded: {deployment.resource_id}")
                return result
                
            except Exception as e:
                deployment.state = DeploymentState.FAILED
                error_msg = f"Deployment failed: {deployment.resource_id}: {e}"
                logger.error(error_msg)
                
                return DeploymentResult(
                    resource_id=deployment.resource_id,
                    deployment_name=deployment.deployment_name,
                    status=ValidationStatus.FAILED,
                    message=error_msg,
                    errors=[str(e)],
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    outputs={}
                )
    
    async def _check_resource_exists(self, deployment: ResourceDeployment) -> bool:
        """
        Check if resource already exists.
        
        Args:
            deployment: Resource deployment
            
        Returns:
            True if resource exists
        """
        try:
            # Try to get resource by name
            resource_name = deployment.resource_id.split('/')[-1]
            
            result = await asyncio.to_thread(
                self.cli.get_resource,
                resource_name,
                self.resource_group
            )
            
            return result is not None
            
        except AzureCLIError:
            return False
    
    async def _validate_template(self, deployment: ResourceDeployment) -> None:
        """
        Validate Bicep template before deployment.
        
        Args:
            deployment: Resource deployment
            
        Raises:
            DeploymentError: If validation fails
        """
        logger.debug(f"Validating template: {deployment.template_path}")
        
        try:
            await asyncio.to_thread(
                self.cli.validate_template,
                str(deployment.template_path),
                self.resource_group,
                deployment.parameters
            )
            logger.debug(f"Template validation passed: {deployment.resource_id}")
            
        except AzureCLIError as e:
            raise DeploymentError(f"Template validation failed: {e}")
    
    async def _execute_deployment(self, deployment: ResourceDeployment) -> DeploymentResult:
        """
        Execute actual deployment via Azure CLI.
        
        Args:
            deployment: Resource deployment
            
        Returns:
            Deployment result
        """
        start_time = datetime.now()
        
        try:
            # Deploy template
            output = await asyncio.to_thread(
                self.cli.deploy_template,
                str(deployment.template_path),
                self.resource_group,
                deployment.deployment_name,
                deployment.parameters
            )
            
            # Parse outputs
            outputs = self._parse_deployment_outputs(output)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Deployment completed: {deployment.resource_id} "
                f"({duration:.1f}s)"
            )
            
            return DeploymentResult(
                resource_id=deployment.resource_id,
                deployment_name=deployment.deployment_name,
                status=ValidationStatus.PASSED,
                message=f"Deployed successfully in {duration:.1f}s",
                start_time=start_time,
                end_time=end_time,
                outputs=outputs
            )
            
        except AzureCLIError as e:
            end_time = datetime.now()
            raise DeploymentError(f"Deployment execution failed: {e}")
    
    def _parse_deployment_outputs(self, cli_output: Dict[str, Any]) -> Dict[str, str]:
        """
        Parse deployment outputs from Azure CLI response.
        
        Args:
            cli_output: Azure CLI JSON output
            
        Returns:
            Dictionary of output key-value pairs
        """
        outputs = {}
        
        if not cli_output or "properties" not in cli_output:
            return outputs
        
        props = cli_output.get("properties", {})
        output_values = props.get("outputs", {})
        
        for key, value_obj in output_values.items():
            if isinstance(value_obj, dict) and "value" in value_obj:
                outputs[key] = str(value_obj["value"])
            else:
                outputs[key] = str(value_obj)
        
        logger.debug(f"Parsed {len(outputs)} deployment outputs")
        return outputs
    
    async def _rollback_deployments(self) -> None:
        """
        Rollback all deployed resources.
        
        Deletes resources in reverse deployment order.
        """
        if not self.deployed_resources:
            logger.info("No resources to rollback")
            return
        
        logger.warning(f"Rolling back {len(self.deployed_resources)} resources")
        
        # Rollback in reverse order
        for deployment in reversed(self.deployed_resources):
            try:
                resource_name = deployment.resource_id.split('/')[-1]
                
                logger.info(f"Deleting resource: {resource_name}")
                await asyncio.to_thread(
                    self.cli.delete_resource,
                    resource_name,
                    self.resource_group
                )
                
            except Exception as e:
                logger.error(f"Failed to delete {resource_name}: {e}")
        
        self.deployed_resources.clear()
        logger.info("Rollback complete")
    
    async def rollback_deployment(
        self,
        deployment_name: str
    ) -> None:
        """
        Rollback a specific deployment.
        
        Args:
            deployment_name: Name of deployment to rollback
        """
        logger.info(f"Rolling back deployment: {deployment_name}")
        
        # Find matching deployments
        matching = [
            d for d in self.deployed_resources
            if d.deployment_name == deployment_name
        ]
        
        for deployment in reversed(matching):
            try:
                resource_name = deployment.resource_id.split('/')[-1]
                await asyncio.to_thread(
                    self.cli.delete_resource,
                    resource_name,
                    self.resource_group
                )
                self.deployed_resources.remove(deployment)
                
            except Exception as e:
                logger.error(f"Failed to rollback {resource_name}: {e}")
    
    def get_deployment_progress(self) -> Dict[str, Any]:
        """
        Get current deployment progress.
        
        Returns:
            Dictionary with progress metrics
        """
        total = len(self.deployed_resources)
        succeeded = sum(
            1 for d in self.deployed_resources
            if d.state == DeploymentState.SUCCEEDED
        )
        failed = sum(
            1 for d in self.deployed_resources
            if d.state == DeploymentState.FAILED
        )
        pending = sum(
            1 for d in self.deployed_resources
            if d.state == DeploymentState.PENDING
        )
        
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "pending": pending,
            "in_progress": total - succeeded - failed - pending
        }
