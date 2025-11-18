# Feature Specification: Shared Learnings Database for Bicep Generation and Validation

**Feature Branch**: `004-bicep-learnings-database`  
**Created**: October 31, 2025  
**Status**: Draft  
**Input**: User description: "Modify both speckit.bicep and speckit.validate commands to use a common .md file that will contain learnings of previous mistakes, to make sure it doesn't run into those issues in the future. We should separate the existing ones in the main prompt and add them to this file. Both verify and bicep should be appending to this file every time they find an issue with bicep creation or deployment, so that it can be avoided in the future. The entries should be as succinct as possible with just enough details for the agent to understand it and apply it. In addition, do not include Azure Front Door in the architectures by default. Instead of Network Security Perimeter use something else that will also keep communications secure like Private links or Private Endpoints. The architecture should do network isolation by deploying everything to the same network and follow Secure Future Initiative (SFI) best practices."

## Clarifications

### Session 2025-10-31

- Q: When the system encounters a deployment or validation error, how should it classify whether the error is worth capturing as a learning entry? → A: By error message keywords: Capture errors containing "missing property", "invalid value", "quota", "already exists", ignore "throttled", "timeout", "unavailable"
- Q: When appending a new learning entry, how should the system determine if "similar guidance" already exists to prevent duplicates? → A: Semantic similarity: Compare new entry against existing entries; if any share >70% semantic similarity in issue/solution, mark as duplicate
- Q: When the learnings database grows large and may impact performance, at what size should the system take action (implement filtering/pagination)? → A: 250 entries
- Q: When two learning entries contradict each other (e.g., different recommendations for the same scenario), how should the system resolve which guidance to apply? → A: Timestamp + category priority: Use most recent timestamp, but security/compliance entries override others regardless of age
- Q: What is the acceptable maximum time for loading and parsing the learnings database before starting template generation or validation? → A: Under 2 seconds

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Self-Improving Bicep Generation (Priority: P1)

When developers generate Bicep templates using the `/speckit.bicep` command, the agent references a centralized learnings database to avoid previously encountered mistakes and applies best practices automatically.

**Why this priority**: This is the core value proposition - preventing repeated errors and continuously improving template quality without manual intervention. Every template generation benefits from accumulated knowledge.

**Independent Test**: Generate a Bicep template for a scenario that previously caused an error (documented in learnings), and verify the agent applies the correct pattern without making the same mistake. Success is measured by zero occurrences of previously documented errors.

**Acceptance Scenarios**:

1. **Given** a learnings database contains an entry "Never use Network Security Perimeter - use Private Endpoints instead", **When** a developer runs `/speckit.bicep` to generate infrastructure, **Then** the generated templates use Private Endpoints and do not include Network Security Perimeter resources.

2. **Given** a learnings database contains an entry "Avoid Azure Front Door by default - only include when explicitly requested", **When** a developer runs `/speckit.bicep` without specifying Front Door, **Then** the generated architecture excludes Azure Front Door but maintains other traffic management solutions.

3. **Given** a learnings database contains Secure Future Initiative (SFI) best practices for network isolation, **When** a developer runs `/speckit.bicep`, **Then** all generated resources are deployed within the same VNet with proper subnet segmentation and no public endpoints.

---

### User Story 2 - Automated Learning Capture (Priority: P1)

When deployment validation encounters errors or issues during `/speckit.bicep` generation or `/speckit.validate` testing, the system automatically extracts the root cause and appends a succinct learning entry to the shared database.

**Why this priority**: Without automatic capture, the learnings database becomes stale and requires manual maintenance. This ensures continuous improvement without human intervention and captures knowledge at the moment of discovery.

**Independent Test**: Trigger a known deployment error (e.g., missing required property in Cosmos DB template), verify the error is detected, and confirm a new learning entry is added to the database with actionable guidance. Success is measured by presence of new entry with correct format.

**Acceptance Scenarios**:

1. **Given** a Bicep template with a missing `throughput` property for Cosmos DB, **When** deployment fails during `/speckit.validate`, **Then** a new learning entry is appended: "Cosmos DB containers require options.throughput property (min 400 RU/s)".

2. **Given** a deployment failure due to regional quota limits, **When** the error is detected, **Then** a learning entry is added: "Default to non-zone-redundant configurations to avoid regional quota exhaustion".

3. **Given** a Key Vault deployment fails with "VaultAlreadyExists" error, **When** this is detected, **Then** a learning entry is added: "Key Vaults have 90-day soft-delete - purge before redeployment: az keyvault purge --name <name>".

---

### User Story 3 - Learnings Review and Manual Editing (Priority: P2)

Developers can review the accumulated learnings database, manually add entries based on external knowledge sources, edit existing entries for clarity, or remove obsolete entries.

**Why this priority**: While automatic capture is primary, human curation ensures quality, removes duplicates, and incorporates knowledge from documentation updates or architectural decisions that don't result from errors.

**Independent Test**: Open the learnings database file, manually add a new entry about a security best practice, run `/speckit.bicep`, and verify the new guideline is applied in generated templates.

**Acceptance Scenarios**:

1. **Given** a developer learns from Microsoft documentation that a new API version is recommended, **When** they manually add an entry to the learnings database, **Then** subsequent `/speckit.bicep` runs use the recommended API version.

2. **Given** the learnings database contains duplicate or contradictory entries, **When** a developer edits the file to consolidate them, **Then** the agent uses the updated, consolidated guidance.

3. **Given** an old learning entry becomes obsolete (e.g., "Use API version 2021-01-01" when 2024-01-01 is now stable), **When** a developer removes the obsolete entry, **Then** the agent no longer references outdated guidance.

---

### User Story 4 - Cross-Command Consistency (Priority: P2)

Both `/speckit.bicep` (generation) and `/speckit.validate` (validation) reference the same learnings database, ensuring consistent architectural patterns and error handling across the entire workflow.

**Why this priority**: Prevents situations where generation follows one set of rules but validation expects different patterns. Consistency reduces confusion and ensures the entire pipeline learns uniformly.

**Independent Test**: Add a learning entry about a specific security pattern, verify `/speckit.bicep` generates templates following this pattern, and confirm `/speckit.validate` validates against the same pattern without conflicts.

**Acceptance Scenarios**:

1. **Given** a learning entry states "All storage accounts must disable public network access", **When** `/speckit.bicep` generates a storage template, **Then** `publicNetworkAccess: 'Disabled'` is set, **And When** `/speckit.validate` tests the deployment, **Then** it verifies this property is correctly configured.

2. **Given** a learning entry about Private Endpoint DNS configuration, **When** `/speckit.bicep` generates networking resources, **Then** private DNS zones are included, **And When** `/speckit.validate` tests connectivity, **Then** it validates DNS resolution through private endpoints.

---

### Edge Cases

- **What happens when the learnings database grows very large (250+ entries)?** The agent may experience performance degradation when loading all learnings. The system implements automatic optimization per FR-013: at 200 entries, log warning; at 250+ entries, enable category-based filtering (networking, security, data services) and context-aware loading to maintain <2 second load time.

- **What happens when two learning entries conflict?** (e.g., one says "Use Front Door for global distribution" and another says "Avoid Front Door by default"). The system resolves conflicts using FR-012 rules: most recent timestamp wins within same priority tier, but Security/Compliance category entries override all other categories regardless of age. The system automatically appends timestamps to all entries (ISO 8601 format) to enable this resolution.

- **What happens if a deployment error is transient (e.g., temporary API throttling) and not a structural template issue?** The agent classifies errors using keyword matching (see FR-011 for complete keyword list and classification rules) - only structural/design errors become learnings, not transient operational failures.

- **What happens when a learning entry is too vague or lacks sufficient context?** The agent may misapply guidance or skip it entirely. Entries must follow a strict format: "[Context] → [Issue] → [Solution]" with sufficient details to understand when and how to apply.

- **What happens if learnings reference deprecated Azure resources or API versions?** The database needs periodic review against Microsoft Learn documentation. Consider adding a "Last Verified" date to each entry and a validation process to flag potentially obsolete guidance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a single shared Markdown file (`.specify/learnings/bicep-learnings.md`) at the repository root that both `/speckit.bicep` and `/speckit.validate` commands reference for architectural guidance and error prevention. This file is shared across all features within the workspace.

- **FR-002**: System MUST automatically append new learning entries to the database when `/speckit.bicep` or `/speckit.validate` detects template errors, deployment failures, or validation issues.

- **FR-003**: Learning entries MUST follow a succinct format with minimal but sufficient detail: "[Timestamp] [Category] [Context/Resource] → [Issue] → [Solution/Pattern]" where Timestamp is ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ), Category is 1-20 alphanumeric characters, and total entry length does not exceed 500 characters. See `contracts/learnings-format.md` for complete field specifications and validation rules.

- **FR-004**: System MUST extract existing architecture guidelines from the main prompt files (`speckit.bicep.prompt.md` and `speckit.validate.prompt.md`) and migrate them to the shared learnings database during initial implementation. Guidelines are defined as statements containing normative keywords: "MUST", "SHOULD", "AVOID", "ALWAYS", "NEVER", or architectural patterns/anti-patterns.

- **FR-005**: System MUST implement specific default behavior changes based on user requirements:
  - Exclude Azure Front Door from default architectures (only include when explicitly requested)
  - Replace Network Security Perimeter with Private Endpoints and Private Links for secure communications
  - Implement network isolation by deploying all resources within the same VNet
  - Follow Secure Future Initiative (SFI) best practices

- **FR-006**: System MUST reference the learnings database at the start of every `/speckit.bicep` generation and `/speckit.validate` validation run, loading relevant guidance before proceeding with operations. Relevant guidance is defined as category-filtered entries (e.g., load "Networking" and "Security" categories for network-focused generation). If `.specify/learnings/bicep-learnings.md` cannot be loaded (missing, corrupted, or inaccessible), the system MUST halt the operation immediately and display an explicit error message with remediation steps.

- **FR-007**: System MUST allow manual editing of the learnings database file, supporting human curation, consolidation of duplicate entries, and removal of obsolete guidance.

- **FR-008**: Learning entries MUST be categorized by domain (e.g., Networking, Security, Data Services, Compute, Configuration) to enable efficient lookup and context-aware filtering.

- **FR-009**: System MUST timestamp each learning entry to track when knowledge was captured and enable identification of potentially outdated guidance.

- **FR-010**: System MUST prevent duplicate learning entries by comparing new entries against existing entries using semantic similarity analysis; entries with >70% similarity in issue/solution content are considered duplicates and not appended. If the semantic similarity library fails to load or any comparison exceeds 500ms timeout, the system MUST raise a fatal error with the library name and installation instructions.

- **FR-011**: System MUST distinguish between structural template errors (worth capturing as learnings) and transient operational errors (not worth capturing) by analyzing error message keywords: capture errors containing "missing property", "invalid value", "quota", "already exists"; ignore errors containing "throttled", "timeout", "unavailable". For ambiguous errors that appear intermittently, apply heuristic: if same error message appears 3+ times across different templates/runs, classify as structural and append learning. If error context is insufficient to formulate actionable guidance (missing resource type, vague error message, no clear solution), log debug message and skip append to prevent low-quality entries.

- **FR-012**: Main prompt files (`speckit.bicep.prompt.md` and `speckit.validate.prompt.md`) MUST be updated to reference the learnings database file, with instructions to load and apply guidance before generation/validation. Prompt instructions MUST specify explicit failure behavior: if learnings database cannot be loaded, halt operation and display error (do not continue with degraded functionality).

- **FR-013**: System MUST implement automatic performance optimization when learnings database reaches 250 entries. At 200 entries, system logs warning about approaching optimization threshold. At 250+ entries, system automatically enables category-based filtering to maintain <2 second loading performance.

### Key Entities

- **Learning Entry**: Individual piece of knowledge capturing a mistake, pattern, or best practice. Attributes: Category (domain), Context (when to apply), Issue (what to avoid), Solution (what to do instead), Timestamp (when captured), Source (auto-captured from error or manually added).

- **Learnings Database**: Central Markdown file containing all accumulated learning entries, organized by category, with metadata for tracking and maintenance.

- **Error Classification**: Logic that determines whether a deployment error should result in a learning entry (structural issues) versus being ignored (transient issues).

- **Prompt Integration**: References within main prompt files that instruct the agent to load and apply learnings from the database before executing generation or validation operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers no longer encounter previously documented errors - 95% reduction in repeated template mistakes within 30 days of implementing the learnings database. Measurement: Compare unique error signatures in error logs during baseline month (pre-implementation) vs 30 days post-implementation; track by error message fingerprint.

- **SC-002**: Template generation quality improves over time - each month shows fewer validation failures compared to the previous month (minimum 10% month-over-month improvement). Measurement: Calculate failure rate as percentage of total runs (failed validations / total validations) to account for usage variance, not absolute failure count.

- **SC-003**: 100% of the architectural guidelines currently embedded in main prompt files are successfully migrated to the learnings database and correctly applied by the agent.

- **SC-004**: Learnings database grows organically - at least 5 new entries are automatically captured per week during active development periods, demonstrating continuous learning. Active development is defined as 10+ Bicep generation/validation runs per week; metric not applicable during low-activity periods.

- **SC-005**: Manual intervention for learnings curation is minimal - developers spend less than 30 minutes per month reviewing and editing the learnings database. Measurement: Cumulative time spent by all team members (not per developer) reviewing/curating database content.

- **SC-009**: Learnings database loading performance remains <2 seconds for databases up to 250 entries, ensuring minimal impact on developer workflow during template generation and validation.

- **SC-006**: Zero Azure Front Door resources appear in generated architectures unless explicitly requested in `$ARGUMENTS`, confirming default behavior change.

- **SC-007**: 100% of generated architectures use Private Endpoints instead of Network Security Perimeter, with all resources deployed in the same VNet, validating network isolation requirements.

- **SC-008**: Generated architectures demonstrate compliance with Secure Future Initiative (SFI) best practices - all storage, databases, and vaults have `publicNetworkAccess: 'Disabled'` and use Private Link connectivity.

## Assumptions

- The learnings database file will be stored in a new `.specify/learnings/` directory to keep it separate from templates and configuration files.

- The Markdown format for learnings will use a simple, structured approach with headers for categories and bullet points for individual entries.

- Both `/speckit.bicep` and `/speckit.validate` have access to file system operations to read from and append to the learnings database file.

- Error detection logic can classify errors into categories (syntax, deployment, quota, security, configuration) to determine if a learning entry should be created.

- The agent has sufficient context during error handling to extract meaningful root causes and formulate actionable guidance. If context is insufficient (per FR-011), the system skips appending low-quality entries.

- Success criteria measurements (SC-001, SC-002, SC-004, SC-005) are manual observational metrics tracked through error logs, validation reports, and team time tracking. No automated measurement instrumentation is implemented as part of this feature - metrics are collected through existing logging and monitoring infrastructure.

- Developers using these commands have write permissions to the `.specify/learnings/` directory to allow automatic appending of new entries.

- The learnings database format is human-readable and editable, allowing developers to use standard text editors for manual curation.

- Initial migration of existing guidelines from prompt files to the learnings database will be a one-time operation performed during feature implementation.

- Private Endpoints provide equivalent or superior security compared to Network Security Perimeter for the identified use cases.

- Network isolation through VNet deployment is compatible with all Azure resource types commonly used in generated templates (App Service, Storage, Key Vault, databases).

## Out of Scope

- **Learnings Database Versioning**: No version control or rollback mechanism for the learnings database - developers use Git for version history if needed.

- **Learnings Validation Service**: No automated checking of learnings against current Azure best practices or API documentation - manual review is sufficient.

- **Multi-Tenant Learnings Sharing**: No mechanism to share learnings across teams or organizations - each workspace maintains its own database.

- **Learnings Analytics Dashboard**: No UI or reporting tools to visualize learning trends, categories, or impact metrics.

- **AI-Powered Learning Consolidation**: No automated merging or refactoring of similar learning entries - human curation handles this.

- **Integration with External Knowledge Bases**: No automatic import of learnings from Microsoft Learn, Azure Advisor, or other external sources.

- **Learnings for Other Commands**: This feature focuses only on `/speckit.bicep` and `/speckit.validate` - other commands (plan, tasks, implement) are not included.

- **Rollback of Bad Learnings**: No mechanism to automatically detect and remove incorrect or harmful learning entries - relies on manual review.

