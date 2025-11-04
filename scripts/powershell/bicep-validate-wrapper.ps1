# Bicep Validate Command Wrapper (PowerShell)
# Calls specify CLI validate command with proper error handling

[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Project name to validate")]
    [string]$Project,
    
    [Parameter(HelpMessage = "Target environment (default: test-corp)")]
    [string]$Environment = "test-corp",
    
    [Parameter(HelpMessage = "Maximum fix-and-retry attempts (default: 3)")]
    [int]$MaxRetries = 3,
    
    [Parameter(HelpMessage = "Skip resource cleanup after validation")]
    [switch]$SkipCleanup,
    
    [Parameter(HelpMessage = "Enable verbose output")]
    [switch]$Verbose,
    
    [Parameter(HelpMessage = "Regex pattern to filter endpoint paths")]
    [string]$EndpointFilter,
    
    [Parameter(HelpMessage = "Comma-separated HTTP methods (e.g., GET,POST)")]
    [string]$Methods,
    
    [Parameter(HelpMessage = "Comma-separated status codes (e.g., 200,201,204)")]
    [string]$StatusCodes,
    
    [Parameter(HelpMessage = "Override request timeout in seconds")]
    [int]$Timeout,
    
    [Parameter(HelpMessage = "Skip endpoints that require authentication")]
    [switch]$SkipAuth
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Test-SpecifyCLI {
    try {
        $version = specify --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Specify CLI found: $version"
            return $true
        }
    } catch {
        Write-ErrorMessage "Specify CLI not found in PATH"
        Write-Info "Install with: pip install -e ."
        return $false
    }
    return $false
}

function Invoke-ValidateCommand {
    Write-Info "Starting Bicep validation workflow..."
    
    # Build command arguments
    $cmdArgs = @("validate")
    
    if ($Project) {
        $cmdArgs += "--project", $Project
    }
    
    if ($Environment) {
        $cmdArgs += "--environment", $Environment
    }
    
    if ($MaxRetries -ge 0) {
        $cmdArgs += "--max-retries", $MaxRetries
    }
    
    if ($SkipCleanup) {
        $cmdArgs += "--skip-cleanup"
    }
    
    if ($Verbose) {
        $cmdArgs += "--verbose"
    }
    
    if ($EndpointFilter) {
        $cmdArgs += "--endpoint-filter", $EndpointFilter
    }
    
    if ($Methods) {
        $cmdArgs += "--methods", $Methods
    }
    
    if ($StatusCodes) {
        $cmdArgs += "--status-codes", $StatusCodes
    }
    
    if ($Timeout -gt 0) {
        $cmdArgs += "--timeout", $Timeout
    }
    
    if ($SkipAuth) {
        $cmdArgs += "--skip-auth"
    }
    
    # Execute command
    Write-Info "Executing: specify $($cmdArgs -join ' ')"
    Write-Host ""
    
    & specify @cmdArgs
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    
    if ($exitCode -eq 0) {
        Write-Success "Validation completed successfully"
        return $true
    } else {
        Write-ErrorMessage "Validation failed with exit code: $exitCode"
        return $false
    }
}

# Main execution
try {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "  Bicep Validate Workflow (PowerShell Wrapper)" -ForegroundColor Yellow
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check prerequisites
    if (-not (Test-SpecifyCLI)) {
        exit 1
    }
    
    Write-Host ""
    
    # Run validation
    $success = Invoke-ValidateCommand
    
    if ($success) {
        exit 0
    } else {
        exit 1
    }
    
} catch {
    Write-ErrorMessage "Unexpected error: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
