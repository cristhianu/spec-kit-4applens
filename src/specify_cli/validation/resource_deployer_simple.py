"""
Resource deployer for Azure Bicep templates - simplified version.

Handles deployment of Azure resources using Azure CLI with correct data models.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict
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

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class ResourceDeployer:
    """
    Deploys Azure resources from Bicep templates.
    
    Uses correct data models from __init__.py:
    - ResourceDeployment: resource_id, resource_type, resource_name, deployment_order, 
      deployment_status, bicep_template_path, output_values
    - DeploymentResult: deployment_id, timestamp, success, deployed_resources,
      resource_group, subscription_id, deployment_outputs, error_messages, duration_seconds
    """
    
    def __init__(
        self,
        resource_group: str,
        location: str = "eastus",
        subscription_id: Optional[str] = None,
        max_concurrent: int = 4,
        force_redeploy: bool = False,
        enable_rollback: bool = True
    ):
        """Initialize resource deployer."""
        self.resource_group = resource_group
        self.location = location
        self.subscription_id = subscription_id
        self.max_concurrent = max_concurrent
        self.force_redeploy = force_redeploy
        self.enable_rollback = enable_rollback
        self.cli = AzureCLIWrapper(subscription_id=subscription_id)
        self._deployment_sem = asyncio.Semaphore(max_concurrent)
        self._deployed_resources: List[ResourceDeployment] = []
        self._retry_policy = ExponentialBackoff(max_attempts=3, base_delay=2.0)
        
        logger.info(f"Initialized ResourceDeployer for RG: {resource_group}")

    
    async def deploy_resources(
        self,
        deployments: List[ResourceDeployment],
        dependency_graph: Optional[DependencyGraph] = None,
        show_progress: bool = True
    ) -> DeploymentResult:
        """
        Deploy multiple resources with dependency ordering.
        
        Args:
            deployments: List of resource deployments
            dependency_graph: Optional dependency graph for ordering
            show_progress: Whether to show progress bars (requires rich)
            
        Returns:
            DeploymentResult with overall status
        """
        start_time = datetime.now()
        deployment_id = str(uuid.uuid4())
        
        logger.info(f"Starting deployment {deployment_id} with {len(deployments)} resources")
        
        # Check for circular dependencies
        if dependency_graph and dependency_graph.has_cycle():
            raise ValidationError("Circular dependency detected in resource graph")
        
        # Order deployments
        if dependency_graph:
            try:
                ordered_ids = dependency_graph.get_ordered_resources()
                deployments = sorted(
                    deployments,
                    key=lambda d: ordered_ids.index(d.resource_id) if d.resource_id in ordered_ids else 999
                )
            except Exception as e:
                logger.warning(f"Could not order deployments: {e}")
        
        # Deploy with progress tracking
        deployed_resources: List[ResourceDeployment] = []
        deployment_outputs: Dict[str, str] = {}
        error_messages: List[str] = []
        
        if show_progress and RICH_AVAILABLE:
            deployed_resources, deployment_outputs, error_messages = await self._deploy_with_progress(deployments)
        else:
            deployed_resources, deployment_outputs, error_messages = await self._deploy_without_progress(deployments)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Determine success
        success = len(error_messages) == 0 and len(deployed_resources) > 0
        
        # Rollback on failure if enabled
        if not success and self.enable_rollback and deployed_resources:
            logger.warning("Deployment failed, initiating rollback...")
            await self._rollback_deployments(deployed_resources)
        
        return DeploymentResult(
            deployment_id=deployment_id,
            timestamp=start_time.timestamp(),
            success=success,
            deployed_resources=deployed_resources,
            resource_group=self.resource_group,
            subscription_id=self.subscription_id or "default",
            deployment_outputs=deployment_outputs,
            error_messages=error_messages,
            duration_seconds=duration
        )
    
    async def _deploy_single(self, deployment: ResourceDeployment) -> bool:
        """
        Deploy a single resource.
        
        Returns:
            True if successful, False otherwise
        """
        async with self._deployment_sem:
            try:
                logger.info(f"Deploying {deployment.resource_name} ({deployment.resource_type})")
                
                # Check if resource already exists (idempotency)
                if not self.force_redeploy:
                    exists = await self._check_resource_exists(deployment)
                    if exists:
                        logger.info(f"Resource {deployment.resource_name} already exists (skipping)")
                        self._deployed_resources.append(deployment)
                        return True
                
                # Validate template
                template_path = deployment.bicep_template_path
                logger.debug(f"Validating template: {template_path}")
                
                # Retry validation with exponential backoff
                for attempt in range(self._retry_policy.max_attempts):
                    try:
                        validation_result = await asyncio.to_thread(
                            self.cli.validate_template,
                            self.resource_group,
                            template_path
                        )
                        
                        if not validation_result["valid"]:
                            raise ValidationError(f"Template validation failed: {validation_result.get('error')}")
                        break
                    except Exception as e:
                        if attempt < self._retry_policy.max_attempts - 1:
                            delay = self._retry_policy.get_delay(attempt)
                            logger.warning(f"Validation attempt {attempt + 1} failed, retrying in {delay}s...")
                            await asyncio.sleep(delay)
                        else:
                            raise
                
                # Deploy template with retry
                for attempt in range(self._retry_policy.max_attempts):
                    try:
                        logger.info(f"Deploying template: {template_path}")
                        deploy_result = await asyncio.to_thread(
                            self.cli.deploy_template,
                            self.resource_group,
                            template_path,
                            deployment_name=f"deploy-{deployment.resource_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        )
                        
                        # Update output values
                        if "outputs" in deploy_result:
                            deployment.output_values.update(deploy_result["outputs"])
                        
                        logger.info(f"Successfully deployed: {deployment.resource_name}")
                        self._deployed_resources.append(deployment)
                        return True
                    except Exception as e:
                        if attempt < self._retry_policy.max_attempts - 1:
                            delay = self._retry_policy.get_delay(attempt)
                            logger.warning(f"Deployment attempt {attempt + 1} failed, retrying in {delay}s...")
                            await asyncio.sleep(delay)
                        else:
                            raise
                
            except Exception as e:
                logger.error(f"Deployment failed for {deployment.resource_name}: {e}")
                return False
        
        return False  # Should not reach here
    
    async def _check_resource_exists(self, deployment: ResourceDeployment) -> bool:
        """Check if a resource already exists (idempotency check)."""
        try:
            result = await asyncio.to_thread(
                self.cli.get_resource,
                deployment.resource_id
            )
            return result is not None
        except AzureCLIError:
            return False
        except Exception:
            return False
    
    async def _deploy_with_progress(
        self,
        deployments: List[ResourceDeployment]
    ) -> tuple[List[ResourceDeployment], Dict[str, str], List[str]]:
        """Deploy resources with Rich progress bars."""
        deployed_resources: List[ResourceDeployment] = []
        deployment_outputs: Dict[str, str] = {}
        error_messages: List[str] = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Deploying resources...", total=len(deployments))
            
            for deployment in deployments:
                progress.update(task, description=f"[cyan]Deploying {deployment.resource_name}...")
                try:
                    result = await self._deploy_single(deployment)
                    if result:
                        deployed_resources.append(deployment)
                        if deployment.output_values:
                            for key, value in deployment.output_values.items():
                                deployment_outputs[f"{deployment.resource_id}/{key}"] = str(value)
                    else:
                        # Deployment failed (returned False)
                        error_msg = f"Deployment failed for {deployment.resource_name}"
                        logger.error(error_msg)
                        error_messages.append(error_msg)
                except Exception as e:
                    error_msg = f"Failed to deploy {deployment.resource_id}: {e}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
                
                progress.advance(task)
        
        return deployed_resources, deployment_outputs, error_messages
    
    async def _deploy_without_progress(
        self,
        deployments: List[ResourceDeployment]
    ) -> tuple[List[ResourceDeployment], Dict[str, str], List[str]]:
        """Deploy resources without progress bars."""
        deployed_resources: List[ResourceDeployment] = []
        deployment_outputs: Dict[str, str] = {}
        error_messages: List[str] = []
        
        for deployment in deployments:
            try:
                result = await self._deploy_single(deployment)
                if result:
                    deployed_resources.append(deployment)
                    if deployment.output_values:
                        for key, value in deployment.output_values.items():
                            deployment_outputs[f"{deployment.resource_id}/{key}"] = str(value)
                else:
                    # Deployment failed (returned False)
                    error_msg = f"Deployment failed for {deployment.resource_name}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to deploy {deployment.resource_id}: {e}"
                logger.error(error_msg)
                error_messages.append(error_msg)
        
        return deployed_resources, deployment_outputs, error_messages
    
    async def _rollback_deployments(self, deployed_resources: List[ResourceDeployment]) -> None:
        """Rollback deployed resources by deleting them."""
        logger.warning(f"Rolling back {len(deployed_resources)} deployed resources...")
        
        for deployment in reversed(deployed_resources):
            try:
                logger.info(f"Deleting resource: {deployment.resource_name}")
                await asyncio.to_thread(
                    self.cli.delete_resource,
                    deployment.resource_id
                )
                logger.info(f"Successfully deleted: {deployment.resource_name}")
            except Exception as e:
                logger.error(f"Failed to delete {deployment.resource_name}: {e}")
