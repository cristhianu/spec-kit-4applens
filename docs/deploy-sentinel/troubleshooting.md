# Troubleshooting Guide

This guide provides solutions to common issues encountered when using Deploy Sentinel.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [State File Issues](#state-file-issues)
- [Authentication Issues](#authentication-issues)
- [MCP Server Issues](#mcp-server-issues)
- [Rollout Issues](#rollout-issues)
- [Stress Testing Issues](#stress-testing-issues)
- [Pipeline Integration Issues](#pipeline-integration-issues)
- [Approval Gate Issues](#approval-gate-issues)
- [Teams Notification Issues](#teams-notification-issues)
- [Performance Issues](#performance-issues)
- [Error Reference](#error-reference)

## Quick Diagnostics

### Check Current State

```powershell
# View state file
Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json | ConvertTo-Json -Depth 10

# View recent logs
Get-Content ".deploy-sentinel.log" -Tail 50

# Check lock file
if (Test-Path ".deploy-sentinel-state.lock") {
    Get-Content ".deploy-sentinel-state.lock" | ConvertFrom-Json
}
```

### Basic Health Check

```powershell
# Run this script to check system health
Write-Host "=== Deploy Sentinel Health Check ===" -ForegroundColor Cyan

# PowerShell version
Write-Host "`nPowerShell Version: $($PSVersionTable.PSVersion)" -ForegroundColor Yellow

# MCP tools
Write-Host "`nMCP Tools:" -ForegroundColor Yellow
try { dnx --version; Write-Host "  ✅ dnx available" -ForegroundColor Green } 
catch { Write-Host "  ❌ dnx not found" -ForegroundColor Red }

try { node --version; Write-Host "  ✅ Node.js available" -ForegroundColor Green } 
catch { Write-Host "  ❌ Node.js not found" -ForegroundColor Red }

# Configuration
Write-Host "`nConfiguration:" -ForegroundColor Yellow
if (Test-Path ".deploy-sentinel-config.json") {
    Write-Host "  ✅ Config file exists" -ForegroundColor Green
} else {
    Write-Host "  ❌ Config file missing" -ForegroundColor Red
}

# State and logs
Write-Host "`nState & Logs:" -ForegroundColor Yellow
if (Test-Path ".deploy-sentinel-state.json") {
    Write-Host "  ✅ State file exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ State file missing (expected for first run)" -ForegroundColor Yellow
}

if (Test-Path ".deploy-sentinel.log") {
    $logSize = (Get-Item ".deploy-sentinel.log").Length / 1KB
    Write-Host "  ✅ Log file exists ($([Math]::Round($logSize, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ Log file missing" -ForegroundColor Yellow
}
```

## State File Issues

### Issue: "Unable to acquire state file lock"

**Symptoms:**
```
Error: Unable to acquire state file lock. Another instance may be running.
```

**Causes:**
- Another Deploy Sentinel instance is running
- Previous instance crashed without releasing lock
- Stale lock file (>5 minutes old)

**Solutions:**

1. **Check for running instances:**
```powershell
# Find running deploy-sentinel processes
Get-Process | Where-Object { $_.CommandLine -like "*deploy-sentinel*" }

# If found, wait for completion or terminate
Stop-Process -Id <PID>
```

2. **Check lock file details:**
```powershell
if (Test-Path ".deploy-sentinel-state.lock") {
    $lock = Get-Content ".deploy-sentinel-state.lock" | ConvertFrom-Json
    Write-Host "Lock held by PID: $($lock.pid)"
    Write-Host "Hostname: $($lock.hostname)"
    Write-Host "Locked at: $($lock.timestamp)"
    
    # Check if process still exists
    $process = Get-Process -Id $lock.pid -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "Process not found - stale lock detected"
    }
}
```

3. **Force unlock (use cautiously):**
```powershell
# Remove stale lock manually
Remove-Item ".deploy-sentinel-state.lock" -Force

# Or use -ForceUnlock parameter
.\deploy-sentinel.ps1 -Action monitor -ForceUnlock
```

**Prevention:**
- Don't run multiple instances simultaneously
- Ensure proper error handling in automation
- Monitor lock file age in production

### Issue: "State file corrupted"

**Symptoms:**
```
Error: Unable to parse state file
ConvertFrom-Json: Invalid JSON format
```

**Solutions:**

1. **Backup and inspect:**
```powershell
# Backup current state
Copy-Item ".deploy-sentinel-state.json" ".deploy-sentinel-state.json.backup"

# Inspect content
Get-Content ".deploy-sentinel-state.json" | Out-Host

# Validate JSON
try {
    Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json
    Write-Host "JSON is valid"
} catch {
    Write-Host "JSON is invalid: $_"
}
```

2. **Recreate state file:**
```powershell
# If you know the rollout ID
$state = @{
    rolloutId = "your-rollout-id"
    status = "InProgress"
    serviceInfo = @{
        serviceId = "your-service"
        artifactVersion = "unknown"
        stageMapVersion = "unknown"
    }
    startedAt = (Get-Date).ToString("o")
    lastUpdated = (Get-Date).ToString("o")
    branchName = $null
    pipelineRunId = $null
    stressTests = @()
    notifications = @()
} | ConvertTo-Json -Depth 10

$state | Out-File ".deploy-sentinel-state.json" -Encoding utf8
```

3. **Delete and start fresh:**
```powershell
# Remove corrupted state
Remove-Item ".deploy-sentinel-state.json" -Force

# Continue monitoring with explicit rollout ID
.\deploy-sentinel.ps1 -Action monitor -RolloutId "your-rollout-id"
```

## Authentication Issues

### Issue: "Azure authentication failed"

**Symptoms:**
```
Error: Unable to authenticate to Azure
Error: AADSTS700016: Application not found
```

**Solutions:**

1. **Check authentication method:**
```powershell
# Test MSI (for Azure VMs)
$response = Invoke-WebRequest -Uri "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" -Headers @{Metadata="true"} -UseBasicParsing
if ($response.StatusCode -eq 200) {
    Write-Host "✅ MSI available"
} else {
    Write-Host "❌ MSI not available"
}

# Test Azure CLI
try {
    az account show
    Write-Host "✅ Azure CLI authenticated"
} catch {
    Write-Host "❌ Azure CLI not authenticated"
}
```

2. **Configure Service Principal:**
```powershell
# Set environment variables
$env:AZURE_TENANT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
$env:AZURE_CLIENT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
$env:AZURE_CLIENT_SECRET = "your-client-secret"

# Verify they're set
Get-ChildItem env: | Where-Object Name -like "AZURE_*"
```

3. **Test authentication manually:**
```powershell
# Using Azure CLI
az login --service-principal -u $env:AZURE_CLIENT_ID -p $env:AZURE_CLIENT_SECRET --tenant $env:AZURE_TENANT_ID

# Verify subscription access
az account list
```

**Prevention:**
- Document authentication method in deployment guide
- Use MSI for production Azure VM deployments
- Rotate Service Principal secrets regularly
- Test authentication before deployments

### Issue: "Azure DevOps authentication failed"

**Symptoms:**
```
Error: TF400813: Resource not available for anonymous access
Error: VS403403: The provided token is invalid
```

**Solutions:**

1. **Check PAT validity:**
```powershell
# Verify PAT is set
if ($env:AZURE_DEVOPS_PAT) {
    Write-Host "✅ PAT is set (length: $($env:AZURE_DEVOPS_PAT.Length))"
} else {
    Write-Host "❌ PAT not set"
}

# Test Azure DevOps connection
$headers = @{
    Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$($env:AZURE_DEVOPS_PAT)"))
}
$response = Invoke-WebRequest -Uri "$env:AZURE_DEVOPS_ORG_URL/_apis/projects?api-version=6.0" -Headers $headers -UseBasicParsing
Write-Host "Response: $($response.StatusCode)"
```

2. **Regenerate PAT:**
   - Navigate to Azure DevOps → User Settings → Personal Access Tokens
   - Create new token with required scopes:
     - **Code**: Read & Write
     - **Build**: Read & Execute
   - Update environment variable:
   ```powershell
   $env:AZURE_DEVOPS_PAT = "new-token-value"
   ```

3. **Verify PAT scopes:**
   - Check existing PAT scopes in Azure DevOps portal
   - Ensure not expired
   - Confirm organization access

## MCP Server Issues

### Issue: "MCP tool not found"

**Symptoms:**
```
Error: The term 'Invoke-McpTool' is not recognized
Error: mcp_ev2_mcp_serve_get_rollout_details not found
```

**Solutions:**

1. **Verify MCP server installation:**
```powershell
# Check EV2 MCP Server
dnx tool list -g | Select-String "mcp-server-ev2"

# Check Azure DevOps MCP Server
npm list -g mcp-server-azuredevops
```

2. **Install missing servers:**
```powershell
# Install EV2 MCP Server
dnx tool install -g mcp-server-ev2

# Install Azure DevOps MCP Server
npm install -g mcp-server-azuredevops
```

3. **Check PATH configuration:**
```powershell
# Verify tools are in PATH
$env:PATH -split ";" | Where-Object { $_ -like "*dotnet*" -or $_ -like "*npm*" }

# Add to PATH if needed (temporary)
$env:PATH += ";$env:USERPROFILE\.dotnet\tools"
$env:PATH += ";$env:APPDATA\npm"
```

See [MCP Setup Guide](mcp-setup.md) for detailed installation instructions.

### Issue: "MCP server timeout"

**Symptoms:**
```
Error: Operation timed out after 30 seconds
Error: No response from MCP server
```

**Solutions:**

1. **Check network connectivity:**
```powershell
# Test Azure connectivity
Test-NetConnection management.azure.com -Port 443

# Test Azure DevOps connectivity
Test-NetConnection dev.azure.com -Port 443
```

2. **Increase timeout (if available):**
```powershell
# Modify retry configuration in deploy-sentinel.ps1
# Or use environment variable
$env:MCP_TIMEOUT_SECONDS = 60
```

3. **Check MCP server logs:**
```powershell
# EV2 MCP Server logs location (varies by installation)
Get-Content "$env:TEMP\mcp-server-ev2.log" -Tail 50

# Azure DevOps MCP Server
Get-Content "$env:TEMP\mcp-server-azuredevops.log" -Tail 50
```

## Rollout Issues

### Issue: "Rollout failed to start"

**Symptoms:**
```
Error: Unable to start rollout
Error: Invalid artifact version
Error: Stage map not found
```

**Solutions:**

1. **Verify configuration:**
```powershell
# Check required fields
$config = Get-Content ".deploy-sentinel-config.json" | ConvertFrom-Json
$required = @("serviceGroupName", "serviceId", "stageMapName", "environment")
foreach ($field in $required) {
    if (-not $config.$field) {
        Write-Host "❌ Missing: $field" -ForegroundColor Red
    } else {
        Write-Host "✅ $field = $($config.$field)" -ForegroundColor Green
    }
}
```

2. **Check artifact availability:**
```powershell
# Manually query artifact versions
# (would use MCP tool directly)
# Verify artifact exists in expected location
```

3. **Validate stage map:**
```powershell
# Check stage map name spelling
# Verify stage map version exists
# Confirm stage map is in correct format
```

### Issue: "Rollout stuck in InProgress"

**Symptoms:**
- Status never changes
- No stage transitions
- Polling timeout reached

**Solutions:**

1. **Check rollout status directly:**
```powershell
# View status in EV2 portal
# Or query via MCP tool
$status = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_rollout_details" -Parameters @{ rolloutId = "your-rollout-id" }
$status | ConvertTo-Json -Depth 10
```

2. **Check for wait actions:**
```powershell
# Look for wait actions requiring approval
# Check if rollout is blocked on manual approval
```

3. **Verify deployment progress:**
```powershell
# Check Azure resource deployment status
az deployment group list --resource-group <rg> --query "[?name=='<deployment-name>']"

# Check for errors in Azure Activity Log
az monitor activity-log list --resource-group <rg> --max-events 50 --query "[?level=='Error']"
```

### Issue: "Rollout cancellation failed"

**Symptoms:**
```
Error: Unable to cancel rollout
Error: Rollout already in terminal state
```

**Solutions:**

1. **Verify rollout state:**
```powershell
# Check if already completed/failed/cancelled
$state = Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json
Write-Host "Current status: $($state.status)"
```

2. **Try cancellation via portal:**
   - Navigate to EV2 portal
   - Find rollout
   - Cancel manually

3. **Force state update:**
```powershell
# Update local state to match reality
$state = Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json
$state.status = "Cancelled"
$state.lastUpdated = (Get-Date).ToString("o")
$state | ConvertTo-Json -Depth 10 | Out-File ".deploy-sentinel-state.json" -Encoding utf8
```

## Stress Testing Issues

### Issue: "Stress test always fails"

**Symptoms:**
- Success rate below threshold
- High latency percentiles
- Timeout errors

**Solutions:**

1. **Check endpoint availability:**
```powershell
# Test endpoint manually
$response = Invoke-WebRequest -Uri $config.stressTestConfig.endpointUrl -UseBasicParsing
Write-Host "Status: $($response.StatusCode)"
Write-Host "Time: $($response.Headers.'X-Response-Time')"
```

2. **Adjust thresholds:**
```json
{
  "stressTestConfig": {
    "minSuccessRatePercent": 90,  // Lower if needed
    "maxP95LatencyMs": 1000,       // Increase if needed
    "timeoutSeconds": 60            // Increase for cold starts
  }
}
```

3. **Reduce request count:**
```json
{
  "stressTestConfig": {
    "requestCount": 25  // Reduce for lower load
  }
}
```

4. **Check for cold starts:**
```powershell
# Warm up endpoint before stress test
1..5 | ForEach-Object {
    Invoke-WebRequest -Uri $endpointUrl -UseBasicParsing | Out-Null
    Start-Sleep -Seconds 1
}
```

### Issue: "Stress test times out"

**Symptoms:**
```
Error: Stress test exceeded timeout (30 seconds)
Warning: Some requests did not complete
```

**Solutions:**

1. **Increase timeout:**
```json
{
  "stressTestConfig": {
    "timeoutSeconds": 60  // Double the timeout
  }
}
```

2. **Check endpoint performance:**
```powershell
# Measure single request time
Measure-Command {
    Invoke-WebRequest -Uri $endpointUrl -UseBasicParsing
}
```

3. **Reduce concurrent requests:**
```json
{
  "stressTestConfig": {
    "requestCount": 10  // Fewer concurrent requests
  }
}
```

## Pipeline Integration Issues

### Issue: "Pipeline failed to trigger"

**Symptoms:**
```
Error: Unable to start pipeline
Error: Pipeline not found
```

**Solutions:**

1. **Verify pipeline configuration:**
```powershell
# Check pipeline ID
$config = Get-Content ".deploy-sentinel-config.json" | ConvertFrom-Json
Write-Host "Pipeline ID: $($config.pipelineConfig.pipelineId)"
Write-Host "Project: $($config.pipelineConfig.project)"
```

2. **Test pipeline access:**
```powershell
# List pipelines in project
# (would use MCP tool)
# Verify pipeline ID exists
```

3. **Check permissions:**
   - Ensure PAT has "Build: Execute" permission
   - Verify pipeline run permissions
   - Check project-level restrictions

### Issue: "Build monitoring stuck"

**Symptoms:**
- Build never completes
- Monitoring loop times out
- No status updates

**Solutions:**

1. **Check build status directly:**
```powershell
# View in Azure DevOps portal
# Navigate to Pipelines → Builds
# Find build by ID
```

2. **Increase polling iterations:**
```powershell
# Modify Watch-AdoPipeline function
# Or adjust timeout in config
```

3. **Check build logs:**
```powershell
# Retrieve logs manually
# (would use MCP tool get_build_logs)
```

## Approval Gate Issues

### Issue: "Wait action not detected"

**Symptoms:**
- Rollout stuck but no approval prompt
- Wait actions not showing in monitoring

**Solutions:**

1. **Check rollout status structure:**
```powershell
# View raw status
$status = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_rollout_details" -Parameters @{ rolloutId = "..." }
$status | ConvertTo-Json -Depth 10
```

2. **Verify wait action format:**
```powershell
# Check if status.stages contains actions
# Look for type: "WaitAction" or status: "WaitingForApproval"
```

3. **Enable debug logging:**
```powershell
# Add verbose logging to Get-WaitActions
# Verify function is called during monitoring
```

### Issue: "Approval/rejection not working"

**Symptoms:**
```
Error: Unable to approve wait action
Error: Action ID not found
```

**Solutions:**

1. **Verify action ID:**
```powershell
# Get wait actions from rollout status
# Copy exact action ID (case-sensitive)
```

2. **Check required parameters:**
```powershell
# Ensure all parameters provided:
# -RolloutId, -ActionId, -ApproveWaitAction OR -RejectWaitAction
# Plus service details from config
```

3. **Try via portal:**
   - Navigate to EV2 portal
   - Find rollout
   - Approve/reject manually

## Teams Notification Issues

### Issue: "Notifications not sending"

**Symptoms:**
```
Warning: Failed to send Teams notification
Error: Unable to reach webhook
```

**Solutions:**

1. **Verify webhook URL:**
```powershell
# Test webhook manually
$body = @{
    text = "Test notification from Deploy Sentinel"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
Write-Host "Response: $response"
```

2. **Check webhook expiration:**
   - Teams webhooks can expire
   - Regenerate webhook in Teams channel settings
   - Update configuration

3. **Review retry logs:**
```powershell
# Check logs for retry attempts
Get-Content ".deploy-sentinel.log" | Select-String "Teams notification"
```

### Issue: "Rate limiting (429 errors)"

**Symptoms:**
```
Warning: Rate limited (429). Waiting N seconds before retry
```

**Solutions:**

1. **Reduce notification frequency:**
```powershell
# Consider consolidating notifications
# Or increase delays between sends
```

2. **Respect Retry-After header:**
```powershell
# Code already handles this
# Just wait for automatic retry
```

3. **Check webhook quota:**
   - Teams webhooks have rate limits
   - Consider using different webhook for high-frequency notifications

## Performance Issues

### Issue: "Polling too frequent"

**Symptoms:**
- High API call volume
- Resource consumption
- Potential throttling

**Solutions:**

1. **Increase polling interval:**
```json
{
  "pollingInterval": 60  // Check every 60 seconds instead of 30
}
```

2. **Implement adaptive polling:**
```powershell
# Reduce frequency after initial stages
# (consider implementing in future version)
```

### Issue: "Log file growing too large"

**Symptoms:**
- `.deploy-sentinel.log` > 100MB
- Disk space warnings

**Solutions:**

1. **Implement log rotation:**
```powershell
# Manual rotation
$maxSizeMB = 50
$logFile = ".deploy-sentinel.log"
if ((Get-Item $logFile).Length / 1MB -gt $maxSizeMB) {
    $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    Move-Item $logFile "$logFile.$timestamp"
}
```

2. **Reduce log verbosity:**
```powershell
# Remove DEBUG level logs in production
# Keep only INFO, WARN, ERROR
```

## Error Reference

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `QUOTA_EXCEEDED` | Azure quota limit reached | Request quota increase, reduce deployment size |
| `TIMEOUT` | Operation timed out | Check network, increase timeout, retry |
| `AUTHORIZATION_FAILED` | Permission denied | Verify RBAC roles, check authentication |
| `CONFLICT` | Resource conflict | Check for existing resources, review deployment mode |
| `INVALID_PARAMETER` | Bad parameter value | Review configuration, validate parameter types |
| `RESOURCE_NOT_FOUND` | Missing dependency | Ensure dependencies deployed first |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Rollout failed |
| 2 | Rollout cancelled or other non-success terminal state |

## Getting Additional Help

1. **Check logs:**
   ```powershell
   Get-Content ".deploy-sentinel.log" | Out-GridView
   ```

2. **Enable verbose output:**
   ```powershell
   $VerbosePreference = "Continue"
   .\deploy-sentinel.ps1 -Action monitor
   ```

3. **Review Azure Activity Logs:**
   ```powershell
   az monitor activity-log list --resource-group <rg> --max-events 100
   ```

4. **Contact support:**
   - Include log files
   - Include state file (remove sensitive data)
   - Include configuration (remove secrets)
   - Include error messages and timestamps

---

**Return to**: [Deploy Sentinel README](README.md) | [MCP Setup Guide](mcp-setup.md)
