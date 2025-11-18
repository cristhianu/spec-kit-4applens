"""
Unit tests for ValidationSession module (T068)

Tests session orchestration, stage transitions, progress tracking,
and validation summary generation.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from specify_cli.validation.validation_session import (
    ValidationSession, ValidationStage, ValidationSummary
)
from specify_cli.validation.project_discovery import ProjectInfo
from specify_cli.validation.endpoint_discoverer import Endpoint
from specify_cli.validation.endpoint_tester import TestResult, TestStatus


class TestValidationSummary:
    """Test ValidationSummary dataclass"""
    
    def test_summary_initialization(self):
        """Test ValidationSummary creation"""
        summary = ValidationSummary(
            session_id="test-123",
            start_time=datetime.now(),
        )
        
        assert summary.session_id == "test-123"
        assert summary.current_stage == ValidationStage.INITIALIZING
        assert summary.stages_completed == []
        assert summary.success == False
        assert summary.error_message is None
    
    def test_summary_to_dict(self):
        """Test ValidationSummary serialization"""
        start = datetime.now()
        summary = ValidationSummary(
            session_id="test-456",
            start_time=start,
            current_stage=ValidationStage.TESTING,
            projects_discovered=2,
            endpoints_tested=5,
            tests_passed=4,
            tests_failed=1,
        )
        
        result = summary.to_dict()
        
        assert result["session_id"] == "test-456"
        assert result["start_time"] == start.isoformat()
        assert result["current_stage"] == "testing"
        assert result["projects_discovered"] == 2
        assert result["endpoints_tested"] == 5
        assert result["tests_passed"] == 4
        assert result["tests_failed"] == 1


class TestValidationSession:
    """Test ValidationSession class"""
    
    def test_session_initialization(self, tmp_path):
        """Test ValidationSession creation"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
            keyvault_url="https://test-kv.vault.azure.net/",
            enable_fixes=True,
            max_fix_attempts=5,
        )
        
        assert session.project_root == tmp_path
        assert session.resource_group == "test-rg"
        assert session.keyvault_url == "https://test-kv.vault.azure.net/"
        assert session.enable_fixes == True
        assert session.max_fix_attempts == 5
        assert session.summary.current_stage == ValidationStage.INITIALIZING
        assert len(session.summary.session_id) > 0
    
    def test_get_current_stage(self, tmp_path):
        """Test get_current_stage method"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Initially in INITIALIZING stage
        assert session.get_current_stage() == ValidationStage.INITIALIZING
        
        # Transition to DISCOVERING
        session._transition_to_stage(ValidationStage.DISCOVERING)
        assert session.get_current_stage() == ValidationStage.DISCOVERING
        
        # Transition to ANALYZING
        session._transition_to_stage(ValidationStage.ANALYZING)
        assert session.get_current_stage() == ValidationStage.ANALYZING
    
    def test_get_progress(self, tmp_path):
        """Test get_progress method"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Initial progress
        progress = session.get_progress()
        assert progress["current_stage"] == "initializing"
        assert progress["stages_completed"] == []
        assert progress["progress_percentage"] == 0.0
        
        # Complete first stage
        session._transition_to_stage(ValidationStage.DISCOVERING)
        session._complete_stage(ValidationStage.DISCOVERING)
        
        progress = session.get_progress()
        assert progress["current_stage"] == "discovering"
        assert len(progress["stages_completed"]) == 1
        assert progress["stages_completed"][0] == "discovering"
        assert progress["progress_percentage"] > 0
    
    def test_stage_transitions(self, tmp_path):
        """Test stage transition tracking"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Transition through stages
        stages = [
            ValidationStage.DISCOVERING,
            ValidationStage.ANALYZING,
            ValidationStage.DEPLOYING,
            ValidationStage.TESTING,
        ]
        
        for stage in stages:
            session._transition_to_stage(stage)
            assert session.summary.current_stage == stage
            
            session._complete_stage(stage)
            assert stage in session.summary.stages_completed
    
    def test_stage_completion_tracking(self, tmp_path):
        """Test that completed stages are tracked correctly"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Complete multiple stages
        session._transition_to_stage(ValidationStage.DISCOVERING)
        session._complete_stage(ValidationStage.DISCOVERING)
        
        session._transition_to_stage(ValidationStage.ANALYZING)
        session._complete_stage(ValidationStage.ANALYZING)
        
        # Verify all completed stages are tracked
        assert len(session.summary.stages_completed) == 2
        assert ValidationStage.DISCOVERING in session.summary.stages_completed
        assert ValidationStage.ANALYZING in session.summary.stages_completed
        
        # Current stage should be the last transitioned
        assert session.summary.current_stage == ValidationStage.ANALYZING
    
    def test_progress_percentage_calculation(self, tmp_path):
        """Test progress percentage calculation"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # No stages complete = 0%
        progress = session.get_progress()
        assert progress["progress_percentage"] == 0.0
        
        # Complete 1 of 6 stages = ~16.7%
        session._transition_to_stage(ValidationStage.DISCOVERING)
        session._complete_stage(ValidationStage.DISCOVERING)
        progress = session.get_progress()
        assert progress["progress_percentage"] == pytest.approx(16.67, rel=0.1)
        
        # Complete 3 of 6 stages = 50%
        session._transition_to_stage(ValidationStage.ANALYZING)
        session._complete_stage(ValidationStage.ANALYZING)
        session._transition_to_stage(ValidationStage.DEPLOYING)
        session._complete_stage(ValidationStage.DEPLOYING)
        progress = session.get_progress()
        assert progress["progress_percentage"] == 50.0
    
    @pytest.mark.asyncio
    async def test_run_discovery_stage(self, tmp_path):
        """Test discovery stage execution"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Create mock project
        mock_project = ProjectInfo(
            project_id="test-123",
            name="test-project",
            path=tmp_path,
            source_code_path=tmp_path / "src",
            bicep_templates_path=tmp_path / "bicep-templates",
            framework="dotnet",
            last_modified=datetime.now().timestamp(),
        )
        
        # Mock ProjectDiscovery
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_instance = MagicMock()
            mock_instance.discover_projects.return_value = [mock_project]
            mock_discovery_class.return_value = mock_instance
            
            await session._run_discovery_stage()
        
        # Verify stage progression
        assert ValidationStage.DISCOVERING in session.summary.stages_completed
        assert session.summary.projects_discovered == 1
        assert len(session.discovered_projects) == 1
    
    @pytest.mark.asyncio
    async def test_run_discovery_stage_no_projects(self, tmp_path):
        """Test discovery stage with no projects found"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Mock ProjectDiscovery to return empty list
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_instance = MagicMock()
            mock_instance.discover_projects.return_value = []
            mock_discovery_class.return_value = mock_instance
            
            with pytest.raises(ValueError, match="No projects discovered"):
                await session._run_discovery_stage()
    
    @pytest.mark.asyncio
    async def test_run_analysis_stage(self, tmp_path):
        """Test analysis stage execution"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Setup discovered project
        mock_project = ProjectInfo(
            project_id="test-456",
            name="test-project",
            path=tmp_path,
            source_code_path=tmp_path / "src",
            bicep_templates_path=tmp_path / "bicep-templates",
            framework="dotnet",
            last_modified=datetime.now().timestamp(),
        )
        session.discovered_projects = [mock_project]
        
        # Mock ConfigAnalyzer
        mock_analysis = MagicMock()
        mock_analysis.app_settings = [{"key": "value"}]
        
        with patch('specify_cli.validation.validation_session.ConfigAnalyzer') as mock_analyzer_class:
            mock_instance = MagicMock()
            mock_instance.analyze_project.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_instance
            
            await session._run_analysis_stage()
        
        # Verify stage progression
        assert ValidationStage.ANALYZING in session.summary.stages_completed
        assert session.summary.projects_analyzed == 1
    
    @pytest.mark.asyncio
    async def test_summary_metrics_tracking(self, tmp_path):
        """Test that summary tracks all metrics correctly"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Simulate some results
        session.summary.projects_discovered = 2
        session.summary.projects_analyzed = 2
        session.summary.resources_deployed = 5
        session.summary.secrets_stored = 3
        session.summary.endpoints_discovered = 10
        session.summary.endpoints_tested = 8
        session.summary.tests_passed = 6
        session.summary.tests_failed = 2
        session.summary.fix_attempts = 1
        session.summary.fixes_successful = 1
        
        # Verify metrics
        assert session.summary.projects_discovered == 2
        assert session.summary.resources_deployed == 5
        assert session.summary.endpoints_tested == 8
        assert session.summary.tests_passed == 6
        assert session.summary.fix_attempts == 1
    
    @pytest.mark.asyncio
    async def test_run_with_exception(self, tmp_path):
        """Test that exceptions are handled and recorded"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Mock discovery to raise exception
        with patch('specify_cli.validation.validation_session.ProjectDiscovery') as mock_discovery_class:
            mock_instance = MagicMock()
            mock_instance.discover_projects.side_effect = RuntimeError("Test error")
            mock_discovery_class.return_value = mock_instance
            
            result = await session.run()
        
        # Verify error handling
        assert result.success == False
        assert result.error_message == "Test error"
        assert result.current_stage == ValidationStage.FAILED
        assert result.end_time is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0
    
    @pytest.mark.asyncio
    async def test_session_duration_tracking(self, tmp_path):
        """Test that session duration is tracked"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        # Record start time
        start_time = session.summary.start_time
        
        # Mock a quick success path
        with patch.object(session, '_run_discovery_stage', new_callable=AsyncMock):
            with patch.object(session, '_run_analysis_stage', new_callable=AsyncMock):
                with patch.object(session, '_run_deployment_stage', new_callable=AsyncMock):
                    with patch.object(session, '_run_testing_and_fixing_stages', new_callable=AsyncMock):
                        result = await session.run()
        
        # Verify duration tracking
        assert result.end_time is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
        assert result.end_time >= start_time
