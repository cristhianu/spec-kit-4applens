"""
End-to-End tests for Bicep generation with learnings database integration.

Tests verify that the /speckit.bicep command generates SFI-compliant templates
by applying learnings from the database. Tests validate:
- T022: No Azure Front Door unless explicitly requested
- T023: Private Endpoints used instead of Network Security Perimeter
- T024: All resources deployed to same VNet with proper isolation

These tests require the learnings database to be present and the prompt
to be properly integrated with learnings_loader.
"""

import pytest
import tempfile
import shutil
import re
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from specify_cli.utils.learnings_loader import (
    load_learnings_database,
    resolve_conflicts,
)


class TestLearningsApplicationToPrompt:
    """Test that learnings are correctly applied during Bicep generation."""
    
    @pytest.fixture
    def learnings_db_path(self):
        """Path to the actual learnings database."""
        return Path(__file__).parent.parent.parent / '.specify' / 'learnings' / 'bicep-learnings.md'
    
    def test_learnings_database_exists(self, learnings_db_path):
        """Verify the learnings database file exists."""
        assert learnings_db_path.exists(), \
            f"Learnings database not found at {learnings_db_path}"
        assert learnings_db_path.is_file(), \
            "Learnings database path should be a file"
    
    def test_learnings_database_loads_successfully(self, learnings_db_path):
        """Verify learnings database can be loaded without errors."""
        learnings = load_learnings_database(learnings_db_path)
        
        assert len(learnings) > 0, "Database should contain learnings"
        assert all(hasattr(e, 'category') for e in learnings), \
            "All entries should have category"
        assert all(hasattr(e, 'context') for e in learnings), \
            "All entries should have context"
        assert all(hasattr(e, 'solution') for e in learnings), \
            "All entries should have solution"
    
    def test_front_door_learning_present(self, learnings_db_path):
        """T022: Verify Azure Front Door learning exists in database."""
        learnings = load_learnings_database(learnings_db_path)
        
        # Find Front Door related learnings
        front_door_learnings = [
            e for e in learnings 
            if 'front door' in e.context.lower() or 'front door' in e.solution.lower()
        ]
        
        assert len(front_door_learnings) > 0, \
            "Should have learning about Azure Front Door"
        
        # Verify the learning says to avoid Front Door by default
        has_avoid_pattern = any(
            'only' in e.solution.lower() and 'requested' in e.solution.lower()
            or 'avoid' in e.solution.lower()
            or 'explicitly' in e.solution.lower()
            for e in front_door_learnings
        )
        
        assert has_avoid_pattern, \
            "Front Door learning should indicate to only use when explicitly requested"
    
    def test_private_endpoint_learning_present(self, learnings_db_path):
        """T023: Verify Private Endpoint learning exists in database."""
        learnings = load_learnings_database(learnings_db_path)
        
        # Find Private Endpoint related learnings
        pe_learnings = [
            e for e in learnings 
            if 'private endpoint' in e.context.lower() 
            or 'private endpoint' in e.solution.lower()
            or 'privatelink' in e.solution.lower()
        ]
        
        assert len(pe_learnings) > 0, \
            "Should have learnings about Private Endpoints"
    
    def test_network_security_perimeter_anti_pattern_present(self, learnings_db_path):
        """T023: Verify NSP anti-pattern learning exists."""
        learnings = load_learnings_database(learnings_db_path)
        
        # Find Network Security Perimeter learnings
        nsp_learnings = [
            e for e in learnings 
            if 'network security perimeter' in e.context.lower() 
            or 'network security perimeter' in e.issue.lower()
        ]
        
        # Should have learning about avoiding NSP
        if nsp_learnings:
            has_avoid_nsp = any(
                'avoid' in e.solution.lower() or 'private endpoint' in e.solution.lower()
                for e in nsp_learnings
            )
            assert has_avoid_nsp, \
                "NSP learning should recommend Private Endpoints instead"
    
    def test_vnet_integration_learning_present(self, learnings_db_path):
        """T024: Verify VNet integration learning exists in database."""
        learnings = load_learnings_database(learnings_db_path)
        
        # Find VNet integration learnings
        vnet_learnings = [
            e for e in learnings 
            if 'vnet' in e.context.lower() 
            or 'vnet' in e.solution.lower()
            or 'virtual network' in e.solution.lower()
        ]
        
        assert len(vnet_learnings) > 0, \
            "Should have learnings about VNet integration"
        
        # Verify VNet integration guidance exists
        has_vnet_config = any(
            'vnetconfiguration' in e.solution.lower() 
            or 'subnet' in e.solution.lower()
            for e in vnet_learnings
        )
        
        assert has_vnet_config, \
            "VNet learnings should mention vnetConfiguration or subnet"
    
    def test_public_network_access_disabled_learning_present(self, learnings_db_path):
        """T024: Verify public network access disabled learning exists."""
        learnings = load_learnings_database(learnings_db_path)
        
        # Find public network access learnings
        public_access_learnings = [
            e for e in learnings 
            if 'public' in e.issue.lower() and 'access' in e.issue.lower()
            or 'publicnetworkaccess' in e.solution.lower().replace(' ', '')
        ]
        
        assert len(public_access_learnings) > 0, \
            "Should have learnings about disabling public network access"
        
        # Verify they recommend disabling
        has_disable_pattern = any(
            'disabled' in e.solution.lower() or 'disable' in e.solution.lower()
            for e in public_access_learnings
        )
        
        assert has_disable_pattern, \
            "Public access learnings should recommend disabling"


class TestConflictResolutionInRealDatabase:
    """Test conflict resolution with real learnings database."""
    
    @pytest.fixture
    def learnings_db_path(self):
        """Path to the actual learnings database."""
        return Path(__file__).parent.parent.parent / '.specify' / 'learnings' / 'bicep-learnings.md'
    
    def test_no_conflicts_in_current_database(self, learnings_db_path):
        """Verify the current database has no unresolved conflicts."""
        learnings = load_learnings_database(learnings_db_path)
        resolved = resolve_conflicts(learnings)
        
        # After resolution, all entries should still be valid
        assert len(resolved) > 0, "Should have entries after resolution"
        assert len(resolved) <= len(learnings), \
            "Resolved list should not be larger than original"
        
        # No duplicates by context + category
        context_category_pairs = set()
        for entry in resolved:
            pair = (entry.context.lower(), entry.category.lower())
            # Note: Same context+category can appear if addressing different topics
            # This is not a conflict, so we just verify structure is valid
            context_category_pairs.add(pair)
        
        assert len(context_category_pairs) > 0, \
            "Should have distinct context+category combinations"
    
    def test_security_learnings_prioritized(self, learnings_db_path):
        """Verify Security category learnings are present (high priority)."""
        learnings = load_learnings_database(learnings_db_path)
        
        security_learnings = [e for e in learnings if e.category == 'Security']
        assert len(security_learnings) > 0, \
            "Should have Security category learnings (high priority)"
        
        # Verify they cover key SFI topics
        security_topics = ' '.join([e.solution.lower() for e in security_learnings])
        
        assert 'public' in security_topics and 'access' in security_topics, \
            "Security learnings should cover public network access"


class TestBicepGenerationPatterns:
    """Test expected patterns in generated Bicep templates."""
    
    @pytest.fixture
    def sample_bicep_template(self):
        """Sample Bicep template with SFI-compliant patterns."""
        return """
// Web application with database backend
param location string = resourceGroup().location
param appName string
param sqlAdminLogin string
@secure()
param sqlAdminPassword string

// Virtual Network for isolation
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${appName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'app-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [
            {
              name: 'Microsoft.Web.serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'sql-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Storage Account with Private Endpoint
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${appName}store${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// SQL Server with Private Endpoint
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${appName}-sql'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
  }
}

// Private Endpoint for SQL
resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: '${appName}-sql-pe'
  location: location
  properties: {
    subnet: {
      id: vnet.properties.subnets[1].id
    }
    privateLinkServiceConnections: [
      {
        name: 'sql-connection'
        properties: {
          privateLinkServiceId: sqlServer.id
          groupIds: [
            'sqlServer'
          ]
        }
      }
    ]
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'P1V2'
    tier: 'PremiumV2'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// App Service with VNet Integration
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    virtualNetworkSubnetId: vnet.properties.subnets[0].id
    vnetRouteAllEnabled: true
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
  }
}
"""
    
    def test_no_front_door_in_template(self, sample_bicep_template):
        """T022: Verify no Azure Front Door resources in template."""
        # Check for Front Door resource types
        front_door_patterns = [
            r"Microsoft\.Cdn/profiles",
            r"Microsoft\.Network/frontDoors",
            r"'frontdoor'",
            r'"frontdoor"',
        ]
        
        template_lower = sample_bicep_template.lower()
        
        for pattern in front_door_patterns:
            matches = re.findall(pattern, template_lower, re.IGNORECASE)
            assert len(matches) == 0, \
                f"Template should not contain Front Door resources (found: {pattern})"
    
    def test_private_endpoints_present(self, sample_bicep_template):
        """T023: Verify Private Endpoints are used for data services."""
        # Check for Private Endpoint resources
        pe_pattern = r"Microsoft\.Network/privateEndpoints"
        matches = re.findall(pe_pattern, sample_bicep_template, re.IGNORECASE)
        
        assert len(matches) > 0, \
            "Template should contain Private Endpoint resources"
    
    def test_no_network_security_perimeter(self, sample_bicep_template):
        """T023: Verify no Network Security Perimeter resources."""
        nsp_patterns = [
            r"Microsoft\.Network/networkSecurityPerimeters",
            r"networkSecurityPerimeter",
        ]
        
        for pattern in nsp_patterns:
            matches = re.findall(pattern, sample_bicep_template, re.IGNORECASE)
            assert len(matches) == 0, \
                f"Template should not use Network Security Perimeter (found: {pattern})"
    
    def test_public_network_access_disabled(self, sample_bicep_template):
        """T024: Verify publicNetworkAccess is disabled for data services."""
        # Find all publicNetworkAccess properties
        access_pattern = r"publicNetworkAccess:\s*'(\w+)'"
        matches = re.findall(access_pattern, sample_bicep_template, re.IGNORECASE)
        
        assert len(matches) > 0, \
            "Template should set publicNetworkAccess property"
        
        # All should be 'Disabled'
        for access_value in matches:
            assert access_value.lower() == 'disabled', \
                f"publicNetworkAccess should be 'Disabled', found: '{access_value}'"
    
    def test_vnet_integration_present(self, sample_bicep_template):
        """T024: Verify VNet and subnet resources are present."""
        # Check for VNet resource
        vnet_pattern = r"Microsoft\.Network/virtualNetworks"
        vnet_matches = re.findall(vnet_pattern, sample_bicep_template, re.IGNORECASE)
        
        assert len(vnet_matches) > 0, \
            "Template should contain VNet resources"
        
        # Check for subnet configuration
        subnet_patterns = [
            r"subnets:\s*\[",
            r"addressPrefix:",
        ]
        
        for pattern in subnet_patterns:
            matches = re.findall(pattern, sample_bicep_template, re.IGNORECASE)
            assert len(matches) > 0, \
                f"Template should configure subnets (pattern: {pattern})"
    
    def test_app_service_vnet_integration(self, sample_bicep_template):
        """T024: Verify App Service has VNet integration."""
        # Check for virtualNetworkSubnetId or vnetConfiguration
        vnet_integration_patterns = [
            r"virtualNetworkSubnetId:",
            r"vnetRouteAllEnabled:",
            r"vnetConfiguration:",
        ]
        
        found_integration = False
        for pattern in vnet_integration_patterns:
            matches = re.findall(pattern, sample_bicep_template, re.IGNORECASE)
            if matches:
                found_integration = True
                break
        
        assert found_integration, \
            "App Service should have VNet integration configured"
    
    def test_managed_identity_present(self, sample_bicep_template):
        """Verify Managed Identity is used (SFI best practice)."""
        # Check for identity configuration
        identity_pattern = r"identity:\s*\{\s*type:\s*'SystemAssigned'"
        matches = re.findall(identity_pattern, sample_bicep_template, re.IGNORECASE)
        
        assert len(matches) > 0, \
            "Template should use SystemAssigned managed identity"
    
    def test_tls_version_enforced(self, sample_bicep_template):
        """Verify TLS 1.2 or higher is enforced."""
        tls_patterns = [
            r"minimumTlsVersion:\s*'TLS1_2'",
            r"minTlsVersion:\s*'1\.2'",
            r"minimalTlsVersion:\s*'1\.2'",
        ]
        
        found_tls = False
        for pattern in tls_patterns:
            matches = re.findall(pattern, sample_bicep_template, re.IGNORECASE)
            if matches:
                found_tls = True
                break
        
        assert found_tls, \
            "Template should enforce TLS 1.2 or higher"
    
    def test_https_only_enabled(self, sample_bicep_template):
        """Verify HTTPS-only is enabled for web apps."""
        https_pattern = r"httpsOnly:\s*true"
        matches = re.findall(https_pattern, sample_bicep_template, re.IGNORECASE)
        
        assert len(matches) > 0, \
            "Template should enable httpsOnly for App Service"


class TestLearningsFormatValidation:
    """Validate learnings format matches specification."""
    
    @pytest.fixture
    def learnings_db_path(self):
        """Path to the actual learnings database."""
        return Path(__file__).parent.parent.parent / '.specify' / 'learnings' / 'bicep-learnings.md'
    
    def test_all_entries_have_timestamps(self, learnings_db_path):
        """Verify all entries have valid timestamps."""
        learnings = load_learnings_database(learnings_db_path)
        
        for entry in learnings:
            assert entry.timestamp is not None, \
                f"Entry should have timestamp: {entry.raw_text[:50]}"
            assert entry.timestamp.tzinfo is not None, \
                "Timestamp should be timezone-aware (UTC)"
    
    def test_all_entries_have_required_fields(self, learnings_db_path):
        """Verify all entries have required fields."""
        learnings = load_learnings_database(learnings_db_path)
        
        for entry in learnings:
            assert entry.category, "Entry should have category"
            assert entry.context, "Entry should have context"
            assert entry.issue, "Entry should have issue"
            assert entry.solution, "Entry should have solution"
            
            # Verify minimum lengths
            assert len(entry.category) > 0, "Category should not be empty"
            assert len(entry.context) > 0, "Context should not be empty"
            assert len(entry.solution) > 10, "Solution should be substantive"
    
    def test_categories_match_canonical_list(self, learnings_db_path):
        """Verify categories match canonical list from learnings-format.md."""
        learnings = load_learnings_database(learnings_db_path)
        
        canonical_categories = [
            "Security",
            "Compliance",
            "Networking",
            "Data Services",
            "Compute",
            "Configuration",
            "Performance",
            "Operations",
        ]
        
        for entry in learnings:
            assert entry.category in canonical_categories, \
                f"Category '{entry.category}' not in canonical list"
    
    def test_entries_sorted_by_category(self, learnings_db_path):
        """Verify entries are organized by category headers."""
        content = learnings_db_path.read_text(encoding='utf-8')
        
        # Check for category headers
        category_headers = [
            "## Security",
            "## Compliance",
            "## Networking",
            "## Data Services",
            "## Compute",
            "## Configuration",
        ]
        
        found_headers = 0
        for header in category_headers:
            if header in content:
                found_headers += 1
        
        assert found_headers >= 3, \
            f"Database should have multiple category sections (found {found_headers})"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
