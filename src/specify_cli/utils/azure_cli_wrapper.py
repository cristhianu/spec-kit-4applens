"""
Azure CLI wrapper for subprocess execution.

Provides a consistent interface for executing Azure CLI commands with:
- Error handling and output parsing
- Subprocess management
- JSON output parsing
- Command validation
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AzureCLIError(Exception):
    """Raised when Azure CLI command fails"""
    def __init__(self, command: str, exit_code: int, stderr: str):
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Azure CLI command failed with exit code {exit_code}: {command}")


class AzureCLIWrapper:
    """
    Wrapper for Azure CLI command execution.
    
    Provides subprocess management, error handling, and output parsing
    for Azure CLI commands.
    """
    
    def __init__(self, subscription_id: Optional[str] = None):
        """
        Initialize Azure CLI wrapper.
        
        Args:
            subscription_id: Optional Azure subscription ID to use
        """
        self.subscription_id = subscription_id
        self._verify_cli_installed()
    
    def _verify_cli_installed(self) -> None:
        """Verify Azure CLI is installed and accessible"""
        try:
            result = subprocess.run(
                ["az", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Azure CLI is not functioning correctly")
            version_line = result.stdout.split('\n')[0]
            logger.debug(f"Azure CLI version: {version_line}")
        except FileNotFoundError:
            raise RuntimeError(
                "Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Azure CLI command timed out during verification")
    
    def execute(
        self,
        command_args: List[str],
        timeout: int = 300,
        parse_json: bool = True
    ) -> Any:
        """
        Execute an Azure CLI command.
        
        Args:
            command_args: List of command arguments (without 'az' prefix)
            timeout: Command timeout in seconds
            parse_json: Whether to parse output as JSON
            
        Returns:
            Parsed JSON output if parse_json=True, otherwise raw stdout string
            
        Raises:
            AzureCLIError: If command fails
            subprocess.TimeoutExpired: If command exceeds timeout
        """
        # Build full command
        cmd = ["az"] + command_args
        
        # Add subscription if specified
        if self.subscription_id and "--subscription" not in command_args:
            cmd.extend(["--subscription", self.subscription_id])
        
        # Add JSON output format if parsing requested
        if parse_json and "--output" not in command_args:
            cmd.extend(["--output", "json"])
        
        logger.debug(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # We'll handle errors manually
            )
            
            # Check for errors
            if result.returncode != 0:
                logger.error(f"Command failed: {' '.join(cmd)}")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                raise AzureCLIError(
                    command=' '.join(cmd),
                    exit_code=result.returncode,
                    stderr=result.stderr
                )
            
            # Parse output
            if parse_json and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON output: {e}")
                    return result.stdout
            
            return result.stdout
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise
    
    def deploy_template(
        self,
        resource_group: str,
        template_file: Path,
        parameters_file: Optional[Path] = None,
        deployment_name: Optional[str] = None,
        what_if: bool = False
    ) -> Dict[str, Any]:
        """
        Deploy a Bicep/ARM template.
        
        Args:
            resource_group: Resource group name
            template_file: Path to template file
            parameters_file: Optional parameters file
            deployment_name: Optional deployment name
            what_if: Perform what-if validation only
            
        Returns:
            Deployment result as dictionary
        """
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        # Build command
        args = [
            "deployment", "group", "create",
            "--resource-group", resource_group,
            "--template-file", str(template_file),
            "--mode", "Incremental"
        ]
        
        if deployment_name:
            args.extend(["--name", deployment_name])
        
        if parameters_file and parameters_file.exists():
            args.extend(["--parameters", str(parameters_file)])
        
        if what_if:
            args.append("--what-if")
        
        return self.execute(args, timeout=600)  # 10 minute timeout for deployments
    
    def validate_template(
        self,
        resource_group: str,
        template_file: Path,
        parameters_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Validate a Bicep/ARM template.
        
        Args:
            resource_group: Resource group name
            template_file: Path to template file
            parameters_file: Optional parameters file
            
        Returns:
            Validation result
        """
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        args = [
            "deployment", "group", "validate",
            "--resource-group", resource_group,
            "--template-file", str(template_file)
        ]
        
        if parameters_file and parameters_file.exists():
            args.extend(["--parameters", str(parameters_file)])
        
        return self.execute(args, timeout=120)
    
    def get_resource(
        self,
        resource_id: str
    ) -> Dict[str, Any]:
        """
        Get details of an Azure resource.
        
        Args:
            resource_id: Full Azure resource ID
            
        Returns:
            Resource details
        """
        args = ["resource", "show", "--ids", resource_id]
        return self.execute(args)
    
    def delete_resource(
        self,
        resource_id: str
    ) -> None:
        """
        Delete an Azure resource.
        
        Args:
            resource_id: Full Azure resource ID
        """
        args = ["resource", "delete", "--ids", resource_id]
        self.execute(args, parse_json=False)
        logger.info(f"Deleted resource: {resource_id}")
