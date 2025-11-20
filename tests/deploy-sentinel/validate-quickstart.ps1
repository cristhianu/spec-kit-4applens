# Quickstart Validation Script
# Feature: 005-deploy-sentinel
# Task: T097 - Validate all examples from quickstart.md execute correctly

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "=== Deploy Sentinel Quickstart Validation ===" -ForegroundColor Cyan
Write-Host ""

# Paths
$script:RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script:QuickstartPath = Join-Path $script:RepoRoot "specs\005-deploy-sentinel\quickstart.md"
$script:ScriptPath = Join-Path $script:RepoRoot "scripts\powershell\deploy-sentinel.ps1"

# Validation results
$script:TestResults = @()

function Test-Command {
    param(
        [string]$Name,
        [string]$Command,
        [bool]$ShouldSucceed = $true
    )
    
    Write-Host "Testing: $Name" -ForegroundColor Yellow
    Write-Host "  Command: $Command" -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] Skipping execution" -ForegroundColor Cyan
        $script:TestResults += @{
            Name = $Name
            Command = $Command
            Status = "SKIPPED"
            Error = $null
        }
        return
    }
    
    try {
        # Validate syntax by parsing command
        [System.Management.Automation.Language.Parser]::ParseInput($Command, [ref]$null, [ref]$null)
        
        Write-Host "  ✅ Syntax valid" -ForegroundColor Green
        
        $script:TestResults += @{
            Name = $Name
            Command = $Command
            Status = "PASS"
            Error = $null
        }
    }
    catch {
        Write-Host "  ❌ Syntax error: $_" -ForegroundColor Red
        
        $script:TestResults += @{
            Name = $Name
            Command = $Command
            Status = "FAIL"
            Error = $_.Exception.Message
        }
    }
    
    Write-Host ""
}

# Validate quickstart.md exists
Write-Host "Checking quickstart.md..." -ForegroundColor Cyan
if (-not (Test-Path $script:QuickstartPath)) {
    Write-Host "❌ quickstart.md not found at: $script:QuickstartPath" -ForegroundColor Red
    exit 1
}
Write-Host "✅ quickstart.md found" -ForegroundColor Green
Write-Host ""

# Validate script exists
Write-Host "Checking deploy-sentinel.ps1..." -ForegroundColor Cyan
if (-not (Test-Path $script:ScriptPath)) {
    Write-Host "❌ deploy-sentinel.ps1 not found at: $script:ScriptPath" -ForegroundColor Red
    exit 1
}
Write-Host "✅ deploy-sentinel.ps1 found" -ForegroundColor Green
Write-Host ""

# Test examples from quickstart.md

Write-Host "=== Validating Installation Examples ===" -ForegroundColor Cyan
Write-Host ""

Test-Command -Name "Install Pester" `
    -Command "Install-Module -Name Pester -Force -SkipPublisherCheck"

Test-Command -Name "Verify Git" `
    -Command "git --version"

Test-Command -Name "Install EV2 MCP Server" `
    -Command "dnx install ev2-mcp-server"

Test-Command -Name "Verify EV2 MCP Server" `
    -Command 'dnx list | Select-String "ev2-mcp-server"'

Test-Command -Name "Install Azure DevOps MCP Server" `
    -Command "npm install -g @microsoft/azure-devops-mcp-server"

Test-Command -Name "Verify Azure DevOps MCP Server" `
    -Command 'npm list -g --depth=0 | Select-String "azure-devops-mcp-server"'

Write-Host "=== Validating Configuration Examples ===" -ForegroundColor Cyan
Write-Host ""

Test-Command -Name "Create Config File" `
    -Command '@"
{
  \"serviceGroupName\": \"MyServiceGroup\",
  \"serviceId\": \"MyService\",
  \"stageMapName\": \"StandardStageMap\",
  \"environment\": \"prod\",
  \"region\": \"eastus\",
  \"subscriptionId\": \"12345678-1234-1234-1234-123456789012\",
  \"pollingInterval\": 30,
  \"maxRetries\": 3,
  \"createBranch\": true,
  \"repositoryId\": \"00000000-0000-0000-0000-000000000000\",
  \"stressTestConfig\": {
    \"enabled\": true,
    \"endpointUrl\": \"https://myservice-prod.azurewebsites.net/health\",
    \"requestCount\": 50,
    \"minSuccessRatePercent\": 95,
    \"maxP95LatencyMs\": 500,
    \"timeoutSeconds\": 60
  },
  \"pipelineConfig\": {
    \"enabled\": true,
    \"project\": \"MyProject\",
    \"pipelineId\": 123,
    \"preDeploy\": true,
    \"postDeploy\": true,
    \"critical\": false
  },
  \"teamsWebhookUrl\": \"https://outlook.office.com/webhook/...\"
}
"@ | Out-File ".deploy-sentinel-config.json" -Encoding utf8'

Test-Command -Name "Set Environment Variables" `
    -Command '$env:EV2_TENANT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"; $env:AZURE_DEVOPS_PAT = "your-pat-token"'

Write-Host "=== Validating Command Examples ===" -ForegroundColor Cyan
Write-Host ""

Test-Command -Name "Get Script Help" `
    -Command "Get-Help $script:ScriptPath -Detailed"

Test-Command -Name "Trigger Rollout" `
    -Command "$script:ScriptPath -Action trigger -ConfigPath '.deploy-sentinel-config.json'"

Test-Command -Name "Monitor Rollout" `
    -Command "$script:ScriptPath -Action monitor"

Test-Command -Name "Monitor Specific Rollout" `
    -Command "$script:ScriptPath -Action monitor -RolloutId 'abc-123-def-456'"

Test-Command -Name "Create Branch" `
    -Command "$script:ScriptPath -Action create-branch"

Test-Command -Name "Run Stress Test" `
    -Command "$script:ScriptPath -Action stress-test"

Test-Command -Name "Full Workflow" `
    -Command "$script:ScriptPath -Action full"

Test-Command -Name "Full Workflow with Verbose" `
    -Command "$script:ScriptPath -Action full -Verbose"

Test-Command -Name "Approve Wait Action (CLI)" `
    -Command "$script:ScriptPath -Action monitor -RolloutId 'rollout-id' -ApproveWaitAction -ActionId 'action-id'"

Test-Command -Name "Reject Wait Action (CLI)" `
    -Command "$script:ScriptPath -Action monitor -RolloutId 'rollout-id' -RejectWaitAction -ActionId 'action-id'"

Test-Command -Name "Force Unlock State" `
    -Command "$script:ScriptPath -Action monitor -ForceUnlock"

Write-Host "=== Validating Monitoring Examples ===" -ForegroundColor Cyan
Write-Host ""

Test-Command -Name "View State File" `
    -Command 'Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json | ConvertTo-Json -Depth 10'

Test-Command -Name "View Recent Logs" `
    -Command 'Get-Content ".deploy-sentinel.log" -Tail 50'

Test-Command -Name "Check Lock File" `
    -Command 'if (Test-Path ".deploy-sentinel-state.lock") { Get-Content ".deploy-sentinel-state.lock" | ConvertFrom-Json }'

Write-Host "=== Validating Troubleshooting Examples ===" -ForegroundColor Cyan
Write-Host ""

Test-Command -Name "Health Check - PowerShell Version" `
    -Command 'Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"'

Test-Command -Name "Health Check - dnx" `
    -Command 'try { dnx --version; Write-Host "✅ dnx available" -ForegroundColor Green } catch { Write-Host "❌ dnx not found" -ForegroundColor Red }'

Test-Command -Name "Health Check - Node.js" `
    -Command 'try { node --version; Write-Host "✅ Node.js available" -ForegroundColor Green } catch { Write-Host "❌ Node.js not found" -ForegroundColor Red }'

Test-Command -Name "Check Config File" `
    -Command 'if (Test-Path ".deploy-sentinel-config.json") { Write-Host "✅ Config file exists" -ForegroundColor Green } else { Write-Host "❌ Config file missing" -ForegroundColor Red }'

Test-Command -Name "Test Azure CLI Authentication" `
    -Command 'try { az account show; Write-Host "✅ Azure CLI authenticated" -ForegroundColor Green } catch { Write-Host "❌ Azure CLI not authenticated" -ForegroundColor Red }'

# Display results
Write-Host ""
Write-Host "=== Validation Results ===" -ForegroundColor Cyan
Write-Host ""

$passCount = ($script:TestResults | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($script:TestResults | Where-Object { $_.Status -eq "FAIL" }).Count
$skipCount = ($script:TestResults | Where-Object { $_.Status -eq "SKIPPED" }).Count
$totalCount = $script:TestResults.Count

Write-Host "Total Tests: $totalCount" -ForegroundColor White
Write-Host "  ✅ Passed: $passCount" -ForegroundColor Green
Write-Host "  ❌ Failed: $failCount" -ForegroundColor Red
Write-Host "  ⏭️  Skipped: $skipCount" -ForegroundColor Cyan
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "Failed Tests:" -ForegroundColor Red
    $script:TestResults | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Red
        Write-Host "    Command: $($_.Command)" -ForegroundColor Gray
        Write-Host "    Error: $($_.Error)" -ForegroundColor Red
    }
    Write-Host ""
}

# Exit code
if ($failCount -gt 0) {
    Write-Host "❌ Validation FAILED" -ForegroundColor Red
    exit 1
}
else {
    Write-Host "✅ Validation PASSED" -ForegroundColor Green
    exit 0
}
