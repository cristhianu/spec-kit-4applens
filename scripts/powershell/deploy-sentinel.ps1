<#
.SYNOPSIS
    EV2 Deployment Follower Agent - Automates Azure EV2 rollouts with monitoring, stress testing, and notifications

.DESCRIPTION
    deploy-sentinel.ps1 orchestrates EV2 rollouts by:
    - Triggering deployments via EV2 MCP Server
    - Creating feature branches via Azure DevOps MCP Server
    - Monitoring rollout progress with configurable polling
    - Running stress tests against deployed endpoints
    - Sending Teams notifications at key milestones
    
    State Management:
    - JSON file persistence with atomic writes (temp file + rename)
    - Exclusive file locking for idempotency across parallel runs
    - Stale lock detection with configurable timeout (default: 5 minutes)
    
    PowerShell Compatibility:
    - PowerShell 5.1+ (Windows PowerShell)
    - PowerShell Core 7+ (cross-platform)

.PARAMETER ConfigPath
    Path to the deployment configuration JSON file (default: .deploy-sentinel-config.json)

.PARAMETER Action
    Action to perform:
    - trigger: Start EV2 rollout
    - monitor: Check rollout status
    - stress-test: Run stress tests against deployed endpoints
    - create-branch: Create feature branch in Azure DevOps
    - full: Execute complete workflow (trigger + monitor + stress-test + notify)

.PARAMETER RolloutId
    Existing rollout ID to monitor (optional - auto-discovered if omitted)
    
    Where to find RolloutId:
    - EV2 Portal: Navigate to your service group → Rollouts → Copy ID from URL or rollout list
    - State file: Check ".deploy-sentinel-state.json" if rollout was previously triggered
    - EV2 API: Use get_rollout_details MCP tool with service/artifact information

.PARAMETER ForceUnlock
    Force unlock state file if stale lock detected

.PARAMETER Verbose
    Enable verbose logging output

.EXAMPLE
    .\deploy-sentinel.ps1 -Action trigger
    Starts a new EV2 rollout using the default configuration

.EXAMPLE
    .\deploy-sentinel.ps1 -Action monitor -RolloutId "abc-123-def-456"
    Monitors an existing rollout by ID

.EXAMPLE
    .\deploy-sentinel.ps1 -Action full -ConfigPath ".\my-config.json" -Verbose
    Executes the complete workflow with verbose logging

.NOTES
    Feature: 005-deploy-sentinel
    MCP Servers Required:
    - EV2 MCP Server (dnx)
    - Azure DevOps MCP Server (npm install -g @azure/mcp-server-azuredevops)
    
    Configuration: See .deploy-sentinel-config.json for parameter documentation
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ConfigPath = ".deploy-sentinel-config.json",
    
    [Parameter(Mandatory = $true)]
    [ValidateSet("trigger", "monitor", "stress-test", "create-branch", "full")]
    [string]$Action,
    
    [Parameter(Mandatory = $false)]
    [string]$RolloutId,
    
    [Parameter(Mandatory = $false)]
    [switch]$ForceUnlock,
    
    [Parameter(Mandatory = $false)]
    [switch]$Verbose,
    
    # User Story 7 - Approval Gate Parameters
    [Parameter(Mandatory = $false)]
    [switch]$ApproveWaitAction,
    
    [Parameter(Mandatory = $false)]
    [switch]$RejectWaitAction,
    
    [Parameter(Mandatory = $false)]
    [string]$ActionId
)

#Requires -Version 5.1

# ============================================================================
# Global Variables
# ============================================================================

$script:StateFilePath = ".deploy-sentinel-state.json"
$script:LockFilePath = ".deploy-sentinel-state.lock"
$script:LogFilePath = ".deploy-sentinel.log"
$script:StaleLockTimeoutMinutes = 5
$script:DefaultPollingIntervalSeconds = 30
$script:DefaultMaxRetries = 3

# ============================================================================
# Configuration Functions
# ============================================================================

<#
.SYNOPSIS
    Load and validate deployment configuration from JSON file

.DESCRIPTION
    Reads the configuration file, validates required parameters, and supports
    environment variable substitution for sensitive values (e.g., ${TEAMS_WEBHOOK_URL})

.PARAMETER Path
    Path to the configuration JSON file

.OUTPUTS
    [PSCustomObject] Configuration object with validated parameters

.EXAMPLE
    $config = Load-DeploymentConfig -Path ".deploy-sentinel-config.json"
#>
function Load-DeploymentConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    
    Write-DeploymentLog -Level INFO -Message "Loading configuration from: $Path"
    Write-Verbose "Load-DeploymentConfig: Reading configuration file '$Path'"
    
    # Security: Path sanitization to prevent directory traversal
    $Path = [System.IO.Path]::GetFullPath($Path)
    if (-not $Path.EndsWith(".json")) {
        throw "Configuration file must have .json extension: $Path"
    }
    
    if (-not (Test-Path $Path)) {
        throw @"
Configuration file not found: $Path

Where to find configuration file:
- Default location: .deploy-sentinel-config.json in current directory
- Specify custom path: Use -ConfigPath parameter
- Template available: See docs/deploy-sentinel/README.md for configuration examples
- Create new: Copy from repository templates/ directory
"@
    }
    
    try {
        $configJson = Get-Content -Path $Path -Raw
        
        # Environment variable substitution: ${VAR_NAME} -> $env:VAR_NAME
        $configJson = [regex]::Replace($configJson, '\$\{([^}]+)\}', {
            param($match)
            $envVar = $match.Groups[1].Value
            $value = [System.Environment]::GetEnvironmentVariable($envVar)
            if ($null -eq $value) {
                Write-DeploymentLog -Level WARN -Message "Environment variable not found: $envVar"
                return $match.Value
            }
            return $value
        })
        
        $config = $configJson | ConvertFrom-Json
        
        # Validate required parameters
        $requiredParams = @(
            "serviceGroupName",
            "serviceId",
            "stageMapName",
            "environment"
        )
        
        foreach ($param in $requiredParams) {
            if (-not $config.PSObject.Properties.Name.Contains($param) -or [string]::IsNullOrWhiteSpace($config.$param)) {
                $guidance = switch ($param) {
                    "serviceGroupName" { "Find in EV2 Portal → Service Groups → Copy exact name" }
                    "serviceId" { "Find in EV2 Portal → Service Groups → Services → Copy service ID" }
                    "stageMapName" { "Find in EV2 Portal → Stage Maps → Copy stage map name for your service" }
                    "environment" { "Specify target environment (e.g., 'prod', 'staging', 'canary')" }
                    default { "See docs/deploy-sentinel/README.md for configuration details" }
                }
                throw @"
Required configuration parameter missing or empty: $param

Where to find '$param':
$guidance

Example configuration:
{
  "serviceGroupName": "MyServiceGroup",
  "serviceId": "MyService",
  "stageMapName": "StandardStageMap",
  "environment": "prod"
}
"@
            }
        }
        
        # Security: Input validation with regex patterns
        Write-Verbose "Load-DeploymentConfig: Validating configuration parameters"
        if ($config.serviceGroupName -notmatch '^[a-zA-Z0-9_-]+$') {
            throw "Invalid serviceGroupName: Must contain only letters, numbers, underscores, and hyphens"
        }
        if ($config.serviceId -notmatch '^[a-zA-Z0-9_-]+$') {
            throw "Invalid serviceId: Must contain only letters, numbers, underscores, and hyphens"
        }
        if ($config.environment -notmatch '^[a-zA-Z0-9_-]+$') {
            throw "Invalid environment: Must contain only letters, numbers, underscores, and hyphens"
        }
        
        # Set defaults for optional parameters
        if (-not $config.PSObject.Properties.Name.Contains("pollingInterval")) {
            $config | Add-Member -NotePropertyName "pollingInterval" -NotePropertyValue $script:DefaultPollingIntervalSeconds
        }
        
        if (-not $config.PSObject.Properties.Name.Contains("maxRetries")) {
            $config | Add-Member -NotePropertyName "maxRetries" -NotePropertyValue $script:DefaultMaxRetries
        }
        
        Write-DeploymentLog -Level INFO -Message "Configuration loaded successfully"
        return $config
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to load configuration: $_"
        throw
    }
}

# ============================================================================
# State Management Functions
# ============================================================================

<#
.SYNOPSIS
    Read rollout state from JSON file

.DESCRIPTION
    Loads the current deployment state with file locking support

.OUTPUTS
    [PSCustomObject] RolloutState object or $null if file doesn't exist

.EXAMPLE
    $state = Read-RolloutState
#>
function Read-RolloutState {
    [CmdletBinding()]
    param()
    
    if (-not (Test-Path $script:StateFilePath)) {
        Write-DeploymentLog -Level INFO -Message "No existing state file found"
        return $null
    }
    
    try {
        $stateJson = Get-Content -Path $script:StateFilePath -Raw
        $state = $stateJson | ConvertFrom-Json
        Write-DeploymentLog -Level INFO -Message "State loaded: RolloutId=$($state.rolloutId), Status=$($state.status)"
        return $state
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to read state file: $_"
        throw
    }
}

<#
.SYNOPSIS
    Write rollout state to JSON file with atomic operation

.DESCRIPTION
    Persists deployment state using atomic writes (temp file + rename) to prevent corruption

.PARAMETER State
    RolloutState object to persist

.EXAMPLE
    Write-RolloutState -State $state
#>
function Write-RolloutState {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$State
    )
    
    try {
        # Update timestamp
        $State.lastUpdated = (Get-Date).ToString("o")
        
        # Atomic write: temp file + rename
        $tempFile = "$($script:StateFilePath).tmp"
        $State | ConvertTo-Json -Depth 10 | Set-Content -Path $tempFile -Force
        
        # Rename is atomic on Windows/Linux
        Move-Item -Path $tempFile -Destination $script:StateFilePath -Force
        
        Write-DeploymentLog -Level INFO -Message "State persisted: RolloutId=$($State.rolloutId), Status=$($State.status)"
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to write state file: $_"
        throw
    }
}

<#
.SYNOPSIS
    Acquire exclusive lock on state file

.DESCRIPTION
    Creates a lock file with process ID and timestamp for idempotency.
    Supports stale lock detection and force unlock.

.PARAMETER Force
    Force unlock if stale lock detected (older than $script:StaleLockTimeoutMinutes)

.OUTPUTS
    [bool] $true if lock acquired, $false otherwise

.EXAMPLE
    if (Lock-StateFile -Force:$ForceUnlock) { ... }
#>
function Lock-StateFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [switch]$Force
    )
    
    if (Test-Path $script:LockFilePath) {
        # Check for stale lock
        $lockInfo = Get-Content -Path $script:LockFilePath | ConvertFrom-Json
        $lockAge = (Get-Date) - [datetime]$lockInfo.timestamp
        
        if ($lockAge.TotalMinutes -gt $script:StaleLockTimeoutMinutes) {
            Write-DeploymentLog -Level WARN -Message "Stale lock detected (age: $($lockAge.TotalMinutes) minutes, PID: $($lockInfo.processId))"
            
            if ($Force) {
                Write-DeploymentLog -Level INFO -Message "Force unlock requested - removing stale lock"
                Remove-Item -Path $script:LockFilePath -Force
            }
            else {
                Write-DeploymentLog -Level ERROR -Message "State file locked by stale process. Use -ForceUnlock to override."
                return $false
            }
        }
        else {
            Write-DeploymentLog -Level ERROR -Message "State file locked by process $($lockInfo.processId) (age: $($lockAge.TotalMinutes) minutes)"
            return $false
        }
    }
    
    try {
        $lockInfo = @{
            processId = $PID
            timestamp = (Get-Date).ToString("o")
            hostname  = $env:COMPUTERNAME
        }
        
        $lockInfo | ConvertTo-Json | Set-Content -Path $script:LockFilePath -Force
        Write-DeploymentLog -Level INFO -Message "Lock acquired (PID: $PID)"
        return $true
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to acquire lock: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Release exclusive lock on state file

.DESCRIPTION
    Removes the lock file created by Lock-StateFile

.EXAMPLE
    Unlock-StateFile
#>
function Unlock-StateFile {
    [CmdletBinding()]
    param()
    
    if (Test-Path $script:LockFilePath) {
        try {
            Remove-Item -Path $script:LockFilePath -Force
            Write-DeploymentLog -Level INFO -Message "Lock released (PID: $PID)"
        }
        catch {
            Write-DeploymentLog -Level ERROR -Message "Failed to release lock: $_"
        }
    }
}

# ============================================================================
# Logging Functions
# ============================================================================

<#
.SYNOPSIS
    Write timestamped log entry to file and console

.DESCRIPTION
    Logs messages with level (INFO/WARN/ERROR) and ISO 8601 timestamps

.PARAMETER Level
    Log level: INFO, WARN, ERROR

.PARAMETER Message
    Log message text

.EXAMPLE
    Write-DeploymentLog -Level INFO -Message "Deployment started"
#>
function Write-DeploymentLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level,
        
        [Parameter(Mandatory = $true)]
        [string]$Message
    )
    
    $timestamp = (Get-Date).ToString("o")
    $logEntry = "$timestamp [$Level] $Message"
    
    # Write to file
    Add-Content -Path $script:LogFilePath -Value $logEntry
    
    # Write to console with color
    $color = switch ($Level) {
        "INFO" { "White" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
    }
    
    Write-Host $logEntry -ForegroundColor $color
}

# ============================================================================
# Retry Logic Functions
# ============================================================================

<#
.SYNOPSIS
    Execute script block with retry logic and exponential backoff

.DESCRIPTION
    Retries failed operations with delays: 1s, 2s, 4s, 8s, etc.
    Configurable max retries from configuration (default: 3)

.PARAMETER ScriptBlock
    Code to execute with retry logic

.PARAMETER MaxRetries
    Maximum retry attempts (default: $script:DefaultMaxRetries)

.PARAMETER Description
    Human-readable description for logging

.OUTPUTS
    Result of script block execution

.EXAMPLE
    Invoke-WithRetry -ScriptBlock { Get-RolloutStatus } -Description "Get rollout status"
#>
function Invoke-WithRetry {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock,
        
        [Parameter(Mandatory = $false)]
        [int]$MaxRetries = $script:DefaultMaxRetries,
        
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    
    $attempt = 0
    $delay = 1
    
    while ($attempt -le $MaxRetries) {
        try {
            Write-DeploymentLog -Level INFO -Message "$Description (attempt $($attempt + 1)/$($MaxRetries + 1))"
            return & $ScriptBlock
        }
        catch {
            $attempt++
            
            if ($attempt -gt $MaxRetries) {
                Write-DeploymentLog -Level ERROR -Message "$Description failed after $($MaxRetries + 1) attempts: $_"
                throw
            }
            
            Write-DeploymentLog -Level WARN -Message "$Description failed (attempt $attempt/$($MaxRetries + 1)): $_. Retrying in $delay seconds..."
            Start-Sleep -Seconds $delay
            $delay = $delay * 2  # Exponential backoff
        }
    }
}

# ============================================================================
# MCP Tool Wrapper Functions
# ============================================================================

<#
.SYNOPSIS
    Invoke MCP tool with error handling and logging

.DESCRIPTION
    Wrapper for MCP tool invocations with standardized error handling,
    logging, and response parsing

.PARAMETER ToolName
    MCP tool name (e.g., "mcp_ev2_mcp_serve_start_rollout")

.PARAMETER Parameters
    Hashtable of tool parameters

.OUTPUTS
    [PSCustomObject] Tool response

.EXAMPLE
    $result = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_start_rollout" -Parameters @{ serviceId = "..."; ... }
#>
function Invoke-McpTool {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ToolName,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$Parameters
    )
    
    Write-DeploymentLog -Level INFO -Message "Invoking MCP tool: $ToolName"
    
    try {
        # TODO: Implement actual MCP tool invocation
        # For now, this is a placeholder structure
        # Real implementation will use VS Code MCP API or CLI integration
        
        throw "MCP tool invocation not yet implemented. Tool: $ToolName"
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "MCP tool invocation failed: $ToolName - $_"
        throw
    }
}

# ============================================================================
# EV2 Operations - User Story 1
# ============================================================================

<#
.SYNOPSIS
    Get EV2 best practices from MCP Server

.DESCRIPTION
    Calls mcp_ev2_mcp_serve_get_ev2_best_practices and logs the output.
    Should be called before any other EV2 operations per best practices.

.OUTPUTS
    [PSCustomObject] Best practices response

.EXAMPLE
    $bestPractices = Get-Ev2BestPractices
#>
function Get-Ev2BestPractices {
    [CmdletBinding()]
    param()
    
    Write-DeploymentLog -Level INFO -Message "Retrieving EV2 best practices"
    
    $result = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_ev2_best_practices" -Parameters @{}
    
    if ($result.bestPractices) {
        Write-DeploymentLog -Level INFO -Message "EV2 Best Practices:"
        foreach ($practice in $result.bestPractices) {
            Write-DeploymentLog -Level INFO -Message "  - $practice"
        }
    }
    
    return $result
}

<#
.SYNOPSIS
    Get latest artifact version for a service

.DESCRIPTION
    Calls mcp_ev2_mcp_serve_get_artifact_versions and returns the latest version

.PARAMETER ServiceId
    Service ID to query

.OUTPUTS
    [PSCustomObject] Latest artifact version details

.EXAMPLE
    $artifact = Get-LatestArtifactVersion -ServiceId "test-service-001"
#>
function Get-LatestArtifactVersion {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceId
    )
    
    Write-DeploymentLog -Level INFO -Message "Discovering latest artifact version for service: $ServiceId"
    
    $params = @{
        serviceId = $ServiceId
    }
    
    $versions = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_artifact_versions" -Parameters $params
    
    if (-not $versions -or $versions.Count -eq 0) {
        throw "No artifact versions found for service: $ServiceId"
    }
    
    # Find version marked as latest
    $latest = $versions | Where-Object { $_.isLatest -eq $true } | Select-Object -First 1
    
    if (-not $latest) {
        # Fallback: sort by createdAt descending
        $latest = $versions | Sort-Object -Property createdAt -Descending | Select-Object -First 1
    }
    
    Write-DeploymentLog -Level INFO -Message "Latest artifact version: $($latest.version) (created: $($latest.createdAt))"
    return $latest
}

<#
.SYNOPSIS
    Get latest stage map version

.DESCRIPTION
    Calls mcp_ev2_mcp_serve_get_stage_map_versions and returns the latest version

.PARAMETER StageMapName
    Stage map name to query

.OUTPUTS
    [PSCustomObject] Latest stage map version details

.EXAMPLE
    $stageMap = Get-LatestStageMapVersion -StageMapName "TestStageMap"
#>
function Get-LatestStageMapVersion {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$StageMapName
    )
    
    Write-DeploymentLog -Level INFO -Message "Discovering latest stage map version: $StageMapName"
    
    $params = @{
        stageMapName = $StageMapName
    }
    
    $versions = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_stage_map_versions" -Parameters $params
    
    if (-not $versions -or $versions.Count -eq 0) {
        throw "No stage map versions found: $StageMapName"
    }
    
    # Find version marked as latest
    $latest = $versions | Where-Object { $_.isLatest -eq $true } | Select-Object -First 1
    
    if (-not $latest) {
        # Fallback: sort by createdAt descending
        $latest = $versions | Sort-Object -Property createdAt -Descending | Select-Object -First 1
    }
    
    Write-DeploymentLog -Level INFO -Message "Latest stage map version: $($latest.version) (created: $($latest.createdAt))"
    return $latest
}

<#
.SYNOPSIS
    Create ServiceInfo entity from artifact and stage map discovery

.DESCRIPTION
    Constructs ServiceInfo data structure with discovered versions

.PARAMETER ServiceId
    Service ID

.PARAMETER ServiceGroupName
    Service group name

.PARAMETER ArtifactVersion
    Artifact version object from Get-LatestArtifactVersion

.PARAMETER StageMapVersion
    Stage map version object from Get-LatestStageMapVersion

.OUTPUTS
    [PSCustomObject] ServiceInfo entity

.EXAMPLE
    $serviceInfo = New-ServiceInfo -ServiceId "..." -ServiceGroupName "..." -ArtifactVersion $artifact -StageMapVersion $stageMap
#>
function New-ServiceInfo {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceId,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceGroupName,
        
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$ArtifactVersion,
        
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$StageMapVersion
    )
    
    $serviceInfo = [PSCustomObject]@{
        serviceId         = $ServiceId
        serviceGroupName  = $ServiceGroupName
        artifactVersion   = $ArtifactVersion.version
        artifactId        = $ArtifactVersion.artifactId
        stageMapVersion   = $StageMapVersion.version
        stageMapId        = $StageMapVersion.stageMapId
        discoveredAt      = (Get-Date).ToString("o")
    }
    
    Write-DeploymentLog -Level INFO -Message "ServiceInfo created: Service=$ServiceId, Artifact=$($serviceInfo.artifactVersion), StageMap=$($serviceInfo.stageMapVersion)"
    return $serviceInfo
}

<#
.SYNOPSIS
    Build EV2 selection scope from configuration

.DESCRIPTION
    Constructs scope object for EV2 rollout (subscriptions, regions, etc.)

.PARAMETER Config
    Deployment configuration object

.OUTPUTS
    [hashtable] EV2 scope parameters

.EXAMPLE
    $scope = Build-SelectionScope -Config $config
#>
function Build-SelectionScope {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Config
    )
    
    $scope = @{
        environment = $Config.environment
    }
    
    if ($Config.PSObject.Properties.Name.Contains("selectionScope")) {
        if ($Config.selectionScope.subscriptions) {
            $scope.subscriptions = $Config.selectionScope.subscriptions
        }
        if ($Config.selectionScope.regions) {
            $scope.regions = $Config.selectionScope.regions
        }
    }
    
    if ($Config.PSObject.Properties.Name.Contains("exclusionScope")) {
        $scope.exclusionScope = @{}
        if ($Config.exclusionScope.regions) {
            $scope.exclusionScope.regions = $Config.exclusionScope.regions
        }
    }
    
    Write-DeploymentLog -Level INFO -Message "Selection scope built: Environment=$($scope.environment)"
    return $scope
}

<#
.SYNOPSIS
    Start EV2 rollout

.DESCRIPTION
    Calls mcp_ev2_mcp_serve_start_rollout with discovered versions and scope

.PARAMETER ServiceGroupName
    Service group name

.PARAMETER ServiceId
    Service ID

.PARAMETER ArtifactVersion
    Artifact version string

.PARAMETER StageMapVersion
    Stage map version string

.PARAMETER Scope
    Selection scope hashtable

.OUTPUTS
    [PSCustomObject] Rollout start response

.EXAMPLE
    $rollout = Start-Ev2Rollout -ServiceGroupName "..." -ServiceId "..." -ArtifactVersion "1.2.3" -StageMapVersion "2.0.1" -Scope $scope
#>
function Start-Ev2Rollout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceGroupName,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceId,
        
        [Parameter(Mandatory = $true)]
        [string]$ArtifactVersion,
        
        [Parameter(Mandatory = $true)]
        [string]$StageMapVersion,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$Scope
    )
    
    Write-DeploymentLog -Level INFO -Message "Starting EV2 rollout for service: $ServiceId"
    
    $params = @{
        serviceGroupName = $ServiceGroupName
        serviceId        = $ServiceId
        artifactVersion  = $ArtifactVersion
        stageMapVersion  = $StageMapVersion
        environment      = $Scope.environment
    }
    
    if ($Scope.subscriptions) {
        $params.subscriptions = $Scope.subscriptions
    }
    if ($Scope.regions) {
        $params.regions = $Scope.regions
    }
    if ($Scope.exclusionScope) {
        $params.exclusionScope = $Scope.exclusionScope
    }
    
    $result = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_start_rollout" -Parameters $params
    
    Write-DeploymentLog -Level INFO -Message "Rollout started: RolloutId=$($result.rolloutId), Status=$($result.status)"
    return $result
}

<#
.SYNOPSIS
    Get Azure authentication token

.DESCRIPTION
    Implements Azure credential chain: MSI, service principal, user credentials.
    Used for stress test authentication (User Story 5).

.OUTPUTS
    [string] Bearer token

.EXAMPLE
    $token = Get-AzureAuthToken
#>
function Get-AzureAuthToken {
    [CmdletBinding()]
    param()
    
    Write-DeploymentLog -Level INFO -Message "Acquiring Azure authentication token"
    
    # Try Managed Service Identity (MSI) first
    try {
        $msiEndpoint = $env:MSI_ENDPOINT
        $msiSecret = $env:MSI_SECRET
        
        if ($msiEndpoint -and $msiSecret) {
            Write-DeploymentLog -Level INFO -Message "Using Managed Service Identity (MSI)"
            $response = Invoke-RestMethod -Uri "$msiEndpoint`?resource=https://management.azure.com/&api-version=2017-09-01" -Method Get -Headers @{ Secret = $msiSecret }
            return $response.access_token
        }
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "MSI authentication failed: $_"
    }
    
    # Try Service Principal (environment variables)
    try {
        $clientId = $env:AZURE_CLIENT_ID
        $clientSecret = $env:AZURE_CLIENT_SECRET
        $tenantId = $env:AZURE_TENANT_ID
        
        if ($clientId -and $clientSecret -and $tenantId) {
            Write-DeploymentLog -Level INFO -Message "Using Service Principal credentials"
            $body = @{
                grant_type    = "client_credentials"
                client_id     = $clientId
                client_secret = $clientSecret
                resource      = "https://management.azure.com/"
            }
            $response = Invoke-RestMethod -Uri "https://login.microsoftonline.com/$tenantId/oauth2/token" -Method Post -Body $body
            return $response.access_token
        }
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "Service Principal authentication failed: $_"
    }
    
    # Try Azure CLI token (user credentials)
    try {
        Write-DeploymentLog -Level INFO -Message "Using Azure CLI user credentials"
        $azAccount = az account show 2>$null | ConvertFrom-Json
        if ($azAccount) {
            $token = az account get-access-token --resource https://management.azure.com/ | ConvertFrom-Json
            return $token.accessToken
        }
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "Azure CLI authentication failed: $_"
    }
    
    throw "Unable to acquire Azure authentication token. No credentials available (MSI, Service Principal, or Azure CLI)."
}

<#
.SYNOPSIS
    Orchestrate rollout trigger workflow

.DESCRIPTION
    Main workflow function for User Story 1:
    - Get EV2 best practices
    - Discover latest artifact/stage map versions
    - Build selection scope
    - Start rollout
    - Create RolloutState entity

.PARAMETER Config
    Deployment configuration object

.OUTPUTS
    [PSCustomObject] RolloutState entity

.EXAMPLE
    $state = Invoke-TriggerRollout -Config $config
#>
function Invoke-TriggerRollout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Config
    )
    
    Write-DeploymentLog -Level INFO -Message "=== Starting Rollout Trigger Workflow ==="
    
    # Parameter validation
    if ([string]::IsNullOrWhiteSpace($Config.serviceGroupName)) {
        throw "Configuration parameter 'serviceGroupName' is required"
    }
    if ([string]::IsNullOrWhiteSpace($Config.serviceId)) {
        throw "Configuration parameter 'serviceId' is required"
    }
    if ([string]::IsNullOrWhiteSpace($Config.stageMapName)) {
        throw "Configuration parameter 'stageMapName' is required"
    }
    if ([string]::IsNullOrWhiteSpace($Config.environment)) {
        throw "Configuration parameter 'environment' is required"
    }
    
    # Step 1: Get EV2 best practices
    Get-Ev2BestPractices | Out-Null
    
    # Step 2: Discover latest versions
    $artifactVersion = Get-LatestArtifactVersion -ServiceId $Config.serviceId
    $stageMapVersion = Get-LatestStageMapVersion -StageMapName $Config.stageMapName
    
    # Step 3: Create ServiceInfo entity
    $serviceInfo = New-ServiceInfo -ServiceId $Config.serviceId -ServiceGroupName $Config.serviceGroupName -ArtifactVersion $artifactVersion -StageMapVersion $stageMapVersion
    
    # Step 4: Build selection scope
    $scope = Build-SelectionScope -Config $Config
    
    # Step 5: Start rollout
    $rollout = Start-Ev2Rollout -ServiceGroupName $Config.serviceGroupName -ServiceId $Config.serviceId -ArtifactVersion $serviceInfo.artifactVersion -StageMapVersion $serviceInfo.stageMapVersion -Scope $scope
    
    # Step 6: Create RolloutState entity
    $state = [PSCustomObject]@{
        rolloutId     = $rollout.rolloutId
        status        = $rollout.status
        serviceInfo   = $serviceInfo
        startedAt     = (Get-Date).ToString("o")
        lastUpdated   = (Get-Date).ToString("o")
        branchName    = $null  # Will be set by User Story 2
        pipelineRunId = $null  # Will be set by User Story 7
        stressTests   = @()    # Will be populated by User Story 6
        notifications = @()    # Will be populated by User Story 5
    }
    
    Write-DeploymentLog -Level INFO -Message "Rollout trigger workflow complete. RolloutId: $($state.rolloutId)"
    return $state
}

# ============================================================================
# Rollout Monitoring - User Story 3
# ============================================================================

<#
.SYNOPSIS
    Get current rollout status from EV2

.DESCRIPTION
    Calls mcp_ev2_mcp_serve_get_rollout_details to retrieve detailed status

.PARAMETER RolloutId
    Rollout ID to query

.OUTPUTS
    [PSCustomObject] Rollout status details

.EXAMPLE
    $status = Get-RolloutStatus -RolloutId "test-rollout-12345-abc"
#>
function Get-RolloutStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RolloutId
    )
    
    Write-DeploymentLog -Level INFO -Message "Retrieving rollout status: $RolloutId"
    
    $params = @{
        rolloutId = $RolloutId
    }
    
    $status = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_get_rollout_details" -Parameters $params
    
    Write-DeploymentLog -Level INFO -Message "Rollout status: $($status.status), Progress: $($status.progress)%"
    if ($status.currentStage) {
        Write-DeploymentLog -Level INFO -Message "Current stage: $($status.currentStage)"
    }
    
    return $status
}

<#
.SYNOPSIS
    Format rollout status for console display

.DESCRIPTION
    Creates human-readable status output with stages, regions, and progress

.PARAMETER Status
    Rollout status object from Get-RolloutStatus

.OUTPUTS
    [string] Formatted status message

.EXAMPLE
    $display = Format-RolloutStatusDisplay -Status $status
    Write-Host $display
#>
function Format-RolloutStatusDisplay {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Status
    )
    
    $lines = @()
    $lines += "═══════════════════════════════════════════════════════════════"
    $lines += "Rollout ID: $($Status.rolloutId)"
    $lines += "Status: $($Status.status)"
    $lines += "Progress: $($Status.progress)%"
    $lines += "Last Updated: $($Status.lastUpdated)"
    
    if ($Status.currentStage) {
        $lines += "Current Stage: $($Status.currentStage)"
        
        if ($Status.stageDetails) {
            $lines += "  Stage Status: $($Status.stageDetails.status)"
            $lines += "  Started At: $($Status.stageDetails.startedAt)"
            if ($Status.stageDetails.resourcesDeployed) {
                $lines += "  Resources: $($Status.stageDetails.resourcesDeployed)/$($Status.stageDetails.totalResources)"
            }
        }
    }
    
    if ($Status.completedStages -and $Status.completedStages.Count -gt 0) {
        $lines += "Completed Stages: $($Status.completedStages.Count)"
        foreach ($stage in $Status.completedStages) {
            $lines += "  ✓ $stage"
        }
    }
    
    if ($Status.status -eq "Failed" -and $Status.errorMessage) {
        $lines += "ERROR: $($Status.errorMessage)"
    }
    
    if ($Status.status -eq "Cancelled") {
        $lines += "CANCELLED by $($Status.cancelledBy) at $($Status.cancelledAt)"
    }
    
    $lines += "═══════════════════════════════════════════════════════════════"
    
    return $lines -join "`n"
}

<#
.SYNOPSIS
    Test if rollout has reached terminal state

.DESCRIPTION
    Checks if rollout status is Completed, Failed, or Cancelled

.PARAMETER Status
    Rollout status object

.OUTPUTS
    [bool] $true if terminal state, $false otherwise

.EXAMPLE
    if (Test-RolloutComplete -Status $status) { ... }
#>
function Test-RolloutComplete {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Status
    )
    
    $terminalStates = @("Completed", "Failed", "Cancelled")
    $isComplete = $Status.status -in $terminalStates
    
    if ($isComplete) {
        Write-DeploymentLog -Level INFO -Message "Rollout reached terminal state: $($Status.status)"
    }
    
    return $isComplete
}

<#
.SYNOPSIS
    Monitor rollout with continuous polling

.DESCRIPTION
    Polls EV2 rollout status at configured interval until terminal state reached

.PARAMETER RolloutId
    Rollout ID to monitor

.PARAMETER PollingInterval
    Polling interval in seconds (default: 30)

.PARAMETER MaxIterations
    Maximum polling iterations before timeout (default: 120, i.e., 1 hour at 30s interval)

.OUTPUTS
    [PSCustomObject] Final rollout status

.EXAMPLE
    $finalStatus = Watch-Ev2Rollout -RolloutId "test-rollout-12345-abc" -PollingInterval 30
#>
function Watch-Ev2Rollout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RolloutId,
        
        [Parameter(Mandatory = $false)]
        [int]$PollingInterval = 30,
        
        [Parameter(Mandatory = $false)]
        [int]$MaxIterations = 120
    )
    
    Write-DeploymentLog -Level INFO -Message "Starting rollout monitoring: $RolloutId (interval: ${PollingInterval}s)"
    
    $iteration = 0
    $previousStage = $null
    
    while ($iteration -lt $MaxIterations) {
        $iteration++
        
        try {
            $status = Get-RolloutStatus -RolloutId $RolloutId
            
            # Display formatted status
            $display = Format-RolloutStatusDisplay -Status $status
            Write-Host $display
            
            # Detect stage transitions
            if ($status.currentStage -and $status.currentStage -ne $previousStage) {
                if ($previousStage) {
                    Write-DeploymentLog -Level INFO -Message "Stage transition detected: $previousStage → $($status.currentStage)"
                    Write-Host "`n✅ Stage completed: $previousStage" -ForegroundColor Green
                    
                    # User Story 5 - Run stress tests after stage completion
                    $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
                    if ($config.stressTestConfig -and $config.stressTestConfig.enabled -eq $true) {
                        Write-DeploymentLog -Level INFO -Message "Running stress test for completed stage: $previousStage"
                        Write-Host "`n🔄 Running stress test..." -ForegroundColor Cyan
                        
                        try {
                            $stressTestResult = Invoke-StressTest `
                                -EndpointUrl $config.stressTestConfig.endpointUrl `
                                -RequestCount $config.stressTestConfig.requestCount `
                                -TimeoutSeconds $config.stressTestConfig.timeoutSeconds
                            
                            # Display results
                            Write-Host "`nStress Test Results:" -ForegroundColor Cyan
                            Write-Host "  Endpoint: $($stressTestResult.endpointUrl)" -ForegroundColor Gray
                            Write-Host "  Total Requests: $($stressTestResult.totalRequests)" -ForegroundColor Gray
                            Write-Host "  Success Rate: $($stressTestResult.successRatePercent)%" -ForegroundColor Gray
                            Write-Host "  p50 Latency: $($stressTestResult.p50LatencyMs)ms" -ForegroundColor Gray
                            Write-Host "  p95 Latency: $($stressTestResult.p95LatencyMs)ms" -ForegroundColor Gray
                            Write-Host "  p99 Latency: $($stressTestResult.p99LatencyMs)ms" -ForegroundColor Gray
                            Write-Host "  Duration: $($stressTestResult.durationSeconds)s" -ForegroundColor Gray
                            
                            # Validate against thresholds
                            $passed = Test-StressTestPassed `
                                -StressTestResult $stressTestResult `
                                -MinSuccessRatePercent $config.stressTestConfig.minSuccessRatePercent `
                                -MaxP95LatencyMs $config.stressTestConfig.maxP95LatencyMs
                            
                            if ($passed) {
                                Write-Host "`n✅ Stress test PASSED" -ForegroundColor Green
                            }
                            else {
                                Write-Host "`n❌ Stress test FAILED" -ForegroundColor Red
                                Write-DeploymentLog -Level ERROR -Message "Stress test failed after stage: $previousStage"
                            }
                            
                            # User Story 8 - Send stress test results notification
                            if ($config.teamsWebhookUrl) {
                                $state = Read-RolloutState
                                if ($state) {
                                    $metrics = @{
                                        successRate = $stressTestResult.successRatePercent
                                        p50         = $stressTestResult.p50LatencyMs
                                        p95         = $stressTestResult.p95LatencyMs
                                        p99         = $stressTestResult.p99LatencyMs
                                    }
                                    $additionalData = @{ metrics = $metrics }
                                    $notification = New-NotificationMessage -RolloutState $state -NotificationType "StressTestResults" -AdditionalData $additionalData
                                    $notificationSent = Send-TeamsNotification `
                                        -WebhookUrl $config.teamsWebhookUrl `
                                        -Title $notification.title `
                                        -Message $notification.message `
                                        -ThemeColor $notification.themeColor `
                                        -Facts $notification.facts
                                    
                                    if (-not $notificationSent) {
                                        Write-NotificationLog -NotificationType "StressTestResults" -RolloutState $state -AdditionalData $additionalData
                                    }
                                }
                            }
                            
                            if (-not $passed) {
                                
                                # Prompt user for action (interactive mode only)
                                if ([Environment]::UserInteractive) {
                                    Write-Host "`nWhat would you like to do?" -ForegroundColor Cyan
                                    Write-Host "  1. Continue with rollout (ignore stress test failure)" -ForegroundColor Gray
                                    Write-Host "  2. Cancel rollout" -ForegroundColor Gray
                                    $userChoice = Read-Host "Enter choice (1-2)"
                                    
                                    if ($userChoice -eq "2") {
                                        Write-DeploymentLog -Level WARN -Message "User cancelled rollout due to stress test failure"
                                        $cancelResult = Stop-Ev2Rollout -RolloutId $RolloutId -Reason "Stress test failed after stage: $previousStage"
                                        return $cancelResult
                                    }
                                    else {
                                        Write-DeploymentLog -Level WARN -Message "User chose to continue despite stress test failure"
                                    }
                                }
                            }
                        }
                        catch {
                            Write-DeploymentLog -Level ERROR -Message "Stress test execution failed: $_"
                            Write-Host "`n⚠️ Stress test execution error: $_" -ForegroundColor Yellow
                            Write-Host "Continuing with rollout..." -ForegroundColor Yellow
                        }
                    }
                    
                    # User Story 8 - Send Teams notification on stage transition
                    $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
                    if ($config.teamsWebhookUrl) {
                        $state = Read-RolloutState
                        if ($state) {
                            $additionalData = @{ stageName = $previousStage }
                            $notification = New-NotificationMessage -RolloutState $state -NotificationType "StageCompleted" -AdditionalData $additionalData
                            $notificationSent = Send-TeamsNotification `
                                -WebhookUrl $config.teamsWebhookUrl `
                                -Title $notification.title `
                                -Message $notification.message `
                                -ThemeColor $notification.themeColor `
                                -Facts $notification.facts
                            
                            if (-not $notificationSent) {
                                Write-NotificationLog -NotificationType "StageCompleted" -RolloutState $state -AdditionalData $additionalData
                            }
                        }
                    }
                }
                $previousStage = $status.currentStage
            }
            
            # Check for failure state (User Story 4 - Error Handling)
            if ($status.status -eq "Failed") {
                Write-DeploymentLog -Level ERROR -Message "Rollout FAILED - extracting error details"
                
                # Extract errors
                $errors = Get-RolloutErrors -RolloutStatus $status
                
                # Display errors
                Write-Host "`n❌ ROLLOUT FAILED - Error Details:" -ForegroundColor Red
                foreach ($error in $errors) {
                    Write-Host "  Code: $($error.code)" -ForegroundColor Red
                    Write-Host "  Message: $($error.message)" -ForegroundColor Red
                    Write-Host "  Resource: $($error.resource)" -ForegroundColor Red
                    Write-Host "  Stage: $($error.stage)" -ForegroundColor Red
                    Write-Host "  Timestamp: $($error.timestamp)" -ForegroundColor Red
                    Write-Host ""
                }
                
                # Generate recommendation for primary error
                if ($errors.Count -gt 0) {
                    $primaryError = $errors[0]
                    $recommendation = Get-ErrorRecommendation -ErrorCode $primaryError.code -ErrorMessage $primaryError.message
                    Write-Host "📋 RECOMMENDATION:" -ForegroundColor Yellow
                    Write-Host $recommendation -ForegroundColor Yellow
                    Write-Host ""
                }
                
                # User Story 8 - Send "Rollout Failed" notification
                $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
                if ($config.teamsWebhookUrl) {
                    $state = Read-RolloutState
                    if ($state) {
                        $additionalData = @{ errors = $errors }
                        $notification = New-NotificationMessage -RolloutState $state -NotificationType "RolloutFailed" -AdditionalData $additionalData
                        $notificationSent = Send-TeamsNotification `
                            -WebhookUrl $config.teamsWebhookUrl `
                            -Title $notification.title `
                            -Message $notification.message `
                            -ThemeColor $notification.themeColor `
                            -Facts $notification.facts
                        
                        if (-not $notificationSent) {
                            Write-NotificationLog -NotificationType "RolloutFailed" -RolloutState $state -AdditionalData $additionalData
                        }
                    }
                }
                
                # Prompt user for action (interactive mode only)
                if ([Environment]::UserInteractive) {
                    Write-Host "What would you like to do?" -ForegroundColor Cyan
                    Write-Host "  1. Continue monitoring (rollout may auto-retry)" -ForegroundColor Gray
                    Write-Host "  2. Cancel rollout" -ForegroundColor Gray
                    Write-Host "  3. Exit monitoring (leave rollout running)" -ForegroundColor Gray
                    $userChoice = Read-Host "Enter choice (1-3)"
                    
                    switch ($userChoice) {
                        "1" {
                            Write-DeploymentLog -Level INFO -Message "User chose to continue monitoring"
                            # Continue polling loop
                        }
                        "2" {
                            Write-DeploymentLog -Level WARN -Message "User chose to cancel rollout"
                            $cancelResult = Stop-Ev2Rollout -RolloutId $RolloutId -Reason "User cancelled after failure"
                            return $cancelResult
                        }
                        "3" {
                            Write-DeploymentLog -Level INFO -Message "User chose to exit monitoring"
                            return $status
                        }
                        default {
                            Write-DeploymentLog -Level WARN -Message "Invalid choice, continuing monitoring"
                        }
                    }
                }
                else {
                    # Non-interactive mode - just return failed status
                    Write-DeploymentLog -Level WARN -Message "Non-interactive mode - returning failed status"
                    return $status
                }
            }
            
            # User Story 7 - Check for wait actions requiring approval
            $waitActions = Get-WaitActions -RolloutStatus $status
            if ($waitActions.Count -gt 0) {
                Write-DeploymentLog -Level WARN -Message "Found $($waitActions.Count) wait action(s) requiring approval"
                
                foreach ($waitAction in $waitActions) {
                    Write-Host "`n⚠️ APPROVAL REQUIRED" -ForegroundColor Yellow
                    Write-Host "  Stage: $($waitAction.stage)" -ForegroundColor Yellow
                    Write-Host "  Action ID: $($waitAction.actionId)" -ForegroundColor Yellow
                    Write-Host "  Description: $($waitAction.description)" -ForegroundColor Yellow
                    Write-Host ""
                    
                    # Send Teams notification if configured
                    $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
                    if ($config.teamsWebhookUrl) {
                        Write-DeploymentLog -Level INFO -Message "Sending approval notification to Teams"
                        try {
                            $notificationSent = Send-ApprovalNotification `
                                -WebhookUrl $config.teamsWebhookUrl `
                                -RolloutId $RolloutId `
                                -ActionId $waitAction.actionId `
                                -Stage $waitAction.stage `
                                -Message "Manual approval required before proceeding to next stage"
                            
                            if ($notificationSent) {
                                Write-Host "✅ Approval notification sent to Teams channel" -ForegroundColor Green
                            }
                            else {
                                Write-Host "⚠️ Failed to send Teams notification" -ForegroundColor Yellow
                            }
                        }
                        catch {
                            Write-DeploymentLog -Level ERROR -Message "Failed to send approval notification: $_"
                            Write-Host "⚠️ Error sending Teams notification: $_" -ForegroundColor Yellow
                        }
                    }
                    
                    # Prompt for approval decision (interactive mode only)
                    if ([Environment]::UserInteractive) {
                        Write-Host "What would you like to do?" -ForegroundColor Cyan
                        Write-Host "  1. Approve (continue rollout)" -ForegroundColor Gray
                        Write-Host "  2. Reject (cancel rollout)" -ForegroundColor Gray
                        Write-Host "  3. Wait (check again on next poll)" -ForegroundColor Gray
                        $userChoice = Read-Host "Enter choice (1-3)"
                        
                        switch ($userChoice) {
                            "1" {
                                Write-DeploymentLog -Level INFO -Message "User approved wait action: $($waitAction.actionId)"
                                try {
                                    $approvalResult = Stop-WaitAction `
                                        -RolloutId $RolloutId `
                                        -ServiceGroupName $config.serviceGroupName `
                                        -ServiceResourceGroup $config.serviceResourceGroup `
                                        -ServiceResource $config.serviceResource `
                                        -ActionId $waitAction.actionId `
                                        -Approve $true
                                    
                                    Write-Host "✅ Wait action APPROVED - rollout will continue" -ForegroundColor Green
                                }
                                catch {
                                    Write-DeploymentLog -Level ERROR -Message "Failed to approve wait action: $_"
                                    Write-Host "❌ Error approving wait action: $_" -ForegroundColor Red
                                }
                            }
                            "2" {
                                Write-DeploymentLog -Level WARN -Message "User rejected wait action: $($waitAction.actionId)"
                                try {
                                    $rejectionResult = Stop-WaitAction `
                                        -RolloutId $RolloutId `
                                        -ServiceGroupName $config.serviceGroupName `
                                        -ServiceResourceGroup $config.serviceResourceGroup `
                                        -ServiceResource $config.serviceResource `
                                        -ActionId $waitAction.actionId `
                                        -Approve $false
                                    
                                    Write-Host "❌ Wait action REJECTED - rollout will be cancelled" -ForegroundColor Red
                                    return $rejectionResult
                                }
                                catch {
                                    Write-DeploymentLog -Level ERROR -Message "Failed to reject wait action: $_"
                                    Write-Host "❌ Error rejecting wait action: $_" -ForegroundColor Red
                                }
                            }
                            "3" {
                                Write-DeploymentLog -Level INFO -Message "User chose to wait - will check again on next poll"
                                Write-Host "⏳ Will check for approval status on next poll..." -ForegroundColor Cyan
                            }
                            default {
                                Write-DeploymentLog -Level WARN -Message "Invalid choice, treating as 'wait'"
                                Write-Host "⏳ Invalid choice - will check again on next poll..." -ForegroundColor Yellow
                            }
                        }
                    }
                    else {
                        # Non-interactive mode - log and wait for external approval
                        Write-DeploymentLog -Level WARN -Message "Non-interactive mode - waiting for external approval of action: $($waitAction.actionId)"
                        Write-Host "⏳ Non-interactive mode - waiting for approval via CLI parameters..." -ForegroundColor Cyan
                    }
                }
            }
            
            # Check for terminal state
            if (Test-RolloutComplete -Status $status) {
                Write-DeploymentLog -Level INFO -Message "Rollout monitoring complete after $iteration iterations"
                
                # User Story 8 - Send "Rollout Completed" notification if successful
                if ($status.status -eq "Completed") {
                    $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
                    if ($config.teamsWebhookUrl) {
                        $state = Read-RolloutState
                        if ($state) {
                            $notification = New-NotificationMessage -RolloutState $state -NotificationType "RolloutCompleted"
                            $notificationSent = Send-TeamsNotification `
                                -WebhookUrl $config.teamsWebhookUrl `
                                -Title $notification.title `
                                -Message $notification.message `
                                -ThemeColor $notification.themeColor `
                                -Facts $notification.facts
                            
                            if (-not $notificationSent) {
                                Write-NotificationLog -NotificationType "RolloutCompleted" -RolloutState $state
                            }
                        }
                    }
                }
                
                return $status
            }
            
            # Wait before next poll
            Write-DeploymentLog -Level INFO -Message "Waiting ${PollingInterval}s before next poll (iteration $iteration/$MaxIterations)"
            Start-Sleep -Seconds $PollingInterval
        }
        catch {
            Write-DeploymentLog -Level ERROR -Message "Error retrieving rollout status: $_"
            
            # Retry with exponential backoff (integrated with Invoke-WithRetry would be better)
            Write-DeploymentLog -Level WARN -Message "Retrying in ${PollingInterval}s..."
            Start-Sleep -Seconds $PollingInterval
        }
    }
    
    Write-DeploymentLog -Level WARN -Message "Rollout monitoring timeout after $MaxIterations iterations"
    throw "Rollout monitoring timed out. Max iterations ($MaxIterations) exceeded."
}

<#
.SYNOPSIS
    Orchestrate rollout monitoring workflow

.DESCRIPTION
    Main workflow function for User Story 3:
    - Load existing rollout state (or use provided RolloutId)
    - Start monitoring with configured polling interval
    - Update state file with progress

.PARAMETER Config
    Deployment configuration object

.PARAMETER RolloutId
    Optional rollout ID (if not provided, loads from state file)

.OUTPUTS
    [PSCustomObject] Final rollout status

.EXAMPLE
    $finalStatus = Invoke-MonitorRollout -Config $config -RolloutId "test-rollout-12345-abc"
#>
function Invoke-MonitorRollout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Config,
        
        [Parameter(Mandatory = $false)]
        [string]$RolloutId
    )
    
    Write-DeploymentLog -Level INFO -Message "=== Starting Rollout Monitoring Workflow ==="
    
    # Determine rollout ID
    if ([string]::IsNullOrWhiteSpace($RolloutId)) {
        # Load from state file
        $state = Read-RolloutState
        if (-not $state) {
            throw "No existing rollout state found and no RolloutId provided. Run 'trigger' action first."
        }
        $RolloutId = $state.rolloutId
        Write-DeploymentLog -Level INFO -Message "Using rollout ID from state: $RolloutId"
    }
    else {
        Write-DeploymentLog -Level INFO -Message "Using provided rollout ID: $RolloutId"
    }
    
    # Get polling interval from config
    $pollingInterval = if ($Config.pollingInterval) { $Config.pollingInterval } else { $script:DefaultPollingIntervalSeconds }
    
    # Start monitoring
    $finalStatus = Watch-Ev2Rollout -RolloutId $RolloutId -PollingInterval $pollingInterval
    
    # Update state file with final status
    $state = Read-RolloutState
    if ($state -and $state.rolloutId -eq $RolloutId) {
        $state.status = $finalStatus.status
        $state.lastUpdated = (Get-Date).ToString("o")
        Write-RolloutState -State $state
        Write-DeploymentLog -Level INFO -Message "State file updated with final status: $($finalStatus.status)"
    }
    
    Write-DeploymentLog -Level INFO -Message "Rollout monitoring workflow complete"
    return $finalStatus
}

# ============================================================================
# Error Handling - User Story 4
# ============================================================================

<#
.SYNOPSIS
    Extract error details from rollout status

.DESCRIPTION
    Parses rollout status to extract error messages, codes, and affected resources

.PARAMETER RolloutStatus
    Rollout status object from Get-RolloutStatus

.OUTPUTS
    [array] Array of error objects with message, code, resource, timestamp

.EXAMPLE
    $errors = Get-RolloutErrors -RolloutStatus $status
#>
function Get-RolloutErrors {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$RolloutStatus
    )
    
    Write-DeploymentLog -Level INFO -Message "Extracting errors from rollout status"
    
    $errors = @()
    
    # Extract top-level error message
    if ($RolloutStatus.errorMessage) {
        $errors += @{
            message = $RolloutStatus.errorMessage
            code = if ($RolloutStatus.errorCode) { $RolloutStatus.errorCode } else { "UNKNOWN" }
            resource = "Rollout"
            timestamp = if ($RolloutStatus.lastUpdated) { $RolloutStatus.lastUpdated } else { (Get-Date).ToString("o") }
            stage = $RolloutStatus.currentStage
        }
        Write-DeploymentLog -Level ERROR -Message "Rollout error: $($RolloutStatus.errorMessage)"
    }
    
    # Extract stage-level errors
    if ($RolloutStatus.stageDetails -and $RolloutStatus.stageDetails.errors) {
        foreach ($stageError in $RolloutStatus.stageDetails.errors) {
            $errors += @{
                message = $stageError.message
                code = if ($stageError.code) { $stageError.code } else { "STAGE_ERROR" }
                resource = if ($stageError.resourceId) { $stageError.resourceId } else { "Stage: $($RolloutStatus.currentStage)" }
                timestamp = if ($stageError.timestamp) { $stageError.timestamp } else { (Get-Date).ToString("o") }
                stage = $RolloutStatus.currentStage
            }
            Write-DeploymentLog -Level ERROR -Message "Stage error in $($RolloutStatus.currentStage): $($stageError.message)"
        }
    }
    
    # Extract resource-level errors
    if ($RolloutStatus.resourceErrors) {
        foreach ($resourceError in $RolloutStatus.resourceErrors) {
            $errors += @{
                message = $resourceError.message
                code = if ($resourceError.code) { $resourceError.code } else { "RESOURCE_ERROR" }
                resource = if ($resourceError.resourceId) { $resourceError.resourceId } else { "Unknown Resource" }
                timestamp = if ($resourceError.timestamp) { $resourceError.timestamp } else { (Get-Date).ToString("o") }
                stage = $RolloutStatus.currentStage
            }
            Write-DeploymentLog -Level ERROR -Message "Resource error: $($resourceError.resourceId) - $($resourceError.message)"
        }
    }
    
    if ($errors.Count -eq 0) {
        Write-DeploymentLog -Level WARN -Message "No errors found in rollout status (status: $($RolloutStatus.status))"
    }
    else {
        Write-DeploymentLog -Level INFO -Message "Extracted $($errors.Count) error(s) from rollout"
    }
    
    return $errors
}

<#
.SYNOPSIS
    Generate actionable recommendations based on error type

.DESCRIPTION
    Analyzes error codes and messages to provide troubleshooting guidance

.PARAMETER ErrorCode
    Error code from rollout failure

.PARAMETER ErrorMessage
    Error message text

.OUTPUTS
    [string] Recommendation text

.EXAMPLE
    $recommendation = Get-ErrorRecommendation -ErrorCode "QUOTA_EXCEEDED" -ErrorMessage "CPU quota exceeded"
#>
function Get-ErrorRecommendation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ErrorCode,
        
        [Parameter(Mandatory = $false)]
        [string]$ErrorMessage
    )
    
    Write-DeploymentLog -Level INFO -Message "Generating recommendation for error: $ErrorCode"
    
    $recommendation = ""
    
    switch -Regex ($ErrorCode) {
        "QUOTA.*EXCEEDED" {
            $recommendation = @"
QUOTA EXCEEDED ERROR

Recommended Actions:
1. Check subscription quota limits: az vm list-usage --location <region>
2. Request quota increase: Azure Portal > Subscriptions > Usage + quotas
3. Consider using different regions with available capacity
4. Review resource SKU requirements (may need smaller SKUs)
5. Check if resources can be deleted in other environments

Documentation: https://learn.microsoft.com/azure/quotas/
"@
        }
        "TIMEOUT" {
            $recommendation = @"
TIMEOUT ERROR

Recommended Actions:
1. Check Azure service health: https://status.azure.com
2. Retry deployment after transient issue resolves
3. Increase deployment timeout in stage map
4. Check for network connectivity issues
5. Review resource dependencies (may have circular dependencies)

Documentation: https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/
"@
        }
        "AUTHORIZATION.*FAILED|PERMISSION.*DENIED" {
            $recommendation = @"
AUTHORIZATION ERROR

Recommended Actions:
1. Verify service principal has required permissions
2. Check RBAC role assignments: az role assignment list --assignee <principal-id>
3. Ensure managed identity is configured correctly
4. Review subscription/resource group access policies
5. Check for Azure Policy restrictions

Documentation: https://learn.microsoft.com/azure/role-based-access-control/
"@
        }
        "CONFLICT" {
            $recommendation = @"
CONFLICT ERROR

Recommended Actions:
1. Check if resource already exists: az resource show --ids <resource-id>
2. Verify resource names are unique within scope
3. Check for stuck/locked resources: az resource lock list
4. Review deployment mode (Incremental vs Complete)
5. Consider cleaning up failed deployments first

Documentation: https://learn.microsoft.com/azure/azure-resource-manager/templates/common-deployment-errors
"@
        }
        "INVALID.*PARAMETER|BAD.*REQUEST" {
            $recommendation = @"
INVALID PARAMETER ERROR

Recommended Actions:
1. Review artifact parameters in ServiceModel.json
2. Validate parameter types match schema requirements
3. Check for typos in parameter names/values
4. Verify API version compatibility
5. Test parameters locally: az deployment group validate

Error Details: $ErrorMessage
"@
        }
        "RESOURCE.*NOT.*FOUND" {
            $recommendation = @"
RESOURCE NOT FOUND ERROR

Recommended Actions:
1. Verify dependent resources exist before deployment
2. Check resource ID formatting
3. Ensure correct subscription/resource group context
4. Review deployment order (dependencies deployed first?)
5. Check if resource was deleted during rollout

Error Details: $ErrorMessage
"@
        }
        default {
            $recommendation = @"
DEPLOYMENT ERROR: $ErrorCode

Recommended Actions:
1. Review error details: $ErrorMessage
2. Check Azure Activity Log for detailed diagnostics
3. Review EV2 rollout logs: Get-Ev2RolloutDetails -RolloutId <id>
4. Consult Azure resource provider documentation
5. Contact Azure Support if issue persists

Error Code: $ErrorCode
Error Message: $ErrorMessage
"@
        }
    }
    
    Write-DeploymentLog -Level INFO -Message "Generated recommendation for $ErrorCode"
    return $recommendation
}

<#
.SYNOPSIS
    Cancel an active EV2 rollout

.DESCRIPTION
    Calls EV2 MCP Server to cancel rollout and updates state file

.PARAMETER RolloutId
    Rollout ID to cancel

.PARAMETER Reason
    Optional cancellation reason

.OUTPUTS
    [PSCustomObject] Updated rollout status

.EXAMPLE
    $result = Stop-Ev2Rollout -RolloutId "test-rollout-12345-abc" -Reason "Manual intervention required"
#>
function Stop-Ev2Rollout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RolloutId,
        
        [Parameter(Mandatory = $false)]
        [string]$Reason = "Cancelled by deploy-sentinel"
    )
    
    Write-DeploymentLog -Level WARN -Message "Cancelling rollout: $RolloutId (Reason: $Reason)"
    
    $params = @{
        rolloutId = $RolloutId
        reason = $Reason
    }
    
    try {
        $result = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_cancel_rollout" -Parameters $params
        
        Write-DeploymentLog -Level INFO -Message "Rollout cancelled successfully: $RolloutId"
        
        # Update state file
        $state = Read-RolloutState
        if ($state -and $state.rolloutId -eq $RolloutId) {
            $state.status = "Cancelled"
            $state.lastUpdated = (Get-Date).ToString("o")
            Write-RolloutState -State $state
            Write-DeploymentLog -Level INFO -Message "State file updated with cancellation"
            
            # User Story 8 - Send "Rollout Cancelled" notification
            $config = Read-ConfigFile -ConfigPath ".deploy-sentinel-config.json"
            if ($config.teamsWebhookUrl) {
                $notification = New-NotificationMessage -RolloutState $state -NotificationType "RolloutCancelled"
                $notificationSent = Send-TeamsNotification `
                    -WebhookUrl $config.teamsWebhookUrl `
                    -Title $notification.title `
                    -Message $notification.message `
                    -ThemeColor $notification.themeColor `
                    -Facts $notification.facts
                
                if (-not $notificationSent) {
                    Write-NotificationLog -NotificationType "RolloutCancelled" -RolloutState $state
                }
            }
        }
        
        return $result
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to cancel rollout: $_"
        throw
    }
}

# ============================================================================
# Stress Testing - User Story 5
# ============================================================================

<#
.SYNOPSIS
    Execute a single HTTP request with timing measurement

.DESCRIPTION
    Makes an HTTP GET request to the specified endpoint and measures latency.
    Returns timing data, status code, and success flag.

.PARAMETER EndpointUrl
    The URL to send the request to

.PARAMETER TimeoutSeconds
    Maximum time to wait for response (default: 30 seconds)

.OUTPUTS
    [PSCustomObject] with properties: latencyMs, statusCode, success, errorMessage

.EXAMPLE
    $result = Invoke-EndpointRequest -EndpointUrl "https://api.example.com/health"
#>
function Invoke-EndpointRequest {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$EndpointUrl,
        
        [Parameter(Mandatory = $false)]
        [int]$TimeoutSeconds = 30
    )
    
    $result = [PSCustomObject]@{
        latencyMs = 0
        statusCode = 0
        success = $false
        errorMessage = $null
    }
    
    try {
        # Measure request timing
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        
        $response = Invoke-WebRequest -Uri $EndpointUrl -Method Get -TimeoutSec $TimeoutSeconds -UseBasicParsing -ErrorAction Stop
        
        $stopwatch.Stop()
        
        $result.latencyMs = [int]$stopwatch.ElapsedMilliseconds
        $result.statusCode = [int]$response.StatusCode
        $result.success = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
        
        Write-DeploymentLog -Level DEBUG -Message "Request successful: $EndpointUrl (${$result.latencyMs}ms, status ${$result.statusCode})"
    }
    catch {
        $stopwatch.Stop()
        
        $result.latencyMs = [int]$stopwatch.ElapsedMilliseconds
        $result.errorMessage = $_.Exception.Message
        
        # Try to extract status code from exception
        if ($_.Exception.Response) {
            $result.statusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        
        Write-DeploymentLog -Level WARN -Message "Request failed: $EndpointUrl - $($_.Exception.Message)"
    }
    
    return $result
}

<#
.SYNOPSIS
    Execute concurrent HTTP requests using parallel jobs

.DESCRIPTION
    Starts multiple parallel requests to the same endpoint and collects timing data.
    Uses PowerShell background jobs for parallel execution.

.PARAMETER EndpointUrl
    The URL to send requests to

.PARAMETER RequestCount
    Total number of requests to execute

.PARAMETER TimeoutSeconds
    Maximum time to wait for each request (default: 30 seconds)

.OUTPUTS
    [Array] of request result objects

.EXAMPLE
    $results = Start-ConcurrentRequests -EndpointUrl "https://api.example.com/health" -RequestCount 50
#>
function Start-ConcurrentRequests {
    [CmdletBinding()]
    [OutputType([Array])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$EndpointUrl,
        
        [Parameter(Mandatory = $true)]
        [int]$RequestCount,
        
        [Parameter(Mandatory = $false)]
        [int]$TimeoutSeconds = 30
    )
    
    Write-DeploymentLog -Level INFO -Message "Starting $RequestCount concurrent requests to: $EndpointUrl"
    
    $jobs = @()
    $results = @()
    
    # Start all jobs
    for ($i = 1; $i -le $RequestCount; $i++) {
        $job = Start-Job -ScriptBlock {
            param($url, $timeout)
            
            $result = @{
                latencyMs = 0
                statusCode = 0
                success = $false
                errorMessage = $null
            }
            
            try {
                $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
                $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec $timeout -UseBasicParsing -ErrorAction Stop
                $stopwatch.Stop()
                
                $result.latencyMs = [int]$stopwatch.ElapsedMilliseconds
                $result.statusCode = [int]$response.StatusCode
                $result.success = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
            }
            catch {
                $stopwatch.Stop()
                $result.latencyMs = [int]$stopwatch.ElapsedMilliseconds
                $result.errorMessage = $_.Exception.Message
                
                if ($_.Exception.Response) {
                    $result.statusCode = [int]$_.Exception.Response.StatusCode.value__
                }
            }
            
            return $result
        } -ArgumentList $EndpointUrl, $TimeoutSeconds
        
        $jobs += $job
    }
    
    Write-DeploymentLog -Level INFO -Message "Waiting for $($jobs.Count) jobs to complete..."
    
    # Wait for all jobs and collect results
    foreach ($job in $jobs) {
        $jobResult = Wait-Job -Job $job | Receive-Job
        $results += $jobResult
        Remove-Job -Job $job
    }
    
    $successCount = ($results | Where-Object { $_.success -eq $true }).Count
    Write-DeploymentLog -Level INFO -Message "Completed $RequestCount requests: $successCount successful, $($RequestCount - $successCount) failed"
    
    return $results
}

<#
.SYNOPSIS
    Calculate latency percentiles from request results

.DESCRIPTION
    Sorts latency measurements and calculates p50 (median), p95, and p99 percentiles.

.PARAMETER Results
    Array of request result objects containing latencyMs property

.OUTPUTS
    [PSCustomObject] with properties: p50, p95, p99 (all in milliseconds)

.EXAMPLE
    $percentiles = Measure-LatencyPercentiles -Results $requestResults
    Write-Host "p95 latency: $($percentiles.p95)ms"
#>
function Measure-LatencyPercentiles {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [Array]$Results
    )
    
    if ($Results.Count -eq 0) {
        Write-DeploymentLog -Level WARN -Message "No results to calculate percentiles"
        return [PSCustomObject]@{
            p50 = 0
            p95 = 0
            p99 = 0
        }
    }
    
    # Extract and sort latencies
    $latencies = $Results | ForEach-Object { $_.latencyMs } | Sort-Object
    $count = $latencies.Count
    
    # Calculate percentile indices
    $p50Index = [Math]::Floor($count * 0.50)
    $p95Index = [Math]::Floor($count * 0.95)
    $p99Index = [Math]::Floor($count * 0.99)
    
    # Ensure indices are within bounds
    if ($p50Index -ge $count) { $p50Index = $count - 1 }
    if ($p95Index -ge $count) { $p95Index = $count - 1 }
    if ($p99Index -ge $count) { $p99Index = $count - 1 }
    
    $percentiles = [PSCustomObject]@{
        p50 = $latencies[$p50Index]
        p95 = $latencies[$p95Index]
        p99 = $latencies[$p99Index]
    }
    
    Write-DeploymentLog -Level INFO -Message "Latency percentiles - p50: $($percentiles.p50)ms, p95: $($percentiles.p95)ms, p99: $($percentiles.p99)ms"
    
    return $percentiles
}

<#
.SYNOPSIS
    Execute complete stress test against endpoint

.DESCRIPTION
    Orchestrates concurrent requests, calculates percentiles, and creates StressTestResult entity.

.PARAMETER EndpointUrl
    The URL to test

.PARAMETER RequestCount
    Total number of requests to execute

.PARAMETER TimeoutSeconds
    Maximum time to wait for each request

.OUTPUTS
    [PSCustomObject] StressTestResult with detailed metrics

.EXAMPLE
    $result = Invoke-StressTest -EndpointUrl "https://api.example.com/health" -RequestCount 100
#>
function Invoke-StressTest {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$EndpointUrl,
        
        [Parameter(Mandatory = $true)]
        [int]$RequestCount,
        
        [Parameter(Mandatory = $false)]
        [int]$TimeoutSeconds = 30
    )
    
    Write-DeploymentLog -Level INFO -Message "Starting stress test: $EndpointUrl ($RequestCount requests)"
    
    $startTime = Get-Date
    
    # Execute concurrent requests
    $results = Start-ConcurrentRequests -EndpointUrl $EndpointUrl -RequestCount $RequestCount -TimeoutSeconds $TimeoutSeconds
    
    # Calculate metrics
    $successfulRequests = ($results | Where-Object { $_.success -eq $true }).Count
    $failedRequests = $RequestCount - $successfulRequests
    $successRatePercent = [Math]::Round(($successfulRequests / $RequestCount) * 100, 2)
    
    # Calculate latency percentiles
    $percentiles = Measure-LatencyPercentiles -Results $results
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Create StressTestResult entity
    $stressTestResult = [PSCustomObject]@{
        endpointUrl = $EndpointUrl
        totalRequests = $RequestCount
        successfulRequests = $successfulRequests
        failedRequests = $failedRequests
        successRatePercent = $successRatePercent
        p50LatencyMs = $percentiles.p50
        p95LatencyMs = $percentiles.p95
        p99LatencyMs = $percentiles.p99
        startedAt = $startTime.ToString("o")
        completedAt = $endTime.ToString("o")
        durationSeconds = [Math]::Round($duration, 2)
    }
    
    Write-DeploymentLog -Level INFO -Message "Stress test completed: $successRatePercent% success rate, p95: $($percentiles.p95)ms"
    
    return $stressTestResult
}

<#
.SYNOPSIS
    Validate stress test results against thresholds

.DESCRIPTION
    Compares success rate and p95 latency against configured thresholds.

.PARAMETER StressTestResult
    The StressTestResult entity to validate

.PARAMETER MinSuccessRatePercent
    Minimum acceptable success rate (default: 95%)

.PARAMETER MaxP95LatencyMs
    Maximum acceptable p95 latency in milliseconds (default: 500ms)

.OUTPUTS
    [bool] $true if test passed, $false if failed

.EXAMPLE
    $passed = Test-StressTestPassed -StressTestResult $result -MinSuccessRatePercent 98 -MaxP95LatencyMs 300
#>
function Test-StressTestPassed {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$StressTestResult,
        
        [Parameter(Mandatory = $false)]
        [double]$MinSuccessRatePercent = 95.0,
        
        [Parameter(Mandatory = $false)]
        [int]$MaxP95LatencyMs = 500
    )
    
    $passed = $true
    $failureReasons = @()
    
    # Check success rate
    if ($StressTestResult.successRatePercent -lt $MinSuccessRatePercent) {
        $passed = $false
        $failureReasons += "Success rate $($StressTestResult.successRatePercent)% below threshold $MinSuccessRatePercent%"
    }
    
    # Check p95 latency
    if ($StressTestResult.p95LatencyMs -gt $MaxP95LatencyMs) {
        $passed = $false
        $failureReasons += "p95 latency $($StressTestResult.p95LatencyMs)ms exceeds threshold ${MaxP95LatencyMs}ms"
    }
    
    if ($passed) {
        Write-DeploymentLog -Level INFO -Message "Stress test PASSED: $($StressTestResult.endpointUrl)"
    }
    else {
        Write-DeploymentLog -Level ERROR -Message "Stress test FAILED: $($StressTestResult.endpointUrl)"
        foreach ($reason in $failureReasons) {
            Write-DeploymentLog -Level ERROR -Message "  - $reason"
        }
    }
    
    return $passed
}

# ============================================================================
# Pipeline Integration - User Story 6
# ============================================================================

<#
.SYNOPSIS
    List Azure DevOps pipelines in a project

.DESCRIPTION
    Retrieves all pipelines from specified Azure DevOps project.

.PARAMETER Project
    Azure DevOps project name or ID

.OUTPUTS
    [Array] of pipeline objects with id, name, folder, revision

.EXAMPLE
    $pipelines = Get-AdoPipelines -Project "MyProject"
#>
function Get-AdoPipelines {
    [CmdletBinding()]
    [OutputType([Array])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Project
    )
    
    Write-DeploymentLog -Level INFO -Message "Retrieving pipelines for project: $Project"
    
    $params = @{
        project = $Project
    }
    
    try {
        $result = Invoke-McpTool -ToolName "mcp_ado_pipelines_list" -Parameters $params
        
        Write-DeploymentLog -Level INFO -Message "Found $($result.Count) pipelines in project: $Project"
        
        return $result
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to list pipelines: $_"
        throw
    }
}

<#
.SYNOPSIS
    Start an Azure DevOps pipeline run

.DESCRIPTION
    Triggers a pipeline run with optional parameters and variables.

.PARAMETER Project
    Azure DevOps project name or ID

.PARAMETER PipelineId
    Pipeline ID to run

.PARAMETER SourceBranch
    Source branch for the pipeline run (default: refs/heads/main)

.PARAMETER TemplateParameters
    Hashtable of template parameters to pass to the pipeline

.PARAMETER Variables
    Hashtable of variables to pass to the pipeline

.OUTPUTS
    [PSCustomObject] Build object with id, buildNumber, status, queueTime

.EXAMPLE
    $build = Start-AdoPipeline -Project "MyProject" -PipelineId 42 -SourceBranch "refs/heads/feature"
#>
function Start-AdoPipeline {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Project,
        
        [Parameter(Mandatory = $true)]
        [int]$PipelineId,
        
        [Parameter(Mandatory = $false)]
        [string]$SourceBranch = "refs/heads/main",
        
        [Parameter(Mandatory = $false)]
        [hashtable]$TemplateParameters = @{},
        
        [Parameter(Mandatory = $false)]
        [hashtable]$Variables = @{}
    )
    
    Write-DeploymentLog -Level INFO -Message "Starting pipeline: Project=$Project, PipelineId=$PipelineId, Branch=$SourceBranch"
    
    $params = @{
        project = $Project
        pipelineId = $PipelineId
    }
    
    # Add optional parameters
    if ($SourceBranch) {
        $params.resources = @{
            repositories = @{
                self = @{
                    refName = $SourceBranch
                }
            }
        }
    }
    
    if ($TemplateParameters.Count -gt 0) {
        $params.templateParameters = $TemplateParameters
    }
    
    if ($Variables.Count -gt 0) {
        $params.variables = $Variables
    }
    
    try {
        $result = Invoke-McpTool -ToolName "mcp_ado_pipelines_run_pipeline" -Parameters $params
        
        Write-DeploymentLog -Level INFO -Message "Pipeline started: Build ID $($result.id), Build Number $($result.buildNumber)"
        
        return $result
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to start pipeline: $_"
        throw
    }
}

<#
.SYNOPSIS
    Get Azure DevOps build status

.DESCRIPTION
    Retrieves current status of a build/pipeline run.

.PARAMETER Project
    Azure DevOps project name or ID

.PARAMETER BuildId
    Build ID to query

.OUTPUTS
    [PSCustomObject] Build status with id, status, result, startTime, finishTime

.EXAMPLE
    $status = Get-AdoBuildStatus -Project "MyProject" -BuildId 98765
#>
function Get-AdoBuildStatus {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Project,
        
        [Parameter(Mandatory = $true)]
        [int]$BuildId
    )
    
    $params = @{
        project = $Project
        buildId = $BuildId
    }
    
    try {
        $result = Invoke-McpTool -ToolName "mcp_ado_build_get" -Parameters $params
        
        Write-DeploymentLog -Level DEBUG -Message "Build status: ID=$BuildId, Status=$($result.status), Result=$($result.result)"
        
        return $result
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to get build status: $_"
        throw
    }
}

<#
.SYNOPSIS
    Monitor pipeline execution until completion

.DESCRIPTION
    Polls build status at configured interval until build completes.

.PARAMETER Project
    Azure DevOps project name or ID

.PARAMETER BuildId
    Build ID to monitor

.PARAMETER PollingInterval
    Polling interval in seconds (default: 15)

.PARAMETER MaxIterations
    Maximum polling iterations before timeout (default: 240, i.e., 1 hour at 15s interval)

.OUTPUTS
    [PSCustomObject] Final build status

.EXAMPLE
    $finalStatus = Watch-AdoPipeline -Project "MyProject" -BuildId 98765
#>
function Watch-AdoPipeline {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Project,
        
        [Parameter(Mandatory = $true)]
        [int]$BuildId,
        
        [Parameter(Mandatory = $false)]
        [int]$PollingInterval = 15,
        
        [Parameter(Mandatory = $false)]
        [int]$MaxIterations = 240
    )
    
    Write-DeploymentLog -Level INFO -Message "Monitoring pipeline: Build ID $BuildId (interval: ${PollingInterval}s)"
    
    $iteration = 0
    
    while ($iteration -lt $MaxIterations) {
        $iteration++
        
        try {
            $status = Get-AdoBuildStatus -Project $Project -BuildId $BuildId
            
            # Display status
            $statusDisplay = "Build $BuildId | Status: $($status.status)"
            if ($status.result) {
                $statusDisplay += " | Result: $($status.result)"
            }
            Write-Host $statusDisplay -ForegroundColor Cyan
            
            # Check for terminal state
            if ($status.status -eq "completed") {
                Write-DeploymentLog -Level INFO -Message "Pipeline completed: Build ID $BuildId, Result: $($status.result)"
                
                if ($status.result -eq "succeeded") {
                    Write-Host "`n✅ Pipeline SUCCEEDED" -ForegroundColor Green
                }
                elseif ($status.result -eq "failed") {
                    Write-Host "`n❌ Pipeline FAILED" -ForegroundColor Red
                }
                elseif ($status.result -eq "canceled") {
                    Write-Host "`n⚠️ Pipeline CANCELED" -ForegroundColor Yellow
                }
                
                return $status
            }
            
            # Wait before next poll
            Write-DeploymentLog -Level DEBUG -Message "Waiting ${PollingInterval}s before next poll (iteration $iteration/$MaxIterations)"
            Start-Sleep -Seconds $PollingInterval
        }
        catch {
            Write-DeploymentLog -Level ERROR -Message "Error retrieving build status: $_"
            Write-DeploymentLog -Level WARN -Message "Retrying in ${PollingInterval}s..."
            Start-Sleep -Seconds $PollingInterval
        }
    }
    
    Write-DeploymentLog -Level WARN -Message "Pipeline monitoring timeout after $MaxIterations iterations"
    throw "Pipeline monitoring timed out. Max iterations ($MaxIterations) exceeded."
}

<#
.SYNOPSIS
    Retrieve build logs on failure

.DESCRIPTION
    Downloads build logs when a pipeline fails.

.PARAMETER Project
    Azure DevOps project name or ID

.PARAMETER BuildId
    Build ID to retrieve logs for

.OUTPUTS
    [string] Build logs

.EXAMPLE
    $logs = Get-AdoBuildLogs -Project "MyProject" -BuildId 98765
#>
function Get-AdoBuildLogs {
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Project,
        
        [Parameter(Mandatory = $true)]
        [int]$BuildId
    )
    
    Write-DeploymentLog -Level INFO -Message "Retrieving logs for build: $BuildId"
    
    $params = @{
        project = $Project
        buildId = $BuildId
    }
    
    try {
        $result = Invoke-McpTool -ToolName "mcp_ado_build_get_logs" -Parameters $params
        
        Write-DeploymentLog -Level INFO -Message "Retrieved logs for build: $BuildId ($($result.Length) bytes)"
        
        return $result
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to retrieve build logs: $_"
        throw
    }
}

<#
.SYNOPSIS
    Orchestrate pipeline execution in deployment workflow

.DESCRIPTION
    Manages pipeline triggers before/after rollout with proper error handling.

.PARAMETER PipelineConfig
    Pipeline configuration from .deploy-sentinel-config.json

.PARAMETER DeploymentContext
    Hashtable with rolloutId, environment, branchName, serviceId

.PARAMETER TriggerBefore
    If true, trigger pipeline before rollout (default: false)

.PARAMETER TriggerAfter
    If true, trigger pipeline after rollout (default: false)

.OUTPUTS
    [PSCustomObject] Pipeline execution result

.EXAMPLE
    $result = Invoke-DeploymentPipeline -PipelineConfig $config.pipelineConfig -DeploymentContext @{rolloutId="123"} -TriggerBefore
#>
function Invoke-DeploymentPipeline {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$PipelineConfig,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$DeploymentContext,
        
        [Parameter(Mandatory = $false)]
        [switch]$TriggerBefore,
        
        [Parameter(Mandatory = $false)]
        [switch]$TriggerAfter
    )
    
    if (-not $PipelineConfig.enabled) {
        Write-DeploymentLog -Level INFO -Message "Pipeline integration disabled"
        return $null
    }
    
    $timing = if ($TriggerBefore) { "pre-deployment" } else { "post-deployment" }
    Write-DeploymentLog -Level INFO -Message "Triggering $timing pipeline: Project=$($PipelineConfig.project), Pipeline=$($PipelineConfig.pipelineId)"
    
    try {
        # Prepare pipeline variables from deployment context
        $variables = @{
            rolloutId = @{ value = $DeploymentContext.rolloutId }
            environment = @{ value = $DeploymentContext.environment }
            serviceId = @{ value = $DeploymentContext.serviceId }
        }
        
        if ($DeploymentContext.branchName) {
            $variables.branchName = @{ value = $DeploymentContext.branchName }
        }
        
        # Start pipeline
        $build = Start-AdoPipeline `
            -Project $PipelineConfig.project `
            -PipelineId $PipelineConfig.pipelineId `
            -SourceBranch $PipelineConfig.sourceBranch `
            -Variables $variables
        
        Write-Host "`n🔄 Pipeline started: Build #$($build.buildNumber) (ID: $($build.id))" -ForegroundColor Cyan
        
        # Monitor pipeline
        $finalStatus = Watch-AdoPipeline -Project $PipelineConfig.project -BuildId $build.id
        
        # Handle failure
        if ($finalStatus.result -eq "failed") {
            $errorMsg = "Pipeline failed: Build #$($build.buildNumber)"
            
            # Retrieve logs on failure
            try {
                $logs = Get-AdoBuildLogs -Project $PipelineConfig.project -BuildId $build.id
                Write-DeploymentLog -Level ERROR -Message "Pipeline logs:`n$logs"
            }
            catch {
                Write-DeploymentLog -Level WARN -Message "Could not retrieve pipeline logs: $_"
            }
            
            # Pre-deployment failures are critical
            if ($TriggerBefore) {
                throw $errorMsg
            }
            else {
                # Post-deployment failures are warnings
                Write-DeploymentLog -Level WARN -Message $errorMsg
                Write-Host "`n⚠️ Post-deployment pipeline failed (non-critical)" -ForegroundColor Yellow
            }
        }
        
        return $finalStatus
    }
    catch {
        $errorMsg = "Failed to execute $timing pipeline: $_"
        
        if ($TriggerBefore) {
            Write-DeploymentLog -Level ERROR -Message $errorMsg
            throw
        }
        else {
            Write-DeploymentLog -Level WARN -Message $errorMsg
            Write-Host "`n⚠️ Post-deployment pipeline error (continuing): $_" -ForegroundColor Yellow
            return $null
        }
    }
}

# ============================================================================
# Approval Gates - User Story 7
# ============================================================================

<#
.SYNOPSIS
    Extract wait actions from rollout status

.DESCRIPTION
    Parses rollout details to identify wait actions that require human approval.
    Wait actions block rollout progression until manually approved or rejected.

.PARAMETER RolloutStatus
    Rollout status object from Get-RolloutStatus

.OUTPUTS
    [Array] of wait action objects with id, stage, status

.EXAMPLE
    $waitActions = Get-WaitActions -RolloutStatus $status
#>
function Get-WaitActions {
    [CmdletBinding()]
    [OutputType([Array])]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$RolloutStatus
    )
    
    Write-DeploymentLog -Level DEBUG -Message "Extracting wait actions from rollout status"
    
    $waitActions = @()
    
    try {
        # Check if rollout has stages
        if (-not $RolloutStatus.stages) {
            Write-DeploymentLog -Level DEBUG -Message "No stages found in rollout status"
            return $waitActions
        }
        
        # Iterate through stages to find wait actions
        foreach ($stage in $RolloutStatus.stages) {
            if ($stage.actions) {
                foreach ($action in $stage.actions) {
                    # Wait actions typically have type "WaitAction" or status "WaitingForApproval"
                    if ($action.type -eq "WaitAction" -or $action.status -eq "WaitingForApproval") {
                        $waitActions += [PSCustomObject]@{
                            actionId    = $action.id
                            actionName  = $action.name
                            stage       = $stage.name
                            status      = $action.status
                            description = $action.description
                            createdAt   = $action.createdAt
                        }
                        
                        Write-DeploymentLog -Level INFO -Message "Found wait action: $($action.id) in stage $($stage.name)"
                    }
                }
            }
        }
        
        Write-DeploymentLog -Level INFO -Message "Found $($waitActions.Count) wait action(s)"
        return $waitActions
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to extract wait actions: $_"
        throw
    }
}

<#
.SYNOPSIS
    Send approval notification to Teams channel

.DESCRIPTION
    Sends an Adaptive Card notification to Teams webhook requesting approval
    for a wait action. Includes rollout details and CLI command examples.

.PARAMETER WebhookUrl
    Microsoft Teams webhook URL

.PARAMETER RolloutId
    EV2 rollout ID

.PARAMETER ActionId
    Wait action ID requiring approval

.PARAMETER Stage
    Stage name where wait action is pending

.PARAMETER Message
    Approval request message

.OUTPUTS
    [bool] $true if notification sent successfully, $false otherwise

.EXAMPLE
    Send-ApprovalNotification -WebhookUrl $url -RolloutId $id -ActionId $action -Stage $stage -Message $msg
#>
function Send-ApprovalNotification {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$WebhookUrl,
        
        [Parameter(Mandatory = $true)]
        [string]$RolloutId,
        
        [Parameter(Mandatory = $true)]
        [string]$ActionId,
        
        [Parameter(Mandatory = $true)]
        [string]$Stage,
        
        [Parameter(Mandatory = $true)]
        [string]$Message
    )
    
    Write-DeploymentLog -Level INFO -Message "Sending approval notification for wait action: $ActionId"
    
    try {
        # Build Adaptive Card (MessageCard schema v1.0)
        $card = @{
            '@type'      = 'MessageCard'
            '@context'   = 'https://schema.org/extensions'
            summary      = "EV2 Rollout Approval Required: $RolloutId"
            themeColor   = 'FFC107'  # Yellow/warning color
            title        = "`u26a0`ufe0f EV2 Rollout Requires Approval"
            sections     = @(
                @{
                    activityTitle    = 'Manual Approval Required'
                    activitySubtitle = "Rollout: $RolloutId"
                    facts            = @(
                        @{ name = 'Stage'; value = $Stage }
                        @{ name = 'Action ID'; value = $ActionId }
                        @{ name = 'Rollout ID'; value = $RolloutId }
                        @{ name = 'Message'; value = $Message }
                    )
                    text             = @"
**How to approve or reject:**

**Approve:**
``````powershell
.\deploy-sentinel.ps1 -ApproveWaitAction -ActionId "$ActionId" -RolloutId "$RolloutId"
``````

**Reject:**
``````powershell
.\deploy-sentinel.ps1 -RejectWaitAction -ActionId "$ActionId" -RolloutId "$RolloutId"
``````
"@
                }
            )
        }
        
        $body = $card | ConvertTo-Json -Depth 10
        
        Write-DeploymentLog -Level DEBUG -Message "Sending Teams webhook request"
        
        $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType 'application/json' -ErrorAction Stop
        
        if ($response -eq "1") {
            Write-DeploymentLog -Level INFO -Message "Approval notification sent successfully"
            return $true
        }
        else {
            Write-DeploymentLog -Level WARN -Message "Unexpected webhook response: $response"
            return $false
        }
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to send approval notification: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Approve or reject a wait action

.DESCRIPTION
    Calls EV2 MCP Server to approve or reject a wait action, allowing
    the rollout to continue or be cancelled.

.PARAMETER RolloutId
    EV2 rollout ID

.PARAMETER ServiceGroupName
    Service group name

.PARAMETER ServiceResourceGroup
    Service resource group

.PARAMETER ServiceResource
    Service resource name

.PARAMETER ActionId
    Wait action ID to approve/reject

.PARAMETER Approve
    If $true, approves the wait action. If $false, rejects it.

.OUTPUTS
    [PSCustomObject] Result with status, timestamp

.EXAMPLE
    Stop-WaitAction -RolloutId $id -ServiceGroupName $sg -ServiceResourceGroup $srg -ServiceResource $sr -ActionId $action -Approve $true
#>
function Stop-WaitAction {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RolloutId,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceGroupName,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceResourceGroup,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceResource,
        
        [Parameter(Mandatory = $true)]
        [string]$ActionId,
        
        [Parameter(Mandatory = $true)]
        [bool]$Approve
    )
    
    $decision = if ($Approve) { "approve" } else { "reject" }
    Write-DeploymentLog -Level INFO -Message "Processing wait action decision: $decision for action $ActionId"
    
    try {
        $params = @{
            rolloutId            = $RolloutId
            serviceGroupName     = $ServiceGroupName
            serviceResourceGroup = $ServiceResourceGroup
            serviceResource      = $ServiceResource
            action               = $ActionId
        }
        
        Write-DeploymentLog -Level DEBUG -Message "Calling mcp_ev2_mcp_serve_approve_rollout_continuation"
        
        $result = Invoke-McpTool -ToolName "mcp_ev2_mcp_serve_approve_rollout_continuation" -Parameters $params
        
        $status = if ($Approve) { "Approved" } else { "Rejected" }
        Write-DeploymentLog -Level INFO -Message "Wait action $ActionId $status successfully"
        
        return [PSCustomObject]@{
            actionId  = $ActionId
            status    = $status
            timestamp = (Get-Date).ToString("o")
            result    = $result
        }
    }
    catch {
        Write-DeploymentLog -Level ERROR -Message "Failed to process wait action decision: $_"
        throw
    }
}

# ============================================================================
# Teams Notifications - User Story 8
# ============================================================================

<#
.SYNOPSIS
    Create a notification message from rollout state

.DESCRIPTION
    Transforms rollout state into a structured notification entity
    with appropriate theme color and message content based on the
    notification type.

.PARAMETER RolloutState
    Current rollout state object

.PARAMETER NotificationType
    Type of notification to create:
    - RolloutStarted
    - StageCompleted
    - RolloutFailed
    - RolloutCompleted
    - RolloutCancelled
    - StressTestResults
    - ApprovalRequired

.PARAMETER AdditionalData
    Optional hashtable with extra data (e.g., stage name, metrics)

.OUTPUTS
    [PSCustomObject] Notification entity with title, message, themeColor, facts

.EXAMPLE
    New-NotificationMessage -RolloutState $state -NotificationType "RolloutStarted"
#>
function New-NotificationMessage {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$RolloutState,
        
        [Parameter(Mandatory = $true)]
        [ValidateSet("RolloutStarted", "StageCompleted", "RolloutFailed", "RolloutCompleted", "RolloutCancelled", "StressTestResults", "ApprovalRequired")]
        [string]$NotificationType,
        
        [Parameter(Mandatory = $false)]
        [hashtable]$AdditionalData = @{}
    )
    
    # Map notification type to theme color
    $themeColors = @{
        RolloutStarted    = "0078D4"  # Blue
        StageCompleted    = "28A745"  # Green
        RolloutFailed     = "DC3545"  # Red
        RolloutCompleted  = "28A745"  # Green
        RolloutCancelled  = "FFC107"  # Yellow
        StressTestResults = "17A2B8"  # Info blue
        ApprovalRequired  = "FFC107"  # Yellow
    }
    
    $themeColor = $themeColors[$NotificationType]
    
    # Build notification content based on type
    $notification = [PSCustomObject]@{
        title      = ""
        message    = ""
        themeColor = $themeColor
        facts      = @()
    }
    
    switch ($NotificationType) {
        "RolloutStarted" {
            $notification.title = "🚀 Rollout Started"
            $notification.message = "Deployment has been initiated for $($RolloutState.serviceId) in $($RolloutState.environment)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Environment"; value = $RolloutState.environment }
                @{ name = "Started At"; value = $RolloutState.startedAt }
            )
        }
        "StageCompleted" {
            $stageName = if ($AdditionalData.ContainsKey("stageName")) { $AdditionalData.stageName } else { "Unknown" }
            $notification.title = "✅ Stage Completed"
            $notification.message = "Stage '$stageName' completed successfully for $($RolloutState.serviceId)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Stage"; value = $stageName }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Status"; value = $RolloutState.status }
            )
        }
        "RolloutFailed" {
            $notification.title = "❌ Rollout Failed"
            $notification.message = "Deployment failed for $($RolloutState.serviceId) in $($RolloutState.environment)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Environment"; value = $RolloutState.environment }
                @{ name = "Status"; value = $RolloutState.status }
            )
            if ($AdditionalData.ContainsKey("errors") -and $AdditionalData.errors) {
                $errorSummary = $AdditionalData.errors | Select-Object -First 3 | ForEach-Object { $_.message }
                $notification.facts += @{ name = "Errors"; value = ($errorSummary -join "`n") }
            }
        }
        "RolloutCompleted" {
            $notification.title = "🎉 Rollout Completed"
            $notification.message = "Deployment completed successfully for $($RolloutState.serviceId) in $($RolloutState.environment)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Environment"; value = $RolloutState.environment }
                @{ name = "Completed At"; value = (Get-Date).ToString("o") }
            )
        }
        "RolloutCancelled" {
            $notification.title = "⚠️ Rollout Cancelled"
            $notification.message = "Deployment was cancelled for $($RolloutState.serviceId) in $($RolloutState.environment)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Environment"; value = $RolloutState.environment }
                @{ name = "Cancelled At"; value = (Get-Date).ToString("o") }
            )
        }
        "StressTestResults" {
            $notification.title = "📊 Stress Test Results"
            $notification.message = "Stress testing completed for $($RolloutState.serviceId)"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
            )
            if ($AdditionalData.ContainsKey("metrics")) {
                $metrics = $AdditionalData.metrics
                $notification.facts += @{ name = "Success Rate"; value = "$($metrics.successRate)%" }
                $notification.facts += @{ name = "P50 Latency"; value = "$($metrics.p50)ms" }
                $notification.facts += @{ name = "P95 Latency"; value = "$($metrics.p95)ms" }
                $notification.facts += @{ name = "P99 Latency"; value = "$($metrics.p99)ms" }
            }
        }
        "ApprovalRequired" {
            $notification.title = "⏸️ Approval Required"
            $notification.message = "Deployment requires manual approval to continue"
            $notification.facts = @(
                @{ name = "Rollout ID"; value = $RolloutState.rolloutId }
                @{ name = "Service"; value = $RolloutState.serviceId }
                @{ name = "Environment"; value = $RolloutState.environment }
            )
            if ($AdditionalData.ContainsKey("actionId")) {
                $notification.facts += @{ name = "Action ID"; value = $AdditionalData.actionId }
            }
        }
    }
    
    Write-DeploymentLog -Level DEBUG -Message "Created $NotificationType notification for rollout $($RolloutState.rolloutId)"
    return $notification
}

<#
.SYNOPSIS
    Send a notification to Teams webhook

.DESCRIPTION
    Posts a formatted MessageCard to Teams webhook with retry logic.
    Implements exponential backoff for transient failures and handles
    rate limiting (429 status code) with Retry-After header respect.

.PARAMETER WebhookUrl
    Teams webhook URL

.PARAMETER Title
    Notification title

.PARAMETER Message
    Notification message body

.PARAMETER ThemeColor
    Hex color code (without #) for the card theme

.PARAMETER Facts
    Array of hashtables with name/value pairs to display

.PARAMETER MaxRetries
    Maximum number of retry attempts (default: 3)

.OUTPUTS
    [bool] True if notification sent successfully, false otherwise

.EXAMPLE
    Send-TeamsNotification -WebhookUrl $url -Title "Rollout Started" -Message "Deployment initiated" -ThemeColor "0078D4" -Facts @(@{name="ID"; value="123"})
#>
function Send-TeamsNotification {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$WebhookUrl,
        
        [Parameter(Mandatory = $true)]
        [string]$Title,
        
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [Parameter(Mandatory = $true)]
        [string]$ThemeColor,
        
        [Parameter(Mandatory = $false)]
        [array]$Facts = @(),
        
        [Parameter(Mandatory = $false)]
        [int]$MaxRetries = 3
    )
    
    $card = @{
        "@type"      = "MessageCard"
        "@context"   = "https://schema.org/extensions"
        themeColor   = $ThemeColor
        title        = $Title
        text         = $Message
        sections     = @(
            @{
                facts = $Facts
            }
        )
    }
    
    $body = $card | ConvertTo-Json -Depth 10
    $retryCount = 0
    $success = $false
    
    while (-not $success -and $retryCount -le $MaxRetries) {
        try {
            Write-DeploymentLog -Level DEBUG -Message "Sending Teams notification (attempt $($retryCount + 1)/$($MaxRetries + 1))"
            
            $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType 'application/json' -ErrorAction Stop
            
            if ($response -eq "1") {
                Write-DeploymentLog -Level INFO -Message "Teams notification sent: $Title"
                $success = $true
                return $true
            }
            else {
                Write-DeploymentLog -Level WARN -Message "Unexpected webhook response: $response"
                $retryCount++
            }
        }
        catch {
            $statusCode = $null
            $retryAfter = $null
            
            # Extract status code and Retry-After header if available
            if ($_.Exception.Response) {
                $statusCode = [int]$_.Exception.Response.StatusCode
                $retryAfter = $_.Exception.Response.Headers["Retry-After"]
            }
            
            Write-DeploymentLog -Level WARN -Message "Teams notification failed (attempt $($retryCount + 1)): $($_.Exception.Message)"
            
            # Handle rate limiting (429)
            if ($statusCode -eq 429) {
                if ($retryAfter) {
                    $waitSeconds = [int]$retryAfter
                    Write-DeploymentLog -Level WARN -Message "Rate limited (429). Waiting $waitSeconds seconds before retry"
                    Start-Sleep -Seconds $waitSeconds
                }
                else {
                    # Default exponential backoff
                    $waitSeconds = [Math]::Pow(2, $retryCount)
                    Write-DeploymentLog -Level WARN -Message "Rate limited (429). Exponential backoff: waiting $waitSeconds seconds"
                    Start-Sleep -Seconds $waitSeconds
                }
            }
            # Exponential backoff for other failures
            elseif ($retryCount -lt $MaxRetries) {
                $waitSeconds = [Math]::Pow(2, $retryCount)
                Write-DeploymentLog -Level DEBUG -Message "Retrying after $waitSeconds seconds"
                Start-Sleep -Seconds $waitSeconds
            }
            
            $retryCount++
        }
    }
    
    if (-not $success) {
        Write-DeploymentLog -Level ERROR -Message "Failed to send Teams notification after $MaxRetries retries"
        return $false
    }
    
    return $success
}

<#
.SYNOPSIS
    Write notification to deployment log as fallback

.DESCRIPTION
    Logs notification details when Teams webhook fails, ensuring
    important deployment milestones are recorded even if external
    notification systems are unavailable.

.PARAMETER NotificationType
    Type of notification

.PARAMETER RolloutState
    Current rollout state object

.PARAMETER AdditionalData
    Optional hashtable with extra data

.EXAMPLE
    Write-NotificationLog -NotificationType "RolloutFailed" -RolloutState $state
#>
function Write-NotificationLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$NotificationType,
        
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$RolloutState,
        
        [Parameter(Mandatory = $false)]
        [hashtable]$AdditionalData = @{}
    )
    
    $logMessage = "NOTIFICATION FALLBACK - $NotificationType | Rollout: $($RolloutState.rolloutId) | Service: $($RolloutState.serviceId) | Environment: $($RolloutState.environment)"
    
    if ($AdditionalData.Count -gt 0) {
        $additionalInfo = ($AdditionalData.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "
        $logMessage += " | Additional: $additionalInfo"
    }
    
    Write-DeploymentLog -Level WARN -Message $logMessage
}

# ============================================================================
# Git Operations - User Story 2
# ============================================================================

<#
.SYNOPSIS
    Test if git repository is properly configured

.DESCRIPTION
    Validates:
    - Git command is available
    - Current directory is inside a git repository
    - Git remote is configured

.OUTPUTS
    [bool] $true if git repository is valid, $false otherwise

.EXAMPLE
    if (Test-GitRepository) { ... }
#>
function Test-GitRepository {
    [CmdletBinding()]
    param()
    
    # Check if git command exists
    try {
        $gitCommand = Get-Command git -ErrorAction Stop
        Write-DeploymentLog -Level INFO -Message "Git command found: $($gitCommand.Source)"
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "Git command not available"
        return $false
    }
    
    # Check if inside git repository
    try {
        $isInsideWorkTree = git rev-parse --is-inside-work-tree 2>$null
        if ($isInsideWorkTree -ne "true") {
            Write-DeploymentLog -Level WARN -Message "Not inside a git repository"
            return $false
        }
        Write-DeploymentLog -Level INFO -Message "Inside git repository"
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "Git repository check failed: $_"
        return $false
    }
    
    # Check if git remote exists
    try {
        $remotes = git remote -v 2>$null
        if (-not $remotes -or $remotes.Count -eq 0) {
            Write-DeploymentLog -Level WARN -Message "No git remotes configured"
            return $false
        }
        Write-DeploymentLog -Level INFO -Message "Git remotes configured: $($remotes.Count) remote(s)"
    }
    catch {
        Write-DeploymentLog -Level WARN -Message "Git remote check failed: $_"
        return $false
    }
    
    return $true
}

<#
.SYNOPSIS
    Generate deployment branch name

.DESCRIPTION
    Creates branch name with pattern: deploy/{environment}/{serviceId}/{timestamp}
    Timestamp format: YYYYMMDDHHmmss (ISO 8601 compact)

.PARAMETER Environment
    Deployment environment (e.g., Test, Prod)

.PARAMETER ServiceId
    Service identifier

.OUTPUTS
    [string] Generated branch name

.EXAMPLE
    $branchName = New-DeploymentBranchName -Environment "Test" -ServiceId "test-service-001"
    # Returns: deploy/Test/test-service-001/20250115103045
#>
function New-DeploymentBranchName {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Environment,
        
        [Parameter(Mandatory = $true)]
        [string]$ServiceId
    )
    
    $timestamp = (Get-Date).ToString("yyyyMMddHHmmss")
    $branchName = "deploy/$Environment/$ServiceId/$timestamp"
    
    Write-DeploymentLog -Level INFO -Message "Generated branch name: $branchName"
    return $branchName
}

<#
.SYNOPSIS
    Create deployment branch via Azure DevOps MCP Server

.DESCRIPTION
    Creates a new branch in Azure DevOps repository for tracking the deployment.
    Handles branch conflicts gracefully.

.PARAMETER RepositoryId
    Azure DevOps repository ID (GUID)

.PARAMETER BranchName
    Branch name to create

.PARAMETER SourceBranch
    Source branch to create from (default: main)

.OUTPUTS
    [PSCustomObject] Branch creation response or $null if failed

.EXAMPLE
    $branch = New-DeploymentBranch -RepositoryId "repo-12345" -BranchName "deploy/Test/service/timestamp"
#>
function New-DeploymentBranch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryId,
        
        [Parameter(Mandatory = $true)]
        [string]$BranchName,
        
        [Parameter(Mandatory = $false)]
        [string]$SourceBranch = "main"
    )
    
    Write-DeploymentLog -Level INFO -Message "Creating branch: $BranchName in repository: $RepositoryId"
    
    try {
        $params = @{
            repositoryId   = $RepositoryId
            branchName     = $BranchName
            sourceBranch   = $SourceBranch
        }
        
        $result = Invoke-McpTool -ToolName "mcp_ado_repo_create_branch" -Parameters $params
        
        Write-DeploymentLog -Level INFO -Message "Branch created successfully: $BranchName (commit: $($result.commitId))"
        return $result
    }
    catch {
        # Check if error is due to branch already existing
        if ($_.Exception.Message -match "already exists") {
            Write-DeploymentLog -Level WARN -Message "Branch already exists: $BranchName. Continuing without creating new branch."
            return [PSCustomObject]@{
                branchName   = $BranchName
                existed      = $true
                errorMessage = $_.Exception.Message
            }
        }
        
        # Other errors are logged but don't stop workflow (branch creation is optional)
        Write-DeploymentLog -Level WARN -Message "Failed to create branch (non-fatal): $_"
        return $null
    }
}

# ============================================================================
# Workflow Integration - User Story 2
# ============================================================================

<#
.SYNOPSIS
    Orchestrate rollout trigger workflow with branch creation

.DESCRIPTION
    Extended version of Invoke-TriggerRollout that includes branch creation (User Story 2).
    This is the updated workflow that replaces the User Story 1-only version.

.PARAMETER Config
    Deployment configuration object

.OUTPUTS
    [PSCustomObject] RolloutState entity

.EXAMPLE
    $state = Invoke-TriggerRolloutWithBranch -Config $config
#>
function Invoke-TriggerRolloutWithBranch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Config
    )
    
    # Execute User Story 1 workflow
    $state = Invoke-TriggerRollout -Config $Config
    
    # Add environment to state for notifications
    $state | Add-Member -NotePropertyName "environment" -NotePropertyValue $Config.environment -ErrorAction SilentlyContinue
    $state | Add-Member -NotePropertyName "serviceId" -NotePropertyValue $Config.serviceId -ErrorAction SilentlyContinue
    
    # User Story 8: Send "Rollout Started" notification
    if ($Config.PSObject.Properties.Name.Contains("teamsWebhookUrl") -and -not [string]::IsNullOrWhiteSpace($Config.teamsWebhookUrl)) {
        Write-DeploymentLog -Level DEBUG -Message "Sending Rollout Started notification"
        
        $notification = New-NotificationMessage -RolloutState $state -NotificationType "RolloutStarted"
        $notificationSent = Send-TeamsNotification `
            -WebhookUrl $Config.teamsWebhookUrl `
            -Title $notification.title `
            -Message $notification.message `
            -ThemeColor $notification.themeColor `
            -Facts $notification.facts
        
        if (-not $notificationSent) {
            Write-NotificationLog -NotificationType "RolloutStarted" -RolloutState $state
        }
    }
    
    # User Story 2: Create deployment branch
    if (Test-GitRepository) {
        Write-DeploymentLog -Level INFO -Message "Git repository available - creating deployment branch"
        
        $branchName = New-DeploymentBranchName -Environment $Config.environment -ServiceId $Config.serviceId
        
        # Check if repository ID configured in config
        if ($Config.PSObject.Properties.Name.Contains("repositoryId") -and -not [string]::IsNullOrWhiteSpace($Config.repositoryId)) {
            $branch = New-DeploymentBranch -RepositoryId $Config.repositoryId -BranchName $branchName
            
            if ($branch) {
                $state.branchName = $branchName
                Write-DeploymentLog -Level INFO -Message "Branch created and tracked in state: $branchName"
            }
            else {
                Write-DeploymentLog -Level WARN -Message "Branch creation failed - continuing without branch tracking"
            }
        }
        else {
            Write-DeploymentLog -Level WARN -Message "Repository ID not configured - skipping branch creation"
        }
    }
    else {
        Write-DeploymentLog -Level WARN -Message "Git repository not available - skipping branch creation"
    }
    
    return $state
}

# ============================================================================
# Main Entry Point
# ============================================================================

try {
    Write-DeploymentLog -Level INFO -Message "=== EV2 Deployment Sentinel Started ==="
    Write-DeploymentLog -Level INFO -Message "Action: $Action"
    
    # User Story 7 - Handle approval decision parameters
    if ($ApproveWaitAction -or $RejectWaitAction) {
        if (-not $ActionId) {
            throw "ActionId parameter is required when using -ApproveWaitAction or -RejectWaitAction"
        }
        
        if ($ApproveWaitAction -and $RejectWaitAction) {
            throw "Cannot specify both -ApproveWaitAction and -RejectWaitAction"
        }
        
        Write-DeploymentLog -Level INFO -Message "Processing approval decision for action: $ActionId"
        
        # Load configuration
        $config = Load-DeploymentConfig -Path $ConfigPath
        
        # Load rollout state to get rollout ID
        if (-not (Lock-StateFile -Force:$ForceUnlock)) {
            throw "Unable to acquire state file lock. Another instance may be running."
        }
        
        try {
            $state = Read-RolloutState
            if (-not $state) {
                throw "No rollout state found. Cannot process approval decision."
            }
            
            $rolloutIdToUse = if ($RolloutId) { $RolloutId } else { $state.rolloutId }
            
            $approvalResult = Stop-WaitAction `
                -RolloutId $rolloutIdToUse `
                -ServiceGroupName $config.serviceGroupName `
                -ServiceResourceGroup $config.serviceResourceGroup `
                -ServiceResource $config.serviceResource `
                -ActionId $ActionId `
                -Approve $ApproveWaitAction.IsPresent
            
            $decision = if ($ApproveWaitAction) { "APPROVED" } else { "REJECTED" }
            Write-Host "`n✅ Wait action $decision: $ActionId" -ForegroundColor Green
            Write-DeploymentLog -Level INFO -Message "Wait action $decision successfully: $ActionId"
            
            exit 0
        }
        finally {
            Unlock-StateFile
        }
    }
    
    # Load configuration
    $config = Load-DeploymentConfig -Path $ConfigPath
    
    # Acquire state file lock
    if (-not (Lock-StateFile -Force:$ForceUnlock)) {
        throw "Unable to acquire state file lock. Another instance may be running."
    }
    
    try {
        # Load existing state (if any)
        $state = Read-RolloutState
        
        # Execute requested action
        switch ($Action) {
            "trigger" {
                # User Stories 1 & 2: Trigger rollout with branch creation
                Write-DeploymentLog -Level INFO -Message "Executing rollout trigger with branch creation"
                $state = Invoke-TriggerRolloutWithBranch -Config $config
                Write-RolloutState -State $state
                Write-DeploymentLog -Level INFO -Message "Rollout triggered: $($state.rolloutId)"
                if ($state.branchName) {
                    Write-DeploymentLog -Level INFO -Message "Branch created: $($state.branchName)"
                }
            }
            "monitor" {
                # User Story 3: Monitor Rollout Status
                Write-DeploymentLog -Level INFO -Message "Action: monitor"
                
                # Monitor workflow (can provide RolloutId or use state file)
                $finalStatus = Invoke-MonitorRollout -Config $config -RolloutId $RolloutId
                
                # Display final result
                Write-Host "`nFinal Status: $($finalStatus.status)" -ForegroundColor $(
                    if ($finalStatus.status -eq "Completed") { "Green" }
                    elseif ($finalStatus.status -eq "Failed") { "Red" }
                    else { "Yellow" }
                )
                
                # Exit code based on final status
                if ($finalStatus.status -eq "Completed") {
                    exit 0
                }
                elseif ($finalStatus.status -eq "Failed") {
                    Write-DeploymentLog -Level ERROR -Message "Rollout failed: $($finalStatus.errorMessage)"
                    exit 1
                }
                else {
                    # Cancelled or other status
                    exit 2
                }
            }
            "stress-test" {
                Write-DeploymentLog -Level INFO -Message "TODO: Implement stress-test action (Phase 6 - User Story 6)"
            }
            "create-branch" {
                # Standalone branch creation (requires existing rollout state)
                $existingState = Read-RolloutState
                if (-not $existingState) {
                    throw "No existing rollout state found. Run 'trigger' action first."
                }
                
                if (Test-GitRepository) {
                    $branchName = New-DeploymentBranchName -Environment $config.environment -ServiceId $config.serviceId
                    
                    if ($config.repositoryId) {
                        $branch = New-DeploymentBranch -RepositoryId $config.repositoryId -BranchName $branchName
                        if ($branch) {
                            $existingState.branchName = $branchName
                            Write-RolloutState -State $existingState
                            Write-DeploymentLog -Level INFO -Message "Branch created and state updated: $branchName"
                        }
                    }
                    else {
                        throw "Repository ID not configured. Add 'repositoryId' to configuration."
                    }
                }
                else {
                    throw "Git repository not available"
                }
            }
            "full" {
                Write-DeploymentLog -Level INFO -Message "TODO: Implement full workflow (Phases 3-8: trigger + monitor + stress-test + notify + pipeline)"
            }
        }
        
        Write-DeploymentLog -Level INFO -Message "=== EV2 Deployment Sentinel Completed ==="
    }
    finally {
        # Always release lock
        Unlock-StateFile
    }
}
catch {
    Write-DeploymentLog -Level ERROR -Message "Fatal error: $_"
    Write-DeploymentLog -Level ERROR -Message $_.ScriptStackTrace
    exit 1
}
