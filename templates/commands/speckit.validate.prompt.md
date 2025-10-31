---
description: "Validate Bicep templates by discovering projects, deploying resources, and testing endpoints with automated fix-and-retry"
---

# Bicep Template Validation Command

You are an expert in Azure infrastructure validation and Bicep template testing.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Command Purpose

This command automates end-to-end validation of generated Bicep templates by:
1. Discovering projects with Bicep templates
2. Analyzing configuration requirements and dependencies
3. Deploying prerequisite resources to test environments
4. Storing secrets in Azure Key Vault
5. Testing API endpoints for functionality
6. Iteratively fixing issues through `/speckit.bicep` integration

## Prerequisites

- Azure CLI installed and authenticated
- Python 3.11+ with specify-cli package
- Access to test/corp Azure subscription
- Appropriate RBAC permissions for resource deployment
- Azure Key Vault access for secret storage

## Execution Steps

### 1. Project Discovery

Run project discovery to find projects with Bicep templates:

```powershell
# Option A: Interactive selection
specify bicep validate

# Option B: Direct project targeting
specify bicep validate --project "my-api-project"
```

**Expected Output:**
- List of discovered projects with Bicep templates
- Project selection prompt (if not specified)
- Framework detection (ASP.NET, Node.js, Python, etc.)

### 2. Configuration Analysis

The command will automatically analyze:
- Application settings from configuration files
- Secure values requiring Key Vault storage
- Resource dependencies (SQL, Storage, CosmosDB, etc.)
- Deployment order based on dependency graph

**Expected Output:**
- List of identified app settings
- Resource dependency graph
- Deployment sequence

### 3. Resource Deployment

Resources are deployed in topological order:
- Validates Bicep templates before deployment
- Deploys up to 4 resources concurrently
- Extracts connection strings from deployment outputs
- Stores secrets in Azure Key Vault with naming convention

**Expected Output:**
- Deployment progress with status updates
- Deployed resource IDs and outputs
- Key Vault secret references

### 4. Endpoint Testing

Discovers and tests API endpoints:
- Extracts endpoints from source code (controllers, routes, decorators)
- Parses OpenAPI/Swagger specifications
- Tests endpoints with retry logic and exponential backoff
- Validates 2xx status codes by default

**Expected Output:**
- List of discovered endpoints
- Test results with response times
- Success/failure summary

### 5. Fix-and-Retry (if issues detected)

Automatically attempts to fix template issues:
- Classifies errors (timeout, auth, server error, template issue)
- Calls `/speckit.bicep <issue explanation>` for template fixes
- Retries deployment and testing
- Maximum 3 retry attempts by default

**Expected Output:**
- Error classification
- Fix attempts and outcomes
- Final validation status

## Usage Examples

### Basic Validation (Interactive)

```powershell
# Discover and select project interactively
specify bicep validate
```

### Direct Project Validation

```powershell
# Validate specific project
specify bicep validate --project "backend-api"
```

### Custom Environment

```powershell
# Target specific test environment
specify bicep validate --project "frontend-app" --environment "test-staging"
```

### Verbose Output for Debugging

```powershell
# Enable detailed logging
specify bicep validate --project "data-service" --verbose
```

### Custom Retry Limit

```powershell
# Increase fix-and-retry attempts
specify bicep validate --project "api-gateway" --max-retries 5
```

### Skip Cleanup (for inspection)

```powershell
# Leave deployed resources for manual inspection
specify bicep validate --project "auth-service" --skip-cleanup
```

### Filter Endpoints by HTTP Method

```powershell
# Test only GET and POST endpoints
specify bicep validate --methods GET,POST
```

### Filter Endpoints by Path Pattern

```powershell
# Test only API v1 endpoints
specify bicep validate --endpoint-filter "^/api/v1/"
```

### Custom Status Codes and Timeout

```powershell
# Accept 201 Created responses and increase timeout
specify bicep validate --status-codes 200,201,204 --timeout 60
```

### Skip Authenticated Endpoints

```powershell
# Test only public endpoints (skip auth requirements)
specify bicep validate --skip-auth
```

### Combined Custom Options

```powershell
# Comprehensive custom validation
specify bicep validate \
  --project "backend-api" \
  --environment production \
  --methods GET,POST \
  --endpoint-filter "^/api/v2/" \
  --timeout 45 \
  --verbose
```

## Interpreting $ARGUMENTS

Parse user input to determine validation scope:

1. **If $ARGUMENTS contains a project name**: Use it as `--project` parameter
2. **If $ARGUMENTS mentions environment** (e.g., "test", "staging", "production"): Use `--environment` parameter
3. **If $ARGUMENTS mentions HTTP methods** (e.g., "only GET", "GET and POST"): Use `--methods` parameter
4. **If $ARGUMENTS mentions endpoint filtering** (e.g., "only API endpoints", "/api/v1/"): Use `--endpoint-filter` parameter
5. **If $ARGUMENTS mentions timeout** (e.g., "60 second timeout"): Use `--timeout` parameter
6. **If $ARGUMENTS mentions skipping auth** (e.g., "skip authentication", "public endpoints only"): Add `--skip-auth` flag
7. **If $ARGUMENTS requests verbose/detailed output**: Add `--verbose` flag
8. **If $ARGUMENTS mentions retry limit**: Use `--max-retries` parameter
9. **If $ARGUMENTS requests cleanup skip**: Add `--skip-cleanup` flag
10. **If $ARGUMENTS is empty**: Run interactive project selection

## Error Handling

### Common Issues and Resolutions

**"No projects found with Bicep templates"**
- Verify Bicep templates exist in workspace
- Check for `bicep-templates/` or similar directory
- Suggest running `/speckit.bicep` to generate templates first

**"Deployment failed: Quota exceeded"**
- Resource quota limits reached in test subscription
- Suggest cleanup of unused resources or different region
- Provide quota increase documentation link

**"Key Vault access denied"**
- Check Managed Identity configuration
- Verify RBAC permissions (Key Vault Secrets Officer role)
- Suggest Key Vault access policy troubleshooting

**"Endpoint tests failed: Connection refused"**
- Application may not be fully started
- Check application logs for startup errors
- Verify deployment outputs for correct URL

**"Max retries exhausted"**
- Persistent template or configuration issues
- Review error messages for root cause
- Suggest manual inspection with `--skip-cleanup`

## Integration with Other Commands

### With `/speckit.bicep`

Validation automatically calls `/speckit.bicep` when template issues are detected:

```text
Issue: "SQL Server firewall rule missing for Azure services"
Action: /speckit.bicep Add firewall rule to allow Azure services in SQL Server template
```

### With `/speckit.plan`

Use validation results to inform planning:

```powershell
# After validation failures
/speckit.plan "Add detailed error handling for database connection failures"
```

### With `/speckit.tasks`

Create tasks based on validation findings:

```powershell
# Generate tasks for fixing validation issues
/speckit.tasks "Fix all endpoint authentication issues found in validation"
```

## Best Practices

1. **Run validation in test environments only** - Never validate against production
2. **Review validation summary** - Check deployed resources and test results
3. **Clean up resources** - Use default cleanup unless debugging
4. **Monitor retry attempts** - If hitting max retries frequently, investigate root causes
5. **Use verbose mode for debugging** - Enable when validation fails unexpectedly
6. **Validate before production deployment** - Catch issues early in development cycle
7. **Keep templates modular** - Easier to identify and fix validation issues
8. **Document custom endpoints** - Use OpenAPI/Swagger for comprehensive testing
9. **Test with realistic data** - Use representative test parameters
10. **Review Key Vault secrets** - Verify secure values are properly stored

## Security Considerations

- **Secrets never logged in plain text** - All secure values go through Key Vault
- **Managed Identity preferred** - Avoid storing credentials
- **RBAC over access policies** - Use role-based access control
- **Audit trails enabled** - Key Vault operations are logged
- **Test environments isolated** - No production resource access
- **Cleanup enabled by default** - Minimizes security surface area

## Performance Tips

- **Use caching** - Project discovery cache speeds up subsequent runs
- **Parallel deployments** - Up to 4 resources deploy concurrently
- **Optimize endpoint tests** - Up to 10 endpoints test concurrently
- **Skip unnecessary tests** - Use `--endpoints` filter for targeted testing
- **Reuse deployments** - Skip redeployment with `--skip-deployment` when iterating

## Output Interpretation

### Successful Validation

```
✅ Validation completed successfully
   - 15/15 app settings identified
   - 3/3 resources deployed
   - 8/8 endpoints passed
   - 0 fix attempts required
   Duration: 12m 34s
```

### Partial Success

```
⚠️ Validation completed with warnings
   - 15/15 app settings identified
   - 3/3 resources deployed
   - 6/8 endpoints passed (2 failed)
   - 1 fix attempt (1 successful)
   Duration: 18m 12s
```

### Failure

```
❌ Validation failed
   - 15/16 app settings identified (1 missing)
   - 2/3 resources deployed (1 failed)
   - 0/8 endpoints tested (deployment failed)
   - 3 fix attempts (all failed)
   Duration: 25m 03s
   
   See detailed errors above for resolution steps.
```

## Next Steps After Validation

1. **If validation succeeds**: Templates are ready for production deployment
2. **If validation fails**: Review error messages and apply fixes
3. **If partial success**: Investigate failed endpoints, may be configuration issues
4. **If max retries hit**: Manual intervention required, use `--skip-cleanup` to inspect

---

**Remember**: This command validates the END-TO-END functionality, not just template syntax. It ensures your infrastructure and application work together correctly.
