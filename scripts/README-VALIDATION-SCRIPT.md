# Bicep Architecture Validation Script

Automated validation script for Secure Future Initiative (SFI) compliance in Bicep templates.

## Overview

The `bicep-validate-architecture.py` script checks generated Bicep templates against organizational security and architecture standards documented in the learnings database. It provides automated verification of SFI compliance patterns to prevent common security misconfigurations.

## Features

- **8 Automated Checks**: Validates critical SFI compliance patterns
- **CI/CD Integration**: Exit codes enable pipeline automation
- **Line-Level Reporting**: Pinpoints exact violations for quick remediation
- **Flexible Output**: Human-readable or JSON format
- **Configurable Validation**: Optional flags for specific scenarios

## Installation

No installation required - the script uses Python 3.11+ standard library only.

```bash
# Make executable (Linux/macOS)
chmod +x scripts/bicep-validate-architecture.py

# Run directly
python scripts/bicep-validate-architecture.py <bicep-file>
```

## Usage

### Basic Validation

```bash
python scripts/bicep-validate-architecture.py main.bicep
```

**Output**:
```
🔍 Validating: main.bicep
================================================================================

✅ PASSED:
  • No Front Door: No Azure Front Door resources found ✓
  • No Network Security Perimeter: No Network Security Perimeter resources found ✓
  • Private Endpoints Recommended: Private Endpoints configured ✓
  • Public Network Access Disabled: All data services have publicNetworkAccess disabled ✓
  • VNet Integration: VNet integration configured ✓
  • Managed Identity: Managed Identity configured ✓
  • TLS Version: TLS 1.2+ enforced ✓
  • HTTPS Only: HTTPS-only configured for web services ✓

================================================================================

✅ VALIDATION PASSED: 8/8 checks passed, 0 warnings
```

### Verbose Output

Show detailed information about all checks:

```bash
python scripts/bicep-validate-architecture.py main.bicep --verbose
```

### JSON Output

Machine-readable output for integration with other tools:

```bash
python scripts/bicep-validate-architecture.py main.bicep --json
```

**Output**:
```json
{
  "file": "main.bicep",
  "passed": true,
  "results": [
    {
      "check_name": "No Front Door",
      "passed": true,
      "message": "No Azure Front Door resources found ✓",
      "severity": "info",
      "line_number": null,
      "resource_name": null
    },
    ...
  ]
}
```

### Allow Front Door

For CDN scenarios where Front Door is intentionally required:

```bash
python scripts/bicep-validate-architecture.py main.bicep --allow-front-door
```

## Validation Checks

### 1. No Azure Front Door (Error)

**Check**: Azure Front Door should only be used when explicitly requested for global CDN scenarios.

**Why**: Most applications don't need global distribution. Regional deployments with Private Endpoints provide better security and lower latency for single-region workloads.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Networking category

**Example Violation**:
```bicep
resource frontDoor 'Microsoft.Cdn/profiles@2021-06-01' = {
  name: 'fd-profile'
  location: 'global'
}
```

**Fix**: Remove Front Door unless required. Use regional Load Balancer or Application Gateway instead.

**Override**: Use `--allow-front-door` flag if Front Door is intentional.

---

### 2. No Network Security Perimeter (Error)

**Check**: Network Security Perimeter should not be used. Prefer Private Endpoints with VNet integration.

**Why**: Private Endpoints provide more granular control and better align with zero-trust architecture. NSP is a legacy pattern being phased out.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Networking category

**Example Violation**:
```bicep
resource nsp 'Microsoft.Network/networkSecurityPerimeters@2021-02-01-preview' = {
  name: 'nsp'
  location: 'eastus'
}
```

**Fix**: Replace with Private Endpoints:
```bicep
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-storage'
  location: 'eastus'
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [...]
  }
}
```

---

### 3. Private Endpoints Recommended (Warning)

**Check**: Data services (Storage, SQL, KeyVault, Cosmos, etc.) should use Private Endpoints.

**Why**: Private Endpoints ensure data services are accessible only within your VNet, preventing public internet exposure.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Security category

**Example Warning**: Storage account without Private Endpoint

**Fix**: Add Private Endpoint configuration for all data services.

---

### 4. Public Network Access Disabled (Error)

**Check**: Data services must have `publicNetworkAccess: 'Disabled'`.

**Why**: Disabling public access ensures services are only accessible via Private Endpoints, preventing data exfiltration.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Security category

**Example Violation**:
```bicep
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  properties: {
    publicNetworkAccess: 'Enabled'  // ❌ VIOLATION
  }
}
```

**Fix**:
```bicep
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  properties: {
    publicNetworkAccess: 'Disabled'  // ✅ CORRECT
  }
}
```

**Applies To**:
- Microsoft.Storage/storageAccounts
- Microsoft.Sql/servers
- Microsoft.KeyVault/vaults
- Microsoft.DocumentDB/databaseAccounts (Cosmos DB)
- Microsoft.DBforMySQL/servers
- Microsoft.DBforPostgreSQL/servers
- Microsoft.Cache/redis

---

### 5. VNet Integration (Warning)

**Check**: Compute services should be deployed within a VNet with proper subnet integration.

**Why**: VNet integration provides network isolation and secure communication between services without traversing the public internet.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Networking category

**Example Warning**: App Service without VNet integration

**Fix**:
```bicep
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  properties: {
    virtualNetworkSubnetId: subnet.id
    vnetRouteAllEnabled: true
  }
}
```

**Applies To**:
- Microsoft.Web/sites (App Service)
- Microsoft.Web/sites/slots
- Microsoft.ContainerApp/containerApps
- Microsoft.Compute/virtualMachines

---

### 6. Managed Identity (Warning)

**Check**: Compute services should use SystemAssigned or UserAssigned Managed Identity for authentication.

**Why**: Managed Identity eliminates the need for storing credentials in code or configuration, reducing security risks.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Security category

**Example Warning**: App Service without Managed Identity

**Fix**:
```bicep
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  identity: {
    type: 'SystemAssigned'
  }
}
```

---

### 7. TLS Version (Error)

**Check**: TLS 1.2 or higher must be enforced for all services.

**Why**: TLS 1.0 and 1.1 have known vulnerabilities and should not be used.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Security category

**Example Violation**:
```bicep
properties: {
  minimumTlsVersion: 'TLS1_0'  // ❌ VIOLATION
}
```

**Fix**:
```bicep
properties: {
  minimumTlsVersion: 'TLS1_2'  // ✅ CORRECT
}
```

**Property Names**:
- `minimumTlsVersion` (Storage)
- `minimalTlsVersion` (SQL)
- `minTlsVersion` (App Service)

---

### 8. HTTPS Only (Warning)

**Check**: Web services must have `httpsOnly: true` to redirect HTTP traffic to HTTPS.

**Why**: Ensures all web traffic is encrypted, preventing man-in-the-middle attacks.

**Learnings Reference**: `.specify/learnings/bicep-learnings.md` - Compute category

**Example Warning**:
```bicep
properties: {
  httpsOnly: false  // ⚠️ WARNING
}
```

**Fix**:
```bicep
properties: {
  httpsOnly: true  // ✅ CORRECT
}
```

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | All validation checks passed |
| `1` | Validation Failed | One or more error-level violations found |
| `2` | Script Error | Invalid arguments, file not found, or internal error |

## CI/CD Integration

### Azure Pipelines

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    python scripts/bicep-validate-architecture.py main.bicep --json > validation-results.json
  displayName: 'Validate Bicep Architecture'
  continueOnError: false

- task: PublishBuildArtifacts@1
  inputs:
    PathtoPublish: 'validation-results.json'
    ArtifactName: 'validation-results'
  condition: always()
```

### GitHub Actions

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'

- name: Validate Bicep Architecture
  run: |
    python scripts/bicep-validate-architecture.py main.bicep
  continue-on-error: false

- name: Upload validation results (if failed)
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: validation-results
    path: validation-results.json
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Find all modified .bicep files
bicep_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.bicep$')

if [ -n "$bicep_files" ]; then
    echo "🔍 Validating Bicep templates..."
    for file in $bicep_files; do
        python scripts/bicep-validate-architecture.py "$file" || exit 1
    done
    echo "✅ All Bicep templates passed validation"
fi
```

## Testing

The validation script has comprehensive unit tests covering all validation checks.

### Run Tests

```bash
# Run all validation script tests
pytest tests/unit/test_bicep_validate_architecture.py -v

# Run with coverage
pytest tests/unit/test_bicep_validate_architecture.py --cov=scripts --cov-report=html
```

### Test Fixtures

Test fixtures are available in `tests/fixtures/`:

- **sample-compliant.bicep**: SFI-compliant template (all checks pass)
- **sample-non-compliant.bicep**: Non-compliant template (violations for testing)

### Test Coverage

21 unit tests covering:
- Validator initialization
- All 8 validation checks (positive and negative cases)
- CLI flags (--allow-front-door, --verbose, --json)
- Output formats (text and JSON)
- Integration with fixture files

**Test Results**: 21/21 passing in <1s ✅

## Development

### Adding New Checks

1. Add check method to `BicepValidator` class:
   ```python
   def check_new_pattern(self) -> None:
       """Check for new SFI pattern."""
       # Implementation
       self.results.append(ValidationResult(...))
   ```

2. Call from `validate()` method:
   ```python
   def validate(self) -> bool:
       self.check_no_front_door()
       self.check_new_pattern()  # Add here
       # ...
   ```

3. Add unit tests in `tests/unit/test_bicep_validate_architecture.py`

4. Update this README with check documentation

### Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style (follows Black formatter)
- Testing requirements (pytest with >80% coverage)
- Documentation standards
- Pull request process

## Troubleshooting

### False Positives

**Issue**: Check reports violation but configuration is correct

**Solution**: Verify the check logic matches your template syntax. Some Azure resources have multiple property names for the same setting (e.g., `minimumTlsVersion` vs `minimalTlsVersion` vs `minTlsVersion`).

### Missing Detections

**Issue**: Known violation not detected

**Solution**: Check that resource type pattern matches your template. Add regex pattern to appropriate `*_TYPES` constant if needed.

### Performance

**Issue**: Script takes too long on large templates

**Solution**: The script uses line-by-line parsing optimized for large files. For templates >10,000 lines, consider breaking into modules.

## Related Tools

- **Bicep Linter**: Built-in Bicep validation (`az bicep lint`)
- **Azure Policy**: Runtime compliance checking
- **PSRule for Azure**: Infrastructure-as-code testing framework
- **Checkov**: Multi-cloud policy-as-code tool

This script complements these tools by focusing specifically on SFI patterns from your organization's learnings database.

## Support

For issues or questions:
- Check existing learnings: `.specify/learnings/bicep-learnings.md`
- Review SFI patterns: `specs/004-bicep-learnings-database/contracts/sfi-patterns.md`
- Open GitHub issue with template snippet and validation output

## License

See `LICENSE` file in repository root.
