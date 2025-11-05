"""
Unit tests for learnings database conflict resolution.

Tests the conflict resolution logic that prioritizes entries based on:
1. Category priority (Security/Compliance override others)
2. Timestamp (most recent wins within same priority)
3. Position (first in file wins for identical timestamps)
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from specify_cli.utils.learnings_loader import (
    LearningEntry,
    resolve_conflicts,
    _get_category_priority,
    _entries_conflict,
    HIGH_PRIORITY_CATEGORIES,
)


class TestCategoryPriority:
    """Test category priority levels."""
    
    def test_high_priority_security(self):
        """Security category should have HIGH priority (0)."""
        assert _get_category_priority("Security") == 0
    
    def test_high_priority_compliance(self):
        """Compliance category should have HIGH priority (0)."""
        assert _get_category_priority("Compliance") == 0
    
    def test_normal_priority_networking(self):
        """Networking category should have NORMAL priority (1)."""
        assert _get_category_priority("Networking") == 1
    
    def test_normal_priority_configuration(self):
        """Configuration category should have NORMAL priority (1)."""
        assert _get_category_priority("Configuration") == 1
    
    def test_high_priority_categories_constant(self):
        """HIGH_PRIORITY_CATEGORIES should contain Security and Compliance."""
        assert "Security" in HIGH_PRIORITY_CATEGORIES
        assert "Compliance" in HIGH_PRIORITY_CATEGORIES
        assert len(HIGH_PRIORITY_CATEGORIES) == 2


class TestEntriesConflict:
    """Test conflict detection between entries."""
    
    def test_different_context_no_conflict(self):
        """Entries with different contexts don't conflict."""
        entry1 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Issue 1",
            solution="Enable encryption",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="KeyVault",
            issue="Issue 2",
            solution="Disable public access",
            raw_text="test2",
        )
        assert not _entries_conflict(entry1, entry2)
    
    def test_same_context_contradictory_enable_disable(self):
        """Entries with enable/disable contradiction should conflict."""
        entry1 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Issue 1",
            solution="Enable public network access for testing",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Issue 2",
            solution="Disable public network access for security",
            raw_text="test2",
        )
        assert _entries_conflict(entry1, entry2)
    
    def test_same_context_contradictory_use_avoid(self):
        """Entries with use/avoid contradiction should conflict."""
        entry1 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Networking",
            context="FrontDoor",
            issue="Issue 1",
            solution="Use Azure Front Door for global distribution",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="FrontDoor",
            issue="Issue 2",
            solution="Avoid Azure Front Door unless explicitly requested",
            raw_text="test2",
        )
        assert _entries_conflict(entry1, entry2)
    
    def test_same_context_no_contradiction(self):
        """Entries with same context but no contradiction don't conflict."""
        entry1 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Issue 1",
            solution="Use TLS 1.2 or higher",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Issue 2",
            solution="Configure customer-managed keys",
            raw_text="test2",
        )
        assert not _entries_conflict(entry1, entry2)
    
    def test_case_insensitive_context_matching(self):
        """Context matching should be case-insensitive."""
        entry1 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="StorageAccount",
            issue="Public network access",
            solution="Enable public network access for testing",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime.now(timezone.utc),
            category="Security",
            context="storageaccount",
            issue="Public network access",
            solution="Disable public network access for security",
            raw_text="test2",
        )
        assert _entries_conflict(entry1, entry2)


class TestConflictResolution:
    """Test conflict resolution logic."""
    
    def test_no_conflicts_all_returned(self):
        """When no conflicts exist, all entries should be returned."""
        entries = [
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 10, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="Issue 1",
                solution="Disable public access",
                raw_text="test1",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 11, 0, 0, tzinfo=timezone.utc),
                category="Networking",
                context="VNet",
                issue="Issue 2",
                solution="Use /24 subnets",
                raw_text="test2",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 12, 0, 0, tzinfo=timezone.utc),
                category="Configuration",
                context="AppService",
                issue="Issue 3",
                solution="Set minimum TLS version",
                raw_text="test3",
            ),
        ]
        resolved = resolve_conflicts(entries)
        assert len(resolved) == 3
    
    def test_empty_list_returns_empty(self):
        """Empty input should return empty output."""
        assert resolve_conflicts([]) == []
    
    def test_security_overrides_networking_same_context(self):
        """Security category should override Networking for same context."""
        older_security = LearningEntry(
            timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
            category="Security",
            context="FrontDoor",
            issue="Security concern",
            solution="Avoid Azure Front Door unless explicitly requested",
            raw_text="test1",
        )
        newer_networking = LearningEntry(
            timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
            category="Networking",
            context="FrontDoor",
            issue="Performance need",
            solution="Use Azure Front Door for global distribution",
            raw_text="test2",
        )
        
        # Security should win even though it's older
        resolved = resolve_conflicts([older_security, newer_networking])
        assert len(resolved) == 1
        assert resolved[0].category == "Security"
        assert "Avoid" in resolved[0].solution
    
    def test_compliance_overrides_configuration_same_context(self):
        """Compliance category should override Configuration for same context."""
        older_compliance = LearningEntry(
            timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
            category="Compliance",
            context="StorageAccount",
            issue="Data retention policy",
            solution="Must retain data for 7 years per compliance",
            raw_text="test1",
        )
        newer_config = LearningEntry(
            timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
            category="Configuration",
            context="StorageAccount",
            issue="Data retention setting",
            solution="Optional retention - should not retain for cost savings",
            raw_text="test2",
        )
        
        # Compliance should win even though it's older
        resolved = resolve_conflicts([older_compliance, newer_config])
        assert len(resolved) == 1
        assert resolved[0].category == "Compliance"
        assert "Must retain" in resolved[0].solution
    
    def test_most_recent_wins_within_same_priority(self):
        """Within same priority tier, most recent timestamp wins."""
        older_networking = LearningEntry(
            timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
            category="Networking",
            context="VNet",
            issue="Old guidance",
            solution="Use /16 subnets for flexibility",
            raw_text="test1",
        )
        newer_networking = LearningEntry(
            timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
            category="Networking",
            context="VNet",
            issue="Updated guidance",
            solution="Avoid /16 subnets, use /24 for better management",
            raw_text="test2",
        )
        
        # Newer networking entry should win
        resolved = resolve_conflicts([older_networking, newer_networking])
        assert len(resolved) == 1
        assert resolved[0].timestamp == newer_networking.timestamp
        assert "Avoid /16" in resolved[0].solution
    
    def test_multiple_conflicts_resolved_correctly(self):
        """Multiple conflicts should all be resolved according to rules."""
        entries = [
            # Conflict 1: Security vs Networking (Security wins)
            LearningEntry(
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="FrontDoor",
                issue="Security",
                solution="Avoid Front Door",
                raw_text="test1",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
                category="Networking",
                context="FrontDoor",
                issue="Performance",
                solution="Use Front Door",
                raw_text="test2",
            ),
            # Conflict 2: Configuration old vs new (newer wins)
            LearningEntry(
                timestamp=datetime(2025, 10, 20, 10, 0, 0, tzinfo=timezone.utc),
                category="Configuration",
                context="AppService",
                issue="Old API",
                solution="Use API version 2020-01-01",
                raw_text="test3",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 15, 0, 0, tzinfo=timezone.utc),
                category="Configuration",
                context="AppService",
                issue="New API",
                solution="Avoid API version 2020-01-01, use 2023-01-01",
                raw_text="test4",
            ),
            # No conflict: Different context
            LearningEntry(
                timestamp=datetime(2025, 10, 25, 10, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="Encryption",
                solution="Enable encryption at rest",
                raw_text="test5",
            ),
        ]
        
        resolved = resolve_conflicts(entries)
        
        # Should have 3 entries: Security FrontDoor, newer Configuration, StorageAccount
        assert len(resolved) == 3
        
        # Check FrontDoor conflict resolution
        frontdoor_entries = [e for e in resolved if e.context == "FrontDoor"]
        assert len(frontdoor_entries) == 1
        assert frontdoor_entries[0].category == "Security"
        
        # Check AppService conflict resolution
        appservice_entries = [e for e in resolved if e.context == "AppService"]
        assert len(appservice_entries) == 1
        assert "2023-01-01" in appservice_entries[0].solution
        
        # Check StorageAccount (no conflict)
        storage_entries = [e for e in resolved if e.context == "StorageAccount"]
        assert len(storage_entries) == 1
    
    def test_identical_timestamps_first_wins(self):
        """When timestamps are identical, first entry in file wins."""
        entry1 = LearningEntry(
            timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
            category="Configuration",
            context="AppService",
            issue="API version selection",
            solution="Use API version 2023-01-01",
            raw_text="test1",
        )
        entry2 = LearningEntry(
            timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
            category="Configuration",
            context="AppService",
            issue="API version recommendation",
            solution="Avoid API version 2023-01-01, use 2024-01-01 instead",
            raw_text="test2",
        )
        
        # First entry should win (order in list represents file order)
        resolved = resolve_conflicts([entry1, entry2])
        assert len(resolved) == 1
        assert "2023-01-01" in resolved[0].solution and "Avoid" not in resolved[0].solution
    
    def test_non_conflicting_entries_same_context(self):
        """Non-conflicting entries with same context should all be kept."""
        entries = [
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 10, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="Public access",
                solution="Disable public network access",
                raw_text="test1",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 11, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="Encryption",
                solution="Enable encryption at rest",
                raw_text="test2",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 12, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="TLS version",
                solution="Set minimum TLS version to 1.2",
                raw_text="test3",
            ),
        ]
        
        # All should be kept (no contradictions)
        resolved = resolve_conflicts(entries)
        assert len(resolved) == 3
    
    def test_output_sorted_by_timestamp_newest_first(self):
        """Resolved entries should be sorted by timestamp (newest first)."""
        entries = [
            LearningEntry(
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                category="Security",
                context="StorageAccount",
                issue="Issue 1",
                solution="Solution 1",
                raw_text="test1",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 31, 14, 0, 0, tzinfo=timezone.utc),
                category="Networking",
                context="VNet",
                issue="Issue 2",
                solution="Solution 2",
                raw_text="test2",
            ),
            LearningEntry(
                timestamp=datetime(2025, 10, 20, 12, 0, 0, tzinfo=timezone.utc),
                category="Configuration",
                context="AppService",
                issue="Issue 3",
                solution="Solution 3",
                raw_text="test3",
            ),
        ]
        
        resolved = resolve_conflicts(entries)
        
        # Should be sorted newest to oldest
        assert resolved[0].timestamp.day == 31  # Oct 31
        assert resolved[1].timestamp.day == 20  # Oct 20
        assert resolved[2].timestamp.day == 15  # Oct 15


class TestConflictResolutionPerformance:
    """Test performance characteristics of conflict resolution."""
    
    def test_performance_with_250_entries(self):
        """Conflict resolution should complete in <50ms for 250 entries."""
        import time
        
        # Create 250 entries with some conflicts
        entries = []
        contexts = ["Context" + str(i % 50) for i in range(250)]  # 50 unique contexts
        
        for i in range(250):
            entry = LearningEntry(
                timestamp=datetime(2025, 10, i % 30 + 1, 10, 0, 0, tzinfo=timezone.utc),
                category=["Security", "Networking", "Configuration"][i % 3],
                context=contexts[i],
                issue=f"Issue {i}",
                solution=f"Solution {i} with {'enable' if i % 2 == 0 else 'disable'}",
                raw_text=f"test{i}",
            )
            entries.append(entry)
        
        # Measure resolution time
        start = time.time()
        resolved = resolve_conflicts(entries)
        elapsed = time.time() - start
        
        # Should complete in <50ms
        assert elapsed < 0.050, f"Resolution took {elapsed:.3f}s (target: <0.050s)"
        
        # Should return valid results
        assert len(resolved) > 0
        assert len(resolved) <= 250


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
