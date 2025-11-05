#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install Specify CLI locally for development and testing.

.DESCRIPTION
    This script installs the Specify CLI from the local source code in editable mode,
    allowing you to test changes immediately. It also copies the GitHub Copilot prompt
    file to the current project so you can test the /speckit.bicep command.

.PARAMETER SpecKitPath
    Path to the spec-kit-4applens repository. Defaults to C:\git\spec-kit-4applens

.PARAMETER SkipPromptFile
    Skip copying the GitHub Copilot prompt file to .github/prompts/

.PARAMETER Force
    Force reinstallation even if already installed

.EXAMPLE
    .\install-local-dev.ps1
    Install from default location (C:\git\spec-kit-4applens)

.EXAMPLE
    .\install-local-dev.ps1 -SpecKitPath "D:\repos\spec-kit-4applens"
    Install from custom location

.EXAMPLE
    .\install-local-dev.ps1 -SkipPromptFile
    Install CLI only, don't copy prompt file

.EXAMPLE
    .\install-local-dev.ps1 -Force
    Force reinstallation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$SpecKitPath = "C:\git\spec-kit-4applens",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipPromptFile,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Get the current project root (where the script is being run from)
$projectRoot = Get-Location

# Colors for output
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Specify CLI - Local Development Installation" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Validate spec-kit path
$specKitPath = Resolve-Path $SpecKitPath -ErrorAction SilentlyContinue
if (-not $specKitPath) {
    Write-Error "Spec Kit repository not found at: $SpecKitPath"
    Write-Host ""
    Write-Host "Please provide the correct path using -SpecKitPath parameter" -ForegroundColor Yellow
    Write-Host "Example: .\install-local-dev.ps1 -SpecKitPath 'D:\repos\spec-kit-4applens'" -ForegroundColor Yellow
    exit 1
}

info "Spec Kit location: $specKitPath"
Write-Info "Current directory: $projectRoot"
Write-Host ""

# Check if pyproject.toml exists
$pyprojectPath = Join-Path $specKitPath "pyproject.toml"
if (-not (Test-Path $pyprojectPath)) {
    Write-Error "pyproject.toml not found in $specKitPath"
    Write-Host ""
    Write-Host "This doesn't appear to be a valid Specify CLI repository." -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
Write-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Found: $pythonVersion"
} catch {
    Write-Error "Python not found in PATH"
    Write-Host ""
    Write-Host "Please install Python 3.8 or later from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check if pip is available
Write-Info "Checking pip installation..."
try {
    $pipVersion = pip --version 2>&1
    Write-Success "Found pip"
} catch {
    Write-Error "pip not found"
    Write-Host ""
    Write-Host "Please ensure pip is installed and available in PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if already installed
$isInstalled = $false
try {
    $installedVersion = specify --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $isInstalled = $true
        Write-Warning "Specify CLI is already installed: $installedVersion"
        
        if (-not $Force) {
            Write-Host ""
            $response = Read-Host "Do you want to reinstall? (y/N)"
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Info "Skipping installation. Use -Force to reinstall without prompting."
                $skipInstall = $true
            }
        } else {
            Write-Info "Force flag detected, proceeding with reinstallation..."
        }
    }
} catch {
    Write-Info "Specify CLI not currently installed"
}

# Install the CLI
if (-not $skipInstall) {
    Write-Host ""
    Write-Host "Installing Specify CLI in editable mode..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        # Uninstall first if already installed
        if ($isInstalled) {
            Write-Info "Uninstalling previous version..."
            pip uninstall -y specify-cli 2>&1 | Out-Null
            Write-Success "Previous version uninstalled"
        }
        
        # Install with bicep extras
        Write-Info "Running: pip install -e `"$specKitPath[bicep]`""
        $installOutput = pip install -e "$specKitPath[bicep]" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Success "Specify CLI installed successfully!"
            
            # Verify installation
            Write-Info "Verifying installation..."
            $newVersion = specify --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Version: $newVersion"
            }
        } else {
            Write-Error "Installation failed"
            Write-Host ""
            Write-Host $installOutput -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Error "Installation failed: $_"
        exit 1
    }
}

# Copy GitHub Copilot prompt files
if (-not $SkipPromptFile) {
    Write-Host ""
    Write-Host "Setting up GitHub Copilot integration..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $promptDestDir = Join-Path $projectRoot ".github\prompts"
    
    # Create directory if it doesn't exist
    if (-not (Test-Path $promptDestDir)) {
        Write-Info "Creating directory: $promptDestDir"
        New-Item -ItemType Directory -Force -Path $promptDestDir | Out-Null
    }
    
    # Define prompt files to copy
    $promptFiles = @(
        @{
            Name = "speckit.bicep.prompt.md"
            Source = ".github\prompts"
            Command = "/speckit.bicep"
        },
        @{
            Name = "speckit.validate.prompt.md"
            Source = "templates\commands"
            Command = "/speckit.validate"
        }
    )
    
    $copiedFiles = 0
    $failedFiles = 0
    
    foreach ($promptFile in $promptFiles) {
        $promptSourcePath = Join-Path $specKitPath $promptFile.Source $promptFile.Name
        $promptDestPath = Join-Path $promptDestDir $promptFile.Name
        
        if (-not (Test-Path $promptSourcePath)) {
            Write-Warning "Prompt file not found at: $promptSourcePath"
            $failedFiles++
            continue
        }
        
        # Copy the file
        Write-Info "Copying $($promptFile.Name)..."
        Copy-Item $promptSourcePath -Destination $promptDestPath -Force
        
        # Verify
        if (Test-Path $promptDestPath) {
            Write-Success "Installed: $($promptFile.Name)"
            $copiedFiles++
        } else {
            Write-Warning "Failed to copy: $($promptFile.Name)"
            $failedFiles++
        }
    }
    
    # Copy learnings database
    Write-Host ""
    Write-Host "Setting up Bicep learnings database..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $learningsSourcePath = Join-Path $specKitPath ".specify\learnings\bicep-learnings.md"
    $learningsDestDir = Join-Path $projectRoot ".specify\learnings"
    $learningsDestPath = Join-Path $learningsDestDir "bicep-learnings.md"
    
    if (-not (Test-Path $learningsSourcePath)) {
        Write-Warning "Learnings database not found at: $learningsSourcePath"
        Write-Info "Bicep commands may not work optimally without the learnings database"
    } else {
        # Create directory if it doesn't exist
        if (-not (Test-Path $learningsDestDir)) {
            Write-Info "Creating directory: $learningsDestDir"
            New-Item -ItemType Directory -Force -Path $learningsDestDir | Out-Null
        }
        
        # Copy the file
        Write-Info "Copying bicep-learnings.md..."
        Copy-Item $learningsSourcePath -Destination $learningsDestPath -Force
        
        # Verify
        if (Test-Path $learningsDestPath) {
            Write-Success "Learnings database installed"
            Write-Info "Location: $learningsDestPath"
            
            # Count entries
            $content = Get-Content $learningsDestPath -Raw
            $entryCount = ([regex]::Matches($content, '\[[\d-]+T[\d:]+Z\]')).Count
            Write-Info "Database contains $entryCount learning entries"
        } else {
            Write-Warning "Failed to copy learnings database"
        }
    }
    
    # Copy validation script
    Write-Host ""
    Write-Host "Setting up Bicep validation script..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $scriptsDestDir = Join-Path $projectRoot "scripts"
    
    # Create directory if it doesn't exist
    if (-not (Test-Path $scriptsDestDir)) {
        Write-Info "Creating directory: $scriptsDestDir"
        New-Item -ItemType Directory -Force -Path $scriptsDestDir | Out-Null
    }
    
    # Copy validation script
    $validationScriptSource = Join-Path $specKitPath "scripts\bicep_validate_architecture.py"
    $validationScriptDest = Join-Path $scriptsDestDir "bicep_validate_architecture.py"
    
    if (-not (Test-Path $validationScriptSource)) {
        Write-Warning "Validation script not found at: $validationScriptSource"
    } else {
        Write-Info "Copying bicep_validate_architecture.py..."
        Copy-Item $validationScriptSource -Destination $validationScriptDest -Force
        
        if (Test-Path $validationScriptDest) {
            Write-Success "Validation script installed"
            Write-Info "Location: $validationScriptDest"
        } else {
            Write-Warning "Failed to copy validation script"
        }
    }
    
    # Copy validation script documentation
    $validationDocSource = Join-Path $specKitPath "scripts\README-VALIDATION-SCRIPT.md"
    $validationDocDest = Join-Path $scriptsDestDir "README-VALIDATION-SCRIPT.md"
    
    if (Test-Path $validationDocSource) {
        Write-Info "Copying README-VALIDATION-SCRIPT.md..."
        Copy-Item $validationDocSource -Destination $validationDocDest -Force
        
        if (Test-Path $validationDocDest) {
            Write-Success "Validation documentation installed"
        }
    }
    
    # Copy wrapper scripts
    Write-Host ""
    Write-Host "Setting up wrapper scripts..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    # Define wrapper scripts to copy
    $wrapperScripts = @(
        @{
            Name = "bicep-validate-wrapper.ps1"
            SourceDir = "scripts\powershell"
            DestDir = Join-Path $scriptsDestDir "powershell"
        },
        @{
            Name = "bicep-validate.ps1"
            SourceDir = "scripts\powershell"
            DestDir = Join-Path $scriptsDestDir "powershell"
        },
        @{
            Name = "bicep-validate-wrapper.sh"
            SourceDir = "scripts\bash"
            DestDir = Join-Path $scriptsDestDir "bash"
        },
        @{
            Name = "bicep-validate.sh"
            SourceDir = "scripts\bash"
            DestDir = Join-Path $scriptsDestDir "bash"
        }
    )
    
    $copiedWrappers = 0
    $failedWrappers = 0
    
    foreach ($wrapper in $wrapperScripts) {
        $wrapperSourcePath = Join-Path $specKitPath $wrapper.SourceDir $wrapper.Name
        $wrapperDestPath = Join-Path $wrapper.DestDir $wrapper.Name
        
        if (-not (Test-Path $wrapperSourcePath)) {
            Write-Warning "Wrapper script not found at: $wrapperSourcePath"
            $failedWrappers++
            continue
        }
        
        # Create directory if it doesn't exist
        if (-not (Test-Path $wrapper.DestDir)) {
            New-Item -ItemType Directory -Force -Path $wrapper.DestDir | Out-Null
        }
        
        # Copy the file
        Write-Info "Copying $($wrapper.Name)..."
        Copy-Item $wrapperSourcePath -Destination $wrapperDestPath -Force
        
        # Verify
        if (Test-Path $wrapperDestPath) {
            Write-Success "Installed: $($wrapper.Name)"
            $copiedWrappers++
        } else {
            Write-Warning "Failed to copy: $($wrapper.Name)"
            $failedWrappers++
        }
    }
    
    # Summary
    Write-Host ""
    if ($copiedFiles -gt 0) {
        Write-Success "GitHub Copilot prompt files installed ($copiedFiles/$($promptFiles.Count))"
        Write-Info "Location: $promptDestDir"
        Write-Host ""
        Write-Host "Available commands in GitHub Copilot Chat:" -ForegroundColor Cyan
        foreach ($promptFile in $promptFiles) {
            $destPath = Join-Path $promptDestDir $promptFile.Name
            if (Test-Path $destPath) {
                Write-Host "  • " -NoNewline
                Write-Host $promptFile.Command -ForegroundColor Green
            }
        }
    }
    
    if ($copiedWrappers -gt 0) {
        Write-Host ""
        Write-Success "Wrapper scripts installed ($copiedWrappers/$($wrapperScripts.Count))"
        Write-Info "Location: $scriptsDestDir"
    }
    
    if ($failedFiles -gt 0 -or $failedWrappers -gt 0) {
        Write-Warning "Some files could not be installed"
    }
} else {
    Write-Info "Skipping GitHub Copilot prompt files (--SkipPromptFile flag)"
}

# Display next steps
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Test the CLI commands:" -ForegroundColor White
Write-Host "     specify bicep --analyze-only" -ForegroundColor Yellow
Write-Host "     specify bicep validate" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Use in GitHub Copilot Chat:" -ForegroundColor White
Write-Host "     /speckit.bicep" -ForegroundColor Yellow
Write-Host "     /speckit.validate" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Validate architecture compliance:" -ForegroundColor White
Write-Host "     python scripts/bicep_validate_architecture.py main.bicep" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Make changes to the source code:" -ForegroundColor White
Write-Host "     Changes in $specKitPath" -ForegroundColor Yellow
Write-Host "     will be immediately reflected (no reinstall needed)" -ForegroundColor Yellow
Write-Host ""

# Show project info
Write-Host "Project Information:" -ForegroundColor Cyan
Write-Host "  Source: $specKitPath" -ForegroundColor DarkGray
Write-Host "  Target: $projectRoot" -ForegroundColor DarkGray
Write-Host ""

# Check for requirements.txt or package.json
$hasRequirements = Test-Path (Join-Path $projectRoot "requirements.txt")
$hasPackageJson = Test-Path (Join-Path $projectRoot "package.json")

if ($hasRequirements -or $hasPackageJson) {
    Write-Host "Detected project files:" -ForegroundColor Cyan
    if ($hasRequirements) { Write-Host "  ✓ requirements.txt" -ForegroundColor Green }
    if ($hasPackageJson) { Write-Host "  ✓ package.json" -ForegroundColor Green }
    Write-Host ""
    Write-Host "Run " -NoNewline
    Write-Host "specify bicep --analyze-only" -ForegroundColor Yellow -NoNewline
    Write-Host " to analyze your project!"
}

Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Magenta
Write-Host ""
