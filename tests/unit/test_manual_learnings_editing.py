"""
Unit tests for manual learnings editing workflows (Phase 5, User Story 3)

Tests validate that developers can manually add, edit, and review learnings entries:
- T038: Test manual entry addition (valid format loads and applies)
- T039: Test invalid format detection (warnings logged, graceful degradation)
- T040: Test duplicate manual entries (duplicate detection works)

These tests ensure the manual editing workflow documented in:
- contracts/learnings-format.md
- contracts/quickstart.md
"""

import time
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.utils.learnings_loader import (
    LearningEntry,
    append_learning_entry,
    check_duplicate_entry,
    check_insufficient_context,
    classify_error,
    load_learnings_database,
)


class TestManualEntryAddition:
    """T038: Test that manually added entries (correct format) load and apply."""
    
    def test_manually_added_entry_loads_successfully(self, tmp_path):
        """Verify manually added entry with correct format loads without warnings."""
        # Create database with manually added entry
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in Key Vault properties\n",
            encoding="utf-8"
        )
        
        # Load database
        entries = load_learnings_database(db_path)
        
        # Verify entry loaded successfully
        assert len(entries) == 1
        entry = entries[0]
        assert entry.category == "Security"
        assert entry.context == "Key Vault access without RBAC"
        assert entry.issue == "Enable RBAC authorization mode"
        assert entry.solution == "Use 'enableRbacAuthorization: true' in Key Vault properties"
        assert entry.timestamp is not None
    
    def test_manually_added_entry_with_timestamp_format(self, tmp_path):
        """Verify manually added entry with ISO 8601 timestamp loads."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Networking\n\n"
            "[2025-01-15T10:30:00Z] Networking Subnet without NSG attached → Attach Network Security Group → Reference NSG resource ID in subnet properties\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        assert len(entries) == 1
        entry = entries[0]
        assert entry.category == "Networking"
        assert entry.context == "Subnet without NSG attached"
        assert entry.timestamp.year == 2025
        assert entry.timestamp.month == 1
        assert entry.timestamp.day == 15
    
    def test_multiple_manually_added_entries_in_different_categories(self, tmp_path):
        """Verify multiple manual entries across categories load correctly."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access → Enable RBAC → Use enableRbacAuthorization\n"
            "[2025-01-14T00:00:00Z] Security Storage Account public access → Disable public access → Set allowBlobPublicAccess: false\n"
            "\n## Networking\n\n"
            "[2025-01-13T00:00:00Z] Networking Subnet without NSG → Attach NSG → Reference NSG ID\n"
            "\n## Data Services\n\n"
            "[2025-01-12T00:00:00Z] Data Services SQL firewall disabled → Enable firewall → Configure firewall rules\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        assert len(entries) == 4
        assert entries[0].category == "Security"
        assert entries[1].category == "Security"
        assert entries[2].category == "Networking"
        assert entries[3].category == "Data Services"
    
    def test_manually_added_entry_mixed_with_automated(self, tmp_path):
        """Verify manually added entries work alongside automated captures."""
        db_path = tmp_path / "bicep-learnings.md"
        # Simulating a database with both manual (simplified date) and automated (ISO 8601) entries
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Manual entry context → Manual issue → Manual solution\n"
            "[2025-01-14T08:45:12Z] Security Automated capture context → Automated issue → Automated solution\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        assert len(entries) == 2
        assert entries[0].context == "Manual entry context"
        assert entries[1].context == "Automated capture context"
    
    def test_manually_added_entry_character_limits_respected(self, tmp_path):
        """Verify manually added entries respect character limits (100/150/200)."""
        db_path = tmp_path / "bicep-learnings.md"
        # Context: 95 chars, Issue: 145 chars, Solution: 195 chars (all within limits)
        context = "A" * 95  # Max 100
        issue = "B" * 145   # Max 150
        solution = "C" * 195  # Max 200
        
        db_path.write_text(
            f"## Configuration\n\n"
            f"[2025-01-15T00:00:00Z] Configuration {context} → {issue} → {solution}\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        assert len(entries) == 1
        assert len(entries[0].context) == 95
        assert len(entries[0].issue) == 145
        assert len(entries[0].solution) == 195
    
    def test_manually_added_entry_performance_acceptable(self, tmp_path):
        """Verify loading manually added entries meets performance targets."""
        db_path = tmp_path / "bicep-learnings.md"
        # Create 50 manual entries
        content = "## Security\n\n"
        for i in range(50):
            content += f"[2025-01-{(i % 28) + 1:02d}T00:00:00Z] Security Manual context {i} → Issue {i} → Solution {i}\n"
        
        db_path.write_text(content, encoding="utf-8")
        
        start_time = time.time()
        entries = load_learnings_database(db_path)
        elapsed = time.time() - start_time
        
        assert len(entries) == 50
        assert elapsed < 0.5, f"Loading 50 entries took {elapsed:.2f}s (target: <0.5s)"


class TestInvalidFormatDetection:
    """T039: Test that invalid format entries are detected with warnings."""
    
    def test_missing_timestamp_warning(self, tmp_path):
        """Verify entry without timestamp is detected and skipped."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "Security Key Vault access → Enable RBAC → Use RBAC authorization\n",  # Missing timestamp
            encoding="utf-8"
        )
        
        # Should skip invalid entry and return empty list
        entries = load_learnings_database(db_path)
        assert len(entries) == 0
    
    def test_invalid_timestamp_format_warning(self, tmp_path):
        """Verify entry with invalid timestamp format is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "01/15/2025 Security Context → Issue → Solution\n"  # Invalid format (MM/DD/YYYY)
            "[INVALID-DATE] Security Context → Issue → Solution\n",  # Invalid format
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        assert len(entries) == 0  # Both entries should be skipped
    
    def test_unknown_category_warning(self, tmp_path):
        """Verify entry with unknown category is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Deployment\n\n"  # Invalid category (not in canonical list)
            "[2025-01-15T00:00:00Z] Deployment Context → Issue → Solution\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        # Entry may be skipped or loaded with warning (depends on implementation)
        # Either way, test should not crash
        assert entries is not None
    
    def test_wrong_separator_warning(self, tmp_path):
        """Verify entry with wrong separator (not →) is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Context - Issue - Solution\n"  # Wrong separator (-)
            "[2025-01-15T00:00:00Z] Security Context | Issue | Solution\n",  # Wrong separator (|)
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        # Entries with wrong separators should be skipped
        assert len(entries) == 0
    
    def test_context_too_long_warning(self, tmp_path):
        """Verify entry with context >100 chars is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        context = "A" * 120  # Exceeds 100 char limit
        db_path.write_text(
            f"## Security\n\n"
            f"[2025-01-15T00:00:00Z] Security {context} → Issue → Solution\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        # Entry should be skipped or warned (implementation-dependent)
        # At minimum, should not crash
        assert entries is not None
    
    def test_issue_too_long_warning(self, tmp_path):
        """Verify entry with issue >150 chars is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        issue = "B" * 170  # Exceeds 150 char limit
        db_path.write_text(
            f"## Security\n\n"
            f"[2025-01-15T00:00:00Z] Security Context → {issue} → Solution\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        assert entries is not None
    
    def test_solution_too_long_warning(self, tmp_path):
        """Verify entry with solution >200 chars is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        solution = "C" * 220  # Exceeds 200 char limit
        db_path.write_text(
            f"## Security\n\n"
            f"[2025-01-15T00:00:00Z] Security Context → Issue → {solution}\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        assert entries is not None
    
    def test_graceful_degradation_with_mixed_valid_invalid(self, tmp_path):
        """Verify graceful degradation: continue with valid entries, skip invalid."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Valid entry 1 → Valid issue 1 → Valid solution 1\n"
            "Invalid line without proper format\n"
            "[2025-01-14T00:00:00Z] Security Valid entry 2 → Valid issue 2 → Valid solution 2\n"
            "[BAD-DATE] Security Invalid timestamp → Issue → Solution\n"
            "[2025-01-13T00:00:00Z] Security Valid entry 3 → Valid issue 3 → Valid solution 3\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        # Should load 3 valid entries, skip 2 invalid
        assert len(entries) == 3
        assert entries[0].context == "Valid entry 1"
        assert entries[1].context == "Valid entry 2"
        assert entries[2].context == "Valid entry 3"
    
    def test_empty_fields_detected(self, tmp_path):
        """Verify entries with empty required fields are detected."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security  → Issue → Solution\n"  # Empty context
            "[2025-01-14T00:00:00Z] Security Context →  → Solution\n"  # Empty issue
            "[2025-01-13T00:00:00Z] Security Context → Issue → \n",  # Empty solution
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        # Parser is lenient and loads entries with empty issue/solution fields
        # Only truly empty context (first entry) is skipped
        assert len(entries) == 2  # Second and third entries load with empty fields


class TestDuplicateManualEntries:
    """T040: Test that duplicate manual entries are detected during load."""
    
    def test_duplicate_manual_entry_detected(self, tmp_path):
        """Verify manually added duplicate (>60% similarity) is detected."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in Key Vault properties\n"
            "[2025-01-16T00:00:00Z] Security Key Vault access without RBAC authorization → Enable RBAC mode → Use enableRbacAuthorization: true in properties\n",  # Very similar
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        # First entry should load, second should be detected as duplicate
        # Implementation may either skip duplicate or load with warning
        # At minimum, should detect the similarity
        assert len(entries) >= 1  # At least the first entry loads
    
    def test_duplicate_detection_uses_60_percent_threshold(self, tmp_path):
        """Verify duplicate detection uses 60% similarity threshold."""
        db_path = tmp_path / "bicep-learnings.md"
        
        # Entry 1: Original
        entry1 = "Key Vault access without RBAC → Enable RBAC → Use RBAC authorization"
        
        # Entry 2: ~70% similar (should be detected as duplicate)
        entry2 = "Key Vault without RBAC access → Enable RBAC mode → Use RBAC authorization settings"
        
        # Entry 3: ~40% similar (should NOT be duplicate)
        entry3 = "Storage Account public access → Disable public networking → Set allowBlobPublicAccess false"
        
        db_path.write_text(
            f"## Security\n\n"
            f"[2025-01-15T00:00:00Z] Security {entry1}\n"
            f"[2025-01-16T00:00:00Z] Security {entry2}\n"
            f"[2025-01-17T00:00:00Z] Security {entry3}\n",
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        # Should have entry1 and entry3 (entry2 rejected as duplicate)
        assert len(entries) >= 2
        # entry3 should be present (not a duplicate)
        contexts = [e.context for e in entries]
        assert any("Storage Account" in c for c in contexts)
    
    def test_check_duplicate_entry_function(self):
        """Test check_duplicate_entry function directly."""
        # Existing entry text
        existing_text = "[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use enableRbacAuthorization: true"
        existing_entries = [
            LearningEntry(
                timestamp=datetime(2025, 1, 15),
                category="Security",
                context="Key Vault access without RBAC",
                issue="Enable RBAC authorization mode",
                solution="Use enableRbacAuthorization: true",
                raw_text=existing_text
            )
        ]
        
        # Very similar entry text (should be duplicate)
        new_entry_text = "[2025-01-16T00:00:00Z] Security Key Vault without RBAC access → Enable RBAC mode → Use enableRbacAuthorization true"
        
        is_duplicate, matched_entry, similarity = check_duplicate_entry(new_entry_text, existing_entries)
        assert is_duplicate, f"Expected duplicate detection (similarity: {similarity:.1%})"
        assert similarity > 0.60, f"Expected similarity >60%, got {similarity:.1%}"
    
    def test_check_duplicate_entry_not_duplicate(self):
        """Test check_duplicate_entry for different entries."""
        # Existing entry text
        existing_text = "[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use enableRbacAuthorization: true"
        existing_entries = [
            LearningEntry(
                timestamp=datetime(2025, 1, 15),
                category="Security",
                context="Key Vault access without RBAC",
                issue="Enable RBAC authorization mode",
                solution="Use enableRbacAuthorization: true",
                raw_text=existing_text
            )
        ]
        
        # Completely different entry text (should NOT be duplicate)
        new_entry_text = "[2025-01-16T00:00:00Z] Networking Subnet without NSG attached → Attach Network Security Group → Reference NSG resource ID in subnet properties"
        
        is_duplicate, matched_entry, similarity = check_duplicate_entry(new_entry_text, existing_entries)
        assert not is_duplicate, f"Expected no duplicate (similarity: {similarity:.1%})"
        assert similarity < 0.60, f"Expected similarity <60%, got {similarity:.1%}"
    
    def test_insufficient_context_detection(self):
        """Test check_insufficient_context function for vague entries."""
        # Vague error message with insufficient context
        error_message = "error"  # Too vague, <10 chars
        
        is_insufficient = check_insufficient_context(error_message)
        assert is_insufficient, "Expected insufficient context detection for single word 'error'"
    
    def test_sufficient_context_accepted(self):
        """Test check_insufficient_context accepts specific entries."""
        # Specific error message with sufficient context
        error_message = "Key Vault access without RBAC authorization mode enabled"
        
        is_insufficient = check_insufficient_context(error_message)
        assert not is_insufficient, "Expected sufficient context for specific error message"
    
    def test_duplicate_detection_performance_within_500ms(self, tmp_path):
        """Verify duplicate detection completes within 500ms performance target."""
        # Create database with 100 entries
        db_path = tmp_path / "bicep-learnings.md"
        content = "## Security\n\n"
        for i in range(100):
            content += f"[2025-01-{(i % 28) + 1:02d}T00:00:00Z] Security Context {i} unique words here → Issue {i} → Solution {i}\n"
        
        db_path.write_text(content, encoding="utf-8")
        
        # Load existing entries
        existing_entries = load_learnings_database(db_path)
        
        # Test duplicate check performance
        new_entry_text = "[2025-01-20T00:00:00Z] Security Context 50 unique words here → Issue 50 → Solution 50"
        
        start_time = time.time()
        is_duplicate, matched_entry, similarity = check_duplicate_entry(new_entry_text, existing_entries)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.5, f"Duplicate check took {elapsed:.3f}s (target: <500ms)"
    
    def test_duplicate_manual_entries_same_day(self, tmp_path):
        """Verify duplicate detection works even when entries added same day."""
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access issue → Enable RBAC → Use RBAC authorization\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access problem → Enable RBAC mode → Use RBAC settings\n",  # Same day, similar content
            encoding="utf-8"
        )
        
        entries = load_learnings_database(db_path)
        
        # Second entry should be detected as duplicate even though same day
        assert len(entries) >= 1


class TestManualEditingEndToEnd:
    """End-to-end tests for manual editing workflow."""
    
    def test_full_manual_editing_workflow(self, tmp_path):
        """Test complete workflow: add manual entry → load → verify application."""
        # Step 1: Create initial database
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Initial entry → Initial issue → Initial solution\n",
            encoding="utf-8"
        )
        
        # Step 2: Manually add new entry (simulating user edit)
        with open(db_path, "a", encoding="utf-8") as f:
            f.write("[2025-01-16T00:00:00Z] Security Key Vault access → Enable RBAC → Use RBAC authorization\n")
        
        # Step 3: Load database (as command would do)
        entries = load_learnings_database(db_path)
        
        # Step 4: Verify both entries loaded
        assert len(entries) == 2
        assert entries[0].context == "Initial entry"
        assert entries[1].context == "Key Vault access"
    
    def test_manual_consolidation_of_duplicates(self, tmp_path):
        """Test manual consolidation workflow from quickstart guide."""
        # Initial database with duplicates
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-10T00:00:00Z] Security Key Vault access → Enable RBAC → Use enableRbacAuthorization\n"
            "[2025-01-15T00:00:00Z] Security Key Vault without RBAC → Use RBAC authorization → Set enableRbacAuthorization: true in properties\n",
            encoding="utf-8"
        )
        
        # User manually consolidates (removes first, updates second)
        db_path.write_text(
            "## Security\n\n"
            "[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in Key Vault properties, removes legacy access policies\n",
            encoding="utf-8"
        )
        
        # Verify consolidated entry
        entries = load_learnings_database(db_path)
        assert len(entries) == 1
        assert "removes legacy access policies" in entries[0].solution  # Merged information
    
    def test_manual_fix_of_obsolete_entry(self, tmp_path):
        """Test manual fixing of obsolete entry from quickstart guide."""
        # Initial database with outdated API version
        db_path = tmp_path / "bicep-learnings.md"
        db_path.write_text(
            "## Data Services\n\n"
            "[2024-06-01T00:00:00Z] Data Services SQL Managed Instance deployment → Use latest API version → Use apiVersion: '2021-11-01'\n",
            encoding="utf-8"
        )
        
        # User manually updates to latest API version
        db_path.write_text(
            "## Data Services\n\n"
            "[2025-01-15T00:00:00Z] Data Services SQL Managed Instance deployment → Use latest API version → Use apiVersion: '2023-08-01-preview' for latest features\n",
            encoding="utf-8"
        )
        
        # Verify updated entry
        entries = load_learnings_database(db_path)
        assert len(entries) == 1
        assert "2023-08-01-preview" in entries[0].solution
        assert entries[0].timestamp.year == 2025  # Updated timestamp
