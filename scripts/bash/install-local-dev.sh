#!/usr/bin/env bash
set -euo pipefail

# Get the current project root (where the script is being run from)
PROJECT_ROOT="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✅ $*${NC}"; }
info() { echo -e "${CYAN}ℹ️  $*${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }

# Default values
SPEC_KIT_PATH="${SPEC_KIT_PATH:-$HOME/git/spec-kit-4applens}"
SKIP_PROMPT_FILE=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --spec-kit-path)
            SPEC_KIT_PATH="$2"
            shift 2
            ;;
        --skip-prompt-file)
            SKIP_PROMPT_FILE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            cat <<EOF
Usage: $0 [OPTIONS]

Install Specify CLI locally for development and testing.

This script installs the Specify CLI from the local source code in editable mode,
allowing you to test changes immediately. It also copies the GitHub Copilot prompt
file to the current project so you can test the /speckit.bicep command.

OPTIONS:
    --spec-kit-path PATH    Path to spec-kit-4applens repository
                            (default: \$HOME/git/spec-kit-4applens)
    --skip-prompt-file      Skip copying the GitHub Copilot prompt file
    --force                 Force reinstallation even if already installed
    -h, --help              Show this help message

EXAMPLES:
    $0
    Install from default location

    $0 --spec-kit-path "/opt/repos/spec-kit-4applens"
    Install from custom location

    $0 --skip-prompt-file
    Install CLI only, don't copy prompt file

    $0 --force
    Force reinstallation

EOF
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  Specify CLI - Local Development Installation${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Validate spec-kit path
if [[ ! -d "$SPEC_KIT_PATH" ]]; then
    error "Spec Kit repository not found at: $SPEC_KIT_PATH"
    echo ""
    echo -e "${YELLOW}Please provide the correct path using --spec-kit-path parameter${NC}"
    echo -e "${YELLOW}Example: $0 --spec-kit-path '/home/user/repos/spec-kit-4applens'${NC}"
    exit 1
fi

SPEC_KIT_PATH=$(cd "$SPEC_KIT_PATH" && pwd)  # Get absolute path

info "Spec Kit location: $SPEC_KIT_PATH"
info "Current directory: $PROJECT_ROOT"
echo ""

# Check if pyproject.toml exists
if [[ ! -f "$SPEC_KIT_PATH/pyproject.toml" ]]; then
    error "pyproject.toml not found in $SPEC_KIT_PATH"
    echo ""
    echo -e "${YELLOW}This doesn't appear to be a valid Specify CLI repository.${NC}"
    exit 1
fi

# Check if Python is available
info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    error "Python not found in PATH"
    echo ""
    echo -e "${YELLOW}Please install Python 3.8 or later from https://www.python.org/${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
success "Found: $PYTHON_VERSION"

# Check if pip is available
info "Checking pip installation..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    error "pip not found"
    echo ""
    echo -e "${YELLOW}Please ensure pip is installed and available${NC}"
    exit 1
fi
success "Found pip"

echo ""

# Check if already installed
IS_INSTALLED=false
SKIP_INSTALL=false
if command -v specify &> /dev/null; then
    INSTALLED_VERSION=$(specify --version 2>&1 || echo "unknown")
    IS_INSTALLED=true
    warning "Specify CLI is already installed: $INSTALLED_VERSION"
    
    if [[ "$FORCE" != "true" ]]; then
        echo ""
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Skipping installation. Use --force to reinstall without prompting."
            SKIP_INSTALL=true
        fi
    else
        info "Force flag detected, proceeding with reinstallation..."
    fi
else
    info "Specify CLI not currently installed"
fi

# Install the CLI
if [[ "$SKIP_INSTALL" != "true" ]]; then
    echo ""
    echo -e "${CYAN}Installing Specify CLI in editable mode...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Uninstall first if already installed
    if [[ "$IS_INSTALLED" == "true" ]]; then
        info "Uninstalling previous version..."
        $PYTHON_CMD -m pip uninstall -y specify-cli &> /dev/null || true
        success "Previous version uninstalled"
    fi
    
    # Install with bicep extras
    info "Running: $PYTHON_CMD -m pip install -e \"$SPEC_KIT_PATH[bicep]\""
    if $PYTHON_CMD -m pip install -e "$SPEC_KIT_PATH[bicep]"; then
        echo ""
        success "Specify CLI installed successfully!"
        
        # Verify installation
        info "Verifying installation..."
        if command -v specify &> /dev/null; then
            NEW_VERSION=$(specify --version 2>&1)
            success "Version: $NEW_VERSION"
        else
            warning "specify command not found in PATH. You may need to restart your shell."
        fi
    else
        error "Installation failed"
        exit 1
    fi
fi

# Copy GitHub Copilot prompt files
if [[ "$SKIP_PROMPT_FILE" != "true" ]]; then
    echo ""
    echo -e "${CYAN}Setting up GitHub Copilot integration...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    PROMPT_DEST_DIR="$PROJECT_ROOT/.github/prompts"
    
    # Create directory if it doesn't exist
    if [[ ! -d "$PROMPT_DEST_DIR" ]]; then
        info "Creating directory: $PROMPT_DEST_DIR"
        mkdir -p "$PROMPT_DEST_DIR"
    fi
    
    # Define prompt files to copy
    declare -a PROMPT_FILES=(
        "speckit.bicep.prompt.md:.github/prompts:/speckit.bicep"
        "speckit.validate.prompt.md:templates/commands:/speckit.validate"
    )
    
    COPIED_FILES=0
    FAILED_FILES=0
    
    for prompt_entry in "${PROMPT_FILES[@]}"; do
        IFS=':' read -r file_name source_dir command <<< "$prompt_entry"
        PROMPT_SOURCE_PATH="$SPEC_KIT_PATH/$source_dir/$file_name"
        PROMPT_DEST_PATH="$PROMPT_DEST_DIR/$file_name"
        
        if [[ ! -f "$PROMPT_SOURCE_PATH" ]]; then
            warning "Prompt file not found at: $PROMPT_SOURCE_PATH"
            ((FAILED_FILES++))
            continue
        fi
        
        # Copy the file
        info "Copying $file_name..."
        cp "$PROMPT_SOURCE_PATH" "$PROMPT_DEST_PATH"
        
        # Verify
        if [[ -f "$PROMPT_DEST_PATH" ]]; then
            success "Installed: $file_name"
            ((COPIED_FILES++))
        else
            warning "Failed to copy: $file_name"
            ((FAILED_FILES++))
        fi
    done
    
    # Copy learnings database
    echo ""
    echo -e "${CYAN}Setting up Bicep learnings database...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    LEARNINGS_SOURCE_PATH="$SPEC_KIT_PATH/.specify/learnings/bicep-learnings.md"
    LEARNINGS_DEST_DIR="$PROJECT_ROOT/.specify/learnings"
    LEARNINGS_DEST_PATH="$LEARNINGS_DEST_DIR/bicep-learnings.md"
    
    if [[ ! -f "$LEARNINGS_SOURCE_PATH" ]]; then
        warning "Learnings database not found at: $LEARNINGS_SOURCE_PATH"
        info "Bicep commands may not work optimally without the learnings database"
    else
        # Create directory if it doesn't exist
        if [[ ! -d "$LEARNINGS_DEST_DIR" ]]; then
            info "Creating directory: $LEARNINGS_DEST_DIR"
            mkdir -p "$LEARNINGS_DEST_DIR"
        fi
        
        # Copy the file
        info "Copying bicep-learnings.md..."
        cp "$LEARNINGS_SOURCE_PATH" "$LEARNINGS_DEST_PATH"
        
        # Verify
        if [[ -f "$LEARNINGS_DEST_PATH" ]]; then
            success "Learnings database installed"
            info "Location: $LEARNINGS_DEST_PATH"
            
            # Count entries
            ENTRY_COUNT=$(grep -c '\[.*T.*Z\]' "$LEARNINGS_DEST_PATH" || echo "0")
            info "Database contains $ENTRY_COUNT learning entries"
        else
            warning "Failed to copy learnings database"
        fi
    fi
    
    # Copy validation script
    echo ""
    echo -e "${CYAN}Setting up Bicep validation script...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    SCRIPTS_DEST_DIR="$PROJECT_ROOT/scripts"
    
    # Create directory if it doesn't exist
    if [[ ! -d "$SCRIPTS_DEST_DIR" ]]; then
        info "Creating directory: $SCRIPTS_DEST_DIR"
        mkdir -p "$SCRIPTS_DEST_DIR"
    fi
    
    # Copy validation script
    VALIDATION_SCRIPT_SOURCE="$SPEC_KIT_PATH/scripts/bicep_validate_architecture.py"
    VALIDATION_SCRIPT_DEST="$SCRIPTS_DEST_DIR/bicep_validate_architecture.py"
    
    if [[ ! -f "$VALIDATION_SCRIPT_SOURCE" ]]; then
        warning "Validation script not found at: $VALIDATION_SCRIPT_SOURCE"
    else
        info "Copying bicep_validate_architecture.py..."
        cp "$VALIDATION_SCRIPT_SOURCE" "$VALIDATION_SCRIPT_DEST"
        
        if [[ -f "$VALIDATION_SCRIPT_DEST" ]]; then
            success "Validation script installed"
            info "Location: $VALIDATION_SCRIPT_DEST"
        else
            warning "Failed to copy validation script"
        fi
    fi
    
    # Copy validation script documentation
    VALIDATION_DOC_SOURCE="$SPEC_KIT_PATH/scripts/README-VALIDATION-SCRIPT.md"
    VALIDATION_DOC_DEST="$SCRIPTS_DEST_DIR/README-VALIDATION-SCRIPT.md"
    
    if [[ -f "$VALIDATION_DOC_SOURCE" ]]; then
        info "Copying README-VALIDATION-SCRIPT.md..."
        cp "$VALIDATION_DOC_SOURCE" "$VALIDATION_DOC_DEST"
        
        if [[ -f "$VALIDATION_DOC_DEST" ]]; then
            success "Validation documentation installed"
        fi
    fi
    
    # Copy wrapper scripts
    echo ""
    echo -e "${CYAN}Setting up wrapper scripts...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Define wrapper scripts to copy
    declare -a WRAPPER_SCRIPTS=(
        "bicep-validate-wrapper.ps1:scripts/powershell:$SCRIPTS_DEST_DIR/powershell"
        "bicep-validate.ps1:scripts/powershell:$SCRIPTS_DEST_DIR/powershell"
        "bicep-validate-wrapper.sh:scripts/bash:$SCRIPTS_DEST_DIR/bash"
        "bicep-validate.sh:scripts/bash:$SCRIPTS_DEST_DIR/bash"
    )
    
    COPIED_WRAPPERS=0
    FAILED_WRAPPERS=0
    
    for wrapper_entry in "${WRAPPER_SCRIPTS[@]}"; do
        IFS=':' read -r file_name source_dir dest_dir <<< "$wrapper_entry"
        WRAPPER_SOURCE_PATH="$SPEC_KIT_PATH/$source_dir/$file_name"
        WRAPPER_DEST_PATH="$dest_dir/$file_name"
        
        if [[ ! -f "$WRAPPER_SOURCE_PATH" ]]; then
            warning "Wrapper script not found at: $WRAPPER_SOURCE_PATH"
            ((FAILED_WRAPPERS++))
            continue
        fi
        
        # Create directory if it doesn't exist
        if [[ ! -d "$dest_dir" ]]; then
            mkdir -p "$dest_dir"
        fi
        
        # Copy the file
        info "Copying $file_name..."
        cp "$WRAPPER_SOURCE_PATH" "$WRAPPER_DEST_PATH"
        
        # Make shell scripts executable
        if [[ "$file_name" == *.sh ]]; then
            chmod +x "$WRAPPER_DEST_PATH"
        fi
        
        # Verify
        if [[ -f "$WRAPPER_DEST_PATH" ]]; then
            success "Installed: $file_name"
            ((COPIED_WRAPPERS++))
        else
            warning "Failed to copy: $file_name"
            ((FAILED_WRAPPERS++))
        fi
    done
    
    # Summary
    echo ""
    if [[ $COPIED_FILES -gt 0 ]]; then
        success "GitHub Copilot prompt files installed ($COPIED_FILES/${#PROMPT_FILES[@]})"
        info "Location: $PROMPT_DEST_DIR"
        echo ""
        echo -e "${CYAN}Available commands in GitHub Copilot Chat:${NC}"
        for prompt_entry in "${PROMPT_FILES[@]}"; do
            IFS=':' read -r file_name source_dir command <<< "$prompt_entry"
            PROMPT_DEST_PATH="$PROMPT_DEST_DIR/$file_name"
            if [[ -f "$PROMPT_DEST_PATH" ]]; then
                echo -e "  • ${GREEN}$command${NC}"
            fi
        done
    fi
    
    if [[ $COPIED_WRAPPERS -gt 0 ]]; then
        echo ""
        success "Wrapper scripts installed ($COPIED_WRAPPERS/${#WRAPPER_SCRIPTS[@]})"
        info "Location: $SCRIPTS_DEST_DIR"
    fi
    
    if [[ $FAILED_FILES -gt 0 ]] || [[ $FAILED_WRAPPERS -gt 0 ]]; then
        warning "Some files could not be installed"
    fi
else
    info "Skipping GitHub Copilot prompt files (--skip-prompt-file flag)"
fi

# Display next steps
echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo ""
echo -e "  ${NC}1. Test the CLI commands:${NC}"
echo -e "     ${YELLOW}specify bicep --analyze-only${NC}"
echo -e "     ${YELLOW}specify bicep validate${NC}"
echo ""
echo -e "  ${NC}2. Use in GitHub Copilot Chat:${NC}"
echo -e "     ${YELLOW}/speckit.bicep${NC}"
echo -e "     ${YELLOW}/speckit.validate${NC}"
echo ""
echo -e "  ${NC}3. Validate architecture compliance:${NC}"
echo -e "     ${YELLOW}python3 scripts/bicep_validate_architecture.py main.bicep${NC}"
echo ""
echo -e "  ${NC}4. Make changes to the source code:${NC}"
echo -e "     ${YELLOW}Changes in $SPEC_KIT_PATH${NC}"
echo -e "     ${YELLOW}will be immediately reflected (no reinstall needed)${NC}"
echo ""

# Show project info
echo -e "${CYAN}Project Information:${NC}"
echo -e "  ${GRAY}Source: $SPEC_KIT_PATH${NC}"
echo -e "  ${GRAY}Target: $PROJECT_ROOT${NC}"
echo ""

# Check for requirements.txt or package.json
HAS_REQUIREMENTS=false
HAS_PACKAGE_JSON=false
[[ -f "$PROJECT_ROOT/requirements.txt" ]] && HAS_REQUIREMENTS=true
[[ -f "$PROJECT_ROOT/package.json" ]] && HAS_PACKAGE_JSON=true

if [[ "$HAS_REQUIREMENTS" == "true" ]] || [[ "$HAS_PACKAGE_JSON" == "true" ]]; then
    echo -e "${CYAN}Detected project files:${NC}"
    [[ "$HAS_REQUIREMENTS" == "true" ]] && echo -e "  ${GREEN}✓ requirements.txt${NC}"
    [[ "$HAS_PACKAGE_JSON" == "true" ]] && echo -e "  ${GREEN}✓ package.json${NC}"
    echo ""
    echo -e "Run ${YELLOW}specify bicep --analyze-only${NC} to analyze your project!"
fi

echo ""
echo -e "${MAGENTA}Happy coding! 🚀${NC}"
echo ""
