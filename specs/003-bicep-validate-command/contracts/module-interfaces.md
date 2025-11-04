# Module Contracts: Bicep Validate Command

**Feature**: 003-bicep-validate-command  
**Date**: October 28, 2025  
**Purpose**: Define Python module interfaces for validation components

## Overview

These contracts define the interfaces between modules in the validation workflow. All modules are Python-based and communicate through function calls (not HTTP APIs).

---

## 1. Project Discovery Module

**Module**: `src/specify_cli/validation/project_discovery.py`

### Interface

```python
from pathlib import Path
from typing import List
from dataclasses import dataclass

@dataclass
class ProjectInfo:
    """Represents a discovered project with Bicep templates"""
    project_id: str
    name: str
    path: Path
    bicep_templates_path: Path
    framework: str  # "dotnet", "nodejs", "python", "unknown"
    last_modified: float  # Unix timestamp

class ProjectDiscovery:
    """Discovers projects with generated Bicep templates"""
    
    def __init__(self, workspace_root: Path, use_cache: bool = True):
        """
        Initialize project discovery.
        
        Args:
            workspace_root: Root directory to search for projects
            use_cache: Whether to use cached results (default: True)
        """
        pass
    
    def discover_projects(self) -> List[ProjectInfo]:
        """
        Discover all projects with Bicep templates.
        
        Returns:
            List of ProjectInfo objects
            
        Raises:
            FileNotFoundError: If workspace_root doesn't exist
            PermissionError: If workspace_root is not readable
        """
        pass
    
    def get_project_by_name(self, name: str) -> ProjectInfo | None:
        """
        Get specific project by name.
        
        Args:
            name: Project name to search for
            
        Returns:
            ProjectInfo if found, None otherwise
        """
        pass
    
    def clear_cache(self) -> None:
        """Clear discovery cache"""
        pass
```

### Usage Example

```python
discovery = ProjectDiscovery(Path.cwd())
projects = discovery.discover_projects()

for project in projects:
    print(f"Found: {project.name} at {project.path}")
```

---

## 2. Configuration Analyzer Module

**Module**: `src/specify_cli/validation/config_analyzer.py`

### Interface

```python
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class AppSetting:
    """Represents an application configuration setting"""
    name: str
    value: str | None
    source_type: str  # "hardcoded", "keyvault", "deployment_output"
    is_secure: bool
    depends_on_resource: str | None  # Azure resource type

@dataclass
class AnalysisResult:
    """Result of configuration analysis"""
    settings: List[AppSetting]
    framework: str
    confidence: float  # 0.0 to 1.0

class ConfigAnalyzer:
    """Analyzes project configuration requirements"""
    
    def analyze_project(self, project_path: Path, framework: str = "auto") -> AnalysisResult:
        """
        Analyze project to identify required configuration.
        
        Args:
            project_path: Path to project root
            framework: Framework type or "auto" to detect
            
        Returns:
            AnalysisResult with discovered settings
            
        Raises:
            ValueError: If framework not supported
            FileNotFoundError: If project_path doesn't exist
        """
        pass
    
    def build_dependency_graph(
        self, 
        settings: List[AppSetting]
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph for settings.
        
        Args:
            settings: List of application settings
            
        Returns:
            Dictionary mapping setting name to list of dependencies
        """
        pass
```

### Usage Example

```python
analyzer = ConfigAnalyzer()
result = analyzer.analyze_project(project.path, project.framework)

print(f"Found {len(result.settings)} settings")
for setting in result.settings:
    if setting.is_secure:
        print(f"  {setting.name} → Key Vault")
```

---

## 3. Resource Deployer Module

**Module**: `src/specify_cli/validation/resource_deployer.py`

### Interface

```python
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ResourceDeployment:
    """Represents a resource to deploy"""
    resource_id: str
    resource_type: str
    template_path: Path
    parameters: Dict[str, any]
    depends_on: List[str]  # List of resource_ids

@dataclass
class DeploymentResult:
    """Result of resource deployment"""
    resource_id: str
    success: bool
    outputs: Dict[str, str] | None
    error_message: str | None
    duration_seconds: float

class ResourceDeployer:
    """Orchestrates Azure resource deployments"""
    
    def __init__(
        self, 
        resource_group: str,
        subscription_id: str,
        max_parallel: int = 4
    ):
        """
        Initialize resource deployer.
        
        Args:
            resource_group: Azure resource group name
            subscription_id: Azure subscription ID
            max_parallel: Maximum parallel deployments (default: 4)
        """
        pass
    
    async def deploy_resources(
        self, 
        resources: List[ResourceDeployment]
    ) -> List[DeploymentResult]:
        """
        Deploy resources in dependency order.
        
        Args:
            resources: List of resources to deploy
            
        Returns:
            List of deployment results
            
        Raises:
            ValueError: If circular dependencies detected
            DeploymentError: If deployment fails
        """
        pass
    
    async def validate_template(
        self, 
        template_path: Path,
        parameters: Dict
    ) -> bool:
        """
        Validate Bicep template before deployment.
        
        Args:
            template_path: Path to Bicep template
            parameters: Deployment parameters
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    async def rollback_deployment(
        self,
        deployed_resources: List[str]
    ) -> None:
        """
        Rollback deployed resources.
        
        Args:
            deployed_resources: List of resource IDs to delete
        """
        pass
```

### Usage Example

```python
deployer = ResourceDeployer(
    resource_group="test-rg",
    subscription_id="00000000-0000-0000-0000-000000000000"
)

results = await deployer.deploy_resources(resources)

for result in results:
    if result.success:
        print(f"✓ {result.resource_id}")
    else:
        print(f"✗ {result.resource_id}: {result.error_message}")
```

---

## 4. Key Vault Manager Module

**Module**: `src/specify_cli/validation/keyvault_manager.py`

### Interface

```python
from typing import Dict, List

class KeyVaultManager:
    """Manages Azure Key Vault secrets"""
    
    def __init__(self, vault_url: str):
        """
        Initialize Key Vault manager.
        
        Args:
            vault_url: Key Vault URL (e.g., https://myvault.vault.azure.net)
        """
        pass
    
    async def store_secret(self, name: str, value: str) -> None:
        """
        Store secret in Key Vault.
        
        Args:
            name: Secret name (will be formatted per naming convention)
            value: Secret value
            
        Raises:
            KeyVaultError: If storage fails
        """
        pass
    
    async def get_secret(self, name: str) -> str:
        """
        Retrieve secret from Key Vault.
        
        Args:
            name: Secret name
            
        Returns:
            Secret value
            
        Raises:
            KeyVaultError: If secret not found or access denied
        """
        pass
    
    async def store_multiple_secrets(
        self, 
        secrets: Dict[str, str]
    ) -> Dict[str, bool]:
        """
        Store multiple secrets in batch.
        
        Args:
            secrets: Dictionary mapping secret names to values
            
        Returns:
            Dictionary mapping secret names to success status
        """
        pass
    
    def build_app_setting_reference(
        self, 
        secret_name: str
    ) -> str:
        """
        Build Key Vault reference for App Service setting.
        
        Args:
            secret_name: Name of secret in Key Vault
            
        Returns:
            Formatted Key Vault reference string
        """
        pass
```

### Usage Example

```python
kv_manager = KeyVaultManager("https://mytest-kv.vault.azure.net")

# Store connection string
await kv_manager.store_secret(
    "myapp--test--database--connection",
    "Server=..."
)

# Build app setting reference
ref = kv_manager.build_app_setting_reference(
    "myapp--test--database--connection"
)
# Returns: "@Microsoft.KeyVault(VaultName=mytest-kv;SecretName=myapp--test--database--connection)"
```

---

## 5. Endpoint Discoverer Module

**Module**: `src/specify_cli/validation/endpoint_discoverer.py`

### Interface

```python
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ApiEndpoint:
    """Represents an API endpoint"""
    path: str  # e.g., "/api/users/{id}"
    method: str  # GET, POST, PUT, DELETE, PATCH
    requires_auth: bool
    auth_type: str | None  # "bearer", "apikey", None
    parameters: Dict[str, str]  # Parameter name -> type

class EndpointDiscoverer:
    """Discovers API endpoints from source code"""
    
    def discover_endpoints(
        self, 
        project_path: Path,
        framework: str
    ) -> List[ApiEndpoint]:
        """
        Discover API endpoints from project source code.
        
        Args:
            project_path: Path to project root
            framework: Framework type (dotnet, nodejs, python)
            
        Returns:
            List of discovered endpoints
            
        Raises:
            ValueError: If framework not supported
            FileNotFoundError: If project_path doesn't exist
        """
        pass
    
    def parse_openapi_spec(self, spec_path: Path) -> List[ApiEndpoint]:
        """
        Parse OpenAPI/Swagger specification.
        
        Args:
            spec_path: Path to openapi.yaml or swagger.json
            
        Returns:
            List of endpoints from spec
            
        Raises:
            ValueError: If spec is invalid
        """
        pass
```

### Usage Example

```python
discoverer = EndpointDiscoverer()
endpoints = discoverer.discover_endpoints(
    project.path,
    project.framework
)

print(f"Found {len(endpoints)} endpoints:")
for ep in endpoints:
    auth = "🔒" if ep.requires_auth else "🔓"
    print(f"  {auth} {ep.method} {ep.path}")
```

---

## 6. Endpoint Tester Module

**Module**: `src/specify_cli/validation/endpoint_tester.py`

### Interface

```python
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"

@dataclass
class EndpointTestResult:
    """Result of endpoint test"""
    endpoint: str
    method: str
    status: TestStatus
    status_code: int | None
    response_time_ms: float
    error_message: str | None
    retry_count: int

class EndpointTester:
    """Tests API endpoints"""
    
    def __init__(
        self, 
        base_url: str,
        auth_config: Dict | None = None,
        timeout: int = 30
    ):
        """
        Initialize endpoint tester.
        
        Args:
            base_url: Base URL of deployed application
            auth_config: Authentication configuration (optional)
            timeout: Request timeout in seconds (default: 30)
        """
        pass
    
    async def test_endpoint(
        self, 
        endpoint: ApiEndpoint
    ) -> EndpointTestResult:
        """
        Test single endpoint.
        
        Args:
            endpoint: Endpoint to test
            
        Returns:
            Test result
        """
        pass
    
    async def test_multiple_endpoints(
        self,
        endpoints: List[ApiEndpoint],
        max_concurrent: int = 10
    ) -> List[EndpointTestResult]:
        """
        Test multiple endpoints with concurrency limit.
        
        Args:
            endpoints: List of endpoints to test
            max_concurrent: Maximum concurrent tests (default: 10)
            
        Returns:
            List of test results
        """
        pass
```

### Usage Example

```python
tester = EndpointTester(base_url="https://myapp-test.azurewebsites.net")

results = await tester.test_multiple_endpoints(endpoints)

success_count = sum(1 for r in results if r.status == TestStatus.SUCCESS)
print(f"✓ {success_count}/{len(results)} endpoints passed")
```

---

## 7. Fix Orchestrator Module

**Module**: `src/specify_cli/validation/fix_orchestrator.py`

### Interface

```python
from typing import Dict
from dataclasses import dataclass

@dataclass
class FixAttempt:
    """Represents an automated fix attempt"""
    error_category: str
    issue_description: str
    fix_strategy: str
    success: bool
    applied_changes: List[str]
    error_message: str | None

class FixOrchestrator:
    """Orchestrates automated issue fixes"""
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize fix orchestrator.
        
        Args:
            max_retries: Maximum retry attempts (default: 3)
        """
        pass
    
    async def attempt_fix(
        self,
        error_category: str,
        context: Dict
    ) -> FixAttempt:
        """
        Attempt to fix issue automatically.
        
        Args:
            error_category: Category of error to fix
            context: Context information for fix
            
        Returns:
            FixAttempt result
        """
        pass
    
    async def fix_template_issue(
        self,
        issue_description: str,
        template_path: Path
    ) -> bool:
        """
        Fix Bicep template issue by calling /speckit.bicep.
        
        Args:
            issue_description: Description of the issue
            template_path: Path to template to fix
            
        Returns:
            True if fix successful, False otherwise
        """
        pass
```

### Usage Example

```python
orchestrator = FixOrchestrator(max_retries=3)

fix_result = await orchestrator.attempt_fix(
    error_category="template_error",
    context={
        "error_message": "Invalid resource type",
        "template_path": template_path
    }
)

if fix_result.success:
    print("✓ Issue fixed automatically")
else:
    print(f"✗ Fix failed: {fix_result.error_message}")
```

---

## 8. Validation Session Module

**Module**: `src/specify_cli/validation/validation_session.py`

### Interface

```python
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
from enum import Enum

class SessionStatus(Enum):
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

class ValidationStage(Enum):
    DISCOVERING = "discovering"
    ANALYZING = "analyzing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"

@dataclass
class ValidationSummary:
    """Summary of validation session"""
    session_id: str
    status: SessionStatus
    duration_seconds: float
    deployed_resources: List[str]
    tested_endpoints: int
    successful_tests: int
    failed_tests: int
    retry_attempts: int
    error_messages: List[str]

class ValidationSession:
    """Orchestrates complete validation workflow"""
    
    def __init__(
        self,
        project: ProjectInfo,
        test_environment: str,
        custom_instructions: str | None = None
    ):
        """
        Initialize validation session.
        
        Args:
            project: Project to validate
            test_environment: Target environment name
            custom_instructions: Optional custom validation instructions
        """
        pass
    
    async def run(self) -> ValidationSummary:
        """
        Run complete validation workflow.
        
        Returns:
            Validation summary
            
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    def get_current_stage(self) -> ValidationStage:
        """Get current validation stage"""
        pass
    
    def get_progress(self) -> Dict:
        """
        Get current progress information.
        
        Returns:
            Dictionary with progress details
        """
        pass
```

### Usage Example

```python
session = ValidationSession(
    project=selected_project,
    test_environment="test-corp"
)

summary = await session.run()

print(f"Validation {'✓ PASSED' if summary.status == SessionStatus.SUCCESS else '✗ FAILED'}")
print(f"  Duration: {summary.duration_seconds:.1f}s")
print(f"  Endpoints: {summary.successful_tests}/{summary.tested_endpoints} passed")
```

---

## Module Dependencies

```text
validation_session.py (orchestrator)
    ├── project_discovery.py
    ├── config_analyzer.py
    ├── resource_deployer.py
    │   └── azure_cli_wrapper.py (utils)
    ├── keyvault_manager.py
    ├── endpoint_discoverer.py
    ├── endpoint_tester.py
    └── fix_orchestrator.py
        └── bicep/cli_simple.py (existing)
```

---

## Error Handling Contract

All modules follow consistent error handling:

### Error Types

```python
class ValidationError(Exception):
    """Base exception for validation errors"""
    pass

class ProjectDiscoveryError(ValidationError):
    """Project discovery failed"""
    pass

class ConfigAnalysisError(ValidationError):
    """Configuration analysis failed"""
    pass

class DeploymentError(ValidationError):
    """Resource deployment failed"""
    pass

class KeyVaultError(ValidationError):
    """Key Vault operation failed"""
    pass

class EndpointTestError(ValidationError):
    """Endpoint testing failed"""
    pass

class FixError(ValidationError):
    """Automated fix failed"""
    pass
```

### Error Response Format

All errors include:

- `error_code`: Machine-readable error code
- `message`: Human-readable error message
- `details`: Additional context (optional)
- `retry_allowed`: Whether operation can be retried

---

## Testing Contract

All modules must provide:

1. **Unit tests**: Test individual functions in isolation
2. **Integration tests**: Test interactions between modules
3. **Mock fixtures**: Provide mocks for external dependencies (Azure CLI, Key Vault, HTTP)
4. **Example usage**: Document typical usage patterns

---

**Contracts Complete**: All module interfaces defined. Ready for quickstart guide generation.
