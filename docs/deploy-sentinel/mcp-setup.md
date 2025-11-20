# MCP Server Setup Guide

This guide explains how to install and configure the Model Context Protocol (MCP) servers required by Deploy Sentinel.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [EV2 MCP Server](#ev2-mcp-server)
- [Azure DevOps MCP Server](#azure-devops-mcp-server)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Overview

Deploy Sentinel requires two MCP servers:

1. **EV2 MCP Server** (dnx-based) - For EV2 rollout operations
2. **Azure DevOps MCP Server** (npm-based) - For branch creation and pipeline integration

Both servers use the Model Context Protocol to provide standardized access to their respective APIs.

## Prerequisites

### General Requirements

- **PowerShell** - Version 5.1+ (Windows) or Core 7+ (cross-platform)
- **Internet Connection** - For downloading server packages
- **Azure Authentication** - One of:
  - Managed Service Identity (MSI)
  - Service Principal credentials
  - Azure CLI authentication

### For EV2 MCP Server

- **.NET SDK** - Version 6.0 or higher
- **dnx** - .NET execution environment
- **EV2 Access** - Permissions to trigger and monitor rollouts

**Install .NET SDK:**

```powershell
# Windows (via winget)
winget install Microsoft.DotNet.SDK.8

# Or download from: https://dotnet.microsoft.com/download
```

**Install dnx:**

```powershell
# Install dnx globally
dotnet tool install --global dnx

# Verify installation
dnx --version
```

### For Azure DevOps MCP Server

- **Node.js** - Version 18.0 or higher
- **npm** - Node package manager (included with Node.js)
- **Azure DevOps Access** - Permissions for:
  - Repository read/write
  - Pipeline execute
  - Build read

**Install Node.js:**

```powershell
# Windows (via winget)
winget install OpenJS.NodeJS.LTS

# Or download from: https://nodejs.org/
```

**Verify installation:**

```powershell
node --version  # Should show v18.x or higher
npm --version   # Should show 8.x or higher
```

## EV2 MCP Server

### Installation

The EV2 MCP Server is distributed as a .NET tool package:

```powershell
# Install globally via dnx
dnx install mcp-server-ev2

# Or install locally in project
dnx install --local mcp-server-ev2
```

### Configuration

Configure EV2 authentication in your environment:

**Option 1: Managed Service Identity (Recommended for Azure VMs)**

```powershell
# No configuration needed - uses VM's MSI automatically
# Ensure VM has EV2 permissions assigned
```

**Option 2: Service Principal**

```powershell
# Set environment variables
$env:AZURE_TENANT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
$env:AZURE_CLIENT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
$env:AZURE_CLIENT_SECRET = "your-client-secret"
```

**Option 3: Azure CLI**

```powershell
# Login via Azure CLI
az login

# Select subscription
az account set --subscription "your-subscription-id"
```

### Available Tools

The EV2 MCP Server provides these tools:

| Tool Name | Description |
|-----------|-------------|
| `get_ev2_best_practices` | Retrieve EV2 deployment best practices |
| `get_artifact_versions` | List artifact versions for a service |
| `get_stage_map_versions` | List stage map versions |
| `start_rollout` | Initiate a new EV2 rollout |
| `get_rollout_details` | Retrieve rollout status and details |
| `cancel_rollout` | Cancel an active rollout |
| `approve_rollout_continuation` | Approve/reject wait actions |

### Testing

Verify the EV2 MCP Server installation:

```powershell
# Test server availability
dnx mcp-server-ev2 --version

# Test best practices retrieval (requires authentication)
dnx mcp-server-ev2 invoke get_ev2_best_practices
```

## Azure DevOps MCP Server

### Installation

The Azure DevOps MCP Server is distributed as an npm package:

```powershell
# Install globally
npm install -g mcp-server-azuredevops

# Or install locally in project
npm install --save-dev mcp-server-azuredevops
```

### Configuration

Configure Azure DevOps authentication:

**Option 1: Personal Access Token (PAT) - Recommended**

```powershell
# Set environment variable
$env:AZURE_DEVOPS_PAT = "your-personal-access-token"
$env:AZURE_DEVOPS_ORG_URL = "https://dev.azure.com/your-organization"
```

**Create PAT:**
1. Navigate to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Set scopes:
   - **Code** - Read & Write (for branch creation)
   - **Build** - Read & Execute (for pipeline triggers)
4. Copy the generated token

**Option 2: Azure CLI**

```powershell
# Login to Azure DevOps
az devops login

# Configure default organization
az devops configure --defaults organization=https://dev.azure.com/your-organization
```

### Available Tools

The Azure DevOps MCP Server provides these tools:

| Tool Name | Description |
|-----------|-------------|
| `create_branch` | Create a new branch in a repository |
| `list_repositories` | List repositories in a project |
| `pipelines_list` | List pipelines in a project |
| `pipelines_run_pipeline` | Trigger a pipeline run |
| `build_get` | Get build details by ID |
| `build_get_logs` | Retrieve build logs |

### Testing

Verify the Azure DevOps MCP Server installation:

```powershell
# Test server availability
npm list -g mcp-server-azuredevops

# Test repository listing (requires authentication)
# This would typically be done via MCP protocol, not directly
```

## Configuration

### MCP Configuration File

Create `.vscode/mcp.json` in your project (if using VS Code MCP integration):

```json
{
  "mcpServers": {
    "ev2": {
      "command": "dnx",
      "args": ["mcp-server-ev2"],
      "env": {
        "AZURE_TENANT_ID": "${AZURE_TENANT_ID}",
        "AZURE_CLIENT_ID": "${AZURE_CLIENT_ID}",
        "AZURE_CLIENT_SECRET": "${AZURE_CLIENT_SECRET}"
      }
    },
    "azuredevops": {
      "command": "npx",
      "args": ["mcp-server-azuredevops"],
      "env": {
        "AZURE_DEVOPS_PAT": "${AZURE_DEVOPS_PAT}",
        "AZURE_DEVOPS_ORG_URL": "${AZURE_DEVOPS_ORG_URL}"
      }
    }
  }
}
```

### Environment Variables

Create `.env` file for local development (exclude from version control):

```bash
# EV2 Authentication
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret

# Azure DevOps Authentication
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
```

**Load environment variables in PowerShell:**

```powershell
# Load from .env file
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^([^=]+)=(.*)$") {
        $name = $matches[1]
        $value = $matches[2]
        Set-Item -Path "env:$name" -Value $value
    }
}
```

## Verification

### Complete Verification Script

```powershell
# verify-mcp-setup.ps1

Write-Host "=== MCP Server Verification ===" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n1. Checking Prerequisites..." -ForegroundColor Yellow

# .NET SDK
try {
    $dotnetVersion = dotnet --version
    Write-Host "   ✅ .NET SDK: $dotnetVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ .NET SDK not found" -ForegroundColor Red
}

# dnx
try {
    $dnxVersion = dnx --version
    Write-Host "   ✅ dnx: $dnxVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ dnx not found" -ForegroundColor Red
}

# Node.js
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Node.js not found" -ForegroundColor Red
}

# npm
try {
    $npmVersion = npm --version
    Write-Host "   ✅ npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ npm not found" -ForegroundColor Red
}

# Check MCP servers
Write-Host "`n2. Checking MCP Servers..." -ForegroundColor Yellow

# EV2 MCP Server
try {
    $ev2Check = dnx tool list -g | Select-String "mcp-server-ev2"
    if ($ev2Check) {
        Write-Host "   ✅ EV2 MCP Server installed" -ForegroundColor Green
    } else {
        Write-Host "   ❌ EV2 MCP Server not found" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Unable to check EV2 MCP Server" -ForegroundColor Red
}

# Azure DevOps MCP Server
try {
    $adoCheck = npm list -g mcp-server-azuredevops 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Azure DevOps MCP Server installed" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Azure DevOps MCP Server not found" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Unable to check Azure DevOps MCP Server" -ForegroundColor Red
}

# Check environment variables
Write-Host "`n3. Checking Environment Variables..." -ForegroundColor Yellow

$requiredVars = @(
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_DEVOPS_PAT",
    "AZURE_DEVOPS_ORG_URL"
)

foreach ($var in $requiredVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        $masked = $value.Substring(0, [Math]::Min(8, $value.Length)) + "***"
        Write-Host "   ✅ $var = $masked" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ $var not set" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Cyan
```

**Run verification:**

```powershell
.\verify-mcp-setup.ps1
```

## Troubleshooting

### EV2 MCP Server Issues

**Issue: "dnx: command not found"**

Solution:
```powershell
# Reinstall dnx
dotnet tool install --global dnx

# Add to PATH (Windows)
$env:PATH += ";$env:USERPROFILE\.dotnet\tools"

# Verify
dnx --version
```

**Issue: "Authentication failed"**

Solution:
```powershell
# Check environment variables
Get-ChildItem env: | Where-Object Name -like "AZURE_*"

# Test Azure CLI authentication
az login
az account show

# For Service Principal
$env:AZURE_TENANT_ID = "your-tenant-id"
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_CLIENT_SECRET = "your-client-secret"
```

**Issue: "EV2 tool not found"**

Solution:
```powershell
# Check tool installation
dnx tool list -g

# Reinstall if missing
dnx tool uninstall -g mcp-server-ev2
dnx tool install -g mcp-server-ev2
```

### Azure DevOps MCP Server Issues

**Issue: "npm: command not found"**

Solution:
```powershell
# Install Node.js
winget install OpenJS.NodeJS.LTS

# Restart PowerShell session
# Verify
node --version
npm --version
```

**Issue: "Personal Access Token expired"**

Solution:
```powershell
# Create new PAT in Azure DevOps
# Update environment variable
$env:AZURE_DEVOPS_PAT = "new-token"

# Test authentication
az devops login --organization https://dev.azure.com/your-organization
```

**Issue: "Permission denied on repository operations"**

Solution:
```powershell
# Verify PAT scopes:
# - Code: Read & Write
# - Build: Read & Execute

# Recreate PAT with correct scopes
# Update environment variable
```

### Common Issues

**Issue: "MCP server not responding"**

Solution:
```powershell
# Check if server process is running
Get-Process | Where-Object Name -like "*mcp*"

# Restart servers by re-sourcing environment
# Or restart PowerShell session
```

**Issue: "Environment variables not persisting"**

Solution:
```powershell
# Set system-level environment variables (requires admin)
[Environment]::SetEnvironmentVariable("AZURE_TENANT_ID", "value", "Machine")

# Or set user-level
[Environment]::SetEnvironmentVariable("AZURE_TENANT_ID", "value", "User")

# Verify
[Environment]::GetEnvironmentVariable("AZURE_TENANT_ID", "Machine")
```

## Security Best Practices

1. **Never commit credentials** - Use `.env` files, add to `.gitignore`
2. **Use least-privilege** - Grant minimum required permissions
3. **Rotate tokens regularly** - Set PAT expiration, rotate before expiry
4. **Use MSI when possible** - Preferred for Azure VM deployments
5. **Encrypt secrets** - Use Azure Key Vault for production
6. **Audit access** - Review MCP server logs regularly

## Production Deployment

### Azure VM with MSI

```powershell
# 1. Create VM with managed identity
az vm create --name "deploy-sentinel-vm" --resource-group "rg" --assign-identity

# 2. Assign EV2 and Azure DevOps permissions to MSI

# 3. Install MCP servers
dnx tool install -g mcp-server-ev2
npm install -g mcp-server-azuredevops

# 4. No credentials needed - MSI handles authentication
```

### Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
steps:
  - task: UseDotNet@2
    inputs:
      version: '8.x'
  
  - task: NodeTool@0
    inputs:
      versionSpec: '18.x'
  
  - script: |
      dnx tool install -g mcp-server-ev2
      npm install -g mcp-server-azuredevops
    displayName: 'Install MCP Servers'
  
  - script: |
      .\deploy-sentinel.ps1 -Action trigger
    displayName: 'Trigger Deployment'
    env:
      AZURE_TENANT_ID: $(AZURE_TENANT_ID)
      AZURE_CLIENT_ID: $(AZURE_CLIENT_ID)
      AZURE_CLIENT_SECRET: $(AZURE_CLIENT_SECRET)
      AZURE_DEVOPS_PAT: $(AZURE_DEVOPS_PAT)
```

## Support

- **EV2 MCP Server Issues**: Contact EV2 support team
- **Azure DevOps MCP Server Issues**: Check npm registry or GitHub
- **General MCP Questions**: See Model Context Protocol documentation
- **Deploy Sentinel Issues**: See [troubleshooting.md](troubleshooting.md)

---

**Next Steps**: Return to [Deploy Sentinel README](README.md) to configure and run deployments.
