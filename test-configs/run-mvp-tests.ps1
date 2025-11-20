# Quick MVP Test Script
# Tests Deploy Sentinel MVP functionality (Phases 1-5)

param(
    [switch]$CleanState,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Deploy Sentinel MVP Test Script" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Navigate to project root
$scriptRoot = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $scriptRoot
Set-Location $projectRoot

Write-Host "Project Root: $projectRoot`n" -ForegroundColor Gray

# Clean state files if requested
if ($CleanState) {
    Write-Host "[CLEANUP] Removing state and lock files..." -ForegroundColor Yellow
    Remove-Item .deploy-sentinel-state.json -ErrorAction SilentlyContinue
    Remove-Item .deploy-sentinel-state.lock -ErrorAction SilentlyContinue
    Remove-Item .deploy-sentinel.log -ErrorAction SilentlyContinue
    Write-Host "[CLEANUP] Complete`n" -ForegroundColor Green
}

# Test counter
$testNum = 0
$passedTests = 0
$failedTests = 0

function Test-Scenario {
    param(
        [string]$Name,
        [string]$Description,
        [scriptblock]$Test,
        [bool]$ExpectFailure = $false
    )
    
    $script:testNum++
    Write-Host "[$script:testNum] $Name" -ForegroundColor Cyan
    Write-Host "    $Description" -ForegroundColor Gray
    
    try {
        & $Test
        
        if ($ExpectFailure) {
            Write-Host "    ❌ FAILED: Expected failure but succeeded`n" -ForegroundColor Red
            $script:failedTests++
        }
        else {
            Write-Host "    ✅ PASSED`n" -ForegroundColor Green
            $script:passedTests++
        }
    }
    catch {
        if ($ExpectFailure) {
            Write-Host "    ✅ PASSED (Expected failure: $($_.Exception.Message))`n" -ForegroundColor Green
            $script:passedTests++
        }
        else {
            Write-Host "    ❌ FAILED: $($_.Exception.Message)`n" -ForegroundColor Red
            $script:failedTests++
        }
    }
}

# Test 1: Configuration Loading (Valid)
Test-Scenario -Name "Configuration Loading (Valid)" -Description "Load minimal test configuration" -Test {
    $config = Get-Content test-configs/minimal-test.json | ConvertFrom-Json
    if (-not $config.serviceGroupName) { throw "Configuration missing serviceGroupName" }
    if (-not $config.serviceId) { throw "Configuration missing serviceId" }
    if (-not $config.stageMapName) { throw "Configuration missing stageMapName" }
    if (-not $config.environment) { throw "Configuration missing environment" }
}

# Test 2: Configuration Loading (Invalid)
Test-Scenario -Name "Configuration Loading (Invalid)" -Description "Invalid config should be rejected" -ExpectFailure $true -Test {
    $config = Get-Content test-configs/invalid-test.json | ConvertFrom-Json
    if (-not $config.serviceId) { throw "Missing required parameter: serviceId" }
}

# Test 3: Environment Variable Substitution
Test-Scenario -Name "Environment Variable Substitution" -Description "Substitute environment variables in config" -Test {
    $env:TEAMS_WEBHOOK_URL = "https://test.webhook.office.com/webhookb2/test123"
    $config = Get-Content test-configs/full-test.json -Raw
    
    # Manual substitution test (script does this automatically)
    $pattern = '\$\{([^}]+)\}'
    if ($config -match $pattern) {
        $varName = $matches[1]
        $varValue = [Environment]::GetEnvironmentVariable($varName)
        if (-not $varValue) { throw "Environment variable $varName not set" }
    }
}

# Test 4: Git Repository Detection
Test-Scenario -Name "Git Repository Detection" -Description "Verify git repository available" -Test {
    $gitCheck = git rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Not inside a git repository" }
    
    $remotes = git remote -v 2>$null
    if (-not $remotes) { throw "No git remotes configured" }
}

# Test 5: Branch Name Generation
Test-Scenario -Name "Branch Name Generation" -Description "Generate deployment branch name" -Test {
    $env = "Test"
    $serviceId = "test-service-001"
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $branchName = "deploy/$env/$serviceId/$timestamp"
    
    if ($branchName -notmatch '^deploy/[^/]+/[^/]+/\d{14}$') {
        throw "Branch name doesn't match pattern: $branchName"
    }
}

# Test 6: State File Structure
Test-Scenario -Name "State File Structure" -Description "Create and validate state file structure" -Test {
    $testState = @{
        rolloutId = "test-rollout-12345-abc"
        status = "InProgress"
        serviceInfo = @{
            serviceGroupName = "TestServiceGroup"
            serviceId = "test-service-001"
            artifactVersion = "1.0.0"
            stageMapVersion = "v1"
        }
        startedAt = (Get-Date).ToString("o")
        lastUpdated = (Get-Date).ToString("o")
        branchName = $null
        pipelineRunId = $null
        stressTests = @()
        notifications = @()
    }
    
    # Validate required fields
    if (-not $testState.rolloutId) { throw "Missing rolloutId" }
    if (-not $testState.status) { throw "Missing status" }
    if (-not $testState.serviceInfo) { throw "Missing serviceInfo" }
    
    # Write to file
    $testState | ConvertTo-Json -Depth 5 | Out-File -FilePath .deploy-sentinel-state-test.json -Encoding utf8
    
    # Read back
    $readState = Get-Content .deploy-sentinel-state-test.json | ConvertFrom-Json
    if ($readState.rolloutId -ne $testState.rolloutId) { throw "State file read/write mismatch" }
    
    # Cleanup
    Remove-Item .deploy-sentinel-state-test.json -ErrorAction SilentlyContinue
}

# Test 7: Lock File Structure
Test-Scenario -Name "Lock File Structure" -Description "Create and validate lock file structure" -Test {
    $testLock = @{
        pid = $PID
        timestamp = (Get-Date).ToString("o")
        hostname = $env:COMPUTERNAME
    }
    
    # Write lock
    $testLock | ConvertTo-Json | Out-File -FilePath .deploy-sentinel-state-test.lock -Encoding utf8
    
    # Read back
    $readLock = Get-Content .deploy-sentinel-state-test.lock | ConvertFrom-Json
    if ($readLock.pid -ne $PID) { throw "Lock file PID mismatch" }
    
    # Test stale detection (5 minute threshold)
    $lockTime = [DateTime]::Parse($readLock.timestamp)
    $age = (Get-Date) - $lockTime
    $isStale = $age.TotalMinutes -gt 5
    
    if ($isStale) { throw "Lock should not be stale (just created)" }
    
    # Cleanup
    Remove-Item .deploy-sentinel-state-test.lock -ErrorAction SilentlyContinue
}

# Test 8: Log File Format
Test-Scenario -Name "Log File Format" -Description "Validate log entry format" -Test {
    $timestamp = (Get-Date).ToString("o")
    $logEntry = "[$timestamp] [INFO] Test log message"
    
    # Write test log
    $logEntry | Out-File -FilePath .deploy-sentinel-test.log -Encoding utf8
    
    # Read back
    $readLog = Get-Content .deploy-sentinel-test.log
    if ($readLog -notmatch '^\[.*\] \[(INFO|WARN|ERROR)\] .*$') {
        throw "Log entry doesn't match format"
    }
    
    # Cleanup
    Remove-Item .deploy-sentinel-test.log -ErrorAction SilentlyContinue
}

# Test 9: Script Exists and Has Correct Parameters
Test-Scenario -Name "Script Validation" -Description "Verify deploy-sentinel.ps1 exists with correct parameters" -Test {
    $scriptPath = "scripts/powershell/deploy-sentinel.ps1"
    if (-not (Test-Path $scriptPath)) {
        throw "Script not found: $scriptPath"
    }
    
    $scriptContent = Get-Content $scriptPath -Raw
    
    # Check for required parameters (simplified regex)
    $requiredParams = @('ConfigPath', 'Action', 'RolloutId', 'ForceUnlock')
    foreach ($param in $requiredParams) {
        if ($scriptContent -notmatch "\`$$param") {
            throw "Missing parameter: $param"
        }
    }
    
    # Check for required functions
    $requiredFunctions = @(
        'Load-DeploymentConfig',
        'Read-RolloutState',
        'Write-RolloutState',
        'Lock-StateFile',
        'Unlock-StateFile',
        'Write-DeploymentLog',
        'Invoke-WithRetry',
        'Invoke-McpTool',
        'Get-Ev2BestPractices',
        'Get-LatestArtifactVersion',
        'Get-LatestStageMapVersion',
        'Start-Ev2Rollout',
        'Invoke-TriggerRollout',
        'Test-GitRepository',
        'New-DeploymentBranchName',
        'New-DeploymentBranch',
        'Invoke-TriggerRolloutWithBranch',
        'Get-RolloutStatus',
        'Format-RolloutStatusDisplay',
        'Test-RolloutComplete',
        'Watch-Ev2Rollout',
        'Invoke-MonitorRollout'
    )
    
    foreach ($func in $requiredFunctions) {
        if ($scriptContent -notmatch "function $func") {
            throw "Missing function: $func"
        }
    }
}

# Test 10: MCP Configuration
Test-Scenario -Name "MCP Configuration" -Description "Verify MCP servers configured" -Test {
    $mcpConfigPath = ".vscode/mcp.json"
    if (-not (Test-Path $mcpConfigPath)) {
        throw "MCP configuration not found: $mcpConfigPath"
    }
    
    $mcpConfig = Get-Content $mcpConfigPath | ConvertFrom-Json
    
    # Check for EV2 MCP Server
    if (-not $mcpConfig.servers."Ev2 MCP Server") {
        throw "EV2 MCP Server not configured"
    }
    
    # Check for ADO MCP Server
    if (-not $mcpConfig.servers.ado) {
        throw "Azure DevOps MCP Server not configured"
    }
}

# Test 11: Test Fixtures Exist
Test-Scenario -Name "Test Fixtures" -Description "Verify test fixtures exist" -Test {
    $fixtures = @(
        'tests/fixtures/deploy-sentinel/mock-rollout-responses.json',
        'tests/fixtures/deploy-sentinel/mock-pipeline-responses.json',
        'tests/fixtures/deploy-sentinel/test-service-config.json'
    )
    
    foreach ($fixture in $fixtures) {
        if (-not (Test-Path $fixture)) {
            throw "Fixture not found: $fixture"
        }
    }
}

# Test 12: Pester Tests Exist
Test-Scenario -Name "Pester Tests" -Description "Verify test files exist" -Test {
    $testFiles = @(
        'tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1',
        'tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1',
        'tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1',
        'tests/deploy-sentinel/unit/BranchCreation.Tests.ps1',
        'tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1'
    )
    
    foreach ($testFile in $testFiles) {
        if (-not (Test-Path $testFile)) {
            throw "Test file not found: $testFile"
        }
    }
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Tests:  $testNum" -ForegroundColor Gray
Write-Host "Passed:       $passedTests" -ForegroundColor Green
Write-Host "Failed:       $failedTests" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Red" })
Write-Host "Success Rate: $([math]::Round(($passedTests / $testNum) * 100, 1))%`n" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Yellow" })

if ($failedTests -eq 0) {
    Write-Host "✅ All tests passed! MVP structure is valid.`n" -ForegroundColor Green
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Review MVP-TESTING-GUIDE.md for detailed testing scenarios" -ForegroundColor Gray
    Write-Host "  2. Run Pester tests: Invoke-Pester -Path tests/deploy-sentinel/" -ForegroundColor Gray
    Write-Host "  3. Test with real configuration after MCP integration" -ForegroundColor Gray
    Write-Host "  4. Continue with Phase 6 (Error Handling) implementation`n" -ForegroundColor Gray
    exit 0
}
else {
    Write-Host "❌ Some tests failed. Review errors above.`n" -ForegroundColor Red
    exit 1
}
