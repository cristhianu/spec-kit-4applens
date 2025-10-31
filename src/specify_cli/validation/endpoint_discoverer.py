"""
Endpoint Discovery Module for Bicep Validate Command

This module discovers API endpoints from application source code and OpenAPI specifications.
Supports ASP.NET, Express.js, FastAPI, and OpenAPI/Swagger files.

Part of User Story 3: Test Deployment and Endpoint Validation
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Endpoint:
    """Represents a discovered API endpoint"""
    
    method: str  # GET, POST, PUT, DELETE, PATCH, etc.
    path: str  # /api/users, /health, etc.
    requires_auth: bool = False
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    description: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation for logging"""
        auth_marker = " [AUTH]" if self.requires_auth else ""
        return f"{self.method} {self.path}{auth_marker}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "method": self.method,
            "path": self.path,
            "requires_auth": self.requires_auth,
            "source_file": self.source_file,
            "line_number": self.line_number,
            "description": self.description,
        }


class EndpointDiscoverer:
    """Discovers API endpoints from application source code and OpenAPI specs"""
    
    def __init__(self, project_root: Path):
        """
        Initialize endpoint discoverer
        
        Args:
            project_root: Root directory of the project to scan
        """
        self.project_root = Path(project_root)
        self.endpoints: List[Endpoint] = []
        
        logger.info(f"Initialized EndpointDiscoverer for: {self.project_root}")
    
    def discover_endpoints(self) -> List[Endpoint]:
        """
        Discover all API endpoints in the project
        
        Returns:
            List of discovered endpoints
        """
        logger.info("Starting endpoint discovery...")
        
        self.endpoints = []
        
        # Try OpenAPI/Swagger first (most reliable)
        openapi_endpoints = self._discover_openapi_endpoints()
        if openapi_endpoints:
            logger.info(f"Discovered {len(openapi_endpoints)} endpoints from OpenAPI specs")
            self.endpoints.extend(openapi_endpoints)
            return self.endpoints
        
        # Try framework-specific discovery
        aspnet_endpoints = self._discover_aspnet_endpoints()
        if aspnet_endpoints:
            logger.info(f"Discovered {len(aspnet_endpoints)} ASP.NET endpoints")
            self.endpoints.extend(aspnet_endpoints)
        
        express_endpoints = self._discover_express_endpoints()
        if express_endpoints:
            logger.info(f"Discovered {len(express_endpoints)} Express.js endpoints")
            self.endpoints.extend(express_endpoints)
        
        fastapi_endpoints = self._discover_fastapi_endpoints()
        if fastapi_endpoints:
            logger.info(f"Discovered {len(fastapi_endpoints)} FastAPI endpoints")
            self.endpoints.extend(fastapi_endpoints)
        
        # Remove duplicates (same method + path)
        self.endpoints = self._deduplicate_endpoints(self.endpoints)
        
        logger.info(f"Endpoint discovery complete: {len(self.endpoints)} unique endpoints")
        return self.endpoints
    
    def _discover_openapi_endpoints(self) -> List[Endpoint]:
        """Discover endpoints from OpenAPI/Swagger files"""
        endpoints = []
        discovered_files = set()  # Track files we've already parsed
        
        # Search for OpenAPI/Swagger files (use rglob for recursive search)
        openapi_patterns = [
            "openapi.yaml", "openapi.yml", "openapi.json",
            "swagger.yaml", "swagger.yml", "swagger.json",
        ]
        
        for pattern in openapi_patterns:
            for file_path in self.project_root.rglob(pattern):
                # Skip if already discovered
                if file_path in discovered_files:
                    continue
                
                discovered_files.add(file_path)
                try:
                    discovered = self.parse_openapi_spec(file_path)
                    endpoints.extend(discovered)
                    logger.info(f"Parsed {len(discovered)} endpoints from {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to parse OpenAPI spec {file_path}: {e}")
        
        return endpoints
    
    def parse_openapi_spec(self, spec_path: Path) -> List[Endpoint]:
        """
        Parse OpenAPI/Swagger specification file
        
        Args:
            spec_path: Path to OpenAPI/Swagger file (YAML or JSON)
        
        Returns:
            List of discovered endpoints
        """
        endpoints = []
        
        # Load spec file
        with open(spec_path, 'r', encoding='utf-8') as f:
            if spec_path.suffix in ['.yaml', '.yml']:
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        
        # Extract paths (OpenAPI 2.0 and 3.0+ compatible)
        paths = spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                # Skip non-method keys (parameters, $ref, etc.)
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    continue
                
                # Check if authentication is required
                requires_auth = False
                if 'security' in operation or 'security' in spec:
                    requires_auth = True
                
                # Get description
                description = operation.get('summary') or operation.get('description')
                
                endpoint = Endpoint(
                    method=method.upper(),
                    path=path,
                    requires_auth=requires_auth,
                    source_file=str(spec_path.relative_to(self.project_root)),
                    description=description,
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _discover_aspnet_endpoints(self) -> List[Endpoint]:
        """Discover endpoints from ASP.NET Core applications"""
        endpoints = []
        
        # Search for C# files
        for cs_file in self.project_root.rglob("*.cs"):
            try:
                with open(cs_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Parse controllers with route attributes
                controller_endpoints = self._parse_aspnet_controller(content, lines, cs_file)
                endpoints.extend(controller_endpoints)
                
                # Parse minimal APIs (app.MapGet, app.MapPost, etc.)
                minimal_api_endpoints = self._parse_aspnet_minimal_api(content, lines, cs_file)
                endpoints.extend(minimal_api_endpoints)
                
            except Exception as e:
                logger.debug(f"Error parsing {cs_file}: {e}")
        
        return endpoints
    
    def _parse_aspnet_controller(self, content: str, lines: List[str], file_path: Path) -> List[Endpoint]:
        """Parse ASP.NET controllers with route attributes"""
        endpoints = []
        
        # Find controller base route
        controller_route_match = re.search(r'\[Route\(["\']([^"\']+)["\']\)\]', content)
        base_route = controller_route_match.group(1) if controller_route_match else ""
        
        # Find HTTP method attributes
        patterns = [
            (r'\[Http(Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']\)\]', True),  # With route
            (r'\[Http(Get|Post|Put|Delete|Patch)\]', False),  # Without route
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, has_route in patterns:
                match = re.search(pattern, line)
                if match:
                    method = match.group(1).upper()
                    route = match.group(2) if has_route else ""
                    
                    # Combine base route and method route
                    full_path = self._combine_routes(base_route, route)
                    
                    # Check for [Authorize] attribute
                    requires_auth = self._check_aspnet_auth(lines, line_num)
                    
                    endpoint = Endpoint(
                        method=method,
                        path=full_path,
                        requires_auth=requires_auth,
                        source_file=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                    )
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _parse_aspnet_minimal_api(self, content: str, lines: List[str], file_path: Path) -> List[Endpoint]:
        """Parse ASP.NET minimal API definitions"""
        endpoints = []
        
        # Pattern: app.MapGet("/path", ...) or app.MapPost("/path", ...)
        pattern = r'app\.Map(Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']'
        
        for line_num, line in enumerate(lines, 1):
            match = re.search(pattern, line)
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                
                # Check for .RequireAuthorization() on current and next few lines
                requires_auth = False
                check_lines = lines[line_num-1:min(len(lines), line_num+3)]  # Check current + next 3 lines
                for check_line in check_lines:
                    if '.RequireAuthorization()' in check_line or '.RequireAuthorization<' in check_line:
                        requires_auth = True
                        break
                
                endpoint = Endpoint(
                    method=method,
                    path=path,
                    requires_auth=requires_auth,
                    source_file=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _discover_express_endpoints(self) -> List[Endpoint]:
        """Discover endpoints from Express.js applications"""
        endpoints = []
        
        # Search for JavaScript/TypeScript files
        for js_file in list(self.project_root.rglob("*.js")) + list(self.project_root.rglob("*.ts")):
            # Skip node_modules
            if 'node_modules' in str(js_file):
                continue
            
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Parse Express routes
                express_endpoints = self._parse_express_routes(content, lines, js_file)
                endpoints.extend(express_endpoints)
                
            except Exception as e:
                logger.debug(f"Error parsing {js_file}: {e}")
        
        return endpoints
    
    def _parse_express_routes(self, content: str, lines: List[str], file_path: Path) -> List[Endpoint]:
        """Parse Express.js route definitions"""
        endpoints = []
        
        # Pattern 1: app.get('/path', ...) or router.get('/path', ...)
        simple_pattern = r'(app|router)\.(get|post|put|delete|patch|all)\(["\']([^"\']+)["\']'
        
        # Pattern 2: app.route('/path').get(...).post(...)
        route_pattern = r'(app|router)\.route\(["\']([^"\']+)["\']\)'
        
        for line_num, line in enumerate(lines, 1):
            # Check for simple route pattern
            match = re.search(simple_pattern, line)
            if match:
                groups = match.groups()
                method = groups[1].upper() if groups[1] != 'all' else 'GET'
                path = groups[2]
                
                # Check for authentication middleware
                requires_auth = self._check_express_auth(line, lines, line_num)
                
                endpoint = Endpoint(
                    method=method,
                    path=path,
                    requires_auth=requires_auth,
                    source_file=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                )
                endpoints.append(endpoint)
                continue
            
            # Check for route() pattern
            route_match = re.search(route_pattern, line)
            if route_match:
                path = route_match.group(2)
                
                # Look for chained methods on subsequent lines
                # Combine current line and next few lines to handle multi-line chains
                combined = line
                for i in range(line_num, min(line_num + 10, len(lines))):
                    combined += lines[i]
                
                # Find all chained methods
                method_pattern = r'\.(get|post|put|delete|patch)\('
                for method_match in re.finditer(method_pattern, combined):
                    method = method_match.group(1).upper()
                    
                    endpoint = Endpoint(
                        method=method,
                        path=path,
                        requires_auth=False,  # Auth check harder for chained routes
                        source_file=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                    )
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _discover_fastapi_endpoints(self) -> List[Endpoint]:
        """Discover endpoints from FastAPI applications"""
        endpoints = []
        
        # Search for Python files
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Parse FastAPI decorators
                fastapi_endpoints = self._parse_fastapi_decorators(content, lines, py_file)
                endpoints.extend(fastapi_endpoints)
                
            except Exception as e:
                logger.debug(f"Error parsing {py_file}: {e}")
        
        return endpoints
    
    def _parse_fastapi_decorators(self, content: str, lines: List[str], file_path: Path) -> List[Endpoint]:
        """Parse FastAPI route decorators"""
        endpoints = []
        
        # Patterns for FastAPI decorators
        # @app.get("/path") or @router.get("/path")
        pattern = r'@(app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        
        for line_num, line in enumerate(lines, 1):
            match = re.search(pattern, line)
            if match:
                method = match.group(2).upper()
                path = match.group(3)
                
                # Check for authentication dependency
                requires_auth = self._check_fastapi_auth(lines, line_num)
                
                endpoint = Endpoint(
                    method=method,
                    path=path,
                    requires_auth=requires_auth,
                    source_file=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                )
                endpoints.append(endpoint)
        
        return endpoints
    
    def _check_aspnet_auth(self, lines: List[str], line_num: int) -> bool:
        """Check if ASP.NET endpoint requires authentication"""
        # Look at surrounding lines for [Authorize] attribute
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 2)
        
        for line in lines[start:end]:
            if '[Authorize' in line:
                return True
        
        return False
    
    def _check_express_auth(self, current_line: str, lines: List[str], line_num: int) -> bool:
        """Check if Express endpoint requires authentication"""
        # Check for auth middleware in the same line
        auth_keywords = ['requireAuth', 'isAuthenticated', 'authenticate', 'authMiddleware', 'checkAuth']
        
        for keyword in auth_keywords:
            if keyword in current_line:
                return True
        
        return False
    
    def _check_fastapi_auth(self, lines: List[str], line_num: int) -> bool:
        """Check if FastAPI endpoint requires authentication"""
        # Look at the function definition for Depends(get_current_user) or similar
        start = line_num
        end = min(len(lines), line_num + 10)
        
        for line in lines[start:end]:
            if 'Depends(' in line and ('current_user' in line or 'get_user' in line or 'auth' in line.lower()):
                return True
            
            # Stop at next decorator or blank line
            if line.strip().startswith('@') or (line.strip() == '' and line_num != start):
                break
        
        return False
    
    def _combine_routes(self, base: str, route: str) -> str:
        """Combine base route and method route"""
        if not base:
            return route or "/"
        if not route:
            return base
        
        # Remove leading/trailing slashes and combine
        base = base.strip('/')
        route = route.strip('/')
        
        return f"/{base}/{route}" if route else f"/{base}"
    
    def _deduplicate_endpoints(self, endpoints: List[Endpoint]) -> List[Endpoint]:
        """Remove duplicate endpoints (same method + path)"""
        seen: Set[tuple] = set()
        unique_endpoints = []
        
        for endpoint in endpoints:
            key = (endpoint.method, endpoint.path)
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(endpoint)
        
        return unique_endpoints
    
    def get_endpoints_by_method(self, method: str) -> List[Endpoint]:
        """Get all endpoints with a specific HTTP method"""
        return [e for e in self.endpoints if e.method.upper() == method.upper()]
    
    def get_authenticated_endpoints(self) -> List[Endpoint]:
        """Get all endpoints that require authentication"""
        return [e for e in self.endpoints if e.requires_auth]
    
    def get_public_endpoints(self) -> List[Endpoint]:
        """Get all endpoints that don't require authentication"""
        return [e for e in self.endpoints if not e.requires_auth]
