#!/usr/bin/env bash
# Bicep Deployment Test Helper
# Bash helper script for consistent Azure deployment commands

set -euo pipefail

# Default values
WHAT_IF=false
PARAMETER_FILE=""

# Help text
show_help() {
    cat << EOF
Usage: $(basename "$0") -g RESOURCE_GROUP -f TEMPLATE_FILE [OPTIONS]

Wraps Azure CLI deployment commands with standardized parameters.

OPTIONS:
    -g, --resource-group NAME   Azure resource group name (required)
    -f, --template-file PATH    Path to Bicep template file (required)
    -p, --parameters PATH       Path to parameters file (optional)
    -w, --what-if               Perform dry-run validation only
    -h, --help                  Show this help message

EXAMPLES:
    $(basename "$0") -g rg-test -f ./main.bicep
    $(basename "$0") -g rg-test -f ./main.bicep --what-if
    $(basename "$0") -g rg-test -f ./main.bicep -p ./params.json
EOF
}

# Parse arguments
RESOURCE_GROUP=""
TEMPLATE_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -f|--template-file)
            TEMPLATE_FILE="$2"
            shift 2
            ;;
        -p|--parameters)
            PARAMETER_FILE="$2"
            shift 2
            ;;
        -w|--what-if)
            WHAT_IF=true
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

# Validate required parameters
if [[ -z "$RESOURCE_GROUP" ]]; then
    echo "Error: Resource group name is required" >&2
    show_help
    exit 1
fi

if [[ -z "$TEMPLATE_FILE" ]]; then
    echo "Error: Template file is required" >&2
    show_help
    exit 1
fi

# Validate template file exists
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: Template file not found: $TEMPLATE_FILE" >&2
    exit 1
fi

# Build deployment command
DEPLOYMENT_NAME="deployment-$(date +%s)"
ARGS=(
    "deployment" "group" "create"
    "--resource-group" "$RESOURCE_GROUP"
    "--template-file" "$TEMPLATE_FILE"
    "--mode" "Incremental"
    "--name" "$DEPLOYMENT_NAME"
)

if [[ -n "$PARAMETER_FILE" ]]; then
    if [[ -f "$PARAMETER_FILE" ]]; then
        ARGS+=("--parameters" "$PARAMETER_FILE")
    else
        echo "Warning: Parameter file not found: $PARAMETER_FILE" >&2
    fi
fi

if [[ "$WHAT_IF" == true ]]; then
    ARGS+=("--what-if")
fi

# Execute deployment
OUTPUT=$(az "${ARGS[@]}" 2>&1) || EXIT_CODE=$?

# Parse and structure output
if [[ -z "${EXIT_CODE:-}" ]]; then
    # Success - extract deployment info
    echo "$OUTPUT" | jq '{
        DeploymentId: .name,
        ProvisioningState: .properties.provisioningState,
        Timestamp: .properties.timestamp,
        Duration: .properties.duration,
        Outputs: .properties.outputs,
        ErrorMessage: null
    }'
    exit 0
else
    # Failure - structure error output
    echo "{
        \"DeploymentId\": null,
        \"ProvisioningState\": \"Failed\",
        \"ErrorMessage\": $(echo "$OUTPUT" | jq -Rs .),
        \"ErrorCode\": $EXIT_CODE
    }"
    exit $EXIT_CODE
fi
