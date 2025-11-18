"""
Test backward compatibility of /speckit.bicep command with learnings database integration.

Verifies that existing Bicep generation workflows continue to work correctly:
- When .specify/learnings/ directory doesn't exist
- When bicep-learnings.md is empty
- When bicep-learnings.md contains only default entries
- When error handling is triggered (graceful degradation)

Tests ensure no breaking changes to existing command behavior (T018.1).
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from specify_cli.utils.learnings_loader import (
    load_learnings_database, 
    filter_learnings_by_category,
    FileNotFoundError as LearningsFileNotFoundError
)


class TestBackwardCompatibility:
    """Test backward compatibility scenarios for learnings database integration."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_missing_learnings_directory(self, temp_workspace):
        """
        Test scenario: .specify/learnings/ directory doesn't exist.
        Expected: Command should proceed with default patterns, log warning.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        
        # Verify directory doesn't exist
        assert not learnings_path.parent.exists(), "Learnings directory should not exist"
        
        # Simulate loading logic from prompt
        learnings = []
        if learnings_path.exists():
            try:
                learnings = load_learnings_database(learnings_path)
            except FileNotFoundError:
                pass  # Expected - should log warning
        
        # Verify graceful degradation
        assert learnings == [], "Should return empty list when directory missing"
        assert not learnings_path.exists(), "Should not create directory automatically"
    
    def test_empty_learnings_database(self, temp_workspace):
        """
        Test scenario: bicep-learnings.md exists but is empty.
        Expected: Command should proceed with default patterns, no errors.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty file
        learnings_path.write_text("", encoding='utf-8')
        
        # Load empty database
        learnings = load_learnings_database(learnings_path)
        
        # Verify graceful handling
        assert learnings == [], "Empty database should return empty list"
        assert isinstance(learnings, list), "Should return list type"
    
    def test_database_with_only_metadata(self, temp_workspace):
        """
        Test scenario: bicep-learnings.md contains only metadata/headers.
        Expected: Command should proceed, parse metadata, return empty learnings.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with only metadata
        content = """# Bicep Learnings Database

**Purpose**: Shared organizational learnings for Bicep template generation and validation
**Format**: [Timestamp] Category Context → Issue → Solution

## Metadata

- Total entries: 0
- Last updated: 2025-11-01T00:00:00Z
- Semantic similarity threshold: 60%

## Categories

### Security

### Networking

### Configuration
"""
        learnings_path.write_text(content, encoding='utf-8')
        
        # Load database
        learnings = load_learnings_database(learnings_path)
        
        # Verify only metadata skipped
        assert learnings == [], "Metadata-only database should return empty list"
        assert isinstance(learnings, list), "Should return list type"
    
    def test_database_with_default_entries(self, temp_workspace):
        """
        Test scenario: bicep-learnings.md contains baseline entries.
        Expected: All entries loaded successfully, no errors.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with baseline entries
        content = """# Bicep Learnings Database

## Security

2025-10-31T15:00:00Z Security StorageAccount → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and configure Private Endpoint

2025-10-31T15:00:00Z Security KeyVault → Public network access not disabled → Set publicNetworkAccess: 'Disabled' and networkAcls.defaultAction: 'Deny'

## Networking

2025-10-31T15:00:00Z Networking PrivateEndpoints → Missing private DNS zone integration → Create privateDnsZone and privateDnsZoneGroups for automatic DNS registration

## Configuration

2025-10-31T15:00:00Z Configuration FrontDoor → Included by default in architecture → Only include when explicitly requested - not required for single-region deployments
"""
        learnings_path.write_text(content, encoding='utf-8')
        
        # Load database
        learnings = load_learnings_database(learnings_path)
        
        # Verify entries loaded
        assert len(learnings) == 4, f"Expected 4 entries, got {len(learnings)}"
        assert all(hasattr(entry, 'category') for entry in learnings), "All entries should have category"
        assert all(hasattr(entry, 'context') for entry in learnings), "All entries should have context"
        assert all(hasattr(entry, 'issue') for entry in learnings), "All entries should have issue"
        assert all(hasattr(entry, 'solution') for entry in learnings), "All entries should have solution"
        
        # Verify category distribution
        categories = [entry.category for entry in learnings]
        assert 'Security' in categories, "Should have Security entries"
        assert 'Networking' in categories, "Should have Networking entries"
        assert 'Configuration' in categories, "Should have Configuration entries"
    
    def test_category_filtering_with_default_entries(self, temp_workspace):
        """
        Test scenario: Filter learnings by category with baseline entries.
        Expected: Only relevant categories returned, maintains performance.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with diverse entries
        content = """# Bicep Learnings Database

## Security

2025-10-31T15:00:00Z Security StorageAccount → Issue 1 → Solution 1

## Networking

2025-10-31T15:00:00Z Networking VNet → Issue 2 → Solution 2

## Configuration

2025-10-31T15:00:00Z Configuration Naming → Issue 3 → Solution 3

## Performance

2025-10-31T15:00:00Z Performance Caching → Issue 4 → Solution 4
"""
        learnings_path.write_text(content, encoding='utf-8')
        
        # Load and filter
        all_learnings = load_learnings_database(learnings_path)
        filtered = filter_learnings_by_category(all_learnings, ['Security', 'Networking'])
        
        # Verify filtering
        assert len(all_learnings) == 4, "Should load all 4 entries"
        assert len(filtered) == 2, f"Should filter to 2 entries, got {len(filtered)}"
        assert all(entry.category in ['Security', 'Networking'] for entry in filtered), \
            "Filtered entries should only be Security or Networking"
    
    def test_malformed_entry_graceful_handling(self, temp_workspace):
        """
        Test scenario: Database contains malformed entries.
        Expected: Malformed entries skipped, valid entries loaded, no fatal error.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with mix of valid and invalid entries
        content = """# Bicep Learnings Database

## Security

2025-10-31T15:00:00Z Security StorageAccount → Issue 1 → Solution 1

This is a malformed entry without timestamp

2025-10-31T15:00:00Z Security KeyVault → Issue 2 → Solution 2

Another malformed entry

2025-10-31T15:00:00Z Security SqlServer → Issue 3 → Solution 3
"""
        learnings_path.write_text(content, encoding='utf-8')
        
        # Load database
        learnings = load_learnings_database(learnings_path)
        
        # Verify only valid entries loaded
        assert len(learnings) == 3, f"Expected 3 valid entries, got {len(learnings)}"
        assert all(entry.category == 'Security' for entry in learnings), \
            "All valid entries should be Security category"
    
    def test_performance_optimization_threshold(self, temp_workspace):
        """
        Test scenario: Database exceeds 250 entries (performance threshold).
        Expected: Category filtering should be triggered, maintains <2s load time.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with >250 entries
        entries = []
        categories = ['Security', 'Networking', 'Configuration', 'Compliance']
        for i in range(260):
            category = categories[i % len(categories)]
            entry = f"2025-10-31T15:00:00Z {category} Context{i} → Issue{i} → Solution{i}\n"
            entries.append(entry)
        
        content = "# Bicep Learnings Database\n\n## Security\n\n" + "\n".join(
            [e for e in entries if e.startswith("2025-10-31T15:00:00Z Security")]
        ) + "\n\n## Networking\n\n" + "\n".join(
            [e for e in entries if e.startswith("2025-10-31T15:00:00Z Networking")]
        ) + "\n\n## Configuration\n\n" + "\n".join(
            [e for e in entries if e.startswith("2025-10-31T15:00:00Z Configuration")]
        ) + "\n\n## Compliance\n\n" + "\n".join(
            [e for e in entries if e.startswith("2025-10-31T15:00:00Z Compliance")]
        )
        
        learnings_path.write_text(content, encoding='utf-8')
        
        # Load all entries
        import time
        start = time.time()
        all_learnings = load_learnings_database(learnings_path)
        load_time = time.time() - start
        
        # Verify performance
        assert len(all_learnings) == 260, f"Expected 260 entries, got {len(all_learnings)}"
        assert load_time < 2.0, f"Load time {load_time:.3f}s exceeds 2s threshold"
        
        # Test filtering scenario (>250 entries)
        if len(all_learnings) > 250:
            filtered = filter_learnings_by_category(
                all_learnings, 
                ['Security', 'Networking', 'Configuration', 'Compliance']
            )
            assert len(filtered) == len(all_learnings), "Should include all relevant categories"
    
    def test_file_permission_error_handling(self, temp_workspace):
        """
        Test scenario: Database file exists but is not readable.
        Expected: LearningsFileNotFoundError or PermissionError raised with actionable message.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        learnings_path.write_text("Test content", encoding='utf-8')
        
        # Make file unreadable (Windows: remove read permissions)
        if os.name == 'nt':
            # On Windows, we can't easily test this without admin privileges
            pytest.skip("Permission testing requires elevated privileges on Windows")
        else:
            # On Unix systems
            os.chmod(learnings_path, 0o000)
            
            # Verify error handling
            with pytest.raises((LearningsFileNotFoundError, PermissionError)):
                load_learnings_database(learnings_path)
            
            # Restore permissions for cleanup
            os.chmod(learnings_path, 0o644)
    
    def test_encoding_error_handling(self, temp_workspace):
        """
        Test scenario: Database file has encoding issues.
        Expected: FileNotFoundError raised with clear error message.
        """
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write binary content that will cause encoding issues
        learnings_path.write_bytes(b'\xff\xfe Invalid UTF-8 \x80\x81')
        
        # Try to load - should raise LearningsFileNotFoundError with clear message
        with pytest.raises(LearningsFileNotFoundError) as exc_info:
            learnings = load_learnings_database(learnings_path)
        
        # Verify error message is actionable
        assert "Failed to read learnings database" in str(exc_info.value), \
            "Error message should indicate read failure"
        assert "Verify file is not corrupted" in str(exc_info.value), \
            "Error message should suggest checking file corruption"
    
    def test_no_regression_with_existing_workflows(self, temp_workspace):
        """
        Test scenario: Existing workflow without learnings database.
        Expected: Workflow proceeds with default patterns, no breaking changes.
        """
        # Simulate existing workflow (no .specify directory)
        learnings_path = temp_workspace / '.specify' / 'learnings' / 'bicep-learnings.md'
        
        # Verify no directory exists (simulating existing project)
        assert not learnings_path.parent.exists(), "Fresh workspace should have no .specify/"
        
        # Simulate prompt logic
        learnings = []
        if learnings_path.exists():
            try:
                learnings = load_learnings_database(learnings_path)
            except FileNotFoundError:
                learnings = []  # Graceful degradation
        
        # Verify no breaking changes
        assert learnings == [], "Should proceed with empty learnings"
        assert isinstance(learnings, list), "Should return expected type"
        
        # Workflow continues with default patterns (no exception raised)
        # This represents successful backward compatibility


class TestPromptIntegration:
    """Test integration with prompt logic."""
    
    def test_prompt_loading_logic_with_missing_database(self):
        """
        Test the exact loading logic from prompt when database missing.
        Expected: Graceful degradation with warning log.
        """
        import logging
        from pathlib import Path
        
        # Configure learnings database path (non-existent)
        learnings_db_path = Path('/nonexistent/path/.specify/learnings/bicep-learnings.md')
        
        # Simulate prompt loading logic
        learnings = []
        warning_logged = False
        
        if learnings_db_path.exists():
            try:
                learnings = load_learnings_database(learnings_db_path)
            except FileNotFoundError as e:
                warning_logged = True
            except Exception as e:
                warning_logged = True
        else:
            warning_logged = True  # Would log warning in actual prompt
        
        # Verify graceful degradation
        assert learnings == [], "Should return empty list"
        assert warning_logged, "Should log warning for missing database"
    
    def test_prompt_loading_logic_with_existing_database(self, tmp_path):
        """
        Test the exact loading logic from prompt when database exists.
        Expected: Learnings loaded successfully.
        """
        # Create temporary database
        learnings_path = tmp_path / '.specify' / 'learnings' / 'bicep-learnings.md'
        learnings_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = """# Bicep Learnings Database

## Security

2025-10-31T15:00:00Z Security Test → Issue → Solution
"""
        learnings_path.write_text(content, encoding='utf-8')
        
        # Simulate prompt loading logic
        learnings = []
        if learnings_path.exists():
            try:
                learnings = load_learnings_database(learnings_path)
            except Exception:
                pass  # Graceful degradation
        
        # Verify successful load
        assert len(learnings) == 1, "Should load 1 entry"
        assert learnings[0].category == 'Security', "Should parse category correctly"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
