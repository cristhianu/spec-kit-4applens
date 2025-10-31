#!/usr/bin/env bash
# Bicep Validate Command
# Bash entry point for Bicep template validation

set -euo pipefail

# Default values
PROJECT_NAME=""
ENVIRONMENT="test-corp"
MAX_RETRIES=3
SKIP_CLEANUP=false
VERBOSE=false

# Help text
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Validates Bicep templates by discovering projects, deploying resources, and testing endpoints.

OPTIONS:
    -p, --project NAME      Specific project name to validate (skips selection prompt)
    -e, --environment ENV   Target environment (default: test-corp)
    -r, --max-retries NUM   Maximum fix-and-retry attempts (default: 3)
    -s, --skip-cleanup      Skip resource cleanup after validation
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $(basename "$0")
        # Interactive: prompts for project selection

    $(basename "$0") --project my-api-project
        # Direct: validates specific project

    $(basename "$0") --project my-api --environment test --max-retries 5 --verbose
        # Custom: with environment and retry settings
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_NAME="$2"
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
        -s|--skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# Build command arguments
ARGS=("bicep" "validate")

if [[ -n "$PROJECT_NAME" ]]; then
    ARGS+=("--project" "$PROJECT_NAME")
fi

if [[ "$ENVIRONMENT" != "test-corp" ]]; then
    ARGS+=("--environment" "$ENVIRONMENT")
fi

if [[ "$MAX_RETRIES" -ne 3 ]]; then
    ARGS+=("--max-retries" "$MAX_RETRIES")
fi

if [[ "$SKIP_CLEANUP" == true ]]; then
    ARGS+=("--skip-cleanup")
fi

if [[ "$VERBOSE" == true ]]; then
    ARGS+=("--verbose")
fi

# Execute validation command
echo "🔍 Starting Bicep template validation..."

if specify "${ARGS[@]}"; then
    echo "✅ Validation completed successfully"
    exit 0
else
    EXIT_CODE=$?
    echo "❌ Validation failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
