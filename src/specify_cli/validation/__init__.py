"""
Validation module for Bicep template validation.

This module provides automated validation of Bicep templates through:
- Project discovery and configuration analysis
- Resource deployment orchestration
- API endpoint testing
- Automated fix-and-retry workflows

Main workflow stages:
1. DISCOVERING: Find projects with Bicep templates
2. ANALYZING: Identify app settings and dependencies
3. DEPLOYING: Deploy resources and store secrets
4. TESTING: Test API endpoints
5. FIXING: Attempt automated fixes
6. COMPLETED: Validation finished

Usage:
    from specify_cli.validation import ValidationSession
    
    session = ValidationSession(project_path="./my-project")
    result = await session.run()
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum


# Custom Exceptions

class ValidationError(Exception):
    """Base exception for validation errors"""
    pass


class ProjectDiscoveryError(ValidationError):
    """Raised when project discovery fails"""
    pass


class ConfigAnalysisError(ValidationError):
    """Raised when configuration analysis fails"""
    pass


class DeploymentError(ValidationError):
    """Raised when resource deployment fails"""
    pass


class KeyVaultError(ValidationError):
    """Raised when Key Vault operations fail"""
    pass


class EndpointTestError(ValidationError):
    """Raised when endpoint testing fails"""
    pass


class FixError(ValidationError):
    """Raised when automated fix attempts fail"""
    pass


# Enums

class ValidationStage(Enum):
    """Validation workflow stages"""
    INITIALIZED = "initialized"
    DISCOVERING = "discovering"
    ANALYZING = "analyzing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"


class ValidationStatus(Enum):
    """Validation session status"""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SourceType(Enum):
    """Application setting source type"""
    HARDCODED = "hardcoded"
    KEYVAULT = "keyvault"
    DEPLOYMENT_OUTPUT = "deployment_output"


class DeploymentState(Enum):
    """Resource deployment state"""
    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class TestStatus(Enum):
    """Endpoint test status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"


# Data Models

@dataclass
class ProjectInfo:
    """Represents a discovered project with Bicep templates"""
    project_id: str
    name: str
    path: Path
    source_code_path: Path
    bicep_templates_path: Path
    framework: str  # "dotnet", "nodejs", "python", "unknown"
    last_modified: float  # Unix timestamp


@dataclass
class AppSetting:
    """Represents an application configuration setting"""
    setting_id: str
    name: str
    value: Optional[str]
    source_type: SourceType
    is_secure: bool
    environment: str
    keyvault_secret_name: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of configuration analysis"""
    app_settings: List[AppSetting]
    resource_dependencies: List[str]
    dependency_graph: Dict[str, List[str]]  # resource_id -> [dependent_resource_ids]


@dataclass
class ResourceDeployment:
    """Represents an Azure resource deployment"""
    resource_id: str
    resource_type: str
    resource_name: str
    deployment_order: int
    deployment_status: DeploymentState
    bicep_template_path: Path
    output_values: Dict[str, str]


@dataclass
class DeploymentResult:
    """Result of resource deployment"""
    deployment_id: str
    timestamp: float
    success: bool
    deployed_resources: List[ResourceDeployment]
    resource_group: str
    subscription_id: str
    deployment_outputs: Dict[str, str]
    error_messages: List[str]
    duration_seconds: float


@dataclass
class ApiEndpoint:
    """Represents an API endpoint to test"""
    endpoint_id: str
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    base_url: str
    requires_auth: bool
    auth_type: str  # "bearer", "apikey", "none"
    expected_status_codes: List[int]
    timeout_seconds: int
    test_parameters: Dict[str, str]


@dataclass
class EndpointTestResult:
    """Result of endpoint testing"""
    test_id: str
    endpoint_id: str
    timestamp: float
    status: TestStatus
    status_code: Optional[int]
    response_time_ms: float
    error_message: Optional[str]
    retry_count: int
    response_body_preview: Optional[str]  # First 500 chars


@dataclass
class ValidationSummary:
    """Summary of validation session"""
    session_id: str
    project_name: str
    status: ValidationStatus
    start_time: float
    end_time: Optional[float]
    total_endpoints: int
    successful_tests: int
    failed_tests: int
    deployment_count: int
    retry_attempts: int
    error_messages: List[str]


__all__ = [
    # Exceptions
    "ValidationError",
    "ProjectDiscoveryError",
    "ConfigAnalysisError",
    "DeploymentError",
    "KeyVaultError",
    "EndpointTestError",
    "FixError",
    # Enums
    "ValidationStage",
    "ValidationStatus",
    "SourceType",
    "DeploymentState",
    "TestStatus",
    # Data Models
    "ProjectInfo",
    "AppSetting",
    "AnalysisResult",
    "ResourceDeployment",
    "DeploymentResult",
    "ApiEndpoint",
    "EndpointTestResult",
    "ValidationSummary",
]
