"""
Unit tests for project_discovery.py

Tests the ProjectDiscovery class for discovering projects with Bicep templates,
framework detection, caching, and project selection.
"""

import pytest
from pathlib import Path
import json
import tempfile
import shutil
from datetime import datetime, timedelta

from specify_cli.validation.project_discovery import ProjectDiscovery
from specify_cli.validation import ProjectInfo, ProjectDiscoveryError


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with sample projects"""
    
    # Create dotnet project
    dotnet_path = tmp_path / "dotnet-api"
    dotnet_path.mkdir()
    (dotnet_path / "Program.cs").write_text("// .NET app")
    (dotnet_path / "dotnet-api.csproj").write_text("<Project></Project>")
    (dotnet_path / "bicep-templates").mkdir()
    (dotnet_path / "bicep-templates" / "main.bicep").write_text("// bicep")
    
    # Create nodejs project
    nodejs_path = tmp_path / "nodejs-express"
    nodejs_path.mkdir()
    (nodejs_path / "package.json").write_text('{"name": "test"}')
    (nodejs_path / "server.js").write_text("// node app")
    (nodejs_path / "infrastructure").mkdir()
    (nodejs_path / "infrastructure" / "main.bicep").write_text("// bicep")
    
    # Create python project
    python_path = tmp_path / "python-fastapi"
    python_path.mkdir()
    (python_path / "requirements.txt").write_text("fastapi")
    (python_path / "main.py").write_text("# python app")
    (python_path / "bicep").mkdir()
    (python_path / "bicep" / "main.bicep").write_text("// bicep")
    
    # Create project without bicep (should be ignored)
    no_bicep_path = tmp_path / "no-bicep"
    no_bicep_path.mkdir()
    (no_bicep_path / "README.md").write_text("# No bicep here")
    
    return tmp_path


@pytest.fixture
def discovery(temp_workspace):
    """Create a ProjectDiscovery instance with temp workspace"""
    return ProjectDiscovery(temp_workspace, use_cache=False)


class TestProjectDiscovery:
    """Tests for ProjectDiscovery class"""
    
    def test_discover_projects_finds_all_projects(self, discovery, temp_workspace):
        """Test that discover_projects finds all projects with Bicep templates"""
        projects = discovery.discover_projects()
        
        assert len(projects) == 3
        project_names = {p.name for p in projects}
        assert "dotnet-api" in project_names
        assert "nodejs-express" in project_names
        assert "python-fastapi" in project_names
    
    def test_discover_projects_excludes_projects_without_bicep(self, discovery):
        """Test that projects without Bicep templates are excluded"""
        projects = discovery.discover_projects()
        
        project_names = {p.name for p in projects}
        assert "no-bicep" not in project_names
    
    def test_framework_detection_dotnet(self, discovery):
        """Test detection of .NET framework"""
        projects = discovery.discover_projects()
        dotnet_project = next(p for p in projects if p.name == "dotnet-api")
        
        assert dotnet_project.framework == "dotnet"
    
    def test_framework_detection_nodejs(self, discovery):
        """Test detection of Node.js framework"""
        projects = discovery.discover_projects()
        nodejs_project = next(p for p in projects if p.name == "nodejs-express")
        
        assert nodejs_project.framework == "nodejs"
    
    def test_framework_detection_python(self, discovery):
        """Test detection of Python framework"""
        projects = discovery.discover_projects()
        python_project = next(p for p in projects if p.name == "python-fastapi")
        
        assert python_project.framework == "python"
    
    def test_bicep_directory_detection(self, discovery):
        """Test that various Bicep directory names are detected"""
        projects = discovery.discover_projects()
        
        # Find each project and verify bicep_templates_path is set
        dotnet_project = next(p for p in projects if p.name == "dotnet-api")
        assert dotnet_project.bicep_templates_path.name == "bicep-templates"
        
        nodejs_project = next(p for p in projects if p.name == "nodejs-express")
        assert nodejs_project.bicep_templates_path.name == "infrastructure"
        
        python_project = next(p for p in projects if p.name == "python-fastapi")
        assert python_project.bicep_templates_path.name == "bicep"
    
    def test_get_project_by_name_exact_match(self, discovery):
        """Test getting project by exact name"""
        discovery.discover_projects()
        project = discovery.get_project_by_name("dotnet-api")
        
        assert project is not None
        assert project.name == "dotnet-api"
        assert project.framework == "dotnet"
    
    def test_get_project_by_name_partial_match(self, discovery):
        """Test getting project by partial name"""
        discovery.discover_projects()
        project = discovery.get_project_by_name("dotnet")
        
        assert project is not None
        assert project.name == "dotnet-api"
    
    def test_get_project_by_name_case_insensitive(self, discovery):
        """Test that name matching is case-insensitive"""
        discovery.discover_projects()
        project = discovery.get_project_by_name("DOTNET-API")
        
        assert project is not None
        assert project.name == "dotnet-api"
    
    def test_get_project_by_name_not_found(self, discovery):
        """Test that None is returned when project not found"""
        discovery.discover_projects()
        project = discovery.get_project_by_name("nonexistent")
        
        assert project is None
    
    def test_caching_saves_to_file(self, temp_workspace):
        """Test that cache is saved to .bicep-cache.json"""
        discovery = ProjectDiscovery(temp_workspace, use_cache=True)
        discovery.discover_projects()
        
        cache_file = temp_workspace / ".bicep-cache.json"
        assert cache_file.exists()
        
        # Verify cache content
        cache_data = json.loads(cache_file.read_text())
        assert "timestamp" in cache_data
        assert "projects" in cache_data
        assert len(cache_data["projects"]) == 3
    
    def test_caching_loads_from_file(self, temp_workspace):
        """Test that cache is loaded from existing file"""
        # Create cached data in cache file
        cache_file = temp_workspace / ".bicep-cache.json"
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "projects": [
                {
                    "project_id": "cached-project-001",
                    "name": "cached-project",
                    "path": str(temp_workspace / "cached-project"),
                    "source_code_path": str(temp_workspace / "cached-project"),
                    "framework": "dotnet",
                    "bicep_templates_path": str(temp_workspace / "cached-project" / "bicep"),
                    "last_modified": 0.0
                }
            ]
        }
        cache_file.write_text(json.dumps(cache_data))
        
        # Discover with cache enabled
        discovery = ProjectDiscovery(temp_workspace, use_cache=True)
        projects = discovery.discover_projects()
        
        # Should load from cache (even though directory doesn't exist)
        assert len(projects) == 1
        assert projects[0].name == "cached-project"
    
    def test_cache_expiry(self, temp_workspace):
        """Test that expired cache is regenerated"""
        # Create expired cache file
        cache_file = temp_workspace / ".bicep-cache.json"
        old_timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
        cache_data = {
            "timestamp": old_timestamp,
            "projects": [
                {
                    "project_id": "cached-project-001",
                    "name": "cached-project",
                    "path": str(temp_workspace / "cached-project"),
                    "source_code_path": str(temp_workspace / "cached-project"),
                    "framework": "dotnet",
                    "bicep_templates_path": str(temp_workspace / "cached-project" / "bicep"),
                    "last_modified": 0.0
                }
            ]
        }
        cache_file.write_text(json.dumps(cache_data))
        
        # Discover with cache enabled (should regenerate)
        discovery = ProjectDiscovery(temp_workspace, use_cache=True)
        projects = discovery.discover_projects()
        
        # Should find real projects, not cached one
        assert len(projects) == 3
        project_names = {p.name for p in projects}
        assert "cached-project" not in project_names
    
    def test_clear_cache(self, temp_workspace):
        """Test that clear_cache removes cache file"""
        discovery = ProjectDiscovery(temp_workspace, use_cache=True)
        discovery.discover_projects()
        
        cache_file = temp_workspace / ".bicep-cache.json"
        assert cache_file.exists()
        
        discovery.clear_cache()
        assert not cache_file.exists()
    
    def test_excluded_directories_ignored(self, temp_workspace):
        """Test that excluded directories are not scanned"""
        # Create project in node_modules (should be excluded)
        node_modules = temp_workspace / "node_modules" / "some-package"
        node_modules.mkdir(parents=True)
        (node_modules / "package.json").write_text('{"name": "test"}')
        (node_modules / "bicep-templates").mkdir()
        (node_modules / "bicep-templates" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(temp_workspace, use_cache=False)
        projects = discovery.discover_projects()
        
        # Should not find project in node_modules
        project_names = {p.name for p in projects}
        assert "some-package" not in project_names
    
    def test_hidden_directories_ignored(self, temp_workspace):
        """Test that hidden directories are not scanned"""
        # Create project in .hidden directory
        hidden_dir = temp_workspace / ".hidden" / "project"
        hidden_dir.mkdir(parents=True)
        (hidden_dir / "package.json").write_text('{"name": "test"}')
        (hidden_dir / "bicep").mkdir()
        (hidden_dir / "bicep" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(temp_workspace, use_cache=False)
        projects = discovery.discover_projects()
        
        # Should not find hidden project
        project_names = {p.name for p in projects}
        assert "project" not in project_names
    
    def test_nonexistent_workspace_raises_error(self):
        """Test that nonexistent workspace raises ProjectDiscoveryError"""
        with pytest.raises(ProjectDiscoveryError, match="does not exist"):
            discovery = ProjectDiscovery(Path("/nonexistent/path"))
            discovery.discover_projects()
    
    def test_file_as_workspace_raises_error(self, temp_workspace):
        """Test that using a file as workspace raises error"""
        file_path = temp_workspace / "somefile.txt"
        file_path.write_text("not a directory")
        
        with pytest.raises(ProjectDiscoveryError, match="not a directory"):
            discovery = ProjectDiscovery(file_path)
            discovery.discover_projects()
    
    def test_discover_projects_returns_sorted_list(self, discovery):
        """Test that projects are returned in sorted order by name"""
        projects = discovery.discover_projects()
        project_names = [p.name for p in projects]
        
        assert project_names == sorted(project_names)
    
    def test_project_info_attributes(self, discovery):
        """Test that ProjectInfo has all required attributes"""
        projects = discovery.discover_projects()
        project = projects[0]
        
        assert hasattr(project, "name")
        assert hasattr(project, "path")
        assert hasattr(project, "framework")
        assert hasattr(project, "bicep_templates_path")
        
        assert isinstance(project.name, str)
        assert isinstance(project.path, Path)
        assert isinstance(project.framework, str)
        assert isinstance(project.bicep_templates_path, Path)


class TestFrameworkDetection:
    """Tests for framework detection logic"""
    
    def test_go_framework_detection(self, tmp_path):
        """Test detection of Go framework"""
        go_path = tmp_path / "go-api"
        go_path.mkdir()
        (go_path / "go.mod").write_text("module test")
        (go_path / "main.go").write_text("package main")
        (go_path / "bicep").mkdir()
        (go_path / "bicep" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(tmp_path, use_cache=False)
        projects = discovery.discover_projects()
        
        assert len(projects) == 1
        assert projects[0].framework == "go"
    
    def test_java_framework_detection(self, tmp_path):
        """Test detection of Java framework"""
        java_path = tmp_path / "java-api"
        java_path.mkdir()
        (java_path / "pom.xml").write_text("<project></project>")
        (java_path / "bicep").mkdir()
        (java_path / "bicep" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(tmp_path, use_cache=False)
        projects = discovery.discover_projects()
        
        assert len(projects) == 1
        assert projects[0].framework == "java"
    
    def test_ruby_framework_detection(self, tmp_path):
        """Test detection of Ruby framework"""
        ruby_path = tmp_path / "ruby-api"
        ruby_path.mkdir()
        (ruby_path / "Gemfile").write_text("source 'https://rubygems.org'")
        (ruby_path / "bicep").mkdir()
        (ruby_path / "bicep" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(tmp_path, use_cache=False)
        projects = discovery.discover_projects()
        
        assert len(projects) == 1
        assert projects[0].framework == "ruby"
    
    def test_unknown_framework_detection(self, tmp_path):
        """Test detection when framework is unknown"""
        unknown_path = tmp_path / "unknown-api"
        unknown_path.mkdir()
        (unknown_path / "somefile.txt").write_text("unknown")
        (unknown_path / "bicep").mkdir()
        (unknown_path / "bicep" / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(tmp_path, use_cache=False)
        projects = discovery.discover_projects()
        
        assert len(projects) == 1
        assert projects[0].framework == "unknown"


class TestBicepDirectoryVariations:
    """Tests for various Bicep directory naming conventions"""
    
    @pytest.mark.parametrize("bicep_dir_name", [
        "bicep-templates",
        "bicep",
        "infrastructure",
        "iac",
        "templates"
    ])
    def test_bicep_directory_names(self, tmp_path, bicep_dir_name):
        """Test that all common Bicep directory names are detected"""
        project_path = tmp_path / "test-project"
        project_path.mkdir()
        (project_path / "package.json").write_text('{"name": "test"}')
        bicep_path = project_path / bicep_dir_name
        bicep_path.mkdir()
        (bicep_path / "main.bicep").write_text("// bicep")
        
        discovery = ProjectDiscovery(tmp_path, use_cache=False)
        projects = discovery.discover_projects()
        
        assert len(projects) == 1
        assert projects[0].bicep_templates_path.name == bicep_dir_name
