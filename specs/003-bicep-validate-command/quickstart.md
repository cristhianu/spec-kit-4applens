# Quickstart: Bicep Validate Command

**Feature**: 003-bicep-validate-command  
**Command**: `/speckit.validate`  
**Purpose**: Automated end-to-end validation of generated Bicep templates

---

## Overview

The `/speckit.validate` command automates the complete validation workflow for Bicep-generated infrastructure:

1. **Discover** projects with Bicep templates
2. **Analyze** configuration requirements
3. **Deploy** prerequisite resources to test environment
4. **Store** secrets securely in Azure Key Vault
5. **Deploy** application infrastructure
6. **Test** API endpoints
7. **Fix** issues automatically (iterative retry)
8. **Validate** successful deployment

---

## Quick Start

### Prerequisites

Before using `/speckit.validate`:

✅ **Azure CLI** installed and authenticated (`az login`)  
✅ **Bicep CLI** installed (`az bicep install`)  
✅ **Test environment** configured (resource group + subscription)  
✅ **Bicep templates** generated (via `/speckit.bicep`)  
✅ **Permissions** to deploy resources and manage Key Vault

**Check prerequisites:**

```powershell
specify check
```

### Basic Usage

**1. Validate with Interactive Project Selection:**

```powershell
specify validate
```

The command will:
- Scan workspace for projects with Bicep templates
- Display interactive selection menu
- Run full validation workflow

**2. Validate Specific Project:**

```powershell
specify validate --project "MyApi"
```

**3. Validate with Custom Environment:**

```powershell
specify validate --environment "staging-corp"
```

**4. Validate with Custom Instructions:**

```powershell
specify validate "Skip authentication tests, focus on database connectivity"
```

---

## Command Options

```text
specify validate [CUSTOM_INSTRUCTIONS]

Arguments:
  CUSTOM_INSTRUCTIONS    Optional custom validation instructions (text)

Options:
  --project TEXT         Project name to validate (default: interactive)
  --environment TEXT     Target environment (default: "test-corp")
  --max-retries INT      Maximum fix retry attempts (default: 3)
  --skip-cleanup         Skip resource cleanup after validation
  --verbose              Enable detailed output
  --help                 Show this message and exit
```

---

## Workflow Stages

### Stage 1: Project Discovery

```text
🔍 Discovering projects...
   Found 3 projects with Bicep templates:
     1. MyApi (dotnet, 12 templates)
     2. DataProcessor (python, 8 templates)
     3. WebApp (nodejs, 15 templates)
   
   Select project to validate: █
```

**What happens:**
- Scans workspace for projects with `bicep-templates/` directory
- Detects framework (ASP.NET, Node.js, Python)
- Caches results for faster subsequent runs
- Prompts for selection if multiple projects found

### Stage 2: Configuration Analysis

```text
📋 Analyzing configuration requirements...
   Detected framework: ASP.NET Core
   Found 12 application settings:
     ✓ DatabaseConnection (secure → Key Vault)
     ✓ StorageAccount (secure → Key Vault)
     ✓ ApiKey (secure → Key Vault)
     ✓ FeatureFlags (deployment output)
     • LogLevel (hardcoded: Information)
     • Environment (hardcoded: Test)
   
   Building dependency graph...
   ✓ 3 resources require deployment
   ✓ 3 secrets need Key Vault storage
```

**What happens:**
- Parses `appsettings.json`, `web.config`, `.env`, `config.py` (framework-specific)
- Identifies secure settings (connection strings, API keys, passwords)
- Determines resource dependencies (e.g., storage account → connection string)
- Builds topological sort of deployment order

### Stage 3: Resource Deployment

```text
☁️ Deploying prerequisite resources...
   Environment: test-corp
   Resource Group: myapi-test-rg
   Subscription: Test Corp (00000000-...)
   
   Deploying in dependency order:
     [1/3] ⏳ SQL Server... 
     [1/3] ✓ SQL Server (45.2s)
           Outputs: serverName, databaseConnection
     
     [2/3] ⏳ Storage Account...
     [2/3] ✓ Storage Account (23.8s)
           Outputs: storageAccountName, connectionString
     
     [3/3] ⏳ Key Vault...
     [3/3] ✓ Key Vault (31.5s)
           Outputs: vaultUrl, vaultName
   
   ✓ All resources deployed (100.5s total)
```

**What happens:**
- Validates Bicep templates before deployment
- Deploys resources in topological order (respecting dependencies)
- Supports up to 4 parallel deployments (independent resources)
- Captures deployment outputs for configuration values
- Implements exponential backoff retry for transient failures

### Stage 4: Key Vault Integration

```text
🔐 Storing secrets in Key Vault...
   Key Vault: myapi-test-kv
   
   Storing 3 secrets:
     ✓ myapi--test--database--connection
     ✓ myapi--test--storage--connection
     ✓ myapi--test--apikey
   
   Building App Service settings:
     ✓ DatabaseConnection → @Microsoft.KeyVault(...)
     ✓ StorageConnection → @Microsoft.KeyVault(...)
     ✓ ApiKey → @Microsoft.KeyVault(...)
   
   ✓ All secrets stored with managed identity access
```

**What happens:**
- Stores secure configuration values in Key Vault
- Follows Azure naming conventions (`app--env--category--name`)
- Configures Managed Identity access (no keys/passwords)
- Builds Key Vault references for App Service settings

### Stage 5: Application Deployment

```text
🚀 Deploying application infrastructure...
   Deploying main.bicep with parameters:
     • appSettings (from Key Vault references)
     • resourceOutputs (from prerequisite deployments)
   
   ⏳ Deploying App Service...
   ✓ App Service deployed (67.3s)
      URL: https://myapi-test.azurewebsites.net
```

**What happens:**
- Deploys main application infrastructure
- Injects app settings with Key Vault references
- Waits for deployment completion
- Captures application URL for testing

### Stage 6: Endpoint Discovery

```text
🔎 Discovering API endpoints...
   Scanning source code...
   Found 8 endpoints:
     🔒 GET    /api/users
     🔒 POST   /api/users
     🔒 GET    /api/users/{id}
     🔒 PUT    /api/users/{id}
     🔒 DELETE /api/users/{id}
     🔓 GET    /api/health
     🔓 GET    /api/version
     🔒 GET    /api/settings
   
   ✓ 8 endpoints discovered (5 require auth)
```

**What happens:**
- Scans source code for route definitions
- Parses OpenAPI/Swagger specs if available
- Identifies authentication requirements
- Builds test request templates

### Stage 7: Endpoint Testing

```text
🧪 Testing endpoints...
   Base URL: https://myapi-test.azurewebsites.net
   
   Testing 8 endpoints (10 concurrent):
     [1/8] ✓ GET /api/health (142ms, HTTP 200)
     [2/8] ✓ GET /api/version (98ms, HTTP 200)
     [3/8] ✓ GET /api/users (234ms, HTTP 200)
     [4/8] ✓ POST /api/users (312ms, HTTP 201)
     [5/8] ✓ GET /api/users/123 (187ms, HTTP 200)
     [6/8] ✗ PUT /api/users/123 (Timeout after 30s)
     [7/8] ✗ DELETE /api/users/123 (HTTP 500, Internal Server Error)
     [8/8] ✓ GET /api/settings (201ms, HTTP 200)
   
   Results: 6/8 passed, 2 failed
```

**What happens:**
- Tests all discovered endpoints
- Implements retry logic (exponential backoff)
- Supports authentication (bearer tokens, API keys)
- Captures response times and status codes
- Identifies failures for automated fixing

### Stage 8: Automated Fixing

```text
🔧 Attempting automated fixes...
   
   Issue 1: Endpoint timeout (PUT /api/users/{id})
   Error Category: timeout
   Strategy: Increase app service plan SKU
   
   ⏳ Calling /speckit.bicep to update template...
   ✓ Template updated: Changed SKU to P1v2
   ⏳ Redeploying infrastructure...
   ✓ Infrastructure redeployed (45.2s)
   ⏳ Retesting endpoint...
   ✓ PUT /api/users/123 (287ms, HTTP 200)
   
   Issue 2: Internal server error (DELETE /api/users/{id})
   Error Category: server_error
   Strategy: Check application logs
   
   ⏳ Fetching App Service logs...
   Log entries:
     [ERROR] Microsoft.Data.SqlClient.SqlException: Cannot delete user
     [ERROR] Violation of FOREIGN KEY constraint
   
   Issue: Database constraint violation (not auto-fixable)
   Recommendation: Update database schema or API logic
   
   ✗ Cannot fix automatically - manual intervention required
```

**What happens:**
- Classifies errors (timeout, authentication, server error, template issue)
- Applies fix strategies:
  - **Template issues**: Calls `/speckit.bicep` to regenerate templates
  - **Timeout**: Increases app service plan SKU
  - **Authentication**: Fixes Key Vault references or managed identity
  - **Server errors**: Fetches logs and provides recommendations
- Retries validation after each fix
- Limits to 3 retry attempts (configurable)
- Reports manual intervention needs

### Stage 9: Validation Summary

```text
📊 Validation Summary
   
   Status: PARTIAL SUCCESS ⚠️
   Duration: 4m 32s
   
   Resources Deployed:
     ✓ SQL Server (myapi-test-sql)
     ✓ Storage Account (myapiteststorage)
     ✓ Key Vault (myapi-test-kv)
     ✓ App Service (myapi-test)
   
   Endpoint Testing:
     ✓ 7/8 endpoints passed (87.5%)
     ✗ 1 endpoint failed:
        • DELETE /api/users/{id} - Server error (database constraint)
   
   Fix Attempts:
     ✓ 1 successful (timeout fix)
     ✗ 1 manual intervention needed (database schema)
   
   Next Steps:
     1. Review database schema for foreign key constraints
     2. Update API to handle constraint violations gracefully
     3. Re-run validation: specify validate --project "MyApi"
```

**What happens:**
- Reports final validation status (SUCCESS, PARTIAL, FAILED)
- Summarizes deployment results
- Lists endpoint test results
- Documents fix attempts
- Provides actionable next steps

---

## Common Scenarios

### Scenario 1: First-Time Validation

**Goal**: Validate newly generated Bicep templates

```powershell
# Generate templates first
specify bicep

# Run validation
specify validate
```

**Expected Flow**:
1. Discovers project (interactive selection if multiple)
2. Analyzes configuration
3. Deploys all resources
4. Tests endpoints
5. Reports success or provides fix recommendations

### Scenario 2: Re-validation After Fixes

**Goal**: Validate after manual fixes

```powershell
specify validate --project "MyApi"
```

**Expected Flow**:
1. Uses cached project discovery
2. Re-analyzes configuration (detects changes)
3. Deploys only changed resources
4. Re-tests all endpoints
5. Reports updated results

### Scenario 3: Custom Validation Scope

**Goal**: Validate specific aspects

```powershell
specify validate "Only test GET endpoints, skip authentication"
```

**Expected Flow**:
1. Parses custom instructions
2. Filters discovered endpoints (GET only)
3. Skips authentication setup
4. Tests filtered endpoints
5. Reports results for requested scope

### Scenario 4: Multi-Project Validation

**Goal**: Validate multiple projects in sequence

```powershell
# Validate all projects
foreach ($project in @("MyApi", "DataProcessor", "WebApp")) {
    specify validate --project $project --skip-cleanup
}
```

**Expected Flow**:
1. Validates each project independently
2. Keeps resources deployed (`--skip-cleanup`)
3. Accumulates validation results
4. Manual cleanup after all validations

---

## Troubleshooting

### Issue: No Projects Found

**Symptom:**
```text
❌ No projects with Bicep templates found
```

**Solutions:**
1. Ensure Bicep templates generated: `specify bicep`
2. Check expected directory structure: `<project>/bicep-templates/`
3. Clear cache: `specify validate --clear-cache`

### Issue: Authentication Failed

**Symptom:**
```text
❌ Azure authentication failed
```

**Solutions:**
1. Login to Azure CLI: `az login`
2. Set subscription: `az account set --subscription <id>`
3. Verify permissions: `az role assignment list --assignee <user>`

### Issue: Deployment Failed

**Symptom:**
```text
❌ Resource deployment failed: Invalid template
```

**Solutions:**
1. Validate template manually: `az bicep build --file <template>`
2. Check Azure quotas: `az vm list-usage --location <region>`
3. Review error details: `specify validate --verbose`
4. Regenerate templates: `specify bicep`

### Issue: Endpoint Test Timeout

**Symptom:**
```text
❌ Endpoint test timeout (30s)
```

**Solutions:**
1. Check application logs: Azure Portal → App Service → Log stream
2. Increase timeout: Edit `src/specify_cli/validation/endpoint_tester.py`
3. Verify network connectivity: `curl <endpoint-url>`
4. Scale up app service plan (automatic fix)

### Issue: Key Vault Access Denied

**Symptom:**
```text
❌ Key Vault access denied
```

**Solutions:**
1. Check managed identity assigned: Azure Portal → App Service → Identity
2. Verify RBAC roles: Key Vault → Access control (IAM)
3. Grant "Key Vault Secrets User" role
4. Wait 5 minutes for permission propagation

---

## Advanced Usage

### Custom Environment Configuration

Create environment-specific configuration:

```yaml
# .specify/environments/staging-corp.yaml
resourceGroup: myapp-staging-rg
subscriptionId: 00000000-0000-0000-0000-000000000000
keyVaultName: myapp-staging-kv
appServicePlan: myapp-staging-plan
location: eastus2
tags:
  environment: staging
  team: platform
```

Use custom environment:

```powershell
specify validate --environment staging-corp
```

### Skip Resource Cleanup

Keep deployed resources for manual testing:

```powershell
specify validate --skip-cleanup
```

**Manual cleanup:**

```powershell
az group delete --name myapi-test-rg --yes --no-wait
```

### Increase Retry Attempts

For complex validation workflows:

```powershell
specify validate --max-retries 5
```

### Verbose Output

For debugging and troubleshooting:

```powershell
specify validate --verbose
```

**Verbose output includes:**
- Detailed Azure CLI command execution
- HTTP request/response details
- Template validation output
- Key Vault operation logs
- Retry attempt details

---

## Integration with Other Commands

### 1. Generate Templates → Validate

```powershell
# Generate Bicep templates
specify bicep "Deploy web API with SQL database and blob storage"

# Validate generated templates
specify validate
```

### 2. Validate → Fix → Validate

```powershell
# Initial validation
specify validate --project "MyApi"

# Fix issues reported
# (manual fixes or /speckit.bicep regeneration)

# Re-validate
specify validate --project "MyApi"
```

### 3. Plan → Implement → Validate

```powershell
# Create implementation plan
specify plan

# Implement feature
specify tasks

# Validate deployment
specify validate
```

---

## Best Practices

### 1. **Use Test Environments**

Always validate in isolated test environments:
- Separate resource groups
- Separate subscriptions (if possible)
- Clear naming conventions (e.g., `-test`, `-staging`)

### 2. **Keep Templates Updated**

Regenerate templates after code changes:

```powershell
specify bicep   # Regenerate templates
specify validate # Validate updated templates
```

### 3. **Review Logs for Failures**

When validation fails:
1. Check verbose output: `--verbose`
2. Review Azure Portal logs
3. Examine application logs
4. Check deployment history

### 4. **Clean Up Resources**

Remove test resources after validation:

```powershell
az group delete --name <test-rg> --yes --no-wait
```

Or use `--skip-cleanup` for manual testing, then clean up explicitly.

### 5. **Version Control Validation Results**

Save validation summaries for audit trails:

```powershell
specify validate > validation-results-$(Get-Date -Format "yyyy-MM-dd").txt
```

---

## Performance Tips

### Cache Project Discovery

First run: ~8-10 seconds for discovery  
Subsequent runs: <1 second (cached)

**Clear cache when needed:**

```powershell
specify validate --clear-cache
```

### Parallel Resource Deployment

Default: Up to 4 resources deployed in parallel  
Independent resources deploy simultaneously

**Deployment time:**
- Sequential: 5 resources × 40s = 200s
- Parallel (4 concurrent): ~80-100s

### Concurrent Endpoint Testing

Default: Up to 10 endpoints tested concurrently

**Test time:**
- Sequential: 20 endpoints × 200ms = 4s
- Parallel (10 concurrent): ~800ms

---

## Security Considerations

### 1. **Use Managed Identity**

All Key Vault access uses Managed Identity (no keys/passwords):
- App Service → Key Vault: Managed Identity + RBAC
- CLI → Key Vault: User identity + Azure CLI authentication

### 2. **Secure Secret Storage**

All sensitive values stored in Key Vault:
- Connection strings
- API keys
- Passwords
- Certificates

### 3. **Test Environment Isolation**

Deploy to isolated test environments:
- Separate resource groups
- Separate subscriptions (if possible)
- Network isolation (VNets, private endpoints)

### 4. **Audit Trails**

Track validation activities:
- Azure Activity Logs (resource deployments)
- Key Vault audit logs (secret access)
- Application Insights (endpoint tests)

---

## FAQ

**Q: How long does validation take?**  
A: Typically 4-10 minutes depending on:
- Number of resources (2-5 minutes for deployment)
- Number of endpoints (1-2 minutes for testing)
- Fix attempts (1-3 minutes per retry)

**Q: Can I validate multiple projects simultaneously?**  
A: Not recommended. Validate projects sequentially to avoid resource conflicts.

**Q: What happens to test resources after validation?**  
A: By default, resources remain deployed. Use `az group delete` to clean up, or add `--auto-cleanup` flag (future enhancement).

**Q: Does validation work with existing infrastructure?**  
A: Yes, validation detects existing resources and only deploys missing components.

**Q: Can I customize endpoint test scenarios?**  
A: Yes, use custom instructions: `specify validate "Test user creation flow with valid data"`

**Q: How do I validate without deploying resources?**  
A: Use template validation only (future enhancement): `specify validate --dry-run`

---

## Next Steps

After successful validation:

1. **Deploy to Production**
   ```powershell
   specify bicep --environment production
   # Manual deployment to production (not automated)
   ```

2. **Update Documentation**
   - Document validation results
   - Update deployment runbooks
   - Share lessons learned

3. **Set Up CI/CD**
   - Integrate validation into pipelines
   - Automate template generation
   - Add quality gates

4. **Monitor Production**
   - Enable Application Insights
   - Configure alerts
   - Set up dashboards

---

**Ready to validate?** Start with: `specify validate`

**Need help?** Run: `specify validate --help`

**Found issues?** Check: [Troubleshooting Guide](#troubleshooting)
