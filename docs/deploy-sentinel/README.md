# Deploy Sentinel - EV2 Deployment Follower Agent

Deploy Sentinel is a PowerShell-based automation tool for Azure EV2 (Express V2) deployments, providing comprehensive workflow orchestration, monitoring, and notification capabilities.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

## Overview

Deploy Sentinel automates the complete EV2 deployment lifecycle:

1. **Trigger Rollouts** - Discover latest artifact/stage map versions and initiate deployments
2. **Create Branches** - Automatically create deployment tracking branches in Azure DevOps
3. **Monitor Status** - Poll rollout status with formatted real-time updates
4. **Handle Errors** - Extract errors and provide actionable recommendations
5. **Stress Testing** - Validate deployments with concurrent request testing
6. **Pipeline Integration** - Trigger pre/post-deployment validation pipelines
7. **Approval Gates** - Handle wait actions with interactive or CLI-based approvals
8. **Teams Notifications** - Send formatted deployment updates to Teams channels

## Features

### Core Capabilities

- ✅ **Automated Rollout Triggering** - Discover versions, build scope, start rollouts
- ✅ **Git Integration** - Create deployment branches with timestamp-based naming
- ✅ **Real-Time Monitoring** - Configurable polling with stage transition detection
- ✅ **Error Analysis** - 6 error type patterns with specific recommendations
- ✅ **Stress Testing** - Concurrent requests with latency percentiles (p50/p95/p99)
- ✅ **Pipeline Orchestration** - Pre/post-deployment ADO pipeline triggers
- ✅ **Approval Workflow** - Interactive or CLI-based wait action handling
- ✅ **Teams Notifications** - 7 notification types for all deployment milestones

### Resilience Features

- 🔄 **Retry Logic** - Exponential backoff for transient failures
- 🔒 **File Locking** - Prevents concurrent execution conflicts
- 📝 **State Persistence** - JSON-based state with atomic writes
- 🛡️ **Stale Detection** - Automatic cleanup of abandoned locks (5 min timeout)
- 📊 **Comprehensive Logging** - Timestamped logs with color-coded console output

## Prerequisites

### Required

1. **PowerShell** - Version 5.1+ (Windows) or Core 7+ (cross-platform)
2. **MCP Servers** - Model Context Protocol servers for EV2 and Azure DevOps
   - EV2 MCP Server (dnx-based)
   - Azure DevOps MCP Server (npm-based)
3. **Azure Authentication** - One of:
   - Managed Service Identity (MSI)
   - Service Principal with credentials
   - Azure CLI authentication

### Optional

- **Git** - For branch creation (User Story 2)
- **Azure DevOps Access** - For pipeline integration (User Story 6)
- **Teams Webhook** - For notifications (User Story 8)

## Installation

### 1. Install MCP Servers

Follow the [MCP Setup Guide](mcp-setup.md) to install required servers.

### 2. Deploy the Script

Copy `deploy-sentinel.ps1` to your deployment environment:

```powershell
# Example: Copy to scripts directory
Copy-Item "deploy-sentinel.ps1" -Destination "C:\deployments\scripts\"
```

### 3. Create Configuration File

Create `.deploy-sentinel-config.json` in your working directory:

```json
{
  "serviceGroupName": "my-service-group",
  "serviceId": "my-service",
  "environment": "prod",
  "stageMapName": "standard-rollout",
  "serviceResourceGroup": "my-resource-group",
  "serviceResource": "my-service-resource",
  "subscriptionIds": ["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
  "regions": ["eastus", "westus"],
  "pollingInterval": 30,
  "repositoryId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "teamsWebhookUrl": "https://outlook.office.com/webhook/...",
  "stressTestConfig": {
    "enabled": true,
    "endpointUrl": "https://my-service.azurewebsites.net/health",
    "requestCount": 50,
    "timeoutSeconds": 30,
    "minSuccessRatePercent": 95,
    "maxP95LatencyMs": 500
  },
  "pipelineConfig": {
    "enabled": true,
    "project": "my-ado-project",
    "pipelineId": 123,
    "triggerBefore": true,
    "triggerAfter": true
  }
}
```

## Quick Start

### Basic Workflow

```powershell
# 1. Trigger rollout with branch creation
.\deploy-sentinel.ps1 -Action trigger -ConfigPath ".deploy-sentinel-config.json"

# 2. Monitor rollout progress
.\deploy-sentinel.ps1 -Action monitor -ConfigPath ".deploy-sentinel-config.json"

# 3. (Optional) Cancel if needed
.\deploy-sentinel.ps1 -Action cancel -RolloutId "rollout-123" -Reason "Rolling back due to issue"
```

### With Specific Rollout ID

```powershell
# Monitor specific rollout
.\deploy-sentinel.ps1 -Action monitor -RolloutId "my-rollout-12345-abc" -ConfigPath ".deploy-sentinel-config.json"
```

## Configuration

### Core Settings

| Field | Required | Description |
|-------|----------|-------------|
| `serviceGroupName` | Yes | EV2 service group name |
| `serviceId` | Yes | Service identifier |
| `environment` | Yes | Deployment environment (dev/stage/prod) |
| `stageMapName` | Yes | Stage map name for rollout progression |
| `serviceResourceGroup` | Yes | Azure resource group for service |
| `serviceResource` | Yes | Service resource name |
| `subscriptionIds` | Yes | Array of Azure subscription IDs |
| `regions` | Yes | Array of Azure regions for deployment |

### Optional Settings

| Field | Default | Description |
|-------|---------|-------------|
| `pollingInterval` | 30 | Seconds between rollout status checks |
| `repositoryId` | - | Azure DevOps repository ID for branch creation |
| `teamsWebhookUrl` | - | Teams webhook URL for notifications |

### Stress Testing Configuration

```json
{
  "stressTestConfig": {
    "enabled": true,
    "endpointUrl": "https://my-service.com/health",
    "requestCount": 50,
    "timeoutSeconds": 30,
    "minSuccessRatePercent": 95,
    "maxP95LatencyMs": 500
  }
}
```

### Pipeline Configuration

```json
{
  "pipelineConfig": {
    "enabled": true,
    "project": "my-ado-project",
    "pipelineId": 123,
    "triggerBefore": true,
    "triggerAfter": true
  }
}
```

## Usage

### Actions

#### Trigger Rollout

Initiates a new EV2 rollout with automatic version discovery:

```powershell
.\deploy-sentinel.ps1 -Action trigger -ConfigPath ".deploy-sentinel-config.json"
```

**What it does:**
1. Calls `Get-Ev2BestPractices` for recommendations
2. Discovers latest artifact and stage map versions
3. Builds deployment scope from configuration
4. Starts EV2 rollout via MCP server
5. Creates deployment branch (if repository configured)
6. Sends "Rollout Started" Teams notification
7. Persists state to `.deploy-sentinel-state.json`

#### Monitor Rollout

Polls rollout status until completion or failure:

```powershell
.\deploy-sentinel.ps1 -Action monitor -ConfigPath ".deploy-sentinel-config.json"

# Or with specific rollout ID
.\deploy-sentinel.ps1 -Action monitor -RolloutId "rollout-123" -ConfigPath ".deploy-sentinel-config.json"
```

**What it does:**
1. Loads rollout ID from state file or parameter
2. Polls status every N seconds (configurable)
3. Detects stage transitions and runs stress tests
4. Extracts and displays errors on failure
5. Handles wait actions (approval gates)
6. Sends Teams notifications at key milestones
7. Updates state file with progress

#### Cancel Rollout

Cancels an active rollout:

```powershell
.\deploy-sentinel.ps1 -Action cancel -RolloutId "rollout-123" -Reason "Manual intervention" -ConfigPath ".deploy-sentinel-config.json"
```

#### Approve/Reject Wait Actions

Handle approval gates via CLI:

```powershell
# Approve
.\deploy-sentinel.ps1 -ApproveWaitAction -ActionId "wait-001" -RolloutId "rollout-123" -ConfigPath ".deploy-sentinel-config.json"

# Reject
.\deploy-sentinel.ps1 -RejectWaitAction -ActionId "wait-001" -RolloutId "rollout-123" -ConfigPath ".deploy-sentinel-config.json"
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `-Action` | String | Action to execute: `trigger`, `monitor`, `cancel` |
| `-ConfigPath` | String | Path to configuration file (default: `.deploy-sentinel-config.json`) |
| `-RolloutId` | String | Specific rollout ID to monitor/cancel |
| `-Reason` | String | Cancellation reason (for cancel action) |
| `-ApproveWaitAction` | Switch | Approve a wait action |
| `-RejectWaitAction` | Switch | Reject a wait action |
| `-ActionId` | String | Wait action ID (required with approve/reject) |
| `-ForceUnlock` | Switch | Force removal of stale state file lock |

## Advanced Features

### Stress Testing

After each stage completion, Deploy Sentinel can run stress tests:

1. **Concurrent Requests** - Sends N requests in parallel using PowerShell jobs
2. **Latency Metrics** - Calculates p50, p95, p99 percentiles
3. **Threshold Validation** - Compares results against configured thresholds
4. **Interactive Decisions** - Prompts to continue or cancel on failure

**Configuration:**
```json
{
  "stressTestConfig": {
    "enabled": true,
    "endpointUrl": "https://my-service.com/health",
    "requestCount": 50,
    "timeoutSeconds": 30,
    "minSuccessRatePercent": 95,
    "maxP95LatencyMs": 500
  }
}
```

### Pipeline Integration

Trigger Azure DevOps pipelines before/after deployments:

**Pre-Deployment Pipeline:**
- Runs before rollout starts
- **Critical** - Deployment halts if pipeline fails
- Use for validation, smoke tests, prerequisites

**Post-Deployment Pipeline:**
- Runs after rollout completes
- **Non-critical** - Logs warning if pipeline fails
- Use for reporting, cleanup, notifications

**Configuration:**
```json
{
  "pipelineConfig": {
    "enabled": true,
    "project": "my-ado-project",
    "pipelineId": 123,
    "triggerBefore": true,
    "triggerAfter": true
  }
}
```

**Pipeline Variables** (automatically injected):
- `rolloutId` - EV2 rollout ID
- `environment` - Deployment environment
- `serviceId` - Service identifier
- `branchName` - Deployment branch name

### Approval Gates

Deploy Sentinel handles EV2 wait actions with two modes:

**Interactive Mode** (default):
- Detects wait actions during monitoring
- Sends Teams notification with approval instructions
- Prompts user for decision: Approve / Reject / Wait
- Continues polling until decision made

**CLI Mode** (for automation):
```powershell
# Approve from external system
.\deploy-sentinel.ps1 -ApproveWaitAction -ActionId "wait-001" -RolloutId "rollout-123"

# Reject from external system
.\deploy-sentinel.ps1 -RejectWaitAction -ActionId "wait-001" -RolloutId "rollout-123"
```

### Teams Notifications

Deploy Sentinel sends 7 notification types:

1. **Rollout Started** (Blue 🔵) - When rollout begins
2. **Stage Completed** (Green 🟢) - After each stage transition
3. **Stress Test Results** (Cyan 🔵) - After stress testing completes
4. **Approval Required** (Yellow 🟡) - When wait action detected
5. **Rollout Failed** (Red 🔴) - On deployment failure
6. **Rollout Completed** (Green 🟢) - On successful completion
7. **Rollout Cancelled** (Yellow 🟡) - On manual cancellation

**Retry Logic:**
- Exponential backoff: 1s, 2s, 4s delays
- Handles rate limiting (429) with Retry-After header
- Falls back to log file if all retries fail

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md) for detailed solutions to common issues.

### Quick Diagnostics

```powershell
# Check state file
Get-Content ".deploy-sentinel-state.json" | ConvertFrom-Json

# Check logs
Get-Content ".deploy-sentinel.log" -Tail 50

# Force unlock stale lock
.\deploy-sentinel.ps1 -Action monitor -ForceUnlock
```

### Common Issues

1. **State file locked** - Another instance running or stale lock (use `-ForceUnlock`)
2. **MCP tool not found** - Install MCP servers (see [MCP Setup](mcp-setup.md))
3. **Authentication failed** - Configure Azure credentials (MSI, Service Principal, or CLI)
4. **Webhook timeout** - Check Teams webhook URL and network connectivity

## State Management

Deploy Sentinel persists state in `.deploy-sentinel-state.json`:

```json
{
  "rolloutId": "my-rollout-12345-abc",
  "status": "InProgress",
  "serviceInfo": {
    "serviceId": "my-service",
    "artifactVersion": "1.2.3",
    "stageMapVersion": "2.0"
  },
  "startedAt": "2025-11-20T10:30:00Z",
  "lastUpdated": "2025-11-20T10:35:00Z",
  "branchName": "deploy/prod/my-service/20251120103000",
  "pipelineRunId": 456,
  "stressTests": [],
  "notifications": []
}
```

**State File Locking:**
- Exclusive lock file: `.deploy-sentinel-state.lock`
- Contains: PID, timestamp, hostname
- Stale detection: 5-minute timeout
- Force removal: `-ForceUnlock` parameter

## Log Files

Deploy Sentinel writes to `.deploy-sentinel.log`:

```
2025-11-20T10:30:00.123Z [INFO] === EV2 Deployment Sentinel Started ===
2025-11-20T10:30:01.456Z [INFO] Action: trigger
2025-11-20T10:30:02.789Z [INFO] Configuration loaded: .deploy-sentinel-config.json
2025-11-20T10:30:05.012Z [INFO] Rollout triggered: my-rollout-12345-abc
2025-11-20T10:30:06.345Z [INFO] Branch created: deploy/prod/my-service/20251120103000
```

**Log Levels:**
- `INFO` - Normal operation
- `WARN` - Non-critical issues
- `ERROR` - Critical failures
- `DEBUG` - Detailed diagnostics

## Examples

### Complete Workflow

```powershell
# Step 1: Trigger rollout
.\deploy-sentinel.ps1 -Action trigger

# Output:
# ✅ Rollout triggered: my-rollout-12345-abc
# ✅ Branch created: deploy/prod/my-service/20251120103000
# ✅ Teams notification sent

# Step 2: Monitor until completion
.\deploy-sentinel.ps1 -Action monitor

# Output shows:
# - Current stage progress
# - Stage transitions
# - Stress test results
# - Approval prompts (if wait actions)
# - Final status
```

### Automated CI/CD Integration

```powershell
# Non-interactive mode for CI/CD pipelines
$ErrorActionPreference = "Stop"

# Trigger
.\deploy-sentinel.ps1 -Action trigger -ConfigPath "config.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Monitor
.\deploy-sentinel.ps1 -Action monitor -ConfigPath "config.json"
if ($LASTEXITCODE -ne 0) { 
    Write-Error "Deployment failed - check logs"
    exit $LASTEXITCODE 
}

Write-Host "✅ Deployment completed successfully"
```

## Best Practices

1. **Configuration Management** - Store configs in version control, use environment-specific files
2. **State File Location** - Keep in deployment workspace, exclude from version control
3. **Lock Cleanup** - Monitor for stale locks, use `-ForceUnlock` judiciously
4. **Error Handling** - Review error recommendations, check Azure Activity Logs
5. **Stress Testing** - Set realistic thresholds, account for cold starts
6. **Pipeline Integration** - Keep pre-deployment pipelines fast and reliable
7. **Approval Gates** - Document approval criteria, use CLI for automation
8. **Teams Notifications** - Use dedicated channel, configure webhook expiry alerts

## Support

- **Documentation**: See [docs/deploy-sentinel/](.)
- **Issues**: Report via GitHub Issues
- **Logs**: Check `.deploy-sentinel.log` for diagnostics
- **MCP Setup**: See [mcp-setup.md](mcp-setup.md)
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)

## Version History

- **1.0.0** - Initial release with all 8 user stories
  - Rollout triggering and monitoring
  - Git branch integration
  - Error handling and recommendations
  - Stress testing with latency metrics
  - Pipeline integration (pre/post-deployment)
  - Approval gates with interactive/CLI modes
  - Teams notifications for all milestones

---

**Deploy Sentinel** - Simplifying EV2 deployments with intelligent automation.
