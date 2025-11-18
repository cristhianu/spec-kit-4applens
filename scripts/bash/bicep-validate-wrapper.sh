#!/usr/bin/env bash
# Bicep Validate Command Wrapper (Bash)
# Calls specify CLI validate command with proper error handling

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${YELLOW}  Bicep Validate Workflow (Bash Wrapper)${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo ""
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Validates Bicep templates end-to-end with automated deployment and testing.

OPTIONS:
    -p, --project NAME          Project name to validate
    -e, --environment ENV       Target environment (default: test-corp)
    -r, --max-retries NUM       Maximum fix-and-retry attempts (default: 3)
    --skip-cleanup              Skip resource cleanup after validation
    -v, --verbose               Enable verbose output
    --endpoint-filter PATTERN   Regex pattern to filter endpoint paths
    --methods METHODS           Comma-separated HTTP methods (e.g., GET,POST)
    --status-codes CODES        Comma-separated status codes (e.g., 200,201,204)
    --timeout SECONDS           Override request timeout in seconds
    --skip-auth                 Skip endpoints that require authentication
    -h, --help                  Show this help message

EXAMPLES:
    # Basic validation
    $(basename "$0")
    
    # Validate specific project
    $(basename "$0") --project my-api
    
    # Custom environment
    $(basename "$0") --environment production --verbose
    
    # Filter endpoints
    $(basename "$0") --methods GET,POST --endpoint-filter "^/api/"
    
    # Skip authentication
    $(basename "$0") --skip-auth --timeout 60

EOF
}

check_specify_cli() {
    if command -v specify &> /dev/null; then
        local version
        version=$(specify --version 2>&1)
        print_success "Specify CLI found: $version"
        return 0
    else
        print_error "Specify CLI not found in PATH"
        print_info "Install with: pip install -e ."
        return 1
    fi
}

# Parse command line arguments
PROJECT=""
ENVIRONMENT="test-corp"
MAX_RETRIES=3
SKIP_CLEANUP=false
VERBOSE=false
ENDPOINT_FILTER=""
METHODS=""
STATUS_CODES=""
TIMEOUT=""
SKIP_AUTH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--max-retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --endpoint-filter)
            ENDPOINT_FILTER="$2"
            shift 2
            ;;
        --methods)
            METHODS="$2"
            shift 2
            ;;
        --status-codes)
            STATUS_CODES="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --skip-auth)
            SKIP_AUTH=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    # Check prerequisites
    if ! check_specify_cli; then
        exit 1
    fi
    
    echo ""
    
    # Build command
    CMD_ARGS=("validate")
    
    if [[ -n "$PROJECT" ]]; then
        CMD_ARGS+=("--project" "$PROJECT")
    fi
    
    if [[ -n "$ENVIRONMENT" ]]; then
        CMD_ARGS+=("--environment" "$ENVIRONMENT")
    fi
    
    if [[ -n "$MAX_RETRIES" ]]; then
        CMD_ARGS+=("--max-retries" "$MAX_RETRIES")
    fi
    
    if [[ "$SKIP_CLEANUP" == true ]]; then
        CMD_ARGS+=("--skip-cleanup")
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        CMD_ARGS+=("--verbose")
    fi
    
    if [[ -n "$ENDPOINT_FILTER" ]]; then
        CMD_ARGS+=("--endpoint-filter" "$ENDPOINT_FILTER")
    fi
    
    if [[ -n "$METHODS" ]]; then
        CMD_ARGS+=("--methods" "$METHODS")
    fi
    
    if [[ -n "$STATUS_CODES" ]]; then
        CMD_ARGS+=("--status-codes" "$STATUS_CODES")
    fi
    
    if [[ -n "$TIMEOUT" ]]; then
        CMD_ARGS+=("--timeout" "$TIMEOUT")
    fi
    
    if [[ "$SKIP_AUTH" == true ]]; then
        CMD_ARGS+=("--skip-auth")
    fi
    
    # Execute command
    print_info "Starting Bicep validation workflow..."
    print_info "Executing: specify ${CMD_ARGS[*]}"
    echo ""
    
    if specify "${CMD_ARGS[@]}"; then
        echo ""
        print_success "Validation completed successfully"
        exit 0
    else
        EXIT_CODE=$?
        echo ""
        print_error "Validation failed with exit code: $EXIT_CODE"
        exit $EXIT_CODE
    fi
}

# Run main function
main
