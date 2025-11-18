# Learnings Database Format Specification

**Feature**: 004-bicep-learnings-database  
**Version**: 1.0.0  
**Status**: Draft  
**Purpose**: Define strict format validation rules for `.specify/learnings/bicep-learnings.md` entries

---

## Entry Format

### Structure

Each learning entry MUST follow this exact format:

```
[Timestamp] [Category] [Context/Resource] → [Issue] → [Solution/Pattern]
```

### Field Specifications

| Field | Required | Format | Max Length | Validation Rules |
|-------|----------|--------|------------|------------------|
| **Timestamp** | Yes | ISO 8601 in brackets: `[YYYY-MM-DDTHH:MM:SSZ]` | ~25 chars | Must parse as valid UTC timestamp, enclosed in `[ ]` |
| **Category** | Yes | Alphanumeric + spaces | 20 chars | Must match canonical category list (see below) |
| **Context/Resource** | Yes | Free text | 100 chars | Must identify Azure resource type or scenario |
| **Issue** | Yes | Free text | 150 chars | Must describe problem/anti-pattern to avoid |
| **Solution/Pattern** | Yes | Free text | 200 chars | Must provide actionable guidance |

**Total Entry Length**: Maximum 500 characters (including separators `→`)

### Example Valid Entry

```
[2025-10-31T14:23:00Z] Security Azure Storage → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and use Private Endpoints
```

---

## Canonical Category Taxonomy

### Priority Categories (Override all others in conflict resolution)

- **Security**: Authentication, authorization, encryption, network security
- **Compliance**: Regulatory requirements, audit trails, data residency

### Standard Categories

- **Networking**: VNet, subnets, Private Endpoints, DNS, routing
- **Data Services**: Storage Accounts, Cosmos DB, SQL Database, Redis Cache
- **Compute**: App Services, Functions, Container Apps, AKS
- **Configuration**: Resource properties, API versions, deployment settings
- **Performance**: Scaling, throughput, quotas, resource limits
- **Operations**: Monitoring, logging, diagnostics, error handling

### Extensibility Rules

1. New categories MAY be added via manual editing of the learnings database
2. New categories MUST be added to this list for validation purposes
3. Category names MUST be unique (case-insensitive)
4. Categories SHOULD represent distinct architectural domains

---

## Timestamp Format

### ISO 8601 UTC Format with Brackets

- **Format**: `[YYYY-MM-DDTHH:MM:SSZ]` (enclosed in square brackets)
- **Example**: `[2025-10-31T14:23:00Z]`
- **Timezone**: Always UTC (denoted by `Z` suffix)
- **Precision**: Seconds (no milliseconds)
- **Brackets**: Required for parser to identify timestamp boundary

### Generation Rules

- **Automatic append**: System generates timestamp at moment of entry creation
- **Manual editing**: User SHOULD use current UTC time when adding entries manually  
  - Can use simplified time like `[2025-01-15T00:00:00Z]` for manual entries
- **Conflict resolution**: Most recent timestamp wins (unless category priority overrides)

---

## Conflict Resolution Priority

### Resolution Logic

When two learning entries conflict (contradict each other):

1. **Check category priority**: Security/Compliance categories override all others
2. **Check timestamp**: Most recent timestamp wins within same priority tier
3. **Tie-breaker**: If timestamps identical, first entry in file wins

### Category Priority Levels

| Priority Level | Categories | Behavior |
|----------------|------------|----------|
| **HIGH** | Security, Compliance | Override all other categories regardless of timestamp |
| **NORMAL** | All other categories | Resolved by timestamp (most recent wins) |

### Example Conflict Resolution

```
Entry A: [2025-10-15T10:00:00Z] Networking Azure Front Door → Use for global distribution → Deploy with WAF enabled
Entry B: [2025-10-31T14:00:00Z] Security Azure Front Door → Avoid by default → Only include when explicitly requested for security reasons
```

**Resolution**: Entry B wins (Security category overrides Networking, even though it's more recent)

---

## Validation Rules

### Loading Time Validation (Non-Fatal)

- Malformed entries during database load: Log warning, skip entry, continue loading
- Allows manual editing mistakes to not break the entire system
- Warning message SHOULD include line number and entry preview

### Append Time Validation (Fatal)

- Malformed entries during append operation: Reject immediately, raise `ValueError`
- Prevents automatic capture from polluting database with invalid entries
- Error message MUST include specific field that failed validation

### Format Validation Checks

1. **Timestamp**: Valid ISO 8601 format, parseable as datetime
2. **Category**: Matches canonical list (case-insensitive), within length limit
3. **Field lengths**: No field exceeds max length
4. **Separator presence**: Contains exactly 2 arrow separators (`→`)
5. **Total length**: Entry ≤ 500 characters

---

## Duplicate Detection

### Algorithm: TF-IDF + Cosine Similarity

When appending new entries, the system checks for duplicates using semantic similarity:

1. **Text Vectorization**: Convert new entry and all existing entries to TF-IDF vectors
2. **Similarity Calculation**: Compute cosine similarity between new entry and each existing entry
3. **Threshold Comparison**: If any similarity score exceeds threshold, reject as duplicate

### Similarity Threshold

**Default**: 60% similarity (0.6 cosine similarity)

**Rationale**:
- Too low (e.g., 40%): Blocks legitimate variations
- Too high (e.g., 80%): Allows near-duplicates
- 60%: Balances specificity and flexibility

**Implementation**: `src/specify_cli/utils/learnings_loader.py::check_duplicate_entry()`

### Duplicate Behavior

**If Duplicate Detected** (similarity > 60%):
- Reject new entry (do not append)
- Log warning with matched entry and similarity score
- Return existing entry for reference

**If No Duplicate** (all similarities ≤ 60%):
- Append new entry to appropriate category section
- Add automatic timestamp if not present
- Validate format before writing

### Insufficient Context Detection

Entries lacking sufficient context are rejected:

**Rejection Criteria**:
- Error message < 10 characters
- Single-word generic errors only ("error", "failed", "failure")

**Example**:
```
# Rejected - too short
"Error" → insufficient context

# Rejected - single-word generic
"failed" → insufficient context

# Accepted - sufficient detail
"Deployment failed: Missing property 'sku'" → sufficient context
```

**Implementation**: `src/specify_cli/utils/learnings_loader.py::check_insufficient_context()`

---

## Performance Budgets

Operations MUST complete within these time limits:

| Operation | Budget | Consequence if Exceeded |
|-----------|--------|-------------------------|
| Load database (250 entries) | 2 seconds | Log warning, continue |
| Append single entry | 100 ms | Log warning, continue |
| Check duplicate entry | 500 ms | Raise PerformanceError |

### Scale Behavior (250+ entries)

- At 200 entries: Log warning about approaching limit
- At 250+ entries: Enable category filtering to maintain performance
- Duplicate checking uses optimized vectorization for large datasets

---

## Error Classification Keywords

### Capture (Structural Errors - Worth Learning)

Append entry when error message contains these keywords:

- `missing property`
- `invalid value`
- `quota exceeded`
- `already exists`
- `not found`
- `unauthorized`
- `forbidden`
- `conflict`
- `bad request`

### Ignore (Transient Errors - Not Worth Learning)

Do NOT append entry when error message contains these keywords:

- `throttled`
- `timeout`
- `unavailable`
- `service unavailable`
- `gateway timeout`
- `too many requests`

### Keyword Matching Algorithm

- **Case-insensitive**: Convert error message and keywords to lowercase before comparison
- **Substring match**: Keyword can appear anywhere in error message
- **First match wins**: Stop checking once first keyword match found
- **Priority**: Check "Ignore" keywords first, then "Capture" keywords

**Implementation**: `src/specify_cli/utils/learnings_loader.py::classify_error()`

---

## Manual Editing Guidelines

### When to Add Entries Manually

1. **External Knowledge**: Learnings from Microsoft documentation, blog posts, or team expertise
2. **Architectural Decisions**: Patterns chosen for consistency across projects
3. **Best Practices**: Industry standards not discovered through errors
4. **Preventive Guidance**: Avoiding issues before they occur

### How to Add Entries Manually

**Step 1**: Open the file

```bash
# Open in VS Code
code .specify/learnings/bicep-learnings.md

# Or use any text editor
notepad .specify/learnings/bicep-learnings.md
```

**Step 2**: Navigate to appropriate category section

**Step 3**: Add entry using format:

```markdown
[YYYY-MM-DDTHH:MM:SSZ] CATEGORY CONTEXT → ISSUE → SOLUTION
```

**Step 4**: Verify format:

- Timestamp is valid ISO 8601 UTC
- Category is canonical
- Context ≤ 100 chars
- Issue ≤ 150 chars
- Solution ≤ 200 chars
- Uses → separator

**Step 5**: Save and test

```bash
# Test with bicep generation
specify bicep "create storage account"

# Verify learning is applied
```

### Examples of Good Manual Entries

```markdown
[2025-11-01T10:00:00Z] Security Managed Identity → Using service principal secrets in code → Use system-assigned managed identity instead
[2025-11-01T11:00:00Z] Compliance Diagnostic logs → Logs not exported to centralized location → Enable diagnostic settings with Log Analytics workspace
[2025-11-01T12:00:00Z] Networking Network isolation → Resources deployed with public endpoints → Deploy all resources to VNet with private endpoints
[2025-11-01T13:00:00Z] Configuration Resource naming → Inconsistent naming across environments → Use naming convention: <app>-<resource>-<env>
```

### Examples of Bad Manual Entries

```markdown
# Missing timestamp
Security Key Vault → Issue → Solution

# Invalid category
[2025-11-01T10:00:00Z] InvalidCategory Context → Issue → Solution

# Context too long (>100 chars)
[2025-11-01T10:00:00Z] Security This is a very long context that exceeds one hundred characters → Issue → Solution

# Using wrong separator
[2025-11-01T10:00:00Z] Security Context -> Issue -> Solution

# Too vague
[2025-11-01T10:00:00Z] Security Stuff → Error → Fix it
```

---

## Integration with Commands

### `/speckit.bicep` Command

**Load Phase**:

1. Check if `.specify/learnings/bicep-learnings.md` exists
2. Parse file and extract all valid entries
3. Log warnings for invalid entries (continue with valid ones)
4. Store entries in memory for generation

**Generation Phase**:

1. Match context patterns against user requirements
2. Apply relevant learnings to template generation
3. Prioritize Security/Compliance category entries
4. Use most recent entry for conflicts

**Error Capture Phase** (if deployment fails):

1. Classify error (CAPTURE vs IGNORE keywords)
2. Check insufficient context criteria
3. Extract learning components (category, context, issue, solution)
4. Check duplicates (60% threshold)
5. Append to database if not duplicate

### `/speckit.validate` Command

**Load Phase**:

1. Same as `/speckit.bicep` command
2. Used for validation logic and fix suggestions

**Validation Phase**:

1. Apply learnings to validation rules
2. Check if deployed resources follow guidance
3. Report violations with learning references

**Error Capture Phase** (if validation fails):

1. Classify validation failure (structural vs transient)
2. Extract failure context (validation phase, resource type, project name)
3. Generate learning entry with phase-aware solution
4. Check duplicates and append if unique

---

## File Structure

### Category Headers

Categories SHOULD be organized with Markdown headers for human readability:

```markdown
## Security

[2025-10-31T14:23:00Z] Security Azure Storage → Public network access enabled → Set publicNetworkAccess: 'Disabled'

## Networking

[2025-10-30T09:15:00Z] Networking Azure VNet → Default subnet too large → Use /24 subnets for better IP management
```

### Optional Metadata

Entries MAY include optional metadata fields:

- `lastVerified`: ISO 8601 timestamp of last manual verification (future enhancement)
- `source`: `auto` (system-captured) or `manual` (user-added) - for analytics

**Note**: Optional fields are NOT required for Phase 1 implementation.

---

## Secure Future Initiative (SFI) Best Practices

### SFI Patterns to Capture

Learning entries SHOULD capture these SFI-compliant patterns:

1. **Network Isolation**: All resources deployed within same VNet with proper subnet segmentation
2. **No Public Endpoints**: `publicNetworkAccess: 'Disabled'` for all data services (Storage, Key Vault, databases)
3. **Private Link Connectivity**: Use Private Endpoints for all service-to-service communication
4. **Managed Identity**: Avoid connection strings, use Managed Identity for authentication
5. **Encryption**: TLS 1.2+ for in-transit, customer-managed keys for at-rest encryption

### Example SFI Learning Entry

```
[2025-10-31T15:00:00Z] Security Azure Key Vault → Public network access not disabled → Set publicNetworkAccess: 'Disabled' and configure Private Endpoint with private DNS zone
```

---

## Version History

- **1.0.0** (2025-10-31): Initial specification created during /speckit.analyze remediation
  - Defined entry format with field specifications
  - Established canonical category taxonomy
  - Documented timestamp format and conflict resolution
  - Specified validation rules (fatal vs non-fatal)
  - Added error classification keywords and matching algorithm
  - Included SFI best practices guidance

- **1.1.0** (2025-11-01): Enhanced specification with Phase 4 and Phase 5 additions
  - Added duplicate detection algorithm (TF-IDF + cosine similarity at 60%)
  - Added insufficient context detection criteria
  - Added performance budgets for operations
  - Added manual editing guidelines with examples
  - Added integration details for `/speckit.bicep` and `/speckit.validate` commands
  - Documented error capture phases for both commands

---

## Related Documents

- [spec.md](../spec.md): Feature specification (FR-003, FR-008, FR-009, FR-011)
- [plan.md](../plan.md): Technical context and constitution check
- [tasks.md](../tasks.md): Implementation tasks (T035, T010, T025, T032-T034)
- [quickstart.md](../quickstart.md): User guide for manual editing (to be created in T036)
- [PHASE-3-COMPLETE.md](../PHASE-3-COMPLETE.md): Phase 3 completion summary
- [PHASE-4-COMPLETE.md](../../PHASE-4-COMPLETE.md): Phase 4 completion summary with automated capture

---

**Contract Compliance**: All implementations MUST adhere to this specification. Deviations require contract update and stakeholder approval.

