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

## 🎯 Apply Learnings Database for Consistent Validation

**CRITICAL**: Before performing any validation, load the shared learnings database to ensure consistency with `/speckit.bicep` command. This ensures both generation AND validation follow the same architectural patterns and best practices.

### Load Learnings Database

```python
from pathlib import Path
import logging

from specify_cli.utils.learnings_loader import (
    load_learnings_database,
    filter_learnings_by_category,
    format_learnings_for_prompt
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_validation_learnings():
    """
    Load learnings database for validation context.
    
    Returns:
        list: Filtered learnings relevant to validation (Security, Networking, Compliance)
        
    Raises:
        FileNotFoundError: If learnings database is missing (HALT per Constitution)
        Exception: If database cannot be loaded (HALT per Constitution)
    """
    learnings_db_path = Path('.specify/learnings/bicep-learnings.md')
    
    # CRITICAL: HALT if database cannot be loaded
    # Per Constitution Principle III (Explicit Failure Over Silent Defaults)
    # Validation MUST have learnings context - no degraded fallback allowed
    if not learnings_db_path.exists():
        raise FileNotFoundError(
            f"❌ CRITICAL: Learnings database not found: {learnings_db_path}\n"
            f"   Action: Ensure .specify/learnings/bicep-learnings.md exists before validation.\n"
            f"   Validation cannot proceed without learnings context (Constitution Principle III).\n"
            f"   Run '/speckit.bicep' first to initialize the learnings database."
        )
    
    try:
        # Load all learnings
        all_learnings = load_learnings_database(learnings_db_path)
        logger.info(f"✅ Loaded {len(all_learnings)} learnings from database")
        
        # Filter to validation-relevant categories
        # Security, Networking, Compliance are critical for validation
        # Configuration and Operations provide additional context
        validation_categories = ['Security', 'Networking', 'Compliance', 'Configuration', 'Operations']
        
        if len(all_learnings) > 250:
            # Performance optimization: filter by relevant categories
            logger.info(f"⚡ Database >250 entries ({len(all_learnings)}), applying category filtering")
            filtered_learnings = filter_learnings_by_category(all_learnings, validation_categories)
            logger.info(f"✅ Filtered to {len(filtered_learnings)} validation-relevant learnings")
            return filtered_learnings
        else:
            # Use all learnings if database size is manageable
            return all_learnings
            
    except FileNotFoundError:
        # Re-raise to enforce explicit failure
        raise
    except Exception as e:
        # Any other loading error is CRITICAL - HALT validation
        raise RuntimeError(
            f"❌ CRITICAL: Failed to load learnings database: {e}\n"
            f"   Action: Check database file format and permissions.\n"
            f"   Validation cannot proceed without learnings context (Constitution Principle III)."
        )

# Load learnings at validation start
try:
    validation_learnings = load_validation_learnings()
    learnings_context = format_learnings_for_prompt(validation_learnings)
    
    print(f"✅ Validation learnings loaded: {len(validation_learnings)} entries")
    print(f"   Categories: Security, Networking, Compliance, Configuration, Operations")
    print(f"   These patterns will be validated against deployed resources.\n")
    
except (FileNotFoundError, RuntimeError) as e:
    # HALT validation - explicit failure required
    print(f"\n{e}\n")
    print("❌ VALIDATION HALTED - Learnings database required for consistent validation")
    raise SystemExit(1)
```

### Apply Learnings During Validation

**Use learnings context throughout validation phases**:

1. **During Deployment Validation**:
   - Check deployed resources against Security learnings (e.g., publicNetworkAccess: 'Disabled')
   - Verify Networking patterns (e.g., VNet integration, Private Endpoints)
   - Validate Compliance requirements (e.g., diagnostic settings, audit logging)

2. **During Endpoint Testing**:
   - Verify Security patterns (e.g., HTTPS-only, Managed Identity auth)
   - Check Configuration learnings (e.g., required app settings)

3. **During Error Classification**:
   - Reference learnings to determine if error is already documented
   - Avoid capturing duplicate patterns
   - Use learnings to suggest fixes

### Learnings Context for Validation

```text
{learnings_context}
```

**How to use this context**:
- **Before deployment**: Check if template follows documented patterns
- **After deployment**: Validate deployed resources match learnings requirements
- **On error**: Check if error pattern is already captured in learnings
- **For fix suggestions**: Reference learnings solutions for known issues

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

### 📝 Automated Learning Capture from Validation Failures

**CRITICAL**: When validation failures occur, automatically capture structural issues as new learnings to prevent future occurrences.

#### When to Capture Learnings from Validation

**Capture These Validation Failures** (structural/configuration issues):
- Missing required properties in Bicep templates
- Invalid property values (incorrect types, out-of-range values)
- Resource name conflicts or uniqueness violations
- Missing or misconfigured resource dependencies
- Permission/RBAC configuration errors
- Network security misconfigurations
- Storage/database connection string errors
- Missing firewall rules or service endpoint configurations

**IGNORE These Validation Failures** (transient/operational):
- Quota exceeded errors (temporary limit issue)
- Throttling or rate limit errors
- Network timeouts during deployment
- Transient service unavailability
- Authentication token expiration (temporary)

#### Validation Error Capture Logic

```python
from specify_cli.utils.learnings_loader import (
    classify_error,
    check_insufficient_context,
    append_learning_entry
)
from pathlib import Path

def capture_validation_failure(
    error_message: str,
    validation_phase: str,  # "deployment", "endpoint_test", "configuration"
    resource_type: str = None,
    project_name: str = None
):
    """
    Capture validation failure as new learning entry if structural issue.
    
    Args:
        error_message: The validation error message
        validation_phase: Which phase of validation failed
        resource_type: Optional Azure resource type
        project_name: Optional project being validated
    """
    import logging
    
    # Classify error
    should_capture, capture_keywords = classify_error(error_message)
    
    if not should_capture:
        logging.info(f"⏭️ Skipping validation failure capture (transient error): {error_message[:80]}")
        return
    
    # Check for insufficient context
    has_insufficient = check_insufficient_context(error_message, resource_type)
    if has_insufficient:
        logging.warning(f"⚠️ Skipping validation failure capture (insufficient context): {error_message[:80]}")
        return
    
    # Extract learning components
    category = categorize_validation_error(error_message, validation_phase, resource_type)
    context = extract_validation_context(error_message, validation_phase, resource_type, project_name)
    issue = extract_validation_issue(error_message, validation_phase)
    solution = extract_validation_solution(error_message, validation_phase, resource_type)
    
    # Load learnings database
    learnings_db_path = Path('.specify/learnings/bicep-learnings.md')
    
    # CRITICAL: HALT if database cannot be loaded for appending
    if not learnings_db_path.parent.exists():
        raise FileNotFoundError(
            f"Learnings database directory not found: {learnings_db_path.parent}\n"
            f"Action: Create .specify/learnings/ directory before validation.\n"
            f"This is a critical failure per Constitution Principle III."
        )
    
    try:
        # Append with automatic duplicate checking
        was_appended = append_learning_entry(
            file_path=learnings_db_path,
            category=category,
            context=context,
            issue=issue,
            solution=solution,
            check_duplicates=True
        )
        
        if was_appended:
            logging.info(f"✅ Captured validation failure as learning: {category} - {context}")
            print(f"\n💡 New learning captured from validation failure!")
            print(f"   Category: {category}")
            print(f"   Context: {context}")
            print(f"   This pattern will be automatically applied in future generations.\n")
        else:
            logging.info(f"ℹ️ Validation failure pattern already captured (duplicate detected)")
            
    except ValueError as e:
        logging.error(f"❌ Invalid learning entry format: {e}")
        raise
    except FileNotFoundError as e:
        logging.error(f"❌ Cannot access learnings database: {e}")
        raise
    except Exception as e:
        logging.error(f"❌ Failed to capture validation failure: {e}")
        raise

def categorize_validation_error(
    error_message: str,
    validation_phase: str,
    resource_type: str = None
) -> str:
    """Determine appropriate category for validation error."""
    error_lower = error_message.lower()
    
    # Deployment phase errors
    if validation_phase == "deployment":
        if any(kw in error_lower for kw in ['unauthorized', 'forbidden', 'permission', 'rbac']):
            return 'Security'
        if any(kw in error_lower for kw in ['firewall', 'network', 'subnet', 'vnet', 'endpoint']):
            return 'Networking'
        if any(kw in error_lower for kw in ['policy', 'compliance', 'encryption', 'tls']):
            return 'Compliance'
        if resource_type and 'Storage' in resource_type:
            return 'Data Services'
        if resource_type and ('Sql' in resource_type or 'Database' in resource_type):
            return 'Data Services'
        return 'Configuration'
    
    # Endpoint testing errors
    if validation_phase == "endpoint_test":
        if any(kw in error_lower for kw in ['authentication', 'authorization', '401', '403']):
            return 'Security'
        if any(kw in error_lower for kw in ['connection refused', 'timeout', 'unreachable']):
            return 'Networking'
        return 'Configuration'
    
    # Configuration analysis errors
    if validation_phase == "configuration":
        if 'connection string' in error_lower or 'secret' in error_lower:
            return 'Security'
        return 'Configuration'
    
    return 'Configuration'

def extract_validation_context(
    error_message: str,
    validation_phase: str,
    resource_type: str = None,
    project_name: str = None
) -> str:
    """Extract context from validation error."""
    if resource_type:
        resource_name = resource_type.split('/')[-1]  # e.g., "storageAccounts"
        if project_name:
            return f"{resource_name} in {project_name}"
        return resource_name
    
    if project_name:
        return f"{validation_phase} validation for {project_name}"
    
    return f"{validation_phase} validation"

def extract_validation_issue(error_message: str, validation_phase: str) -> str:
    """Extract issue description from validation error."""
    # Clean error message
    issue = error_message.replace('\n', ' ').strip()
    
    # Add phase context if not already present
    if validation_phase not in issue.lower():
        issue = f"During {validation_phase}: {issue}"
    
    # Truncate to first sentence or 150 chars
    if '.' in issue:
        issue = issue.split('.')[0] + '.'
    
    return issue[:150]

def extract_validation_solution(
    error_message: str,
    validation_phase: str,
    resource_type: str = None
) -> str:
    """Generate solution guidance from validation error."""
    error_lower = error_message.lower()
    
    # Deployment solutions
    if validation_phase == "deployment":
        if 'missing property' in error_lower or 'required property' in error_lower:
            import re
            prop_match = re.search(r"property['\s]+(\w+)", error_message, re.IGNORECASE)
            if prop_match:
                return f"Add required '{prop_match.group(1)}' property to Bicep template"
            return "Add all required properties to Bicep template"
        
        if 'firewall' in error_lower and 'rule' in error_lower:
            return "Add firewall rule to allow Azure services in Bicep template"
        
        if 'already exists' in error_lower:
            return "Use unique resource name with environment-specific suffix"
        
        if 'permission' in error_lower or 'unauthorized' in error_lower:
            return "Grant required RBAC permissions or configure Managed Identity"
    
    # Endpoint testing solutions
    if validation_phase == "endpoint_test":
        if '401' in error_message or 'unauthorized' in error_lower:
            return "Configure authentication in app settings or use Managed Identity"
        
        if 'connection refused' in error_lower:
            return "Verify application started successfully and check app service logs"
        
        if 'timeout' in error_lower:
            return "Increase endpoint timeout or check for slow startup issues"
    
    # Configuration solutions
    if validation_phase == "configuration":
        if 'connection string' in error_lower:
            return "Add connection string to Key Vault and reference in app settings"
        
        if 'missing' in error_lower:
            return "Add required configuration value to parameters file"
    
    return "Review validation logs and Azure documentation to fix configuration"

# Integration: Call in validation error handler
try:
    # ... validation code ...
    pass
except ValidationError as e:
    capture_validation_failure(
        error_message=str(e),
        validation_phase="deployment",  # or "endpoint_test", "configuration"
        resource_type="Microsoft.Sql/servers",
        project_name="backend-api"
    )
    # Continue with fix-and-retry logic...
```

#### Example: Capturing Deployment Failure

When a deployment fails during validation:

```python
# In deployment handler
try:
    deployment_result = deploy_bicep_template(
        template_path="bicep-templates/main.bicep",
        parameters=params
    )
except DeploymentError as e:
    # Capture learning from deployment failure
    capture_validation_failure(
        error_message=str(e),
        validation_phase="deployment",
        resource_type=e.resource_type,
        project_name=project_name
    )
    
    # Attempt fix with /speckit.bicep
    fix_command = f"/speckit.bicep {str(e)}"
    # ... fix-and-retry logic ...
```

#### Example: Capturing Endpoint Test Failure

When endpoint tests fail:

```python
# In endpoint testing loop
for endpoint in discovered_endpoints:
    try:
        response = test_endpoint(endpoint)
        assert response.status_code in expected_codes
    except (ConnectionError, TimeoutError, AssertionError) as e:
        # Capture learning from endpoint failure
        capture_validation_failure(
            error_message=f"Endpoint {endpoint.path} failed: {str(e)}",
            validation_phase="endpoint_test",
            resource_type=None,  # Not resource-specific
            project_name=project_name
        )
        
        # Continue with retry logic...
```

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
