# Bicep Generator - Troubleshooting Guide

## Table of Contents

- [Common Issues](#common-issues)
- [Analysis Issues](#analysis-issues)
- [Generation Issues](#generation-issues)
- [Validation Issues](#validation-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)
- [Debugging Tips](#debugging-tips)

## Common Issues

### Issue: Command Not Found

**Symptoms:**
```
'specify' is not recognized as an internal or external command
```

**Solution:**

1. Verify installation:
```bash
pip show specify-cli
```

2. Check Python PATH:
```bash
# Windows PowerShell
$env:PATH -split ';' | Select-String python

# Bash/Linux
echo $PATH | tr ':' '\n' | grep python
```

3. Reinstall if needed:
```bash
pip uninstall specify-cli
pip install specify-cli
```

---

### Issue: Azure CLI Not Authenticated

**Symptoms:**
```
ERROR: Azure CLI authentication required
Please run: az login
```

**Solution:**

```bash
# Interactive login
az login

# Service principal login
az login --service-principal \
  --username <app-id> \
  --password <password-or-cert> \
  --tenant <tenant-id>

# Managed identity login (on Azure VM)
az login --identity

# Verify authentication
az account show
```

---

### Issue: Missing Dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'azure.identity'
```

**Solution:**

```bash
# Install all dependencies
pip install specify-cli[all]

# Or install specific dependencies
pip install azure-identity azure-mgmt-resource rich typer
```

---

## Analysis Issues

### Issue: No Dependencies Detected

**Symptoms:**
```
WARNING: No Azure dependencies detected in project
Analysis complete but no resources identified
```

**Diagnosis:**

```bash
# Run with verbose output
specify bicep analyze --project-path . --verbose

# Check what files are being analyzed
specify bicep analyze --project-path . --dry-run
```

**Solutions:**

1. **Ensure configuration files are present:**
   - `appsettings.json` (for .NET)
   - `requirements.txt` or `setup.py` (for Python)
   - `package.json` (for Node.js)

2. **Add explicit hints in configuration:**
```json
// bicep_config.json
{
  "hints": {
    "services": ["storage", "webapp", "keyvault"]
  }
}
```

3. **Check file patterns:**
```bash
# Include specific files
specify bicep analyze \
  --include "**/*.config" \
  --include "**/*.json"
```

---

### Issue: Analysis Timeout

**Symptoms:**
```
ERROR: Analysis timed out after 300 seconds
```

**Solution:**

```bash
# Increase timeout
specify bicep analyze \
  --timeout 600 \
  --project-path ./large-project

# Exclude large directories
specify bicep analyze \
  --exclude "**/node_modules/**" \
  --exclude "**/bin/**" \
  --exclude "**/obj/**"

# Use incremental analysis
specify bicep analyze \
  --incremental \
  --cache-dir ./.bicep-cache
```

---

### Issue: Permission Denied Reading Files

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: './file.txt'
```

**Solution:**

```bash
# Windows: Run as administrator
# or adjust file permissions

# Linux/macOS: Fix permissions
chmod -R +r ./project-directory

# Skip inaccessible files
specify bicep analyze \
  --skip-permission-errors \
  --project-path .
```

---

## Generation Issues

### Issue: Template Generation Fails

**Symptoms:**
```
ERROR: Failed to generate template for resource 'storageAccount'
```

**Diagnosis:**

```bash
# Enable debug logging
specify bicep generate \
  --debug \
  --log-file bicep-debug.log

# Validate analysis file
specify bicep validate-analysis \
  --analysis-file ./analysis/project-analysis.json
```

**Solutions:**

1. **Check analysis file integrity:**
```bash
# Verify JSON structure
cat ./analysis/project-analysis.json | python -m json.tool
```

2. **Use fallback templates:**
```bash
specify bicep generate \
  --fallback-on-errors \
  --analysis-file ./analysis/project-analysis.json
```

3. **Generate incrementally:**
```bash
# Generate one resource type at a time
specify bicep generate \
  --resource-types storage \
  --output-dir ./bicep-templates/storage

specify bicep generate \
  --resource-types compute \
  --output-dir ./bicep-templates/compute
```

---

### Issue: Invalid Bicep Syntax Generated

**Symptoms:**
```
Error BCP057: The name "resourceName" does not exist in the current context
```

**Solution:**

```bash
# Validate Bicep CLI version
bicep --version
# Ensure version >= 0.15.0

# Upgrade if needed
az bicep upgrade

# Regenerate with specific Bicep version
specify bicep generate \
  --bicep-version "0.30.0" \
  --analysis-file ./analysis/project-analysis.json

# Use compatibility mode
specify bicep generate \
  --compatibility-mode strict \
  --target-bicep-version "0.15.0"
```

---

### Issue: Missing Resource Dependencies

**Symptoms:**
```
ERROR: Resource 'webapp' depends on 'storageAccount' which was not generated
```

**Solution:**

```bash
# Force dependency resolution
specify bicep generate \
  --resolve-dependencies \
  --analysis-file ./analysis/project-analysis.json

# Manual dependency specification
specify bicep generate \
  --dependencies webapp:storageAccount,keyvault \
  --analysis-file ./analysis/project-analysis.json
```

---

## Validation Issues

### Issue: Bicep Validation Fails

**Symptoms:**
```
Error: Template validation failed with 3 errors
```

**Diagnosis:**

```bash
# Validate manually with Azure CLI
az deployment group validate \
  --resource-group my-rg \
  --template-file ./bicep-templates/main.bicep \
  --parameters @./parameters/dev.parameters.json

# Use bicep CLI directly
bicep build ./bicep-templates/main.bicep
```

**Solutions:**

1. **Check parameter types:**
```bicep
// Ensure parameter types match usage
param storageAccountName string // not object or array
param location string = resourceGroup().location
```

2. **Verify resource API versions:**
```bash
# Check available API versions
az provider show \
  --namespace Microsoft.Storage \
  --query "resourceTypes[?resourceType=='storageAccounts'].apiVersions"
```

3. **Fix circular dependencies:**
```bicep
// Avoid:
// resourceA depends on resourceB
// resourceB depends on resourceA

// Use explicit dependencies instead
resource resourceB 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'storage'
  // ...
}

resource resourceA 'Microsoft.Web/sites@2023-01-01' = {
  name: 'webapp'
  dependsOn: [resourceB]
  // ...
}
```

---

### Issue: Schema Validation Errors

**Symptoms:**
```
ERROR: Schema validation failed: 'sku' is a required property
```

**Solution:**

```bash
# Regenerate with schema validation
specify bicep generate \
  --validate-schema \
  --analysis-file ./analysis/project-analysis.json

# Get latest schemas
specify bicep update-schemas \
  --force

# Use specific API version
specify bicep generate \
  --api-version "2023-01-01" \
  --resource-type "Microsoft.Storage/storageAccounts"
```

---

### Issue: Learnings Database Warnings

The Bicep Generator uses a learnings database (`.specify/learnings/bicep-learnings.md`) to improve template generation based on past issues, best practices, and team knowledge. You may encounter warnings related to this database.

#### Warning: Missing Learnings Database

**Symptoms:**
```
WARNING: Learnings database not found at .specify/learnings/bicep-learnings.md
Continuing without learnings (first-time generation)
```

**Cause:** No learnings database exists yet (common for first-time usage).

**Solution:**

This is **not an error** - just informational. The database will be created automatically when:
- Bicep generation encounters errors that get captured
- You manually add entries following [the quickstart guide](../../specs/004-bicep-learnings-database/contracts/quickstart.md)

**No action needed** - generation continues normally.

---

#### Warning: Invalid Learnings Entry Format

**Symptoms:**
```
WARNING: Cannot parse timestamp at line 42 in bicep-learnings.md
Skipping invalid entry and continuing...

WARNING: Unknown category 'Deployment' at line 57
Valid categories: Security, Compliance, Networking, Data Services, Compute, Configuration, Operations, Cost

WARNING: Context too long (150 chars, max 100) at line 63
Entry will be skipped
```

**Cause:** Manual edits to learnings database with incorrect format:
- Missing or invalid timestamp
- Unknown category name
- Field length exceeds limits (Context ≤100, Issue ≤150, Solution ≤200)
- Wrong separator (must use `→` unicode U+2192)

**Solution:**

1. **Locate the problematic entry** in `.specify/learnings/bicep-learnings.md`:

```bash
# Linux/macOS
sed -n '42p' .specify/learnings/bicep-learnings.md

# Windows PowerShell
Get-Content .specify/learnings/bicep-learnings.md | Select-Object -Index 41
```

2. **Fix the entry format** - see [Entry Format Rules](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#entry-format):

```markdown
<!-- ✅ GOOD: Correct format -->
[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in Key Vault properties

<!-- ❌ BAD: Missing timestamp brackets -->
2025-01-15 Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true'

<!-- ❌ BAD: Invalid category -->
[2025-01-15T00:00:00Z] Deployment Issue here → Solution here → Details here

<!-- ❌ BAD: Context too long (>100 chars) -->
[2025-01-15T00:00:00Z] Security This is a really long context field that exceeds the 100 character limit and will cause validation to fail → Solution → Details

<!-- ❌ BAD: Wrong separator (using dash instead of arrow) -->
[2025-01-15T00:00:00Z] Security Key Vault access - Enable RBAC - Use enableRbacAuthorization
```

3. **Verify character limits**:

| Field | Max Length | Example |
|-------|-----------|---------|
| Context | 100 chars | `Key Vault access without RBAC` (30 chars) ✅ |
| Issue | 150 chars | `Enable RBAC authorization mode` (32 chars) ✅ |
| Solution | 200 chars | `Use 'enableRbacAuthorization: true' in properties` (51 chars) ✅ |

4. **Test your fix**:

```bash
# Test that learnings load without warnings
specify bicep generate --project-path . --dry-run

# Or use validation command
specify validate --project-path .
```

**See also:** [Quickstart Guide - Entry Format Rules](../../specs/004-bicep-learnings-database/contracts/quickstart.md#entry-format-rules)

---

#### Warning: Duplicate Learnings Entry Detected

**Symptoms:**
```
WARNING: Potential duplicate detected at line 89 (72% similar to entry at line 45)
Entry: "2025-01-15 | Security | Key Vault RBAC authorization..."
Skipping duplicate to avoid redundancy
```

**Cause:** The entry you added is >60% similar to an existing entry (detected using TF-IDF + cosine similarity algorithm).

**Why this happens:**
- Manual entry duplicates automated capture
- Two team members independently added similar learnings
- Slight wording variations of same issue

**Solution:**

**Option A: Accept the duplicate rejection** (recommended)
- The system already has coverage for this issue
- No action needed - generation continues with existing entry

**Option B: Consolidate the entries if the new one adds value**

1. **Find the existing entry:**

```bash
# Linux/macOS
sed -n '45p' .specify/learnings/bicep-learnings.md

# Windows PowerShell
Get-Content .specify/learnings/bicep-learnings.md | Select-Object -Index 44
```

2. **Compare the two entries:**
- Does the new entry provide additional details?
- Is the wording clearer or more actionable?
- Does it cover a different aspect of the same issue?

3. **If consolidating, merge the information:**

```markdown
<!-- BEFORE: Two similar entries -->
[2025-01-10T00:00:00Z] Security Key Vault access → Enable RBAC → Use enableRbacAuthorization
[2025-01-15T00:00:00Z] Security Key Vault without RBAC → Use RBAC authorization → Set enableRbacAuthorization: true in properties

<!-- AFTER: Consolidated entry (keep most complete version) -->
[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in Key Vault properties, removes legacy access policies
```

4. **Remove the duplicate line** and save.

**See also:** 
- [Quickstart Guide - Avoiding Duplicates](../../specs/004-bicep-learnings-database/contracts/quickstart.md#avoiding-duplicates)
- [Format Contract - Duplicate Detection](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#duplicate-detection)

---

#### Warning: Insufficient Context in Entry

**Symptoms:**
```
WARNING: Insufficient context at line 73 (context: "error")
Entry lacks specific details - consider expanding or removing
```

**Cause:** The entry's context field is too generic or vague:
- Single-word context (e.g., "error", "failure")
- Context <10 characters
- Generic phrases that don't identify the specific scenario

**Why this matters:** Vague entries don't help future generations because the system can't match them to specific error scenarios.

**Solution:**

1. **Review the entry** at the indicated line.

2. **Expand the context** to be specific:

```markdown
<!-- ❌ BAD: Too vague -->
[2025-01-15T00:00:00Z] Security error → Use RBAC → Enable RBAC authorization

<!-- ✅ GOOD: Specific context -->
[2025-01-15T00:00:00Z] Security Key Vault access without RBAC → Enable RBAC authorization mode → Use 'enableRbacAuthorization: true' in properties

<!-- ❌ BAD: Generic -->
[2025-01-15T00:00:00Z] Networking subnet → Fix config → Update settings

<!-- ✅ GOOD: Specific scenario -->
[2025-01-15T00:00:00Z] Networking Subnet without NSG attached → Attach Network Security Group → Reference NSG resource ID in subnet properties
```

3. **Ask yourself:**
- Would someone else understand the specific problem from the context?
- Does it identify the exact resource type and issue?
- Is it searchable/matchable?

4. **Either fix the entry or remove it** if it can't be made specific.

**See also:** [Quickstart Guide - Examples of Bad Manual Entries](../../specs/004-bicep-learnings-database/contracts/quickstart.md#examples)

---

#### Issue: Learnings Not Being Applied in Generation

**Symptoms:**
- Learnings database loads without warnings
- But generated templates don't reflect the learnings
- Expected fixes not appearing in output

**Diagnosis:**

```bash
# Check if learnings are loading
specify bicep generate --project-path . --verbose

# Look for log messages like:
# "Loaded X learnings from database"
# "Applied learning: [category] [context]..."
```

**Common Causes & Solutions:**

1. **Context doesn't match the error:**

The learning's context field must match the actual error message or scenario.

```markdown
<!-- If error is: "Missing network security group on subnet" -->

<!-- ❌ Won't match: Context too different -->
[2025-01-15T00:00:00Z] Networking NSG not configured → Attach NSG → Add NSG reference

<!-- ✅ Will match: Context similar to error -->
[2025-01-15T00:00:00Z] Networking Subnet without NSG attached → Attach Network Security Group → Reference NSG resource ID in subnet properties
```

**Fix:** Update context to match actual error messages in your project.

2. **Wrong category for the issue:**

The learning must use a [canonical category](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#canonical-categories) that matches the resource type.

```markdown
<!-- ❌ Storage Account issue with wrong category -->
[2025-01-15T00:00:00Z] Compute Storage Account access → Enable RBAC → Use RBAC authorization

<!-- ✅ Correct category -->
[2025-01-15T00:00:00Z] Data Services Storage Account access → Enable RBAC → Use RBAC authorization
```

**Fix:** Use the correct category (Security, Compliance, Networking, Data Services, Compute, Configuration, Operations, Cost).

3. **Category priority conflict:**

Security and Compliance categories override all others. If multiple learnings match, only the highest priority applies.

```markdown
<!-- Both entries match, but Security wins -->
[2025-01-15T00:00:00Z] Security Key Vault access → Enable RBAC → Use RBAC authorization
[2025-01-15T00:00:00Z] Configuration Key Vault access → Set access policy → Define access policies in properties
<!-- ⚠️ Only Security entry will be applied -->
```

**Fix:** Ensure you have the right category priority for your use case. See [Format Contract - Conflict Resolution](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#conflict-resolution).

4. **Performance: Too many learnings (250+ entries):**

At 250+ entries, category filtering is enabled automatically. Only learnings matching the resource category are considered.

```bash
# Check entry count
wc -l .specify/learnings/bicep-learnings.md  # Linux/macOS
(Get-Content .specify/learnings/bicep-learnings.md).Count  # Windows PowerShell
```

**Fix:** If you have 250+ entries:
- Ensure learnings use correct categories
- Consider consolidating duplicate or outdated entries
- Archive obsolete learnings (move to `.specify/learnings/archive/`)

**See also:**
- [Format Contract - Integration with Commands](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#integration-with-commands)
- [Format Contract - Performance Budgets](../../specs/004-bicep-learnings-database/contracts/learnings-format.md#performance-budgets)

---

## Deployment Issues

### Issue: Deployment Fails with Permission Error

**Symptoms:**
```
ERROR: The client '...' does not have authorization to perform action
'Microsoft.Resources/deployments/write'
```

**Solution:**

```bash
# Check current permissions
az role assignment list \
  --assignee $(az account show --query user.name -o tsv) \
  --resource-group my-rg

# Required roles for deployment:
# - Contributor (for resource creation)
# - User Access Administrator (for RBAC assignments)

# Request access from subscription administrator
# Or use service principal with proper permissions
```

---

### Issue: Resource Already Exists

**Symptoms:**
```
ERROR: Resource 'storageaccount123' already exists in resource group
```

**Solutions:**

1. **Use incremental deployment mode:**
```bash
specify bicep deploy \
  --mode incremental \
  --template-dir ./bicep-templates \
  --resource-group my-rg
```

2. **Update existing resources:**
```bash
specify bicep update \
  --template-dir ./bicep-templates \
  --resource-group my-rg \
  --merge-existing
```

3. **Delete and recreate (CAUTION!):**
```bash
# DANGER: This will delete data!
az group delete --name my-rg --yes
az group create --name my-rg --location eastus

specify bicep deploy \
  --template-dir ./bicep-templates \
  --resource-group my-rg
```

---

### Issue: Deployment Timeout

**Symptoms:**
```
ERROR: Deployment timed out waiting for resources to provision
```

**Solution:**

```bash
# Increase deployment timeout
specify bicep deploy \
  --timeout 1800 \
  --template-dir ./bicep-templates \
  --resource-group my-rg

# Deploy in stages
specify bicep deploy \
  --stage infrastructure \
  --template-dir ./bicep-templates \
  --resource-group my-rg

specify bicep deploy \
  --stage applications \
  --template-dir ./bicep-templates \
  --resource-group my-rg \
  --wait-for infrastructure
```

---

## Performance Issues

### Issue: Slow Analysis

**Symptoms:**
- Analysis takes > 5 minutes for small projects

**Solutions:**

```bash
# Enable caching
specify bicep analyze \
  --enable-cache \
  --cache-dir ./.bicep-cache \
  --project-path .

# Exclude large directories
specify bicep analyze \
  --exclude "**/node_modules/**" \
  --exclude "**/.git/**" \
  --exclude "**/venv/**"

# Use parallel processing
specify bicep analyze \
  --parallel \
  --workers 4 \
  --project-path .
```

---

### Issue: High Memory Usage

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solutions:**

```bash
# Reduce batch size
specify bicep analyze \
  --batch-size 100 \
  --project-path ./large-project

# Stream processing mode
specify bicep analyze \
  --streaming \
  --project-path ./large-project

# Clear cache
specify bicep clear-cache --all
```

---

### Issue: Cache Issues

**Symptoms:**
- Stale analysis results
- Incorrect resource detection

**Solution:**

```bash
# Clear cache
specify bicep clear-cache --all

# Disable cache temporarily
specify bicep analyze \
  --no-cache \
  --project-path .

# Rebuild cache
specify bicep rebuild-cache \
  --project-path .
```

---

## Security Issues

### Issue: Credential Exposure Warning

**Symptoms:**
```
WARNING: Potential credential found in analysis
File: config.json, Line: 42
```

**Solution:**

```bash
# Scan for credentials
specify bicep security-scan \
  --project-path . \
  --fix-credentials

# Use Azure Key Vault
specify bicep generate \
  --use-keyvault \
  --keyvault-name my-keyvault \
  --analysis-file ./analysis/project-analysis.json

# Exclude sensitive files from analysis
specify bicep analyze \
  --exclude "**/*.secret" \
  --exclude "**/credentials.json" \
  --project-path .
```

---

### Issue: Insecure Template Generated

**Symptoms:**
```
WARNING: Template contains security issues:
- Public access enabled on storage account
- HTTPS not enforced
```

**Solution:**

```bash
# Enable security hardening
specify bicep generate \
  --security-level high \
  --analysis-file ./analysis/project-analysis.json

# Fix security issues
specify bicep security \
  --template-dir ./bicep-templates \
  --auto-fix \
  --severity high,critical

# Generate with compliance framework
specify bicep generate \
  --compliance CIS-Azure-v1.4.0 \
  --analysis-file ./analysis/project-analysis.json
```

---

## Debugging Tips

### Enable Verbose Logging

```bash
# Maximum verbosity
specify bicep analyze \
  --verbose \
  --debug \
  --log-file debug.log \
  --project-path .

# View logs in real-time
tail -f debug.log
```

### Use Dry Run Mode

```bash
# Preview operations without executing
specify bicep generate \
  --dry-run \
  --analysis-file ./analysis/project-analysis.json

specify bicep deploy \
  --dry-run \
  --template-dir ./bicep-templates \
  --resource-group my-rg
```

### Check System Requirements

```bash
# Run diagnostic check
specify bicep check-requirements

# Test Azure connectivity
specify bicep test-connection \
  --subscription-id xxx-xxx-xxx
```

### Validate Configuration

```bash
# Validate configuration file
specify bicep validate-config \
  --config-file bicep_config.json

# Show effective configuration
specify bicep show-config \
  --merged
```

### Export Diagnostic Information

```bash
# Generate diagnostic report
specify bicep diagnostics \
  --output diagnostic-report.json

# Include in bug reports
cat diagnostic-report.json
```

## Getting Help

If you're still experiencing issues:

1. **Check GitHub Issues**: [spec-kit-4applens/issues](https://github.com/cristhianu/spec-kit-4applens/issues)

2. **Search Documentation**: [Full Documentation](./README.md)

3. **Enable Debug Mode**: Include `--debug --verbose` output in bug reports

4. **Provide Context**:
   - Operating System
   - Python version
   - Azure CLI version
   - Bicep CLI version
   - Full error message
   - Steps to reproduce

5. **Create Minimal Reproduction**: Simplify to smallest case that reproduces the issue

## Additional Resources

- [User Guide](./user-guide.md)
- [API Reference](./api-reference.md)
- [Architecture Guide](./architecture.md)
- [Azure Bicep Documentation](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
