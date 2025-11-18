"""
Unit tests for bicep-validate-architecture.py script.

Tests validation logic for SFI compliance checks.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from bicep_validate_architecture import BicepValidator, ValidationResult


class TestBicepValidator:
    """Test BicepValidator class."""
    
    @pytest.fixture
    def compliant_template(self, tmp_path):
        """Create a compliant Bicep template."""
        template = tmp_path / "compliant.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    publicNetworkAccess: 'Disabled'
    minimumTlsVersion: 'TLS1_2'
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'vnet'
  location: 'eastus'
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe'
  location: 'eastus'
}

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    httpsOnly: true
    virtualNetworkSubnetId: 'subnet-id'
    vnetRouteAllEnabled: true
    siteConfig: {
      minTlsVersion: '1.2'
    }
  }
}
""")
        return template
    
    @pytest.fixture
    def non_compliant_template(self, tmp_path):
        """Create a non-compliant Bicep template."""
        template = tmp_path / "non-compliant.bicep"
        template.write_text("""
resource frontDoor 'Microsoft.Cdn/profiles@2021-06-01' = {
  name: 'fd'
  location: 'global'
}

resource nsp 'Microsoft.Network/networkSecurityPerimeters@2021-02-01-preview' = {
  name: 'nsp'
  location: 'eastus'
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    publicNetworkAccess: 'Enabled'
    minimumTlsVersion: 'TLS1_0'
  }
}

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  properties: {
    httpsOnly: false
    siteConfig: {
      minTlsVersion: '1.0'
    }
  }
}
""")
        return template
    
    def test_validator_initialization(self, compliant_template):
        """Test validator can be initialized with a valid file."""
        validator = BicepValidator(compliant_template)
        assert validator.bicep_file == compliant_template
        assert len(validator.content) > 0
        assert len(validator.lines) > 0
    
    def test_validator_missing_file(self, tmp_path):
        """Test validator raises error for missing file."""
        missing_file = tmp_path / "missing.bicep"
        with pytest.raises(FileNotFoundError):
            BicepValidator(missing_file)
    
    def test_compliant_template_passes(self, compliant_template):
        """Test that compliant template passes all checks."""
        validator = BicepValidator(compliant_template)
        result = validator.validate()
        
        assert result is True
        assert all(r.passed for r in validator.results if r.severity == "error")
    
    def test_non_compliant_template_fails(self, non_compliant_template):
        """Test that non-compliant template fails validation."""
        validator = BicepValidator(non_compliant_template)
        result = validator.validate()
        
        assert result is False
        errors = [r for r in validator.results if not r.passed and r.severity == "error"]
        assert len(errors) > 0
    
    def test_front_door_detection(self, tmp_path):
        """Test Front Door resource detection."""
        template = tmp_path / "frontdoor.bicep"
        template.write_text("""
resource frontDoor 'Microsoft.Cdn/profiles@2021-06-01' = {
  name: 'fd'
  location: 'global'
}
""")
        
        validator = BicepValidator(template)
        validator.check_no_front_door()
        
        result = validator.results[0]
        assert result.check_name == "No Front Door"
        assert result.passed is False
        assert result.severity == "error"
        assert "Cdn/profiles" in result.message or "frontDoor" in result.message
    
    def test_front_door_allowed_flag(self, tmp_path):
        """Test Front Door is allowed with flag."""
        template = tmp_path / "frontdoor.bicep"
        template.write_text("""
resource frontDoor 'Microsoft.Cdn/profiles@2021-06-01' = {
  name: 'fd'
  location: 'global'
}
""")
        
        validator = BicepValidator(template, allow_front_door=True)
        validator.check_no_front_door()
        
        result = validator.results[0]
        assert result.check_name == "No Front Door"
        assert result.passed is True
        assert "skipped" in result.message.lower()
    
    def test_nsp_detection(self, tmp_path):
        """Test Network Security Perimeter detection."""
        template = tmp_path / "nsp.bicep"
        template.write_text("""
resource nsp 'Microsoft.Network/networkSecurityPerimeters@2021-02-01-preview' = {
  name: 'nsp'
  location: 'eastus'
}
""")
        
        validator = BicepValidator(template)
        validator.check_no_network_security_perimeter()
        
        result = validator.results[0]
        assert result.check_name == "No Network Security Perimeter"
        assert result.passed is False
        assert result.severity == "error"
    
    def test_private_endpoint_recommendation(self, tmp_path):
        """Test Private Endpoint recommendation."""
        template = tmp_path / "storage-no-pe.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
}
""")
        
        validator = BicepValidator(template)
        validator.check_private_endpoints_recommended()
        
        result = validator.results[0]
        assert result.check_name == "Private Endpoints Recommended"
        assert result.passed is False
        assert result.severity == "warning"
    
    def test_public_network_access_enabled(self, tmp_path):
        """Test detection of publicNetworkAccess: 'Enabled'."""
        template = tmp_path / "storage-public.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_public_network_access_disabled()
        
        result = validator.results[0]
        assert result.check_name == "Public Network Access Disabled"
        assert result.passed is False
        assert result.severity == "error"
        assert "Enabled" in result.message
    
    def test_public_network_access_disabled(self, tmp_path):
        """Test detection of publicNetworkAccess: 'Disabled'."""
        template = tmp_path / "storage-private.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    publicNetworkAccess: 'Disabled'
  }
}

resource sql 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: 'sqlserver'
  location: 'eastus'
  properties: {
    publicNetworkAccess: 'Disabled'
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_public_network_access_disabled()
        
        result = validator.results[0]
        assert result.check_name == "Public Network Access Disabled"
        assert result.passed is True
    
    def test_vnet_integration_present(self, tmp_path):
        """Test VNet integration detection."""
        template = tmp_path / "vnet.bicep"
        template.write_text("""
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'vnet'
  location: 'eastus'
}

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  properties: {
    virtualNetworkSubnetId: 'subnet-id'
    vnetRouteAllEnabled: true
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_vnet_integration()
        
        result = validator.results[0]
        assert result.check_name == "VNet Integration"
        assert result.passed is True
    
    def test_managed_identity_present(self, tmp_path):
        """Test Managed Identity detection."""
        template = tmp_path / "identity.bicep"
        template.write_text("""
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  identity: {
    type: 'SystemAssigned'
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_managed_identity()
        
        result = validator.results[0]
        assert result.check_name == "Managed Identity"
        assert result.passed is True
    
    def test_tls_version_too_low(self, tmp_path):
        """Test detection of TLS < 1.2."""
        template = tmp_path / "tls-low.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    minimumTlsVersion: 'TLS1_0'
  }
}

resource sql 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: 'sqlserver'
  location: 'eastus'
  properties: {
    minimalTlsVersion: '1.1'
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_tls_version()
        
        result = validator.results[0]
        assert result.check_name == "TLS Version"
        assert result.passed is False
        assert result.severity == "error"
        assert "TLS1_0" in result.message or "1.1" in result.message
    
    def test_tls_version_compliant(self, tmp_path):
        """Test TLS 1.2+ is accepted."""
        template = tmp_path / "tls-good.bicep"
        template.write_text("""
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stgaccount'
  location: 'eastus'
  properties: {
    minimumTlsVersion: 'TLS1_2'
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_tls_version()
        
        result = validator.results[0]
        assert result.check_name == "TLS Version"
        assert result.passed is True
    
    def test_https_only_false(self, tmp_path):
        """Test detection of httpsOnly: false."""
        template = tmp_path / "http.bicep"
        template.write_text("""
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  properties: {
    httpsOnly: false
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_https_only()
        
        result = validator.results[0]
        assert result.check_name == "HTTPS Only"
        assert result.passed is False
        assert result.severity == "warning"
    
    def test_https_only_true(self, tmp_path):
        """Test httpsOnly: true is accepted."""
        template = tmp_path / "https.bicep"
        template.write_text("""
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  location: 'eastus'
  properties: {
    httpsOnly: true
  }
}
""")
        
        validator = BicepValidator(template)
        validator.check_https_only()
        
        result = validator.results[0]
        assert result.check_name == "HTTPS Only"
        assert result.passed is True
    
    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass."""
        result = ValidationResult(
            check_name="Test Check",
            passed=True,
            message="Test message",
            severity="info",
            line_number=10,
            resource_name="testResource"
        )
        
        assert result.check_name == "Test Check"
        assert result.passed is True
        assert result.message == "Test message"
        assert result.severity == "info"
        assert result.line_number == 10
        assert result.resource_name == "testResource"
    
    def test_print_results_verbose(self, compliant_template, capsys):
        """Test verbose output format."""
        validator = BicepValidator(compliant_template, verbose=True)
        validator.validate()
        validator.print_results(json_output=False)
        
        captured = capsys.readouterr()
        assert "Validating:" in captured.out
        assert "PASSED:" in captured.out
        assert "✅" in captured.out
    
    def test_print_results_json(self, compliant_template, capsys):
        """Test JSON output format."""
        validator = BicepValidator(compliant_template)
        validator.validate()
        validator.print_results(json_output=True)
        
        captured = capsys.readouterr()
        assert '"file":' in captured.out
        assert '"passed":' in captured.out
        assert '"results":' in captured.out
        
        # Validate it's valid JSON
        import json
        output = json.loads(captured.out)
        assert "file" in output
        assert "passed" in output
        assert "results" in output


class TestValidationIntegration:
    """Integration tests with actual fixture files."""
    
    def test_sample_compliant_template(self):
        """Test validation of sample-compliant.bicep fixture."""
        template_path = Path(__file__).parent.parent / "fixtures" / "sample-compliant.bicep"
        
        if not template_path.exists():
            pytest.skip("Sample compliant template not found")
        
        validator = BicepValidator(template_path)
        result = validator.validate()
        
        assert result is True, "Sample compliant template should pass validation"
    
    def test_sample_non_compliant_template(self):
        """Test validation of sample-non-compliant.bicep fixture."""
        template_path = Path(__file__).parent.parent / "fixtures" / "sample-non-compliant.bicep"
        
        if not template_path.exists():
            pytest.skip("Sample non-compliant template not found")
        
        validator = BicepValidator(template_path)
        result = validator.validate()
        
        assert result is False, "Sample non-compliant template should fail validation"
        
        # Check specific violations
        errors = [r for r in validator.results if not r.passed and r.severity == "error"]
        warnings = [r for r in validator.results if not r.passed and r.severity == "warning"]
        
        assert len(errors) > 0, "Should have error-level violations"
        assert len(warnings) > 0, "Should have warning-level violations"
        
        # Verify specific checks failed
        check_names = [r.check_name for r in errors]
        assert "No Front Door" in check_names
        assert "No Network Security Perimeter" in check_names
        assert "TLS Version" in check_names


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
