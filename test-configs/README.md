# Test Configurations - Deploy Sentinel MVP

This directory contains test configurations and scripts for validating the Deploy Sentinel MVP (Phases 1-5).

## Quick Start

### Run MVP Validation Tests

```powershell
# Run all validation tests
.\test-configs\run-mvp-tests.ps1

# Run with clean state (removes existing state/lock files)
.\test-configs\run-mvp-tests.ps1 -CleanState

# Run with verbose output
.\test-configs\run-mvp-tests.ps1 -Verbose
```

**Expected Result**: All 12 tests should pass, confirming MVP structure is valid.

## Test Configuration Files

### `minimal-test.json`
Minimal configuration with only required parameters:
- `serviceGroupName`: EV2 Service Group
- `serviceId`: EV2 Service ID
- `stageMapName`: EV2 Stage Map
- `environment`: Target environment (Test, PPE, PROD)
- `selectionScope`: Regions/steps/stamps/actions
- `pollingInterval`: 5 seconds (fast for testing)
- `maxRetries`: 2 (reduced for testing)

**Use Case**: Quick testing of configuration loading and parameter validation.

### `full-test.json`
Complete configuration with all optional parameters:
- All minimal config parameters
- `exclusionScope`: Regions to exclude
- `teamsWebhookUrl`: Teams notification webhook (uses environment variable)
- `repositoryId`: Azure DevOps repository for branch creation
- `stressTestConfig`: Stress test settings (disabled)
- `pipelineConfig`: Pipeline integration settings (disabled)

**Use Case**: Testing environment variable substitution and full workflow scenarios.

### `invalid-test.json`
Invalid configuration missing required parameters.

**Use Case**: Testing error handling and parameter validation.

## Test Scripts

### `run-mvp-tests.ps1`
Comprehensive validation script that tests:

1. **Configuration Loading** (valid and invalid)
2. **Environment Variable Substitution** (`${VAR_NAME}` pattern)
3. **Git Repository Detection** (command availability, remotes)
4. **Branch Name Generation** (pattern validation)
5. **State File Structure** (JSON format, required fields)
6. **Lock File Structure** (PID, timestamp, stale detection)
7. **Log File Format** (ISO 8601 timestamps, levels)
8. **Script Validation** (parameters, functions)
9. **MCP Configuration** (servers configured)
10. **Test Fixtures** (mock responses exist)
11. **Pester Tests** (test files exist)

**Success Criteria**: 12/12 tests pass (100%)

## Manual Testing

See `specs/005-deploy-sentinel/MVP-TESTING-GUIDE.md` for detailed manual testing scenarios:

### Scenario 1: Configuration Loading
```powershell
.\scripts\powershell\deploy-sentinel.ps1 `
    -Action trigger `
    -ConfigPath test-configs\minimal-test.json `
    -Verbose
```

### Scenario 2: State File Management
```powershell
# Create test state manually
$testState = @{
    rolloutId = "test-rollout-12345-abc"
    status = "InProgress"
    # ... (see MVP-TESTING-GUIDE.md for full structure)
} | ConvertTo-Json -Depth 5 | Out-File .deploy-sentinel-state.json

# Monitor existing rollout
.\scripts\powershell\deploy-sentinel.ps1 `
    -Action monitor `
    -ConfigPath test-configs\minimal-test.json
```

### Scenario 3: Branch Creation
```powershell
.\scripts\powershell\deploy-sentinel.ps1 `
    -Action create-branch `
    -ConfigPath test-configs\full-test.json
```

## Environment Variables

For testing environment variable substitution in `full-test.json`:

```powershell
# Set test environment variables
$env:TEAMS_WEBHOOK_URL = "https://yourorg.webhook.office.com/webhookb2/test123"
$env:ADO_PROJECT_NAME = "YourProject"
```

## Pester Tests

Run Pester tests to validate individual components:

```powershell
# Run all deploy-sentinel tests
Invoke-Pester -Path tests/deploy-sentinel/ -Output Detailed

# Run specific test suite
Invoke-Pester -Path tests/deploy-sentinel/unit/BranchCreation.Tests.ps1 -Output Detailed

# Run with code coverage
Invoke-Pester -Path tests/deploy-sentinel/ `
    -CodeCoverage scripts/powershell/deploy-sentinel.ps1 `
    -Output Detailed
```

**Note**: Most Pester tests are currently **skipped** (`Set-ItResult -Skipped`) because:
1. MCP tool integration is placeholder (not yet implemented)
2. Script needs refactoring to separate functions from main entry point

## Current Limitations

### MCP Tool Integration
The `Invoke-McpTool` function is a placeholder that throws "not yet implemented". Real MCP API integration is pending.

**Impact**: Scripts will fail at the MCP tool call, but can validate:
- Configuration loading
- Parameter validation
- State file management
- Lock file handling
- Git validation
- Branch name generation

### Test Execution
All Pester tests are skipped until:
1. MCP tool integration complete
2. Script refactored for isolated function testing

### No Real API Calls
Cannot test actual EV2/ADO interactions without MCP integration.

**Workaround**: Contract tests use mock fixtures to verify response parsing logic.

## Success Criteria

### MVP Validation ✅
- [x] All 12 validation tests pass
- [x] Configuration loads successfully
- [x] Environment variable substitution works
- [x] Git repository detected
- [x] Branch names generated correctly
- [x] State/lock file structures valid
- [x] Log format correct
- [x] All functions exist in script
- [x] MCP servers configured
- [x] Test fixtures present
- [x] Pester test files exist

### Next Steps
1. Implement MCP tool integration
2. Refactor script for testing
3. Unskip and run all Pester tests
4. Test with real EV2 service
5. Continue with Phase 6 (Error Handling)

## Troubleshooting

### Test Failures

If validation tests fail, check:

```powershell
# 1. Verify project structure
Get-ChildItem -Recurse | Where-Object { $_.Name -like "*deploy-sentinel*" }

# 2. Check script exists
Test-Path scripts/powershell/deploy-sentinel.ps1

# 3. Verify MCP config
Test-Path .vscode/mcp.json

# 4. Check test fixtures
Get-ChildItem tests/fixtures/deploy-sentinel/
```

### State File Issues

```powershell
# Clean state files
Remove-Item .deploy-sentinel-state.json -ErrorAction SilentlyContinue
Remove-Item .deploy-sentinel-state.lock -ErrorAction SilentlyContinue
Remove-Item .deploy-sentinel.log -ErrorAction SilentlyContinue

# Run tests with clean state
.\test-configs\run-mvp-tests.ps1 -CleanState
```

### Git Issues

```powershell
# Verify git installed
git --version

# Check repository status
git status

# Verify remotes
git remote -v
```

## Documentation

- **MVP Testing Guide**: `specs/005-deploy-sentinel/MVP-TESTING-GUIDE.md`
- **Feature Specification**: `specs/005-deploy-sentinel/spec.md`
- **Task Breakdown**: `specs/005-deploy-sentinel/tasks.md`
- **Data Model**: `specs/005-deploy-sentinel/data-model.md`
- **Technical Plan**: `specs/005-deploy-sentinel/plan.md`

## Support

For issues or questions:
1. Review `MVP-TESTING-GUIDE.md` for detailed scenarios
2. Check `tasks.md` for implementation status
3. Review `plan.md` for architecture details
4. See `.deploy-sentinel-config.json` for parameter documentation
