# Research: Bicep Validate Command

**Feature**: 003-bicep-validate-command  
**Date**: October 28, 2025  
**Purpose**: Document technology decisions, best practices, and implementation approaches for automated Bicep template validation

## 1. Project Discovery Patterns

### Decision

Use recursive file system scanning with glob patterns and in-memory caching.

### Rationale

- Cross-platform compatibility (Windows, Linux, macOS)
- Fast discovery without external dependencies
- Efficient for repeated operations in CI/CD pipelines
- Python's `pathlib` provides excellent cross-platform path handling

### Implementation Approach

```python
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime, timedelta

BICEP_PATTERNS = [
    "**/bicep-templates/**/*.bicep",
    "**/main.bicep",
    "**/modules/**/*.bicep"
]

class ProjectDiscovery:
    def __init__(self, workspace_root: Path, cache_ttl_minutes: int = 5):
        self.workspace_root = workspace_root
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.cache_file = workspace_root / ".bicep-cache.json"
        
    def discover_projects(self) -> List[Dict]:
        # Check cache first
        if self._is_cache_valid():
            return self._load_from_cache()
        
        # Scan for projects
        projects = []
        for pattern in BICEP_PATTERNS:
            for bicep_file in self.workspace_root.glob(pattern):
                project_info = self._extract_project_info(bicep_file)
                if project_info not in projects:
                    projects.append(project_info)
        
        # Cache results
        self._save_to_cache(projects)
        return projects
```

### Alternatives Considered

- **Database-backed indexing**: Overhead not justified for typical workspace sizes (<1000 files)
- **Git-based discovery**: Not all projects use git; adds unnecessary dependency

### Cross-platform Considerations

- Use `pathlib.Path` for all path operations (automatically handles separators)
- Normalize path separators automatically
- Handle case-sensitive vs case-insensitive file systems
- Use double underscore `__` for environment variable hierarchies (works on all platforms)

---

## 2. Application Settings Analysis

### Decision

Multi-strategy static analysis with framework-specific parsers.

### Rationale

Different frameworks store configuration differently; one approach won't fit all. Need targeted parsing for:

- ASP.NET Core (appsettings.json hierarchy)
- Node.js (process.env, .env files)
- Python (os.environ, config.py)

### Framework-Specific Strategies

#### ASP.NET Core

```python
import json
from pathlib import Path

class DotNetConfigAnalyzer:
    CONFIG_FILES = [
        'appsettings.json',
        'appsettings.Development.json',
        'appsettings.Production.json'
    ]
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        settings = {}
        
        for config_file in self.CONFIG_FILES:
            file_path = project_path / config_file
            if file_path.exists():
                with open(file_path) as f:
                    config = json.load(f)
                    settings.update(self._flatten_config(config))
        
        return settings
    
    def _flatten_config(self, config: Dict, prefix: str = "") -> Dict:
        """Flatten nested config to Section:Subsection:Key format"""
        result = {}
        for key, value in config.items():
            full_key = f"{prefix}:{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_config(value, full_key))
            else:
                result[full_key] = value
        return result
```

#### Node.js

```python
import re
from pathlib import Path

class NodeConfigAnalyzer:
    def analyze(self, project_path: Path) -> Dict[str, str]:
        settings = {}
        
        # Parse .env files
        env_file = project_path / '.env'
        if env_file.exists():
            settings.update(self._parse_env_file(env_file))
        
        # Scan JS/TS files for process.env usage
        settings.update(self._scan_env_usage(project_path))
        
        return settings
    
    def _parse_env_file(self, file_path: Path) -> Dict[str, str]:
        settings = {}
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    settings[key.strip()] = value.strip()
        return settings
    
    def _scan_env_usage(self, project_path: Path) -> Dict[str, None]:
        """Find process.env.VAR_NAME patterns in code"""
        pattern = r'process\.env\.([A-Z_]+)'
        settings = {}
        
        for file_path in project_path.rglob('*.js'):
            with open(file_path) as f:
                content = f.read()
                for match in re.finditer(pattern, content):
                    settings[match.group(1)] = None
        
        return settings
```

#### Python (Flask/FastAPI)

```python
import ast
from pathlib import Path

class PythonConfigAnalyzer:
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        settings = {}
        
        # Parse .env files
        env_file = project_path / '.env'
        if env_file.exists():
            settings.update(self._parse_env_file(env_file))
        
        # Parse config.py or settings.py
        for config_file in ['config.py', 'settings.py']:
            file_path = project_path / config_file
            if file_path.exists():
                settings.update(self._parse_python_config(file_path))
        
        return settings
    
    def _parse_python_config(self, file_path: Path) -> Dict[str, Any]:
        """Use AST to parse Python config files"""
        with open(file_path) as f:
            tree = ast.parse(f.read())
        
        settings = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        settings[target.id] = self._eval_safe(node.value)
        
        return settings
```

### Bicep Parameter Extraction

```python
import re
from pathlib import Path

class BicepConfigAnalyzer:
    def analyze(self, bicep_file: Path) -> Dict[str, Dict]:
        """Extract parameter declarations from Bicep files"""
        params = {}
        
        with open(bicep_file) as f:
            content = f.read()
        
        # Match: param paramName type = 'defaultValue'
        # Match: @secure() param secretName string
        param_pattern = r'(@secure\(\))?\s*param\s+(\w+)\s+(\w+)(?:\s*=\s*(.+))?'
        
        for match in re.finditer(param_pattern, content):
            is_secure, name, param_type, default = match.groups()
            params[name] = {
                'type': param_type,
                'secure': bool(is_secure),
                'default': default.strip() if default else None,
                'required': default is None
            }
        
        return params
```

### Dependency Graph Construction

```python
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class AppSetting:
    name: str
    value: str = None
    source: str = "hardcoded"  # hardcoded, keyvault, deployment_output
    depends_on_resource: str = None  # Resource type (e.g., "Microsoft.Sql/servers")

class DependencyGraphBuilder:
    RESOURCE_PATTERNS = {
        'ConnectionStrings:': 'Microsoft.Sql/servers',
        'ServiceBus': 'Microsoft.ServiceBus/namespaces',
        'Storage': 'Microsoft.Storage/storageAccounts',
        'Redis': 'Microsoft.Cache/Redis',
        'CosmosDb': 'Microsoft.DocumentDB/databaseAccounts'
    }
    
    def build_graph(self, settings: Dict[str, str]) -> Dict[str, AppSetting]:
        graph = {}
        
        for key, value in settings.items():
            app_setting = AppSetting(name=key, value=value)
            
            # Detect resource dependencies
            for pattern, resource_type in self.RESOURCE_PATTERNS.items():
                if pattern in key:
                    app_setting.depends_on_resource = resource_type
                    app_setting.source = "deployment_output"
                    break
            
            # Detect Key Vault references
            if value and '@Microsoft.KeyVault' in value:
                app_setting.source = "keyvault"
            
            graph[key] = app_setting
        
        return graph
```

### Alternatives Considered

- **Dynamic runtime analysis**: Too invasive, requires running application
- **LLM-based code understanding**: Non-deterministic, latency issues, cost concerns

---

## 3. Azure Resource Deployment Orchestration

### Decision

Use Azure CLI with topological sorting for dependency ordering.

### Rationale

- Azure CLI is reliable, well-documented, and handles authentication automatically
- Topological sort ensures correct deployment order
- Can leverage Bicep's built-in `dependsOn` declarations
- Hybrid parallel/sequential strategy optimizes deployment time

### Dependency Ordering Algorithm

```python
from collections import deque, defaultdict
from typing import List, Dict, Set

class DependencyResolver:
    def __init__(self, resources: Dict[str, List[str]]):
        """
        resources: Dict mapping resource_id -> list of dependencies (dependsOn)
        """
        self.resources = resources
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Dict[str, Set[str]]:
        graph = defaultdict(set)
        for resource_id, dependencies in self.resources.items():
            for dep in dependencies:
                graph[dep].add(resource_id)
        return graph
    
    def topological_sort(self) -> List[List[str]]:
        """
        Returns list of deployment levels (resources at same level can deploy in parallel)
        """
        in_degree = {node: 0 for node in self.resources}
        for node in self.resources:
            for dep in self.resources[node]:
                in_degree[node] += 1
        
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        levels = []
        
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node)
                
                for neighbor in self.graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            levels.append(level)
        
        return levels
```

### Deployment Strategy

```python
import asyncio
from typing import List
from dataclasses import dataclass

@dataclass
class DeploymentResult:
    resource_id: str
    success: bool
    error_message: str = None
    outputs: Dict = None

class ResourceDeployer:
    MAX_PARALLEL = 4  # Respect Azure throttling limits
    
    async def deploy_resources(
        self, 
        deployment_levels: List[List[str]]
    ) -> List[DeploymentResult]:
        """Deploy resources level by level, parallel within each level"""
        all_results = []
        
        for level in deployment_levels:
            # Deploy resources in this level in parallel (up to MAX_PARALLEL)
            level_results = await self._deploy_level(level)
            all_results.extend(level_results)
            
            # Check for failures
            failures = [r for r in level_results if not r.success]
            if failures:
                return all_results  # Stop on first failure
        
        return all_results
    
    async def _deploy_level(self, resources: List[str]) -> List[DeploymentResult]:
        semaphore = asyncio.Semaphore(self.MAX_PARALLEL)
        
        async def deploy_with_limit(resource_id: str) -> DeploymentResult:
            async with semaphore:
                return await self._deploy_single_resource(resource_id)
        
        tasks = [deploy_with_limit(r) for r in resources]
        return await asyncio.gather(*tasks)
    
    async def _deploy_single_resource(self, resource_id: str) -> DeploymentResult:
        # Implementation using Azure CLI
        pass
```

### Rollback Strategy

```python
class RollbackManager:
    def __init__(self):
        self.deployed_resources = []
    
    async def rollback(self, strategy: str = "prompt"):
        """
        strategy options:
        - "complete": Delete all deployed resources
        - "keep": Keep deployed resources
        - "prompt": Ask user
        """
        if strategy == "prompt":
            strategy = self._prompt_user()
        
        if strategy == "complete":
            # Delete in reverse order
            for resource_id in reversed(self.deployed_resources):
                await self._delete_resource(resource_id)
```

### Implementation with Azure CLI

```python
import subprocess
import json

class AzureCLIWrapper:
    @staticmethod
    async def deploy_bicep(
        resource_group: str,
        template_file: str,
        parameters: Dict
    ) -> Dict:
        """Deploy Bicep template using Azure CLI"""
        cmd = [
            "az", "deployment", "group", "create",
            "--resource-group", resource_group,
            "--template-file", template_file,
            "--parameters", json.dumps(parameters),
            "--output", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise DeploymentError(result.stderr)
        
        return json.loads(result.stdout)
    
    @staticmethod
    async def validate_deployment(
        resource_group: str,
        template_file: str,
        parameters: Dict
    ) -> bool:
        """Validate Bicep template before deployment"""
        cmd = [
            "az", "deployment", "group", "validate",
            "--resource-group", resource_group,
            "--template-file", template_file,
            "--parameters", json.dumps(parameters),
            "--output", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    @staticmethod
    async def what_if_deployment(
        resource_group: str,
        template_file: str,
        parameters: Dict
    ) -> Dict:
        """Preview deployment changes"""
        cmd = [
            "az", "deployment", "group", "what-if",
            "--resource-group", resource_group,
            "--template-file", template_file,
            "--parameters", json.dumps(parameters),
            "--output", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
```

### Alternatives Considered

- **Azure SDK for Python**: More control but more code; CLI sufficient for this use case
- **ARM template deployments**: Bicep is Microsoft's recommended approach

---

## 4. Azure Key Vault Integration

### Decision

Use Managed Identity with Azure RBAC (not legacy access policies).

### Rationale

- Microsoft recommends RBAC over access policies (modern approach)
- Managed Identity eliminates credential management
- Supports Privileged Identity Management (PIM) for just-in-time access
- Better integration with Azure AD and security features

### Secret Naming Conventions

```python
class KeyVaultNamingConvention:
    @staticmethod
    def format_secret_name(
        app_name: str,
        environment: str,
        category: str,
        setting_name: str
    ) -> str:
        """
        Pattern: {app-name}--{environment}--{category}--{setting-name}
        Replace : with -- (colons not allowed in Key Vault)
        Max length: 127 characters
        """
        # Replace invalid characters
        parts = [app_name, environment, category, setting_name]
        formatted_parts = [p.replace(':', '--').replace('_', '-') for p in parts]
        
        secret_name = '--'.join(formatted_parts)
        
        # Truncate if too long
        if len(secret_name) > 127:
            secret_name = secret_name[:127]
        
        return secret_name.lower()

# Examples:
# "myapp--prod--database--connection-string"
# "myapp--dev--api--key"
```

### Access Configuration

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.authorization import AuthorizationManagementClient

class KeyVaultManager:
    # RBAC Role: "Key Vault Secrets User" for apps (read-only)
    SECRETS_USER_ROLE_ID = "4633458b-17de-408a-b874-0445c86b69e6"
    
    # RBAC Role: "Key Vault Secrets Officer" for CI/CD (read-write)
    SECRETS_OFFICER_ROLE_ID = "b86a8fe4-44ce-4948-aee5-eccb2c155cd7"
    
    def __init__(self, vault_url: str):
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)
    
    async def store_secret(self, name: str, value: str) -> None:
        """Store secret in Key Vault"""
        await self.client.set_secret(name, value)
    
    async def get_secret(self, name: str) -> str:
        """Retrieve secret from Key Vault"""
        secret = await self.client.get_secret(name)
        return secret.value
    
    async def grant_access(
        self,
        principal_id: str,
        role: str = "user"
    ) -> None:
        """Grant RBAC access to Key Vault"""
        role_id = (
            self.SECRETS_USER_ROLE_ID 
            if role == "user" 
            else self.SECRETS_OFFICER_ROLE_ID
        )
        # Implementation using Azure Management SDK
```

### Key Vault Reference Patterns

```python
class KeyVaultReferenceBuilder:
    @staticmethod
    def build_reference(vault_name: str, secret_name: str) -> str:
        """
        Build Key Vault reference for App Service/Function App settings
        Format: @Microsoft.KeyVault(VaultName=myvault;SecretName=secret-name)
        """
        return f"@Microsoft.KeyVault(VaultName={vault_name};SecretName={secret_name})"
    
    @staticmethod
    def build_secret_uri_reference(vault_url: str, secret_name: str) -> str:
        """
        Alternative format using Secret URI
        Format: @Microsoft.KeyVault(SecretUri=https://myvault.vault.azure.net/secrets/secret-name/)
        """
        return f"@Microsoft.KeyVault(SecretUri={vault_url}/secrets/{secret_name}/)"
```

### Implementation Notes

- Store secret metadata (non-sensitive) in Bicep parameters
- Use Key Vault references in app settings, not direct secrets
- Implement secret rotation detection and handling
- Cache secrets with TTL (5-15 minutes) to reduce Key Vault API calls
- Use exponential backoff for Key Vault throttling (429 errors)

### Alternatives Considered

- **Service Principal**: Requires managing credentials (not recommended by Microsoft)
- **Azure App Configuration**: Better for feature flags, not secrets

---

## 5. API Endpoint Discovery

### Decision

Framework-specific reflection with OpenAPI/Swagger spec parsing.

### Rationale

Most accurate approach that leverages existing API documentation. Falls back to code analysis when specs unavailable.

### OpenAPI/Swagger Parsing

```python
import yaml
import json
from pathlib import Path
from typing import List, Dict

class OpenAPIParser:
    def parse_spec(self, spec_file: Path) -> List[Dict]:
        """Parse OpenAPI 3.0 or Swagger 2.0 spec"""
        with open(spec_file) as f:
            if spec_file.suffix == '.yaml' or spec_file.suffix == '.yml':
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        
        endpoints = []
        base_url = self._extract_base_url(spec)
        
        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoint = {
                        'path': path,
                        'method': method.upper(),
                        'operation_id': details.get('operationId'),
                        'summary': details.get('summary'),
                        'parameters': self._parse_parameters(details.get('parameters', [])),
                        'auth_required': 'security' in details or 'security' in spec,
                        'expected_responses': list(details.get('responses', {}).keys())
                    }
                    endpoints.append(endpoint)
        
        return endpoints
```

### ASP.NET Core Code Analysis

```python
import re
from pathlib import Path
from typing import List, Dict

class AspNetCoreEndpointDiscoverer:
    def discover(self, project_path: Path) -> List[Dict]:
        """Discover endpoints from ASP.NET Core controllers"""
        endpoints = []
        
        # Find all controller files
        for controller_file in project_path.rglob('*Controller.cs'):
            endpoints.extend(self._parse_controller(controller_file))
        
        # Find minimal API endpoints in Program.cs
        program_file = project_path / 'Program.cs'
        if program_file.exists():
            endpoints.extend(self._parse_minimal_api(program_file))
        
        return endpoints
    
    def _parse_controller(self, file_path: Path) -> List[Dict]:
        """Parse controller for route attributes"""
        with open(file_path) as f:
            content = f.read()
        
        endpoints = []
        
        # Extract controller-level route
        controller_route = ""
        controller_match = re.search(r'\[Route\("([^"]+)"\)\]', content)
        if controller_match:
            controller_route = controller_match.group(1)
        
        # Extract action methods
        action_pattern = r'\[(Http(?:Get|Post|Put|Delete|Patch))(?:\("([^"]+)")?\)\]\s+public\s+\w+\s+(\w+)'
        for match in re.finditer(action_pattern, content):
            method, route, action_name = match.groups()
            
            full_path = controller_route
            if route:
                full_path = f"{controller_route}/{route}".replace('//', '/')
            
            endpoints.append({
                'path': f"/{full_path}",
                'method': method.upper().replace('HTTP', ''),
                'action': action_name
            })
        
        return endpoints
```

### Node.js (Express) Code Analysis

```python
import re
from pathlib import Path

class ExpressEndpointDiscoverer:
    def discover(self, project_path: Path) -> List[Dict]:
        """Discover endpoints from Express.js routes"""
        endpoints = []
        
        # Find route files (common patterns: routes/*.js, *Route.js, *Routes.js)
        for js_file in project_path.rglob('*.js'):
            if 'route' in js_file.name.lower() or js_file.parent.name == 'routes':
                endpoints.extend(self._parse_express_routes(js_file))
        
        return endpoints
    
    def _parse_express_routes(self, file_path: Path) -> List[Dict]:
        """Parse Express route definitions"""
        with open(file_path) as f:
            content = f.read()
        
        endpoints = []
        
        # Match: app.get('/path', handler) or router.post('/path', handler)
        pattern = r'(?:app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'
        
        for match in re.finditer(pattern, content):
            method, path = match.groups()
            endpoints.append({
                'path': path,
                'method': method.upper()
            })
        
        return endpoints
```

### Python (FastAPI) Code Analysis

```python
import ast
from pathlib import Path
from typing import List, Dict

class FastAPIEndpointDiscoverer:
    def discover(self, project_path: Path) -> List[Dict]:
        """Discover endpoints from FastAPI decorators"""
        endpoints = []
        
        for py_file in project_path.rglob('*.py'):
            endpoints.extend(self._parse_fastapi_routes(py_file))
        
        return endpoints
    
    def _parse_fastapi_routes(self, file_path: Path) -> List[Dict]:
        """Parse FastAPI route decorators using AST"""
        with open(file_path) as f:
            tree = ast.parse(f.read())
        
        endpoints = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        # Match: @app.get("/path") or @router.post("/path")
                        if (isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']):
                            
                            if decorator.args:
                                path = ast.literal_eval(decorator.args[0])
                                endpoints.append({
                                    'path': path,
                                    'method': decorator.func.attr.upper(),
                                    'function': node.name
                                })
        
        return endpoints
```

### Implementation Notes

- Prefer OpenAPI spec if available (most reliable)
- Fall back to code analysis for undocumented APIs
- Generate test cases with valid/invalid parameters
- Detect authentication requirements (JWT, API key headers)
- Handle parameterized routes ({id}, :id, <id>)

### Alternatives Considered

- **Runtime introspection**: Requires running application
- **Manual configuration**: Error-prone, maintenance burden

---

## 6. Endpoint Testing Strategies

### Decision

Use `httpx` for async Python HTTP testing with structured retry policies.

### Rationale

- Modern async support (better than `requests`)
- Clean API with excellent timeout handling
- Supports HTTP/2
- Good integration with pytest-asyncio

### HTTP Client Configuration

```python
import httpx
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"

@dataclass
class EndpointTestResult:
    endpoint: str
    method: str
    status: TestStatus
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class APITester:
    MAX_RETRIES = 3
    INITIAL_DELAY = 2  # seconds
    BACKOFF_FACTOR = 2
    MAX_DELAY = 60
    RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(
                connect=5.0,    # Connection timeout
                read=30.0,      # Read timeout
                write=10.0,     # Write timeout
                pool=5.0        # Pool connection timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            ),
            follow_redirects=True,
            verify=True  # SSL verification
        )
    
    async def test_endpoint(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        retry_count: int = 0
    ) -> EndpointTestResult:
        """Test single endpoint with retry logic"""
        try:
            response = await self.client.request(
                method=method,
                url=path,
                headers=headers
            )
            
            # Check if should retry
            if response.status_code in self.RETRY_STATUS_CODES:
                if retry_count < self.MAX_RETRIES:
                    delay = self._calculate_delay(retry_count)
                    await asyncio.sleep(delay)
                    return await self.test_endpoint(path, method, headers, retry_count + 1)
                
                return EndpointTestResult(
                    endpoint=path,
                    method=method,
                    status=TestStatus.RETRY_EXHAUSTED,
                    status_code=response.status_code,
                    response_time=response.elapsed.total_seconds(),
                    retry_count=retry_count
                )
            
            # Success criteria: 2xx status codes
            status = TestStatus.SUCCESS if 200 <= response.status_code < 300 else TestStatus.FAILURE
            
            return EndpointTestResult(
                endpoint=path,
                method=method,
                status=status,
                status_code=response.status_code,
                response_time=response.elapsed.total_seconds(),
                retry_count=retry_count
            )
            
        except httpx.TimeoutException as e:
            if retry_count < self.MAX_RETRIES:
                delay = self._calculate_delay(retry_count)
                await asyncio.sleep(delay)
                return await self.test_endpoint(path, method, headers, retry_count + 1)
            
            return EndpointTestResult(
                endpoint=path,
                method=method,
                status=TestStatus.TIMEOUT,
                error_message=str(e),
                retry_count=retry_count
            )
        
        except Exception as e:
            return EndpointTestResult(
                endpoint=path,
                method=method,
                status=TestStatus.FAILURE,
                error_message=str(e),
                retry_count=retry_count
            )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        import random
        delay = min(
            self.INITIAL_DELAY * (self.BACKOFF_FACTOR ** attempt),
            self.MAX_DELAY
        )
        # Add jitter (50-150% of calculated delay)
        return delay * (0.5 + random.random())
    
    async def test_multiple_endpoints(
        self,
        endpoints: List[Dict],
        max_concurrent: int = 10
    ) -> List[EndpointTestResult]:
        """Test multiple endpoints with concurrency limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_with_limit(endpoint: Dict) -> EndpointTestResult:
            async with semaphore:
                return await self.test_endpoint(
                    path=endpoint['path'],
                    method=endpoint['method']
                )
        
        tasks = [test_with_limit(ep) for ep in endpoints]
        return await asyncio.gather(*tasks)
```

### Authentication Handling

```python
from azure.identity.aio import DefaultAzureCredential

class AuthenticatedAPITester(APITester):
    def __init__(self, base_url: str, auth_type: str = "bearer"):
        super().__init__(base_url)
        self.auth_type = auth_type
        self.token = None
    
    async def get_token(self, scope: str = "https://management.azure.com/.default") -> str:
        """Get Azure AD token using Managed Identity"""
        credential = DefaultAzureCredential()
        token = await credential.get_token(scope)
        return token.token
    
    async def test_endpoint(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        retry_count: int = 0
    ) -> EndpointTestResult:
        """Test endpoint with authentication"""
        if headers is None:
            headers = {}
        
        # Add authentication header
        if self.auth_type == "bearer":
            if not self.token:
                self.token = await self.get_token()
            headers["Authorization"] = f"Bearer {self.token}"
        
        return await super().test_endpoint(path, method, headers, retry_count)
```

### Circuit Breaker Integration

```python
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(minutes=1),
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return True
    
    def on_success(self):
        """Record successful execution"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
    
    def on_failure(self):
        """Record failed execution"""
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            return
        
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Implementation Notes

- Honor `Retry-After` header from 429 responses
- Log all request/response details for debugging
- Run tests in parallel but limit concurrency (10-20 concurrent requests)
- Implement timeout per endpoint (30s default, configurable)
- Use circuit breaker after 5 consecutive failures

### Alternatives Considered

- **`requests` library**: Synchronous, no HTTP/2 support
- **`aiohttp`**: More complex API, less intuitive than httpx

---

## 7. Iterative Fix-and-Retry Patterns

### Decision

Classified error handling with exponential backoff and circuit breaker.

### Rationale

Based on Azure SDK retry patterns and cloud-native best practices. Distinguishes between retriable and non-retriable errors.

### Error Classification

```python
from enum import Enum
from typing import Set

class ErrorCategory(Enum):
    TRANSIENT = "transient"           # Network timeouts, 5xx errors
    CLIENT_ERROR = "client_error"     # 4xx errors (except 408, 429)
    AUTHENTICATION = "authentication" # 401, 403
    CONFIGURATION = "configuration"   # Missing app settings, invalid config
    DEPLOYMENT = "deployment"         # Resource not found, wrong SKU
    TEMPLATE = "template"             # Bicep template syntax/validation errors

RETRYABLE_CATEGORIES: Set[ErrorCategory] = {
    ErrorCategory.TRANSIENT,
    ErrorCategory.TEMPLATE  # Can retry after calling /speckit.bicep
}
```

### Retry Policy

```python
from dataclasses import dataclass
import random

@dataclass
class RetryPolicy:
    max_attempts: int = 5
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter"""
        delay = min(
            self.initial_delay * (self.backoff_factor ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add jitter: 50-150% of calculated delay
            delay *= (0.5 + random.random())
        
        return delay
```

### Automated Issue Resolution

```python
from typing import Dict, Callable, Optional

class AutoFixStrategy:
    """Strategies for automatically fixing common deployment issues"""
    
    @staticmethod
    async def fix_missing_app_setting(context: Dict) -> bool:
        """Add missing app setting to Key Vault reference"""
        setting_name = context.get('setting_name')
        # Implementation: Add to Key Vault and update app settings
        return True
    
    @staticmethod
    async def fix_connection_timeout(context: Dict) -> bool:
        """Adjust network security rules for connectivity"""
        # Implementation: Check NSG rules, add if missing
        return True
    
    @staticmethod
    async def fix_auth_failed(context: Dict) -> bool:
        """Verify and fix RBAC assignments"""
        # Implementation: Check managed identity, assign missing roles
        return True
    
    @staticmethod
    async def fix_resource_not_found(context: Dict) -> bool:
        """Deploy missing prerequisite resource"""
        # Implementation: Deploy dependency first
        return True
    
    @staticmethod
    async def fix_template_error(context: Dict) -> bool:
        """Call /speckit.bicep to fix template issues"""
        issue_description = context.get('error_message')
        # Implementation: Invoke /speckit.bicep with issue description
        return True

class FixOrchestrator:
    """Orchestrates automated fix attempts"""
    
    strategies: Dict[str, Callable] = {
        'missing_app_setting': AutoFixStrategy.fix_missing_app_setting,
        'connection_timeout': AutoFixStrategy.fix_connection_timeout,
        'auth_failed': AutoFixStrategy.fix_auth_failed,
        'resource_not_found': AutoFixStrategy.fix_resource_not_found,
        'template_error': AutoFixStrategy.fix_template_error,
    }
    
    def __init__(self, max_total_retry_time: int = 300):
        self.max_total_retry_time = max_total_retry_time  # 5 minutes
        self.retry_policy = RetryPolicy()
    
    async def attempt_fix(
        self,
        error_category: str,
        context: Dict,
        attempt: int = 0
    ) -> bool:
        """Attempt to fix issue using appropriate strategy"""
        strategy = self.strategies.get(error_category)
        
        if not strategy:
            return False
        
        try:
            success = await strategy(context)
            if success:
                return True
            
            # Retry if not successful
            if attempt < self.retry_policy.max_attempts:
                delay = self.retry_policy.get_delay(attempt)
                await asyncio.sleep(delay)
                return await self.attempt_fix(error_category, context, attempt + 1)
            
            return False
            
        except Exception as e:
            context['error_message'] = str(e)
            return False
```

### Integration with /speckit.bicep

```python
class BicepFixIntegration:
    """Integration with existing /speckit.bicep command for template fixes"""
    
    async def fix_template_issue(self, issue_description: str, template_path: str) -> bool:
        """
        Call /speckit.bicep command to fix template issues
        Returns True if fix was successful
        """
        # This would integrate with the existing bicep command
        # Implementation depends on how commands communicate
        
        # Example: Could be a direct function call or subprocess
        from specify_cli.bicep.cli_simple import fix_bicep_template
        
        try:
            result = await fix_bicep_template(
                template_path=template_path,
                issue_description=issue_description
            )
            return result.success
        except Exception as e:
            return False
```

### Complete Validation Workflow with Fixes

```python
class ValidationSession:
    """Orchestrates complete validation workflow with fix-and-retry"""
    
    def __init__(self, project_path: Path, test_environment: str):
        self.project_path = project_path
        self.test_environment = test_environment
        self.fix_orchestrator = FixOrchestrator()
        self.circuit_breaker = CircuitBreaker()
        self.retry_attempts = 0
        self.max_retries = 3
    
    async def run_validation(self) -> ValidationResult:
        """Run complete validation workflow"""
        while self.retry_attempts <= self.max_retries:
            try:
                # Check circuit breaker
                if not self.circuit_breaker.can_execute():
                    return ValidationResult(
                        success=False,
                        error="Circuit breaker is open - too many failures"
                    )
                
                # Deploy resources
                deployment_result = await self._deploy_resources()
                
                if not deployment_result.success:
                    # Attempt to fix
                    fix_success = await self._attempt_fix(deployment_result.error)
                    
                    if fix_success:
                        self.retry_attempts += 1
                        continue  # Retry deployment
                    else:
                        self.circuit_breaker.on_failure()
                        return ValidationResult(success=False, error=deployment_result.error)
                
                # Test endpoints
                test_results = await self._test_endpoints()
                
                if not all(r.status == TestStatus.SUCCESS for r in test_results):
                    # Attempt to fix failing endpoints
                    fix_success = await self._fix_endpoint_issues(test_results)
                    
                    if fix_success:
                        self.retry_attempts += 1
                        continue  # Retry testing
                    else:
                        self.circuit_breaker.on_failure()
                        return ValidationResult(success=False, test_results=test_results)
                
                # Success!
                self.circuit_breaker.on_success()
                return ValidationResult(success=True, test_results=test_results)
                
            except Exception as e:
                self.circuit_breaker.on_failure()
                return ValidationResult(success=False, error=str(e))
        
        return ValidationResult(
            success=False,
            error=f"Maximum retry attempts ({self.max_retries}) exceeded"
        )
```

### Implementation Notes

- Log every retry attempt with correlation ID
- Distinguish between retriable and non-retriable errors clearly
- Use exponential backoff with jitter (prevents retry storms)
- Implement circuit breaker for repeated failures (5 failures triggers open)
- Maximum total retry time: 5 minutes (configurable)
- Fall back to manual intervention after max retries with actionable error messages

### Alternatives Considered

- **Linear backoff**: Not recommended by Azure (can overwhelm services during recovery)
- **Infinite retries**: Can hide systemic issues
- **No circuit breaker**: Can cause cascading failures

---

## Summary of Technology Decisions

| Area | Technology Choice | Key Reason |
|------|-------------------|------------|
| Project Discovery | pathlib + glob patterns | Cross-platform, fast, no dependencies |
| App Settings Analysis | Framework-specific parsers | Different frameworks need different approaches |
| Deployment Orchestration | Azure CLI + topological sort | Reliable, well-documented, handles auth |
| Key Vault Integration | Managed Identity + RBAC | Microsoft recommended, no credential management |
| API Discovery | OpenAPI parsing + code analysis | Most accurate, falls back to code scan |
| Endpoint Testing | httpx with async | Modern, HTTP/2 support, clean API |
| Fix-and-Retry | Error classification + circuit breaker | Azure SDK patterns, prevents cascading failures |

---

**Research Complete**: All technical unknowns resolved. Ready for Phase 1 (Design & Contracts).
