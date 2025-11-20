# Deploy Sentinel Quick Start Guide

**Feature**: 005-deploy-sentinel | **Version**: 1.0.0 | **Date**: 2025-11-19

## Overview

Deploy Sentinel is a GitHub Copilot agent that automates EV2 (Express V2) deployments for Azure services. It monitors rollout progress, handles approvals, runs stress tests, and sends notifications to Microsoft Teams.

## Prerequisites

Before using Deploy Sentinel, ensure you have:

### Required Tools

1. **PowerShell** (5.1+ or Core 7+)
   - Windows: Built-in PowerShell 5.1+ or [PowerShell Core 7+](https://github.com/PowerShell/PowerShell)
   - macOS/Linux: [PowerShell Core 7+](https://github.com/PowerShell/PowerShell)

2. **Pester** (PowerShell testing framework)

   ```powershell
   Install-Module -Name Pester -Force -SkipPublisherCheck
   ```

3. **Git CLI** (for branch creation)

   ```powershell
   # Verify git is installed
   git --version
   ```

### Required MCP Servers

Deploy Sentinel requires two Model Context Protocol (MCP) servers:

1. **EV2 MCP Server** (dnx package)
2. **Azure DevOps MCP Server** (npm package)

See [MCP Server Setup](#mcp-server-setup) section below for detailed installation instructions.

### Required Access

1. **EV2 Portal Access**: Permissions to trigger and manage rollouts
2. **Azure DevOps Access**: Permissions to run pipelines and create branches
3. **Azure AD Authentication**: Bearer token for authenticated endpoints (optional)

## MCP Server Setup

### 1. Install EV2 MCP Server

The EV2 MCP Server is distributed as a dnx package from Microsoft's internal package feed.

**Prerequisites**:

- Access to Microsoft internal dnx package feed
- dnx CLI installed ([installation guide](https://aka.ms/dnx))

**Installation**:

```powershell
# Install EV2 MCP Server via dnx
dnx install ev2-mcp-server
```

**Verification**:

```powershell
# Verify installation
dnx list | Select-String "ev2-mcp-server"
```

### 2. Install Azure DevOps MCP Server

The Azure DevOps MCP Server is distributed as an npm package.

**Prerequisites**:

- Node.js 18+ installed ([download](https://nodejs.org/))
- npm CLI available

**Installation**:

```powershell
# Install Azure DevOps MCP Server globally
npm install -g @microsoft/azure-devops-mcp-server
```

**Verification**:

```powershell
# Verify installation
npm list -g --depth=0 | Select-String "azure-devops-mcp-server"
```

### 3. Configure MCP Servers in VS Code

Add MCP server configurations to your VS Code settings:

**File**: `.vscode/mcp.json`

```json
{
  "mcpServers": {
    "ev2": {
      "command": "dnx",
      "args": ["run", "ev2-mcp-server"],
      "env": {
        "EV2_ENDPOINT": "Prod"
      }
    },
    "azure-devops": {
      "command": "npx",
      "args": ["-y", "@microsoft/azure-devops-mcp-server"],
      "env": {
        "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/your-org",
        "AZURE_DEVOPS_PAT": "${env:AZURE_DEVOPS_PAT}"
      }
    }
  }
}
```

**Environment Variables** (required):

```powershell
# Set Azure DevOps Personal Access Token
$env:AZURE_DEVOPS_PAT = "your-pat-token-here"

# Optional: Set EV2 endpoint (defaults to Prod)
$env:EV2_ENDPOINT = "Prod"  # or "Int" for integration environment
```

**Generate Azure DevOps PAT**:

1. Navigate to https://dev.azure.com/{your-org}/_usersSettings/tokens
2. Click "New Token"
3. Scopes required:
   - Build: Read & Execute
   - Code: Read & Write (for branch creation)
   - Project and Team: Read

### 4. Restart VS Code

After configuring MCP servers, restart VS Code to load the configurations:

```
Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (macOS)
> Developer: Reload Window
```

**Verify MCP Integration**:

```powershell
# In VS Code, open GitHub Copilot Chat
# Type: @workspace list MCP servers
# Expected: ev2, azure-devops listed
```

## Configuration

Deploy Sentinel requires a configuration file defining the deployment parameters.

### Configuration File

**File**: `.deploy-sentinel-config.json` (project root)

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "serviceGroupName": "AppLensService",
  "stageMapName": "AppLensStageMap",
  "endpoint": "Prod",
  "adoProject": "AppLensProject",
  "repositoryId": "12345678-1234-1234-1234-123456789abc",
  "sourceBranchName": "main",
  "pipelineIds": [123, 124],
  "teamsWebhookUrl": "https://prod-xx.region.logic.azure.com:443/workflows/{workflow-id}/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig={signature}",
  "stressTest": {
    "enabled": true,
    "endpoints": [
      {
        "region": "EastUS",
        "url": "https://eastus-applens.azurewebsites.net/api/health",
        "method": "GET",
        "expectedStatusCode": 200,
        "bearerToken": "${env:AZURE_HEALTH_TOKEN}"
      },
      {
        "region": "WestUS",
        "url": "https://westus-applens.azurewebsites.net/api/health",
        "method": "GET",
        "expectedStatusCode": 200,
        "bearerToken": "${env:AZURE_HEALTH_TOKEN}"
      }
    ],
    "concurrentRequests": 100,
    "timeout": 120,
    "successRateThreshold": 95.0,
    "latencyThresholdMs": 500.0
  }
}
```

### Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `serviceId` | Yes | EV2 Service GUID |
| `serviceGroupName` | Yes | EV2 Service Group Name |
| `stageMapName` | Yes | EV2 Stage Map Name |
| `endpoint` | Yes | EV2 Endpoint ("Prod" or "Int") |
| `adoProject` | Yes | Azure DevOps Project Name |
| `repositoryId` | Yes | Azure DevOps Repository GUID |
| `sourceBranchName` | Yes | Source branch for deployment branch creation |
| `pipelineIds` | No | Array of pipeline IDs to run (optional) |
| `teamsWebhookUrl` | No | Microsoft Teams webhook URL (optional) |
| `stressTest.enabled` | No | Enable stress testing (default: false) |
| `stressTest.endpoints` | No | Array of endpoints to stress test |
| `stressTest.concurrentRequests` | No | Number of concurrent requests (default: 100) |
| `stressTest.timeout` | No | Test timeout in seconds (default: 120) |
| `stressTest.successRateThreshold` | No | Minimum success rate % (default: 95.0) |
| `stressTest.latencyThresholdMs` | No | Maximum average latency in ms (default: 500.0) |

### Environment Variable Substitution

Configuration supports environment variable substitution using `${env:VAR_NAME}` syntax:

```powershell
# Set bearer token for authenticated endpoints
$env:AZURE_HEALTH_TOKEN = "your-bearer-token-here"
```

**Important**: Never commit bearer tokens or sensitive values to source control. Always use environment variables.

## Teams Webhook Setup (Optional)

Deploy Sentinel can send deployment notifications to Microsoft Teams via Power Automate Workflow Webhooks.

### 1. Create Power Automate Flow

1. Navigate to [Power Automate](https://flow.microsoft.com/)
2. Click "Create" → "Instant cloud flow"
3. Name: "Deploy Sentinel Notifications"
4. Trigger: "When a HTTP request is received"

### 2. Configure Request Schema

In the HTTP trigger, click "Use sample payload to generate schema" and paste:

```json
{
  "title": "EV2 Rollout Started",
  "status": "InProgress",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS", "WestUS"],
  "timestamp": "2025-11-19T10:30:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

### 3. Add Teams Action

1. Click "New step"
2. Search for "Microsoft Teams"
3. Select "Post message in a chat or channel"
4. Configure:
   - **Post as**: Flow bot
   - **Post in**: Channel
   - **Team**: Select your team
   - **Channel**: Select your channel

### 4. Create Adaptive Card

In the "Message" field, switch to "Adaptive Card" editor and paste:

```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "@{triggerBody()?['title']}",
      "weight": "Bolder",
      "size": "Large"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Status", "value": "@{triggerBody()?['status']}"},
        {"title": "Service", "value": "@{triggerBody()?['service']}"},
        {"title": "Artifact", "value": "@{triggerBody()?['artifactVersion']}"},
        {"title": "Regions", "value": "@{join(triggerBody()?['regions'], ', ')}"},
        {"title": "Time", "value": "@{triggerBody()?['timestamp']}"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View Rollout",
      "url": "@{triggerBody()?['actionUrl']}"
    }
  ]
}
```

### 5. Save and Get Webhook URL

1. Click "Save"
2. Copy the "HTTP POST URL" from the trigger
3. Add to `.deploy-sentinel-config.json` as `teamsWebhookUrl`

**Security Note**: The webhook URL contains a signature parameter. Keep it confidential and do not commit to source control.

## First Deployment

### Invoke via GitHub Copilot

Open GitHub Copilot Chat in VS Code and use the `/deploySentinel` command:

```
/deploySentinel trigger rollout for AppLensService
```

**Command Options**:

```
# Basic rollout trigger
/deploySentinel trigger rollout

# Monitor existing rollout
/deploySentinel monitor rollout 12345678-1234-1234-1234-123456789abc

# Approve wait action
/deploySentinel approve wait action wait-12345 for rollout 12345678-1234-1234-1234-123456789abc

# Cancel rollout
/deploySentinel cancel rollout 12345678-1234-1234-1234-123456789abc

# Run stress tests
/deploySentinel stress test endpoints after stage Stage2-WestUS

# Run CI/CD pipelines
/deploySentinel run pipelines for rollout 12345678-1234-1234-1234-123456789abc
```

### Direct PowerShell Invocation

You can also invoke the script directly:

```powershell
# Navigate to scripts directory
cd .specify/scripts/powershell

# Trigger rollout
.\deploy-sentinel.ps1 -Action TriggerRollout -ConfigPath ".deploy-sentinel-config.json"

# Monitor rollout
.\deploy-sentinel.ps1 -Action MonitorRollout -RolloutId "12345678-1234-1234-1234-123456789abc" -ConfigPath ".deploy-sentinel-config.json"

# Approve wait action
.\deploy-sentinel.ps1 -Action ApproveWaitAction -RolloutId "12345678-1234-1234-1234-123456789abc" -ActionId "wait-12345" -ConfigPath ".deploy-sentinel-config.json"
```

### Expected Output

```
[2025-11-19 10:30:00] Loading configuration from .deploy-sentinel-config.json
[2025-11-19 10:30:01] ✓ Configuration loaded successfully
[2025-11-19 10:30:01] Calling EV2 best practices (mandatory first call)
[2025-11-19 10:30:02] ✓ Best practices acknowledged
[2025-11-19 10:30:02] Retrieving latest artifact version for AppLensService
[2025-11-19 10:30:03] ✓ Latest artifact version: 1.2.3
[2025-11-19 10:30:03] Retrieving latest stage map version for AppLensStageMap
[2025-11-19 10:30:04] ✓ Latest stage map version: v2
[2025-11-19 10:30:04] Starting rollout with artifact 1.2.3 and stage map v2
[2025-11-19 10:30:05] ✓ Rollout started: 12345678-1234-1234-1234-123456789abc
[2025-11-19 10:30:05] Sending Teams notification (Rollout Started)
[2025-11-19 10:30:06] ✓ Teams notification sent
[2025-11-19 10:30:06] Creating deployment branch: deploy/rollout-12345678
[2025-11-19 10:30:07] ✓ Branch created: refs/heads/deploy/rollout-12345678
[2025-11-19 10:30:07] Starting rollout monitoring (polling every 30s)
[2025-11-19 10:30:07] Press Ctrl+C to stop monitoring (rollout will continue)
[2025-11-19 10:30:37] Status: InProgress | Current Stage: Stage1-EastUS
[2025-11-19 10:31:07] Status: InProgress | Current Stage: Stage1-EastUS
[2025-11-19 10:31:37] ✓ Stage completed: Stage1-EastUS
[2025-11-19 10:31:37] Running stress tests for EastUS endpoints...
[2025-11-19 10:31:47] ✓ Stress test passed: EastUS (98.0% success, 125ms avg latency)
...
```

## State Persistence

Deploy Sentinel maintains rollout state in a JSON file for idempotency and resumability:

**File**: `.deploy-sentinel-state.json` (project root)

```json
{
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "status": "InProgress",
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "branchName": "deploy/rollout-12345678",
  "startTime": "2025-11-19T10:30:00Z",
  "lastUpdateTime": "2025-11-19T10:45:00Z",
  "completedStages": ["Stage1-EastUS"],
  "currentStage": "Stage2-WestUS",
  "pendingStages": ["Stage3-CentralUS"],
  "errors": [],
  "waitActions": [],
  "pipelinesRun": [],
  "stressTestResults": []
}
```

**State File Behavior**:

- Created on first rollout trigger
- Updated every 30 seconds during monitoring
- Locked during updates (prevents concurrent modifications)
- Persists across PowerShell sessions
- Delete file to start fresh (rollout continues in EV2)

## Troubleshooting

### MCP Server Not Found

**Error**: `MCP server 'ev2' not found`

**Solution**:

1. Verify MCP server installation: `dnx list | Select-String "ev2-mcp-server"`
2. Check `.vscode/mcp.json` configuration
3. Restart VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"

### Authentication Failed

**Error**: `Authentication failed for EV2 endpoint`

**Solution**:

1. Verify Azure AD authentication: `az account show`
2. Login if needed: `az login`
3. Verify service permissions in EV2 portal

### Pipeline Not Found

**Error**: `Pipeline 123 not found in project 'AppLensProject'`

**Solution**:

1. Verify pipeline ID: Navigate to https://dev.azure.com/{org}/{project}/_build
2. Update `pipelineIds` in `.deploy-sentinel-config.json`
3. Verify Azure DevOps PAT has Build (Read & Execute) permissions

### Webhook Notification Failed

**Error**: `Teams notification failed with non-recoverable error: 404`

**Solution**:

1. Verify webhook URL is correct in `.deploy-sentinel-config.json`
2. Test webhook in Power Automate: "Run" → "Test" → "Manually"
3. Check Power Automate flow is enabled
4. **Note**: Webhook failures do not block deployments (graceful degradation)

### Stress Test Failed

**Error**: `Stress test failed: EastUS (92.0% success < 95.0% threshold)`

**Solution**:

1. Check endpoint health: `Invoke-RestMethod -Uri "https://eastus-applens.azurewebsites.net/api/health"`
2. Review endpoint logs in Azure Portal
3. Adjust threshold in config: `"successRateThreshold": 90.0`
4. Disable stress testing temporarily: `"stressTest.enabled": false`

## Next Steps

- **Phase 2**: Review [tasks.md](tasks.md) for implementation task breakdown
- **Testing**: Review [contracts/](contracts/) for API contract tests
- **Implementation**: Follow TDD approach with Pester tests before implementation
- **Documentation**: Update [data-model.md](data-model.md) if entities change

## Additional Resources

- [EV2 Documentation](https://msazure.visualstudio.com/One/_git/Deployment-Ease)
- [Azure DevOps REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/)
- [Power Automate Documentation](https://learn.microsoft.com/en-us/power-automate/)
- [Pester Testing Framework](https://pester.dev/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Feature**: 005-deploy-sentinel | **Status**: Planning Phase | **Last Updated**: 2025-11-19
