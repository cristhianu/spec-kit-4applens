"""
Integration tests for cross-command consistency (T044-T046).

Tests verify that /speckit.bicep and /speckit.validate commands reference
the same learnings database for consistent architectural patterns.
"""

import pytest
from pathlib import Path

# Get repository root (2 levels up from tests/integration)
REPO_ROOT = Path(__file__).parent.parent.parent


class TestPublicNetworkAccessConsistency:
    """T044: Test that publicNetworkAccess learning is referenced by both commands."""
    
    def test_learnings_database_has_public_network_access_entry(self):
        """Verify learnings database contains publicNetworkAccess guidance."""
        learnings_path = REPO_ROOT / ".specify" / "learnings" / "bicep-learnings.md"
        
        assert learnings_path.exists(), "Learnings database not found"
        
        content = learnings_path.read_text()
        
        # Check for publicNetworkAccess learnings
        assert "publicNetworkAccess: 'Disabled'" in content, \
            "publicNetworkAccess learning not found in database"
        
        # Verify at least 2 resources mention publicNetworkAccess (Storage + Key Vault)
        assert content.count("publicNetworkAccess") >= 2, \
            "Expected multiple resources with publicNetworkAccess guidance"
    
    def test_bicep_prompt_loads_learnings_database(self):
        """Verify speckit.bicep prompt loads learnings database."""
        bicep_prompt_path = REPO_ROOT / ".github" / "prompts" / "speckit.bicep.prompt.md"
        
        assert bicep_prompt_path.exists(), "Bicep prompt not found"
        
        content = bicep_prompt_path.read_text(encoding='utf-8')
        
        # Check for learnings loading logic
        assert "load_learnings_database" in content, \
            "Bicep prompt does not load learnings database"
        
        # Check for publicNetworkAccess references
        assert "publicNetworkAccess" in content, \
            "Bicep prompt does not reference publicNetworkAccess"
    
    def test_validate_prompt_loads_learnings_database(self):
        """Verify speckit.validate prompt loads learnings database."""
        validate_prompt_path = REPO_ROOT / "templates" / "commands" / "speckit.validate.prompt.md"
        
        assert validate_prompt_path.exists(), "Validate prompt not found"
        
        content = validate_prompt_path.read_text(encoding='utf-8')
        
        # Check for learnings loading logic
        assert "load_validation_learnings" in content, \
            "Validate prompt does not load learnings database"
        
        # Check for publicNetworkAccess references
        assert "publicNetworkAccess" in content, \
            "Validate prompt does not reference publicNetworkAccess"
    
    def test_both_commands_reference_same_publicNetworkAccess_pattern(self):
        """Verify both commands reference the same publicNetworkAccess pattern."""
        bicep_prompt = (REPO_ROOT / ".github" / "prompts" / "speckit.bicep.prompt.md").read_text(encoding='utf-8')
        validate_prompt = (REPO_ROOT / "templates" / "commands" / "speckit.validate.prompt.md").read_text(encoding='utf-8')
        
        # Expected pattern from learnings database
        expected_pattern = "publicNetworkAccess: 'Disabled'"
        
        assert expected_pattern in bicep_prompt, \
            f"Bicep prompt does not reference pattern: {expected_pattern}"
        
        assert expected_pattern in validate_prompt, \
            f"Validate prompt does not reference pattern: {expected_pattern}"


class TestValidationConsistency:
    """T045: Test that validation correctly uses learnings database."""
    
    def test_validate_prompt_has_halt_behavior_for_missing_database(self):
        """Verify validate prompt HALTs if learnings database is missing."""
        validate_prompt_path = REPO_ROOT / "templates" / "commands" / "speckit.validate.prompt.md"
        content = validate_prompt_path.read_text(encoding='utf-8')
        
        # Check for HALT behavior
        assert "FileNotFoundError" in content, \
            "Validate prompt missing FileNotFoundError handling"
        
        assert "HALT" in content or "halt" in content.lower(), \
            "Validate prompt missing HALT behavior for missing database"
    
    def test_validate_prompt_filters_relevant_categories(self):
        """Verify validate prompt filters to relevant categories."""
        validate_prompt_path = REPO_ROOT / "templates" / "commands" / "speckit.validate.prompt.md"
        content = validate_prompt_path.read_text(encoding='utf-8')
        
        # Check for category filtering logic
        relevant_categories = ["Security", "Networking", "Compliance", "Configuration", "Operations"]
        
        for category in relevant_categories:
            assert category in content, \
                f"Validate prompt missing reference to {category} category"


class TestPrivateEndpointDNSConsistency:
    """T046: Test Private Endpoint DNS consistency between commands."""
    
    def test_learnings_database_has_private_endpoint_dns_entry(self):
        """Verify learnings database contains Private Endpoint DNS guidance."""
        learnings_path = REPO_ROOT / ".specify" / "learnings" / "bicep-learnings.md"
        content = learnings_path.read_text()
        
        # Check for Private DNS zones learning
        assert "Private DNS" in content or "privatelink" in content, \
            "Private Endpoint DNS learning not found in database"
    
    def test_bicep_prompt_references_private_endpoint_dns(self):
        """Verify bicep prompt references Private Endpoint DNS patterns."""
        bicep_prompt_path = REPO_ROOT / ".github" / "prompts" / "speckit.bicep.prompt.md"
        content = bicep_prompt_path.read_text(encoding='utf-8')
        
        # Check for Private Endpoint references
        assert "Private Endpoint" in content or "privateEndpoint" in content, \
            "Bicep prompt does not reference Private Endpoints"
        
        # Check for DNS references
        assert "DNS" in content or "privatelink" in content, \
            "Bicep prompt does not reference DNS configuration"
    
    def test_validate_prompt_checks_private_endpoint_dns(self):
        """Verify validate prompt checks Private Endpoint DNS configuration."""
        validate_prompt_path = REPO_ROOT / "templates" / "commands" / "speckit.validate.prompt.md"
        content = validate_prompt_path.read_text(encoding='utf-8')
        
        # Validate prompt should check networking patterns including DNS
        assert "Networking" in content, \
            "Validate prompt does not reference Networking category"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
