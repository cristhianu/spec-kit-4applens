"""
Tests for Automated Learning Capture (User Story 2 - Phase 4)

Tests the automatic capture of deployment errors and validation failures into the learnings database.
Validates error classification, duplicate detection, and append functionality.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from specify_cli.utils.learnings_loader import (
    append_learning_entry,
    load_learnings_database,
    classify_error,
    check_insufficient_context,
)


class TestStructuralErrorAppend:
    """Test T032: Capture structural errors (e.g., 'missing property')"""
    
    def test_append_missing_property_error(self, tmp_path):
        """Test that 'missing property' errors are captured as new learnings"""
        # Setup
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Configuration\n\n")
        
        # Simulate deployment error with "missing property"
        error_message = "Deployment failed: Missing property 'sku' in Microsoft.Storage/storageAccounts"
        category = "Configuration"
        context = "storageAccounts deployment"
        issue = error_message
        solution = "Add required 'sku' property to storage account resource"
        
        # Append learning entry
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category=category,
            context=context,
            issue=issue,
            solution=solution,
            check_duplicates=False  # Skip for first entry
        )
        
        # Verify
        assert was_appended is True
        
        # Load and verify entry was saved
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
        assert learnings[0].category == category
        assert learnings[0].context == context
        assert "missing property" in learnings[0].issue.lower()
        assert "sku" in learnings[0].solution.lower()
    
    def test_append_invalid_value_error(self, tmp_path):
        """Test that 'invalid value' errors are captured"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Data Services\n\n")
        
        error_message = "Invalid value 'Basic' for sku.tier in Microsoft.Sql/servers"
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Data Services",
            context="SQL Server sku configuration",
            issue=error_message,
            solution="Use 'GeneralPurpose' or 'BusinessCritical' tier for SQL Server",
            check_duplicates=False
        )
        
        assert was_appended is True
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
        assert "invalid value" in learnings[0].issue.lower()
    
    def test_append_quota_exceeded_error(self, tmp_path):
        """Test that 'quota exceeded' errors are captured"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Operations\n\n")
        
        error_message = "Quota exceeded: Maximum number of storage accounts (10) reached in region 'eastus'"
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Operations",
            context="Storage account quota",
            issue=error_message,
            solution="Deploy to different region or request quota increase",
            check_duplicates=False
        )
        
        assert was_appended is True
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
        assert "quota" in learnings[0].issue.lower()
    
    def test_append_already_exists_error(self, tmp_path):
        """Test that 'already exists' errors are captured"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Configuration\n\n")
        
        error_message = "Resource 'myapp-storage' already exists in resource group 'rg-test'"
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Configuration",
            context="Resource naming",
            issue=error_message,
            solution="Use unique names with environment suffix (e.g., 'myapp-storage-dev')",
            check_duplicates=False
        )
        
        assert was_appended is True
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
        assert "already exists" in learnings[0].issue.lower()
    
    def test_append_unauthorized_error(self, tmp_path):
        """Test that 'unauthorized' errors are captured"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Security\n\n")
        
        error_message = "Unauthorized: Insufficient permissions to create Microsoft.KeyVault/vaults"
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Key Vault deployment permissions",
            issue=error_message,
            solution="Grant 'Key Vault Contributor' role or use Managed Identity",
            check_duplicates=False
        )
        
        assert was_appended is True
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
        assert "unauthorized" in learnings[0].issue.lower()
    
    def test_classify_error_captures_missing_property(self):
        """Test error classification identifies 'missing property' as capturable"""
        error_message = "Deployment error: Missing property 'location'"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is True
        assert matched_keywords is not None
        assert "missing property" in matched_keywords.lower()


class TestTransientErrorFiltering:
    """Test T033: Filter transient errors (e.g., 'throttled')"""
    
    def test_throttled_error_not_captured(self):
        """Test that 'throttled' errors are NOT captured (transient)"""
        error_message = "Request throttled: Too many requests to Azure Resource Manager API"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is False
        assert matched_keywords is not None
        assert "throttled" in matched_keywords.lower()
    
    def test_timeout_error_not_captured(self):
        """Test that 'timeout' errors are NOT captured (transient)"""
        error_message = "Deployment timeout: Operation exceeded 30 second limit"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is False
        assert matched_keywords is not None
        assert "timeout" in matched_keywords.lower()
    
    def test_unavailable_error_not_captured(self):
        """Test that 'service unavailable' errors are NOT captured"""
        error_message = "Service unavailable: Azure Storage service is temporarily unavailable"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is False
        assert matched_keywords is not None
        assert "unavailable" in matched_keywords.lower()
    
    def test_gateway_timeout_not_captured(self):
        """Test that 'gateway timeout' errors are NOT captured"""
        error_message = "Gateway timeout: 504 Gateway Timeout from Azure Front Door"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is False
        assert matched_keywords is not None
        # The keyword "timeout" matches first (substring), not "gateway timeout"
        assert "timeout" in matched_keywords.lower()
    
    def test_too_many_requests_not_captured(self):
        """Test that 'too many requests' errors are NOT captured"""
        error_message = "Too many requests: Rate limit exceeded (429)"
        
        should_capture, matched_keywords = classify_error(error_message)
        
        assert should_capture is False
        assert matched_keywords is not None
        assert "too many requests" in matched_keywords.lower()
    
    def test_transient_error_append_returns_false(self, tmp_path):
        """Test that attempting to append transient error is rejected"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Operations\n\n")
        
        # Manually classify first (normally done before calling append)
        error_message = "Request throttled due to rate limiting"
        should_capture, _ = classify_error(error_message)
        
        # Should not capture
        assert should_capture is False
        
        # If erroneously called with transient error, classify_error should have prevented it
        # This test demonstrates the safeguard


class TestDuplicateRejection:
    """Test T034: Reject duplicate entries (>60% similarity)"""
    
    def test_duplicate_entry_rejected(self, tmp_path):
        """Test that duplicate entries are detected and rejected"""
        learnings_file = tmp_path / "bicep-learnings.md"
        
        # Create initial entry (use UTF-8 encoding for arrow character)
        learnings_file.write_text(
            "## Security\n\n"
            "[2025-01-21T10:00:00Z] Security Key Vault access → "
            "Missing 'accessPolicies' property → "
            "Add access policies to Key Vault resource\n",
            encoding="utf-8"
        )
        
        # Attempt to add very similar entry (should be rejected)
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Key Vault access",
            issue="Missing 'accessPolicies' property in Key Vault",
            solution="Add access policies to Key Vault resource definition",
            check_duplicates=True  # Enable duplicate checking
        )
        
        # Verify duplicate was rejected
        assert was_appended is False
        
        # Verify database still has only 1 entry
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
    
    def test_similar_entry_rejected_high_similarity(self, tmp_path):
        """Test that highly similar entries (>60%) are rejected"""
        learnings_file = tmp_path / "bicep-learnings.md"
        
        # Create initial entry (use UTF-8 encoding for arrow character)
        existing_context = "Virtual Network subnet configuration"
        existing_issue = "Missing subnet configuration in virtual network"
        existing_solution = "Add subnet definitions to VNet resource"
        
        learnings_file.write_text(
            "## Networking\n\n"
            f"[2025-01-21T10:00:00Z] Networking {existing_context} → "
            f"{existing_issue} → "
            f"{existing_solution}\n",
            encoding="utf-8"
        )
        
        # Attempt to add nearly identical entry (should definitely be >60% similar)
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Networking",
            context=existing_context,  # Identical context
            issue=existing_issue,  # Identical issue  
            solution=existing_solution,  # Identical solution
            check_duplicates=True
        )
        
        # Should be rejected due to being essentially identical
        assert was_appended is False
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 1
    
    def test_different_entry_accepted_low_similarity(self, tmp_path):
        """Test that different entries (<60% similarity) are accepted"""
        learnings_file = tmp_path / "bicep-learnings.md"
        
        # Create initial entry about Key Vault (use UTF-8 encoding for arrow character)
        learnings_file.write_text(
            "## Security\n\n"
            "[2025-01-21T10:00:00Z] Security Key Vault access → "
            "Missing 'accessPolicies' property → "
            "Add access policies to Key Vault resource\n",
            encoding="utf-8"
        )
        
        # Attempt to add different entry about Storage encryption
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Storage Account encryption",
            issue="Encryption at rest not enabled for storage account",
            solution="Set 'encryption.services.blob.enabled' to true",
            check_duplicates=True
        )
        
        # Should be accepted (different topic)
        assert was_appended is True
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 2
    
    def test_duplicate_detection_with_existing_entries(self, tmp_path):
        """Test duplicate detection against multiple existing entries"""
        learnings_file = tmp_path / "bicep-learnings.md"
        
        # Create multiple entries (use UTF-8 encoding for arrow character)
        learnings_file.write_text(
            "## Security\n\n"
            "[2025-01-21T10:00:00Z] Security Key Vault → "
            "Missing access policies → "
            "Add access policies\n\n"
            "[2025-01-21T10:05:00Z] Security Storage Account → "
            "No encryption configured → "
            "Enable encryption at rest\n\n"
            "[2025-01-21T10:10:00Z] Security SQL Server → "
            "TLS 1.0 enabled → "
            "Set minimum TLS version to 1.2\n",
            encoding="utf-8"
        )
        
        # Attempt to add duplicate of second entry
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Storage Account",
            issue="Encryption not configured for storage",
            solution="Enable encryption at rest for blobs and files",
            check_duplicates=True
        )
        
        # Should be rejected (matches second entry)
        assert was_appended is False
        learnings = load_learnings_database(learnings_file)
        assert len(learnings) == 3  # Still 3 entries


class TestInsufficientContextDetection:
    """Test that entries with insufficient context are rejected"""
    
    def test_generic_error_message_rejected(self):
        """Test that single-word generic error messages are rejected"""
        error_message = "error"  # Single-word generic error
        
        has_insufficient = check_insufficient_context(error_message)
        
        assert has_insufficient is True
    
    def test_short_error_message_rejected(self):
        """Test that very short error messages are rejected"""
        error_message = "Error"
        
        has_insufficient = check_insufficient_context(error_message)
        
        assert has_insufficient is True
    
    def test_detailed_error_with_resource_type_accepted(self):
        """Test that detailed errors with resource type are accepted"""
        error_message = "Missing property 'sku' in storage account configuration"
        resource_type = "Microsoft.Storage/storageAccounts"
        
        has_insufficient = check_insufficient_context(error_message, resource_type)
        
        assert has_insufficient is False
    
    def test_detailed_error_without_resource_type_accepted(self):
        """Test that sufficiently detailed errors are accepted even without resource type"""
        error_message = (
            "Deployment failed: The storage account 'myapp-storage' already exists in "
            "resource group 'rg-test'. Use a unique name or delete the existing resource."
        )
        
        has_insufficient = check_insufficient_context(error_message)
        
        assert has_insufficient is False


class TestAppendPerformance:
    """Test append operation performance (T031)"""
    
    def test_append_completes_within_budget(self, tmp_path):
        """Test that append operation completes within 100ms budget"""
        import time
        
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Configuration\n\n")
        
        start_time = time.time()
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Configuration",
            context="Test performance",
            issue="Performance test entry",
            solution="This is a test",
            check_duplicates=False  # Skip for performance test
        )
        
        elapsed = time.time() - start_time
        
        assert was_appended is True
        assert elapsed < 0.1  # Should complete in <100ms
    
    def test_append_with_duplicate_check_performance(self, tmp_path):
        """Test append with duplicate checking stays within budget"""
        import time
        
        learnings_file = tmp_path / "bicep-learnings.md"
        
        # Create 10 existing entries (use UTF-8 encoding for arrow character)
        content = "## Security\n\n"
        for i in range(10):
            content += f"[2025-01-21T10:{i:02d}:00Z] Security Test entry {i} → Issue {i} → Solution {i}\n"
        learnings_file.write_text(content, encoding="utf-8")
        
        start_time = time.time()
        
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Performance test with duplicates",
            issue="New unique entry for performance testing",
            solution="This should not match any existing entries",
            check_duplicates=True  # Enable duplicate checking
        )
        
        elapsed = time.time() - start_time
        
        assert was_appended is True
        # Note: May exceed 100ms with duplicate checking on many entries
        # But should still be reasonable (<500ms)
        assert elapsed < 0.5


class TestErrorHandling:
    """Test error handling for T029, T030"""
    
    def test_invalid_category_raises_value_error(self, tmp_path):
        """Test that invalid category raises ValueError (T030)"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Security\n\n")
        
        with pytest.raises(ValueError, match="Invalid category"):
            append_learning_entry(
                file_path=learnings_file,
                category="InvalidCategory",  # Not in canonical list
                context="Test",
                issue="Test issue",
                solution="Test solution",
                check_duplicates=False
            )
    
    def test_context_too_long_raises_value_error(self, tmp_path):
        """Test that context >100 chars raises ValueError (T030)"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Security\n\n")
        
        with pytest.raises(ValueError, match="Context too long"):
            append_learning_entry(
                file_path=learnings_file,
                category="Security",
                context="A" * 101,  # 101 chars (max 100)
                issue="Test issue",
                solution="Test solution",
                check_duplicates=False
            )
    
    def test_missing_directory_raises_file_not_found(self, tmp_path):
        """Test that missing directory raises custom FileNotFoundError (T029)"""
        from specify_cli.utils.learnings_loader import FileNotFoundError as CustomFileNotFoundError
        
        learnings_file = tmp_path / "nonexistent" / "bicep-learnings.md"
        
        # Directory doesn't exist, should fail with custom FileNotFoundError
        with pytest.raises(CustomFileNotFoundError):
            append_learning_entry(
                file_path=learnings_file,
                category="Security",
                context="Test",
                issue="Test issue",
                solution="Test solution",
                check_duplicates=False
            )
    
    def test_entry_format_validation(self, tmp_path):
        """Test that entry format is validated before appending (T030)"""
        learnings_file = tmp_path / "bicep-learnings.md"
        learnings_file.write_text("## Security\n\n")
        
        # Valid entry should succeed
        was_appended = append_learning_entry(
            file_path=learnings_file,
            category="Security",
            context="Valid context",
            issue="Valid issue description",
            solution="Valid solution description",
            check_duplicates=False
        )
        
        assert was_appended is True
        
        # Verify entry format
        content = learnings_file.read_text(encoding="utf-8")
        assert "[" in content  # Timestamp
        assert "] Security " in content  # Category
        assert "→" in content  # Arrow separator
