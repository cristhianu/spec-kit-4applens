"""
Project discovery module for finding projects with Bicep templates.

Scans workspace for projects containing generated Bicep templates and
provides caching for performance optimization.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from specify_cli.validation import ProjectInfo, ProjectDiscoveryError

logger = logging.getLogger(__name__)


class ProjectDiscovery:
    """
    Discovers projects with generated Bicep templates.
    
    Scans workspace directory structure for projects containing Bicep
    templates and caches results for performance.
    """
    
    CACHE_FILE = ".bicep-cache.json"
    CACHE_TTL = 300  # 5 minutes
    
    # Signature files for framework detection
    FRAMEWORK_SIGNATURES = {
        "dotnet": ["*.csproj", "*.fsproj", "*.vbproj", "Program.cs", "Startup.cs"],
        "nodejs": ["package.json", "server.js", "app.js", "index.js"],
        "python": ["requirements.txt", "setup.py", "pyproject.toml", "main.py", "app.py"],
        "go": ["go.mod", "main.go"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "ruby": ["Gemfile", "config.ru"],
    }
    
    def __init__(self, workspace_root: Path, use_cache: bool = True):
        """
        Initialize project discovery.
        
        Args:
            workspace_root: Root directory to search for projects
            use_cache: Whether to use cached results (default: True)
            
        Raises:
            FileNotFoundError: If workspace_root doesn't exist
            PermissionError: If workspace_root is not readable
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.use_cache = use_cache
        self.cache_file = self.workspace_root / self.CACHE_FILE
        
        # Validate workspace root
        if not self.workspace_root.exists():
            raise ProjectDiscoveryError(f"Workspace root does not exist: {self.workspace_root}")
        
        if not self.workspace_root.is_dir():
            raise ProjectDiscoveryError(f"Workspace root is not a directory: {self.workspace_root}")
        
        # Test read permissions
        try:
            list(self.workspace_root.iterdir())
        except PermissionError as e:
            raise PermissionError(f"Workspace root is not readable: {self.workspace_root}") from e
        
        logger.info(f"Initialized project discovery for: {self.workspace_root}")
    
    def discover_projects(self) -> List[ProjectInfo]:
        """
        Discover all projects with Bicep templates.
        
        Returns:
            List of ProjectInfo objects
            
        Raises:
            ProjectDiscoveryError: If discovery fails
        """
        # Try cache first
        if self.use_cache:
            cached_projects = self._load_from_cache()
            if cached_projects is not None:
                logger.info(f"Loaded {len(cached_projects)} projects from cache")
                return cached_projects
        
        # Perform discovery
        logger.info("Starting project discovery...")
        start_time = time.time()
        
        try:
            projects = self._scan_for_projects()
            
            # Save to cache
            if self.use_cache and projects:
                self._save_to_cache(projects)
            
            elapsed = time.time() - start_time
            logger.info(f"Discovered {len(projects)} projects in {elapsed:.2f}s")
            
            return projects
            
        except Exception as e:
            logger.error(f"Project discovery failed: {e}")
            raise ProjectDiscoveryError(f"Failed to discover projects: {e}") from e
    
    def get_project_by_name(self, name: str) -> Optional[ProjectInfo]:
        """
        Get specific project by name.
        
        Args:
            name: Project name to search for (case-insensitive)
            
        Returns:
            ProjectInfo if found, None otherwise
        """
        projects = self.discover_projects()
        
        # Try exact match first
        for project in projects:
            if project.name.lower() == name.lower():
                return project
        
        # Try partial match
        for project in projects:
            if name.lower() in project.name.lower():
                logger.info(f"Found partial match: {project.name} for query: {name}")
                return project
        
        logger.warning(f"No project found matching: {name}")
        return None
    
    def clear_cache(self) -> None:
        """Clear discovery cache"""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Cache cleared")
        else:
            logger.debug("No cache file to clear")
    
    def _scan_for_projects(self) -> List[ProjectInfo]:
        """
        Scan workspace for projects with Bicep templates.
        
        Returns:
            List of discovered projects
        """
        projects = []
        
        # Common Bicep template directory names
        bicep_dirs = ["bicep-templates", "bicep", "infrastructure", "iac", "templates"]
        
        # Scan workspace (limit depth to avoid excessive scanning)
        for path in self.workspace_root.rglob("*"):
            # Skip hidden directories and common exclusions
            if any(part.startswith('.') for part in path.parts):
                continue
            
            if any(exclude in path.parts for exclude in ["node_modules", "venv", ".venv", "bin", "obj"]):
                continue
            
            # Check if directory contains Bicep files
            if path.is_dir() and path.name.lower() in bicep_dirs:
                bicep_files = list(path.glob("*.bicep"))
                
                if bicep_files:
                    # Found a project with Bicep templates
                    project_root = path.parent
                    
                    # Detect framework
                    framework = self._detect_framework(project_root)
                    
                    # Get last modified time (most recent .bicep file)
                    last_modified = max(f.stat().st_mtime for f in bicep_files)
                    
                    # Create project info
                    project = ProjectInfo(
                        project_id=str(project_root.relative_to(self.workspace_root)),
                        name=project_root.name,
                        path=project_root,
                        source_code_path=project_root,
                        bicep_templates_path=path,
                        framework=framework,
                        last_modified=last_modified
                    )
                    
                    projects.append(project)
                    logger.debug(f"Found project: {project.name} ({framework})")
        
        return projects
    
    def _detect_framework(self, project_path: Path) -> str:
        """
        Detect project framework based on signature files.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Framework name or "unknown"
        """
        for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
            for signature in signatures:
                if signature.startswith("*."):
                    # Extension pattern
                    ext = signature[1:]  # Remove *
                    if list(project_path.glob(f"**/*{ext}")):
                        return framework
                else:
                    # Specific file
                    if (project_path / signature).exists():
                        return framework
        
        return "unknown"
    
    def _load_from_cache(self) -> Optional[List[ProjectInfo]]:
        """
        Load projects from cache if valid.
        
        Returns:
            List of projects if cache valid, None otherwise
        """
        if not self.cache_file.exists():
            return None
        
        try:
            cache_data = json.loads(self.cache_file.read_text())
            
            # Check cache age
            cache_time = cache_data.get("timestamp", 0)
            # Handle both float (Unix timestamp) and string (ISO format) timestamps
            if isinstance(cache_time, str):
                try:
                    cache_time = datetime.fromisoformat(cache_time).timestamp()
                except (ValueError, AttributeError):
                    cache_time = 0
            age = time.time() - cache_time
            
            if age > self.CACHE_TTL:
                logger.debug(f"Cache expired (age: {age:.0f}s)")
                return None
            
            # Reconstruct projects
            projects = []
            for proj_data in cache_data.get("projects", []):
                project = ProjectInfo(
                    project_id=proj_data["project_id"],
                    name=proj_data["name"],
                    path=Path(proj_data["path"]),
                    source_code_path=Path(proj_data["source_code_path"]),
                    bicep_templates_path=Path(proj_data["bicep_templates_path"]),
                    framework=proj_data["framework"],
                    last_modified=proj_data["last_modified"]
                )
                projects.append(project)
            
            return projects
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache file corrupted: {e}")
            return None
    
    def _save_to_cache(self, projects: List[ProjectInfo]) -> None:
        """
        Save projects to cache.
        
        Args:
            projects: List of projects to cache
        """
        try:
            cache_data = {
                "timestamp": time.time(),
                "projects": [
                    {
                        "project_id": p.project_id,
                        "name": p.name,
                        "path": str(p.path),
                        "source_code_path": str(p.source_code_path),
                        "bicep_templates_path": str(p.bicep_templates_path),
                        "framework": p.framework,
                        "last_modified": p.last_modified
                    }
                    for p in projects
                ]
            }
            
            self.cache_file.write_text(json.dumps(cache_data, indent=2))
            logger.debug(f"Saved {len(projects)} projects to cache")
            
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
