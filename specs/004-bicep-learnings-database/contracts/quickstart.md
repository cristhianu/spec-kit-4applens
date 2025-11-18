# Learnings Database Quickstart Guide

**Feature**: 004-bicep-learnings-database  
**Audience**: Developers who want to manually add, edit, or review learnings  
**Last Updated**: 2025-11-01  
**Version**: 1.0

## Overview

The **Learnings Database** is a shared knowledge base that helps your team avoid repeated mistakes when generating Bicep templates. Both `/speckit.bicep` (generation) and `/speckit.validate` (validation) commands reference this database to apply accumulated wisdom automatically.

### What You Can Do

- ✅ **Add new learnings** from external sources (docs, blogs, team knowledge)
- ✅ **Edit existing entries** for clarity or updates
- ✅ **Remove obsolete entries** that no longer apply
- ✅ **Review learnings** to understand patterns your team has discovered

### How It Works

```
┌──────────────────────┐
│  Manual/Automated    │
│  Entry Addition      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────┐
│  .specify/learnings/             │
│  bicep-learnings.md              │
│                                  │
│  [Timestamp] Category Context    │
│  → Issue → Solution              │
└──────────┬───────────────────────┘
           │
           ├─────────────┬─────────────┐
           ▼             ▼             ▼
    ┌──────────┐  ┌───────────┐  ┌──────────┐
    │ /speckit │  │ /speckit  │  │ Future   │
    │  .bicep  │  │ .validate │  │ Commands │
    └──────────┘  └───────────┘  └──────────┘
```

## Quick Start

### 1. Locate the File

The learnings database is stored at:

```
.specify/learnings/bicep-learnings.md
```

**Open it**:

```bash
# VS Code
code .specify/learnings/bicep-learnings.md

# Notepad (Windows)
notepad .specify\learnings\bicep-learnings.md

# Nano (Linux/Mac)
nano .specify/learnings/bicep-learnings.md
```

### 2. Understand the Format

Each learning follows this structure:

```
[TIMESTAMP] CATEGORY CONTEXT → ISSUE → SOLUTION
```

**Example**:

```markdown
[2025-11-01T10:30:00Z] Security Key Vault access → Missing 'accessPolicies' property → Add access policies with tenant ID and object ID
```

**Breakdown**:

| Component | Value | Explanation |
|-----------|-------|-------------|
| **Timestamp** | `2025-11-01T10:30:00Z` | When this learning was discovered (ISO 8601 UTC) |
| **Category** | `Security` | Which architectural domain it applies to |
| **Context** | `Key Vault access` | When/where to apply this learning |
| **Issue** | `Missing 'accessPolicies' property` | What problem to avoid |
| **Solution** | `Add access policies with tenant ID and object ID` | How to fix or prevent it |

### 3. Add Your First Entry

**Scenario**: You learned from Microsoft docs that Storage Accounts should disable public access.

**Step 1**: Open the file and find the `## Security` section.

**Step 2**: Add a new line with your learning:

```markdown
## Security

[2025-11-01T14:00:00Z] Security Storage Account public access → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and use Private Endpoints
```

**Step 3**: Save the file.

**Step 4**: Test it works:

```bash
specify bicep "create a storage account"
```

Verify the generated template includes `publicNetworkAccess: 'Disabled'`.

## Entry Format Rules

### Required Fields

All five components are required:

1. **Timestamp** - ISO 8601 UTC format: `[YYYY-MM-DDTHH:MM:SSZ]`
2. **Category** - One of the canonical categories (see below)
3. **Context** - Max 100 characters
4. **Issue** - Max 150 characters
5. **Solution** - Max 200 characters

### Separator

Use the arrow symbol `→` (RIGHT ARROW, Unicode U+2192) between components:

- ✅ `CONTEXT → ISSUE → SOLUTION`
- ❌ `CONTEXT -> ISSUE -> SOLUTION` (wrong: ASCII arrow)
- ❌ `CONTEXT — ISSUE — SOLUTION` (wrong: em dash)

**Tip**: Copy the arrow from an existing entry or type it:

- **Windows**: `Alt + 26` (on numpad) or copy from existing entry
- **Mac**: `Option + Shift + Right Arrow` or copy from existing entry
- **Linux**: `Ctrl + Shift + U` then type `2192` and press Enter

### Character Limits

| Field | Max Length | Why |
|-------|------------|-----|
| Context | 100 chars | Keep it specific but brief |
| Issue | 150 chars | Describe problem clearly |
| Solution | 200 chars | Provide actionable guidance |
| **Total** | **500 chars** | Entire entry including separators |

**What happens if you exceed?**

- During manual editing: Warning logged when file loads (entry still used)
- During automated append: Entry rejected immediately

## Canonical Categories

Your learning MUST use one of these categories:

### High Priority (Override All Others)

| Category | Use For |
|----------|---------|
| **Security** | Authentication, authorization, encryption, secrets, RBAC, TLS |
| **Compliance** | Regulatory requirements, audit trails, SFI best practices, data residency |

### Normal Priority

| Category | Use For |
|----------|---------|
| **Networking** | VNets, subnets, Private Endpoints, DNS, routing, firewall |
| **Data Services** | Storage Accounts, Cosmos DB, SQL Database, Redis Cache |
| **Compute** | App Services, Functions, Container Apps, AKS |
| **Configuration** | Resource properties, API versions, deployment settings, naming |
| **Operations** | Monitoring, logging, diagnostics, quotas, error handling |
| **Cost** | Resource sizing, optimization, SKU selection |

**Conflict Resolution**: If two entries contradict, Security/Compliance wins regardless of timestamp. Otherwise, most recent timestamp wins.

## Examples

### Good Entries ✅

**Security - Managed Identity**:

```markdown
[2025-11-01T10:00:00Z] Security Managed Identity → Using service principal secrets in code → Use system-assigned managed identity instead
```

**Compliance - Diagnostic Logs**:

```markdown
[2025-11-01T11:00:00Z] Compliance Diagnostic logs → Logs not exported to centralized location → Enable diagnostic settings with Log Analytics workspace
```

**Networking - Network Isolation**:

```markdown
[2025-11-01T12:00:00Z] Networking Network isolation → Resources deployed with public endpoints → Deploy all resources to VNet with private endpoints
```

**Data Services - Cosmos DB Throughput**:

```markdown
[2025-11-01T13:00:00Z] Data Services Cosmos DB throughput → Container deployed without throughput → Set options.throughput property (min 400 RU/s)
```

**Configuration - Naming Convention**:

```markdown
[2025-11-01T14:00:00Z] Configuration Resource naming → Inconsistent naming across environments → Use naming convention: <app>-<resource>-<env> (e.g., myapp-storage-dev)
```

### Bad Entries ❌

**Missing Timestamp**:

```markdown
Security Key Vault → Issue → Solution
```

❌ **Problem**: No timestamp means can't resolve conflicts.

---

**Invalid Category**:

```markdown
[2025-11-01T10:00:00Z] MyCustomCategory Context → Issue → Solution
```

❌ **Problem**: `MyCustomCategory` not in canonical list.

---

**Context Too Long** (114 chars):

```markdown
[2025-11-01T10:00:00Z] Security This is a very long context that describes the situation in excruciating detail beyond one hundred characters → Issue → Solution
```

❌ **Problem**: Context exceeds 100 character limit.

---

**Wrong Separator**:

```markdown
[2025-11-01T10:00:00Z] Security Context -> Issue -> Solution
```

❌ **Problem**: Using `->` instead of `→`.

---

**Too Vague**:

```markdown
[2025-11-01T10:00:00Z] Security Stuff → Error → Fix it
```

❌ **Problem**: Not specific enough to be useful.

## Common Use Cases

### Use Case 1: Learning from Microsoft Docs

**Scenario**: You read in Microsoft docs that Key Vault should use RBAC instead of access policies.

**Action**:

1. Open `.specify/learnings/bicep-learnings.md`
2. Navigate to `## Security` section
3. Add entry:

```markdown
[2025-11-01T15:00:00Z] Security Key Vault authorization → Using legacy access policies → Use Azure RBAC with 'enableRbacAuthorization: true' instead
```

4. Save and test with `/speckit.bicep`

### Use Case 2: Team Architectural Decision

**Scenario**: Your team decided to standardize on Azure SQL Managed Instance instead of Azure SQL Database for all new projects.

**Action**:

1. Open `.specify/learnings/bicep-learnings.md`
2. Navigate to `## Data Services` section
3. Add entry:

```markdown
[2025-11-01T16:00:00Z] Data Services SQL deployment → Using Azure SQL Database → Use Azure SQL Managed Instance for better feature set and migration compatibility
```

4. Save - now all future generations will prefer Managed Instance

### Use Case 3: Fixing Obsolete Entry

**Scenario**: An old entry says "Use API version 2021-01-01" but 2024-01-01 is now stable.

**Action**:

1. Open `.specify/learnings/bicep-learnings.md`
2. Find the obsolete entry:

```markdown
[2023-06-15T10:00:00Z] Configuration Storage Account API → Old API version used → Use API version 2021-01-01
```

3. **Option A**: Update the entry (keep timestamp to preserve history):

```markdown
[2023-06-15T10:00:00Z] Configuration Storage Account API → Old API version used → Use API version 2024-01-01 (updated 2025-11-01)
```

4. **Option B**: Delete old entry and add new one:

```markdown
[2025-11-01T17:00:00Z] Configuration Storage Account API → Outdated API version → Use API version 2024-01-01 for latest features
```

5. Save - future generations will use the updated API version

### Use Case 4: Consolidating Duplicates

**Scenario**: You find two similar entries about the same topic.

**Existing Entries**:

```markdown
[2025-09-01T10:00:00Z] Security Key Vault → Missing network rules → Add network rules to restrict access
[2025-10-15T14:00:00Z] Security Key Vault networking → Public access enabled → Disable public network access
```

**Action**:

1. Review both entries
2. Consolidate into single, comprehensive entry:

```markdown
[2025-11-01T18:00:00Z] Security Key Vault network access → Public network access enabled → Set publicNetworkAccess: 'Disabled' and configure Private Endpoint
```

3. Delete the two old entries
4. Save - cleaner database, better guidance

## Avoiding Duplicates

The system automatically checks for duplicates when appending entries (60% similarity threshold). For manual editing:

### Before Adding

**Ask yourself**:

1. Does similar guidance already exist in this category?
2. Am I adding new information or repeating existing knowledge?
3. Could I enhance an existing entry instead of adding new one?

### Check Manually

```bash
# Search for related entries
grep -i "key vault" .specify/learnings/bicep-learnings.md

# Or on Windows PowerShell
Select-String -Path .specify/learnings/bicep-learnings.md -Pattern "key vault" -CaseSensitive:$false
```

### Similarity Rules

The system considers entries duplicates if they're >60% similar:

- ✅ **Different topics**: "Key Vault access policies" vs "Storage Account encryption"
- ❌ **Same topic, different wording**: "Missing Key Vault access policies" vs "Key Vault access policies not configured"

## Testing Your Changes

After editing the learnings database, verify it works:

### Test 1: Load Without Errors

```bash
specify bicep "test"
```

**Expected**: No warnings about invalid format or unparseable entries.

### Test 2: Verify Learning Applied

```bash
specify bicep "create storage account with private endpoint"
```

**Expected**: Generated template follows your learnings (e.g., `publicNetworkAccess: 'Disabled'`).

### Test 3: Check Validation

```bash
specify validate
```

**Expected**: Validation rules align with your learnings.

## Troubleshooting

### Warning: "Cannot parse timestamp at line X"

**Cause**: Timestamp format is invalid.

**Fix**: Use ISO 8601 UTC format: `[YYYY-MM-DDTHH:MM:SSZ]`

**Example**:

```markdown
# Wrong
[2025-11-01 10:30:00] Security ...

# Right
[2025-11-01T10:30:00Z] Security ...
```

### Warning: "Unknown category 'X' at line Y"

**Cause**: Category not in canonical list.

**Fix**: Use one of these: Security, Compliance, Networking, Data Services, Compute, Configuration, Operations, Cost

**Example**:

```markdown
# Wrong
[2025-11-01T10:30:00Z] Database ...

# Right
[2025-11-01T10:30:00Z] Data Services ...
```

### Warning: "Context too long (X chars, max 100)"

**Cause**: Context field exceeds 100 characters.

**Fix**: Shorten the context to be more concise.

**Example**:

```markdown
# Wrong (114 chars)
[2025-11-01T10:30:00Z] Security Azure Key Vault deployment with private endpoint and custom DNS configuration for secure access ...

# Right (89 chars)
[2025-11-01T10:30:00Z] Security Key Vault with private endpoint and DNS → Issue → Solution
```

### Entry Not Being Applied

**Possible Causes**:

1. **Wrong category**: Entry in wrong section
2. **Context mismatch**: Context doesn't match user's request
3. **Newer conflicting entry**: Another entry overrides it
4. **Invalid format**: Entry skipped due to warnings

**Debug Steps**:

1. Check file loads without warnings
2. Verify category is correct
3. Check for conflicting entries with newer timestamps
4. Ensure format follows specification exactly

## Best Practices

### ✅ DO

- **Be specific**: "Key Vault access policies" not just "Key Vault"
- **Be actionable**: "Set publicNetworkAccess: 'Disabled'" not "Fix networking"
- **Include examples**: "Use naming: <app>-<resource>-<env>"
- **Keep current**: Update obsolete entries regularly
- **Test changes**: Verify learnings are applied after editing
- **Use timestamps**: Always include current UTC timestamp

### ❌ DON'T

- **Be vague**: "Stuff → Error → Fix it"
- **Write essays**: Keep within character limits
- **Use wrong separators**: Stick to `→` not `->`
- **Add duplicates**: Check existing entries first
- **Skip testing**: Always verify your changes work
- **Ignore warnings**: Fix format issues promptly

## Advanced Topics

### Category Priority

Security and Compliance entries override all others:

**Example**:

```markdown
# Entry A (older, but Security category)
[2025-09-01T10:00:00Z] Security Front Door → Avoid by default → Only use when explicitly requested

# Entry B (newer, but Networking category)
[2025-11-01T14:00:00Z] Networking Front Door → Use for global distribution → Deploy with WAF enabled
```

**Result**: Entry A wins (Security overrides Networking).

### Performance at Scale

- **Up to 200 entries**: Full load, no filtering (< 2 seconds)
- **200-250 entries**: Warning logged, still full load
- **250+ entries**: Category-based filtering enabled automatically

**Recommendation**: If database grows large, consider:

1. Removing obsolete entries
2. Consolidating similar entries
3. Splitting into separate files (future enhancement)

### Integration with CI/CD

**Scenario**: You want to enforce learnings in your deployment pipeline.

**Action**:

1. Commit `.specify/learnings/bicep-learnings.md` to version control
2. Add validation step to CI pipeline:

```yaml
# Azure Pipelines example
- script: |
    specify validate
  displayName: 'Validate Bicep templates against learnings'
```

3. Fail builds if validation finds violations

## Related Documentation

- **Format Contract**: `specs/004-bicep-learnings-database/contracts/learnings-format.md` - Complete technical specification
- **Feature Spec**: `specs/004-bicep-learnings-database/spec.md` - Overall feature design
- **Validation Guide**: (T037) - Understanding validation warnings and errors
- **Phase 4 Complete**: `PHASE-4-COMPLETE.md` - Automated capture implementation

## Getting Help

**Issues with format?** → Check the format contract: `specs/004-bicep-learnings-database/contracts/learnings-format.md`

**Entry not being applied?** → Enable debug logging and check for format warnings

**Found a bug?** → Report in project issues with example entry and expected behavior

---

**Last Updated**: 2025-11-01  
**Next Review**: 2026-01-01  
**Feedback**: Create an issue in the project repository
