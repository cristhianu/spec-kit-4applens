# Bicep Deployment Test Helper
# PowerShell helper script for consistent Azure deployment commands

<#
.SYNOPSIS
    Wraps Azure CLI deployment commands with standardized parameters.

.DESCRIPTION
    This helper script provides a consistent interface for deploying Bicep templates
    to test environments. It's used by the ResourceDeployer module.

.PARAMETER ResourceGroupName
    The Azure resource group name

.PARAMETER TemplateFile
    Path to the Bicep template file

.PARAMETER TemplateParameterFile
    Optional: Path to parameters file

.PARAMETER WhatIf
    Optional: Perform dry-run validation only

.EXAMPLE
    .\bicep-deploy-test.ps1 -ResourceGroupName "rg-test" -TemplateFile "./main.bicep"

.EXAMPLE
    .\bicep-deploy-test.ps1 -ResourceGroupName "rg-test" -TemplateFile "./main.bicep" -WhatIf
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory=$true)]
    [string]$TemplateFile,

    [Parameter(Mandatory=$false)]
    [string]$TemplateParameterFile,

    [Parameter(Mandatory=$false)]
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

# Validate template file exists
if (-not (Test-Path $TemplateFile)) {
    Write-Error "Template file not found: $TemplateFile"
    exit 1
}

# Build deployment command
$deploymentParams = @{
    ResourceGroupName = $ResourceGroupName
    TemplateFile = $TemplateFile
    Mode = 'Incremental'
}

if ($TemplateParameterFile -and (Test-Path $TemplateParameterFile)) {
    $deploymentParams['TemplateParameterFile'] = $TemplateParameterFile
}

if ($WhatIf) {
    $deploymentParams['WhatIf'] = $true
}

try {
    # Execute deployment
    $result = New-AzResourceGroupDeployment @deploymentParams
    
    # Output structured result
    $output = @{
        DeploymentId = $result.DeploymentName
        ProvisioningState = $result.ProvisioningState
        Timestamp = $result.Timestamp
        Duration = $result.Duration
        Outputs = $result.Outputs
    }
    
    if ($result.Error) {
        $output['ErrorMessage'] = $result.Error.Message
        $output['ErrorCode'] = $result.Error.Code
    }
    
    # Return as JSON for easy parsing
    $output | ConvertTo-Json -Depth 10
    
    # Exit with appropriate code
    if ($result.ProvisioningState -eq 'Succeeded') {
        exit 0
    } else {
        exit 1
    }
}
catch {
    # Output error in structured format
    $errorOutput = @{
        DeploymentId = $null
        ProvisioningState = 'Failed'
        ErrorMessage = $_.Exception.Message
        ErrorDetails = $_.Exception.ToString()
    }
    
    $errorOutput | ConvertTo-Json -Depth 10
    exit 1
}
