---
description: "Generate Bicep templates for Azure resource deployment based on project analysis"
---

# Generate Bicep Templates for Azure Resources

You are an expert Azure infrastructure developer specializing in Bicep template generation and deployment strategies.

## Task
Analyze the current project and generate appropriate Bicep templates for deploying the application to Azure. This includes:

1. **Project Analysis**: Scan the project to identify Azure service requirements
2. **Template Generation**: Create Bicep templates for the identified services  
3. **Deployment Strategy**: Provide deployment guidance and best practices

## Project Context
- **Project Path**: {SCRIPT}
- **User Arguments**: $ARGUMENTS

## Analysis Steps

### Step 1: Project Analysis
```powershell
# Run project analysis
$analysisResult = & "{SCRIPT}" analyze --project-path "." --output-format "json"
Write-Output "Project Analysis Results:"
$analysisResult | ConvertFrom-Json | Format-Table -AutoSize
```

### Step 2: Generate Bicep Templates
```powershell
# Generate Bicep templates based on analysis
& "{SCRIPT}" generate --project-path "." --environment "dev" --region "eastus" $ARGUMENTS
```

### Step 3: Validate Templates
```powershell
# Validate generated templates
Get-ChildItem -Path "bicep" -Filter "*.bicep" | ForEach-Object {
    Write-Output "Validating: $($_.Name)"
    & "{SCRIPT}" validate --template-path $_.FullName
}
```

## Expected Outputs

### Bicep Templates
The command will generate the following Bicep templates in the `bicep/` directory:
- **main.bicep**: Main deployment template
- **parameters/**: Parameter files for different environments
- **modules/**: Reusable module templates for each service

### Resource Analysis Report
- Detected Azure services and their confidence scores
- Recommended deployment strategy (simple/moderate/complex)
- Estimated monthly costs for basic tiers
- Resource dependencies and deployment order

### Deployment Instructions
- Step-by-step deployment commands
- Environment-specific configuration guidance
- Post-deployment verification steps

## Configuration Options

Use these arguments to customize the generation:

### Required Arguments
- `--project-path <path>`: Path to the project root directory
- `--environment <env>`: Target environment (dev/staging/prod) 
- `--region <region>`: Azure region for deployment

### Optional Arguments  
- `--output-dir <path>`: Custom output directory (default: ./bicep)
- `--subscription <id>`: Azure subscription ID for validation
- `--resource-group <name>`: Target resource group name
- `--prefix <prefix>`: Resource name prefix
- `--tags <json>`: Additional tags as JSON object
- `--force`: Overwrite existing templates
- `--validate-deployment`: Perform deployment validation
- `--interactive`: Enable interactive mode for customization

### Example Usage
```powershell
# Basic generation for development environment
bicep-generate --project-path "." --environment "dev" --region "eastus"

# Production deployment with custom settings
bicep-generate --project-path "." --environment "prod" --region "westus2" --subscription "12345678-1234-1234-1234-123456789012" --resource-group "rg-myapp-prod" --prefix "mycompany" --validate-deployment

# Interactive mode for custom configuration
bicep-generate --project-path "." --environment "staging" --region "centralus" --interactive
```

## Best Practices Applied

### Template Organization
- **Modular design**: Each Azure service gets its own module
- **Parameter files**: Separate parameters for each environment
- **Dependency management**: Automatic resource dependency resolution
- **Naming conventions**: Consistent Azure naming patterns
- **Self-Improving Generation**: Applies learnings from `.specify/learnings/bicep-learnings.md` database

### Security & Compliance  
- **Key Vault integration**: Secrets stored in Azure Key Vault
- **RBAC configuration**: Role-based access control setup
- **Network security**: Secure network configurations by default
- **Monitoring**: Application Insights integration
- **SFI Compliance**: Follows Secure Future Initiative patterns (VNet isolation, Private Endpoints, Managed Identity)

### Cost Optimization
- **Resource sizing**: Appropriate tiers for each environment
- **Auto-scaling**: Configured where applicable
- **Cost estimation**: Monthly cost estimates provided
- **Resource tagging**: Proper tagging for cost management

## 🧠 Learnings Database Integration

The Bicep generator now applies organizational learnings from `.specify/learnings/bicep-learnings.md`:

### How It Works
1. **Automatic Loading**: Learnings database loaded before template generation
2. **Categorized Guidance**: Learnings organized by category (Security, Networking, Configuration, etc.)
3. **Context-Aware**: Applies relevant learnings to each resource type
4. **SFI Patterns**: Enforces Secure Future Initiative best practices from `specs/004-bicep-learnings-database/contracts/sfi-patterns.md`

### Example Learnings Applied
- **Security**: `publicNetworkAccess: 'Disabled'` for all data services (Storage, Key Vault, SQL)
- **Networking**: Private Endpoints with DNS integration instead of public endpoints
- **Authentication**: Managed Identity with RBAC instead of connection strings
- **Configuration**: No Azure Front Door by default (only when explicitly requested)

### Learnings Database Location
```
.specify/learnings/bicep-learnings.md
```

**Note**: If database doesn't exist, generator proceeds with default patterns and logs a warning.

### Adding Custom Learnings
You can add custom learnings to the database in this format:
```
[Timestamp] Category Context → Issue → Solution
```

Example:
```
2025-10-31T15:00:00Z Security Azure Storage → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and configure Private Endpoint
```

## Troubleshooting

### Common Issues
1. **No Azure services detected**: The project might need manual service specification
2. **Template validation errors**: Check Azure CLI authentication and permissions
3. **Deployment failures**: Verify subscription quotas and regional availability

### Solution Commands
```powershell
# Check Azure CLI authentication
az account show

# Validate Bicep CLI installation
bicep --version

# Test template deployment (what-if)
az deployment group what-if --resource-group <rg-name> --template-file main.bicep --parameters @parameters/dev.json
```

## Integration with Ev2

The generated Bicep templates are designed to integrate seamlessly with Ev2 deployment pipelines:

- **ServiceModel.json**: Generated for Ev2 integration
- **RolloutSpec.yaml**: Deployment rollout specification
- **Parameter mapping**: Environment-specific parameter files
- **Validation hooks**: Pre and post-deployment validation

## Next Steps

After generation, consider these follow-up actions:

1. **Review Templates**: Examine generated Bicep files for accuracy
2. **Customize Parameters**: Adjust parameters for your specific requirements
3. **Set Up CI/CD**: Integrate templates into your deployment pipeline  
4. **Test Deployment**: Deploy to a test environment first
5. **Configure Monitoring**: Set up alerts and monitoring dashboards
6. **Document Changes**: Update project documentation with deployment info

---

*Generated by Specify CLI Bicep Generator - {SCRIPT}*