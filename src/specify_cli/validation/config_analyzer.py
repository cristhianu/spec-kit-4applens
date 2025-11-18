"""
Configuration analyzer for identifying app settings and dependencies.

Analyzes project source code and configuration files to identify
required application settings, secure values, and resource dependencies.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set
import logging

from specify_cli.validation import (
    ProjectInfo,
    AppSetting,
    AnalysisResult,
    SourceType,
    ConfigAnalysisError
)
from specify_cli.utils.dependency_graph import DependencyGraph

logger = logging.getLogger(__name__)


class ConfigAnalyzer:
    """
    Analyzes project configuration to identify app settings and dependencies.
    
    Supports multiple frameworks with framework-specific parsers.
    """
    
    # Patterns for identifying secure values
    SECURE_PATTERNS = [
        r"password",
        r"secret",
        r"apikey",
        r"api[_-]?key",
        r"connectionstring",
        r"connection[_-]?string",
        r"token",
        r"credential",
        r"private[_-]?key",
    ]
    
    # Resource type detection patterns
    RESOURCE_PATTERNS = {
        "Microsoft.Sql/servers": [
            r"sql\.database\.windows\.net",
            r"SqlConnection",
            r"Server=.*database\.windows\.net"
        ],
        "Microsoft.Storage/storageAccounts": [
            r"blob\.core\.windows\.net",
            r"queue\.core\.windows\.net",
            r"table\.core\.windows\.net",
            r"file\.core\.windows\.net",
            r"DefaultEndpointsProtocol=https.*windows\.net"
        ],
        "Microsoft.DocumentDB/databaseAccounts": [
            r"documents\.azure\.com",
            r"cosmos\.azure\.com",
            r"AccountEndpoint=https://.*documents\.azure\.com"
        ],
        "Microsoft.ServiceBus/namespaces": [
            r"servicebus\.windows\.net",
            r"Endpoint=sb://.*servicebus\.windows\.net"
        ],
        "Microsoft.KeyVault/vaults": [
            r"vault\.azure\.net",
            r"@Microsoft\.KeyVault"
        ],
        "Microsoft.Cache/redis": [
            r"redis\.cache\.windows\.net",
            r"StackExchange\.Redis"
        ]
    }
    
    def __init__(self):
        """Initialize configuration analyzer"""
        self.secure_regex = re.compile(
            "|".join(self.SECURE_PATTERNS),
            re.IGNORECASE
        )
    
    def analyze_project(self, project: ProjectInfo) -> AnalysisResult:
        """
        Analyze project configuration and dependencies.
        
        Args:
            project: Project to analyze
            
        Returns:
            AnalysisResult with app settings and dependencies
            
        Raises:
            ConfigAnalysisError: If analysis fails
        """
        logger.info(f"Analyzing project: {project.name}")
        
        try:
            # Parse configuration files based on framework
            settings = self._parse_config_files(project)
            
            # Identify resource dependencies
            dependencies = self._identify_dependencies(settings, project)
            
            # Build dependency graph
            dep_graph = self._build_dependency_graph(dependencies)
            
            logger.info(
                f"Analysis complete: {len(settings)} settings, "
                f"{len(dependencies)} resource dependencies"
            )
            
            return AnalysisResult(
                app_settings=settings,
                resource_dependencies=dependencies,
                dependency_graph=dep_graph
            )
            
        except Exception as e:
            logger.error(f"Configuration analysis failed: {e}")
            raise ConfigAnalysisError(f"Failed to analyze project: {e}") from e
    
    def _parse_config_files(self, project: ProjectInfo) -> List[AppSetting]:
        """
        Parse framework-specific configuration files.
        
        Args:
            project: Project to parse
            
        Returns:
            List of discovered app settings
        """
        settings = []
        
        if project.framework == "dotnet":
            settings.extend(self._parse_appsettings(project))
        elif project.framework == "nodejs":
            settings.extend(self._parse_env_file(project))
            settings.extend(self._parse_package_json(project))
        elif project.framework == "python":
            settings.extend(self._parse_python_config(project))
            settings.extend(self._parse_env_file(project))
        else:
            # Try generic parsing
            settings.extend(self._parse_env_file(project))
        
        return settings
    
    def _parse_appsettings(self, project: ProjectInfo) -> List[AppSetting]:
        """
        Parse ASP.NET appsettings.json files.
        
        Args:
            project: Project to parse
            
        Returns:
            List of app settings
        """
        settings = []
        
        # Look for appsettings files
        for pattern in ["appsettings.json", "appsettings.*.json"]:
            for config_file in project.source_code_path.glob(pattern):
                try:
                    data = json.loads(config_file.read_text())
                    settings.extend(self._extract_settings_from_json(data))
                except Exception as e:
                    logger.warning(f"Failed to parse {config_file}: {e}")
        
        return settings
    
    def _parse_env_file(self, project: ProjectInfo) -> List[AppSetting]:
        """
        Parse .env or .env.example files.
        
        Args:
            project: Project to parse
            
        Returns:
            List of app settings
        """
        settings = []
        
        for env_file in project.source_code_path.glob(".env*"):
            if env_file.name == ".env.local":
                continue  # Skip local overrides
            
            try:
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse KEY=VALUE
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        is_secure = self._is_secure_value(key)
                        
                        setting = AppSetting(
                            setting_id=f"env_{key}",
                            name=key,
                            value=value if not is_secure else None,
                            source_type=SourceType.KEYVAULT if is_secure else SourceType.HARDCODED,
                            is_secure=is_secure,
                            environment="test",
                            keyvault_secret_name=self._format_secret_name(key) if is_secure else None
                        )
                        settings.append(setting)
                        
            except Exception as e:
                logger.warning(f"Failed to parse {env_file}: {e}")
        
        return settings
    
    def _parse_package_json(self, project: ProjectInfo) -> List[AppSetting]:
        """
        Parse Node.js package.json for config hints.
        
        Args:
            project: Project to parse
            
        Returns:
            List of app settings
        """
        settings = []
        package_json = project.source_code_path / "package.json"
        
        if not package_json.exists():
            return settings
        
        try:
            data = json.loads(package_json.read_text())
            
            # Check for config section
            if "config" in data:
                settings.extend(self._extract_settings_from_json(data["config"]))
            
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")
        
        return settings
    
    def _parse_python_config(self, project: ProjectInfo) -> List[AppSetting]:
        """
        Parse Python config.py or settings.py files.
        
        Args:
            project: Project to parse
            
        Returns:
            List of app settings
        """
        settings = []
        
        for config_file in project.source_code_path.glob("**/config.py"):
            settings.extend(self._parse_python_file(config_file))
        
        for settings_file in project.source_code_path.glob("**/settings.py"):
            settings.extend(self._parse_python_file(settings_file))
        
        return settings
    
    def _parse_python_file(self, file_path: Path) -> List[AppSetting]:
        """
        Parse Python file for config variables.
        
        Args:
            file_path: Python file to parse
            
        Returns:
            List of app settings
        """
        settings = []
        
        try:
            content = file_path.read_text()
            
            # Look for uppercase variables (convention for constants)
            for line in content.splitlines():
                line = line.strip()
                
                # Match: VARIABLE_NAME = value
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$', line)
                if match:
                    key = match.group(1)
                    
                    # Skip common non-config constants
                    if key in ["DEBUG", "TESTING", "VERSION"]:
                        continue
                    
                    is_secure = self._is_secure_value(key)
                    
                    setting = AppSetting(
                        setting_id=f"py_{key}",
                        name=key,
                        value=None,
                        source_type=SourceType.KEYVAULT if is_secure else SourceType.HARDCODED,
                        is_secure=is_secure,
                        environment="test",
                        keyvault_secret_name=self._format_secret_name(key) if is_secure else None
                    )
                    settings.append(setting)
                    
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
        
        return settings
    
    def _extract_settings_from_json(
        self,
        data: Dict,
        prefix: str = ""
    ) -> List[AppSetting]:
        """
        Recursively extract settings from JSON structure.
        
        Args:
            data: JSON data dictionary
            prefix: Key prefix for nested structures
            
        Returns:
            List of app settings
        """
        settings = []
        
        for key, value in data.items():
            full_key = f"{prefix}:{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recurse into nested structures
                settings.extend(self._extract_settings_from_json(value, full_key))
            else:
                # Leaf value - create setting
                is_secure = self._is_secure_value(full_key)
                
                setting = AppSetting(
                    setting_id=f"json_{full_key.replace(':', '_')}",
                    name=full_key,
                    value=str(value) if not is_secure else None,
                    source_type=SourceType.KEYVAULT if is_secure else SourceType.HARDCODED,
                    is_secure=is_secure,
                    environment="test",
                    keyvault_secret_name=self._format_secret_name(full_key) if is_secure else None
                )
                settings.append(setting)
        
        return settings
    
    def _is_secure_value(self, key: str) -> bool:
        """
        Determine if a setting key indicates a secure value.
        
        Args:
            key: Setting key/name
            
        Returns:
            True if key suggests secure value
        """
        return bool(self.secure_regex.search(key))
    
    def _format_secret_name(self, key: str) -> str:
        """
        Format setting key as Key Vault secret name.
        
        Follows Azure naming convention:
        - Lowercase
        - Alphanumeric and hyphens only
        - Max 127 characters
        
        Args:
            key: Setting key
            
        Returns:
            Formatted secret name
        """
        # Replace common separators with hyphens
        name = key.replace(":", "-").replace("_", "-").replace(".", "-")
        
        # Convert to lowercase
        name = name.lower()
        
        # Remove invalid characters
        name = re.sub(r'[^a-z0-9-]', '', name)
        
        # Trim to max length
        name = name[:127]
        
        return name
    
    def _identify_dependencies(
        self,
        settings: List[AppSetting],
        project: ProjectInfo
    ) -> List[str]:
        """
        Identify Azure resource dependencies from settings.
        
        Args:
            settings: App settings to analyze
            project: Project being analyzed
            
        Returns:
            List of resource type identifiers
        """
        dependencies: Set[str] = set()
        
        # Check setting values for resource patterns
        for setting in settings:
            if setting.value:
                for resource_type, patterns in self.RESOURCE_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, setting.value, re.IGNORECASE):
                            dependencies.add(resource_type)
                            logger.debug(
                                f"Detected {resource_type} dependency "
                                f"from setting: {setting.name}"
                            )
                            break
        
        return list(dependencies)
    
    def _build_dependency_graph(self, dependencies: List[str]) -> Dict[str, List[str]]:
        """
        Build dependency graph for resources.
        
        Args:
            dependencies: List of resource types
            
        Returns:
            Dependency graph dictionary
        """
        graph = DependencyGraph()
        
        # Add all resources as nodes
        for resource in dependencies:
            graph.add_node(resource)
        
        # Define common dependency relationships
        # Example: Key Vault typically needed first for secrets
        if "Microsoft.KeyVault/vaults" in dependencies:
            for resource in dependencies:
                if resource != "Microsoft.KeyVault/vaults":
                    # Other resources may depend on Key Vault for secrets
                    graph.add_dependency(resource, "Microsoft.KeyVault/vaults")
        
        # SQL Server should be deployed before apps using it
        if "Microsoft.Sql/servers" in dependencies:
            # No dependencies (can be deployed first)
            pass
        
        # Convert graph to dictionary format
        return {node: graph.get_dependencies(node) for node in graph.nodes}
