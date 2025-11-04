"""
Validation Session Module for Bicep Validate Command

This module orchestrates the complete validation workflow:
- Project discovery and configuration analysis
- Resource deployment with dependency management
- Endpoint discovery and testing
- Automated fix orchestration
- Progress tracking and reporting

Part of User Story 3: Test Deployment and Endpoint Validation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from specify_cli.validation.project_discovery import ProjectDiscovery, ProjectInfo
from specify_cli.validation.config_analyzer import ConfigAnalyzer
from specify_cli.validation.resource_deployer_simple import ResourceDeployer, ResourceDeployment
from specify_cli.validation.keyvault_manager import KeyVaultManager
from specify_cli.validation.endpoint_discoverer import EndpointDiscoverer, Endpoint
from specify_cli.validation.endpoint_tester import EndpointTester, TestResult, TestStatus
from specify_cli.validation.fix_orchestrator import FixOrchestrator

logger = logging.getLogger(__name__)
console = Console()


class ValidationStage(Enum):
    """Stages of the validation workflow"""
    INITIALIZING = "initializing"
    DISCOVERING = "discovering"
    ANALYZING = "analyzing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ValidationSummary:
    """Summary of validation session results"""
    
    # Session metadata
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Stage information
    current_stage: ValidationStage = ValidationStage.INITIALIZING
    stages_completed: List[ValidationStage] = field(default_factory=list)
    
    # Discovery results
    projects_discovered: int = 0
    projects_analyzed: int = 0
    
    # Deployment results
    resources_deployed: int = 0
    deployment_errors: int = 0
    secrets_stored: int = 0
    
    # Testing results
    endpoints_discovered: int = 0
    endpoints_tested: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    
    # Fix results
    fix_attempts: int = 0
    fixes_successful: int = 0
    
    # Final status
    success: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "current_stage": self.current_stage.value,
            "stages_completed": [s.value for s in self.stages_completed],
            "projects_discovered": self.projects_discovered,
            "projects_analyzed": self.projects_analyzed,
            "resources_deployed": self.resources_deployed,
            "deployment_errors": self.deployment_errors,
            "secrets_stored": self.secrets_stored,
            "endpoints_discovered": self.endpoints_discovered,
            "endpoints_tested": self.endpoints_tested,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_skipped": self.tests_skipped,
            "fix_attempts": self.fix_attempts,
            "fixes_successful": self.fixes_successful,
            "success": self.success,
            "error_message": self.error_message,
        }


class ValidationSession:
    """Orchestrates the complete validation workflow"""
    
    def __init__(
        self,
        project_root: Path,
        resource_group: str,
        keyvault_url: Optional[str] = None,
        enable_fixes: bool = True,
        max_fix_attempts: int = 3,
        environment: str = "test-corp",
        verbose: bool = False,
    ):
        """
        Initialize validation session
        
        Args:
            project_root: Root directory of the project
            resource_group: Target Azure resource group
            keyvault_url: Optional Key Vault URL for secrets
            enable_fixes: Enable automated fixes
            max_fix_attempts: Maximum number of fix attempts
            environment: Target environment name (default: test-corp)
            verbose: Enable verbose logging (detailed Azure CLI output, HTTP details)
        """
        self.project_root = Path(project_root)
        self.resource_group = resource_group
        self.keyvault_url = keyvault_url
        self.enable_fixes = enable_fixes
        self.max_fix_attempts = max_fix_attempts
        self.environment = environment
        self.verbose = verbose
        
        # Initialize summary
        import uuid
        self.summary = ValidationSummary(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now(),
        )
        
        # Components (initialized during run)
        self.discoverer: Optional[ProjectDiscovery] = None
        self.analyzer: Optional[ConfigAnalyzer] = None
        self.deployer: Optional[ResourceDeployer] = None
        self.keyvault_manager: Optional[KeyVaultManager] = None
        self.endpoint_discoverer: Optional[EndpointDiscoverer] = None
        self.endpoint_tester: Optional[EndpointTester] = None
        self.fix_orchestrator: Optional[FixOrchestrator] = None
        
        # Results
        self.discovered_projects: List[ProjectInfo] = []
        self.deployed_resources: List[str] = []
        self.deployment_outputs: Dict = {}
        self.discovered_endpoints: List[Endpoint] = []
        self.test_results: List[TestResult] = []
        
        logger.info(f"Initialized ValidationSession: {self.summary.session_id}")
        logger.info(f"Project: {self.project_root}")
        logger.info(f"Resource Group: {self.resource_group}")
    
    async def run(self) -> ValidationSummary:
        """
        Run the complete validation workflow
        
        Returns:
            Validation summary with results
        """
        console.print(Panel.fit(
            f"[bold cyan]Starting Validation Session[/bold cyan]\n"
            f"Session ID: {self.summary.session_id}\n"
            f"Project: {self.project_root}\n"
            f"Resource Group: {self.resource_group}",
            title="Bicep Validation",
        ))
        
        try:
            # Stage 1: Project Discovery
            await self._run_discovery_stage()
            
            # Stage 2: Configuration Analysis
            await self._run_analysis_stage()
            
            # Stage 3: Resource Deployment
            await self._run_deployment_stage()
            
            # Stage 4: Endpoint Testing (with fix loop)
            await self._run_testing_and_fixing_stages()
            
            # Mark as completed
            self._transition_to_stage(ValidationStage.COMPLETED)
            self.summary.success = True
            
            console.print("[bold green]✓ Validation completed successfully![/bold green]")
        
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            self.summary.current_stage = ValidationStage.FAILED
            self.summary.success = False
            self.summary.error_message = str(e)
            
            console.print(f"[bold red]✗ Validation failed: {e}[/bold red]")
        
        finally:
            # Finalize summary
            self.summary.end_time = datetime.now()
            self.summary.duration_seconds = (
                self.summary.end_time - self.summary.start_time
            ).total_seconds()
            
            # Display summary
            self._display_summary()
        
        return self.summary
    
    async def _run_discovery_stage(self):
        """Stage 1: Discover projects"""
        self._transition_to_stage(ValidationStage.DISCOVERING)
        console.print("\n[bold]Stage 1: Project Discovery[/bold]")
        
        self.discoverer = ProjectDiscovery(self.project_root)
        self.discovered_projects = self.discoverer.discover_projects()
        
        self.summary.projects_discovered = len(self.discovered_projects)
        
        if not self.discovered_projects:
            raise ValueError("No projects discovered in the directory")
        
        console.print(f"✓ Discovered {len(self.discovered_projects)} project(s)")
        
        self._complete_stage(ValidationStage.DISCOVERING)
    
    async def _run_analysis_stage(self):
        """Stage 2: Analyze configuration"""
        self._transition_to_stage(ValidationStage.ANALYZING)
        console.print("\n[bold]Stage 2: Configuration Analysis[/bold]")
        
        for project in self.discovered_projects:
            self.analyzer = ConfigAnalyzer()
            analysis = self.analyzer.analyze_project(project)
            
            console.print(f"✓ Analyzed {project.name}: {len(analysis.app_settings)} settings")
            self.summary.projects_analyzed += 1
        
        self._complete_stage(ValidationStage.ANALYZING)
    
    async def _run_deployment_stage(self):
        """Stage 3: Deploy resources"""
        self._transition_to_stage(ValidationStage.DEPLOYING)
        console.print("\n[bold]Stage 3: Resource Deployment[/bold]")
        
        # Deploy resources
        self.deployer = ResourceDeployer(self.resource_group)
        
        # TODO: Get actual deployment list from project analysis
        # For now, using placeholder
        deployments = []  # Will be populated from project analysis
        
        if deployments:
            result = self.deployer.deploy_resources(deployments)
            
            self.deployed_resources = result["deployed_resources"]
            self.deployment_outputs = result.get("outputs", {})
            
            self.summary.resources_deployed = len(self.deployed_resources)
            self.summary.deployment_errors = len(result.get("errors", []))
            
            console.print(f"✓ Deployed {len(self.deployed_resources)} resource(s)")
        else:
            console.print("⚠ No resources to deploy")
        
        # Store secrets in Key Vault
        if self.keyvault_url and self.analyzer:
            await self._store_secrets()
        
        self._complete_stage(ValidationStage.DEPLOYING)
    
    async def _store_secrets(self):
        """Store secrets in Key Vault"""
        console.print("\n[bold]Storing Secrets[/bold]")
        
        async with KeyVaultManager(self.keyvault_url) as kv:
            for project in self.discovered_projects:
                analyzer = ConfigAnalyzer()
                analysis = analyzer.analyze_project(project)
                
                if analysis.app_settings:
                    stored_count = await kv.store_app_settings(analysis.app_settings)
                    self.summary.secrets_stored += stored_count
                    console.print(f"✓ Stored {stored_count} secret(s) from {project.name}")
    
    async def _run_testing_and_fixing_stages(self):
        """Stages 4-5: Test endpoints with automated fixing"""
        
        # Initialize fix orchestrator
        self.fix_orchestrator = FixOrchestrator(
            self.project_root,
            max_fix_attempts=self.max_fix_attempts,
            enable_template_fixes=self.enable_fixes,
        )
        
        # Fix loop: test → fix → retry
        for attempt in range(self.max_fix_attempts + 1):
            # Stage 4: Endpoint Testing
            await self._run_testing_stage()
            
            # Check if all tests passed
            failed_tests = [r for r in self.test_results if r.status not in [TestStatus.SUCCESS, TestStatus.SKIPPED]]
            
            if not failed_tests:
                console.print("[bold green]✓ All endpoint tests passed![/bold green]")
                break
            
            # Stage 5: Fix failures (if not last attempt)
            if attempt < self.max_fix_attempts:
                await self._run_fixing_stage(failed_tests)
                
                # Check if fixes were successful
                if self.fix_orchestrator.circuit_breaker_open:
                    console.print("[yellow]⚠ Circuit breaker open - stopping fix attempts[/yellow]")
                    break
            else:
                console.print(f"[yellow]⚠ Maximum fix attempts ({self.max_fix_attempts}) reached[/yellow]")
    
    async def _run_testing_stage(self):
        """Stage 4: Test endpoints"""
        self._transition_to_stage(ValidationStage.TESTING)
        console.print("\n[bold]Stage 4: Endpoint Testing[/bold]")
        
        # Discover endpoints
        self.endpoint_discoverer = EndpointDiscoverer(self.project_root)
        self.discovered_endpoints = self.endpoint_discoverer.discover_endpoints()
        
        self.summary.endpoints_discovered = len(self.discovered_endpoints)
        
        if not self.discovered_endpoints:
            console.print("⚠ No endpoints discovered")
            self._complete_stage(ValidationStage.TESTING)
            return
        
        console.print(f"✓ Discovered {len(self.discovered_endpoints)} endpoint(s)")
        
        # Test endpoints with async context manager (ensures proper cleanup)
        # TODO: Get base URL from deployment outputs
        base_url = self.deployment_outputs.get("app_url", "https://example.com")
        
        async with EndpointTester(base_url=base_url) as endpoint_tester:
            self.endpoint_tester = endpoint_tester
            self.test_results = await endpoint_tester.test_multiple_endpoints(
                self.discovered_endpoints
            )
        
        # Update summary
        self.summary.endpoints_tested = len(self.test_results)
        self.summary.tests_passed = sum(1 for r in self.test_results if r.status == TestStatus.SUCCESS)
        self.summary.tests_failed = sum(1 for r in self.test_results if r.status not in [TestStatus.SUCCESS, TestStatus.SKIPPED])
        self.summary.tests_skipped = sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)
        
        # Display results
        self._display_test_results()
        
        self._complete_stage(ValidationStage.TESTING)
    
    async def _run_fixing_stage(self, failed_tests: List[TestResult]):
        """Stage 5: Fix failures"""
        self._transition_to_stage(ValidationStage.FIXING)
        console.print("\n[bold]Stage 5: Automated Fixing[/bold]")
        
        # Attempt fixes
        fix_success = await self.fix_orchestrator.attempt_fix(
            test_results=failed_tests,
            deployment_errors=None,
        )
        
        # Update summary
        fix_summary = self.fix_orchestrator.get_fix_summary()
        self.summary.fix_attempts = fix_summary["total_attempts"]
        self.summary.fixes_successful = fix_summary["successful_fixes"]
        
        if fix_success:
            console.print("✓ Fixes applied successfully")
        else:
            console.print("✗ Some fixes failed")
        
        self._complete_stage(ValidationStage.FIXING)
    
    def _transition_to_stage(self, stage: ValidationStage):
        """Transition to a new validation stage"""
        logger.info(f"Transitioning to stage: {stage.value}")
        self.summary.current_stage = stage
    
    def _complete_stage(self, stage: ValidationStage):
        """Mark a stage as completed"""
        logger.info(f"Completed stage: {stage.value}")
        self.summary.stages_completed.append(stage)
    
    def _display_test_results(self):
        """Display endpoint test results in a table"""
        table = Table(title="Endpoint Test Results")
        
        table.add_column("Method", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Status", style="white")
        table.add_column("Response Time", style="white")
        
        for result in self.test_results:
            # Status with color
            if result.status == TestStatus.SUCCESS:
                status = "[green]✓ PASS[/green]"
            elif result.status == TestStatus.SKIPPED:
                status = "[yellow]⊘ SKIP[/yellow]"
            else:
                status = f"[red]✗ {result.status.value.upper()}[/red]"
            
            # Response time
            time_str = f"{result.response_time_ms:.0f}ms" if result.response_time_ms else "-"
            
            table.add_row(
                result.endpoint.method,
                result.endpoint.path,
                status,
                time_str,
            )
        
        console.print(table)
    
    def _display_summary(self):
        """Display validation summary"""
        # Create summary table
        summary_text = f"""
[bold cyan]Validation Summary[/bold cyan]
Session ID: {self.summary.session_id}
Duration: {self.summary.duration_seconds:.1f}s

[bold]Discovery:[/bold]
  Projects: {self.summary.projects_discovered}
  Analyzed: {self.summary.projects_analyzed}

[bold]Deployment:[/bold]
  Resources: {self.summary.resources_deployed}
  Secrets: {self.summary.secrets_stored}
  Errors: {self.summary.deployment_errors}

[bold]Testing:[/bold]
  Endpoints: {self.summary.endpoints_discovered}
  Tested: {self.summary.endpoints_tested}
  Passed: [green]{self.summary.tests_passed}[/green]
  Failed: [red]{self.summary.tests_failed}[/red]
  Skipped: [yellow]{self.summary.tests_skipped}[/yellow]

[bold]Fixes:[/bold]
  Attempts: {self.summary.fix_attempts}
  Successful: {self.summary.fixes_successful}

[bold]Result:[/bold] {"[green]SUCCESS ✓[/green]" if self.summary.success else "[red]FAILED ✗[/red]"}
"""
        
        console.print(Panel(summary_text, title="Session Complete"))
    
    def get_current_stage(self) -> ValidationStage:
        """Get current validation stage"""
        return self.summary.current_stage
    
    def get_progress(self) -> Dict:
        """Get current progress information"""
        return {
            "current_stage": self.summary.current_stage.value,
            "stages_completed": [s.value for s in self.summary.stages_completed],
            "progress_percentage": len(self.summary.stages_completed) / 6 * 100,
        }
