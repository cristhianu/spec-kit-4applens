# Data Model: Bicep Validate Command

**Feature**: 003-bicep-validate-command  
**Date**: October 28, 2025  
**Purpose**: Define core entities and their relationships for the Bicep validation workflow

## Core Entities

### 1. Project

Represents a workspace project with generated Bicep templates.

**Attributes**:

- `project_id`: Unique identifier (derived from path)
- `name`: Project display name
- `path`: Absolute path to project root
- `source_code_path`: Path to application source code
- `bicep_templates_path`: Path to generated Bicep templates directory
- `framework`: Detected framework type (dotnet, nodejs, python, etc.)
- `last_modified`: Timestamp of last template modification

**Relationships**:

- Has many `Application Settings`
- Has many `Validation Endpoints`
- Has one `Validation Session` (per validation run)

**Validation Rules**:

- `path` must exist and be readable
- `bicep_templates_path` must contain at least one `.bicep` file
- `framework` must be one of supported types

---

### 2. Application Setting

Represents a configuration value required by the application.

**Attributes**:

- `setting_id`: Unique identifier
- `name`: Setting key/name (e.g., "ConnectionStrings:DefaultConnection")
- `value`: Setting value (may be null if from deployment)
- `source_type`: Where value comes from ("hardcoded", "keyvault", "deployment_output")
- `is_secure`: Boolean indicating if value is sensitive
- `environment`: Target environment (dev, test, prod)
- `keyvault_secret_name`: Formatted Key Vault secret name (if applicable)

**Relationships**:

- Belongs to `Project`
- May depend on `Resource Dependency`
- Stored in `Key Vault` (if secure)

**Validation Rules**:

- `name` must not be empty
- If `is_secure` is true, `source_type` must be "keyvault"
- `keyvault_secret_name` must follow naming convention (127 chars max, lowercase, no special chars except hyphen)

**State Transitions**:

```text
Discovered → Analyzed → Deployed → Validated
```

---

### 3. Resource Dependency

Represents an Azure resource that must be deployed to obtain configuration values.

**Attributes**:

- `resource_id`: Azure resource identifier
- `resource_type`: Azure resource type (e.g., "Microsoft.Sql/servers")
- `resource_name`: Resource name
- `deployment_order`: Integer indicating deployment sequence (from topological sort)
- `deployment_status`: Current deployment state
- `bicep_template_path`: Path to Bicep template for this resource
- `output_values`: Dictionary of deployment outputs

**Relationships**:

- Depends on zero or more other `Resource Dependencies` (dependency graph)
- Provides values for one or more `Application Settings`
- Part of `Deployment Result`

**Validation Rules**:

- `deployment_order` must be non-negative
- `resource_type` must be valid Azure resource type
- Circular dependencies must be rejected

**State Transitions**:

```text
Pending → Validating → Deploying → Deployed → Failed
```

---

### 4. Validation Endpoint

Represents an API endpoint to test.

**Attributes**:

- `endpoint_id`: Unique identifier
- `path`: URL path (e.g., "/api/users/{id}")
- `method`: HTTP method ("GET", "POST", "PUT", "DELETE", "PATCH")
- `base_url`: Base URL after deployment (e.g., "https://app.azurewebsites.net")
- `requires_auth`: Boolean indicating if authentication needed
- `auth_type`: Authentication type ("bearer", "apikey", "none")
- `expected_status_codes`: List of acceptable HTTP status codes
- `timeout_seconds`: Maximum time to wait for response
- `test_parameters`: Dictionary of test parameter values

**Relationships**:

- Belongs to `Project`
- Produces `Endpoint Test Result`

**Validation Rules**:

- `path` must start with "/"
- `method` must be valid HTTP verb
- `expected_status_codes` must contain at least one valid status code (100-599)
- `timeout_seconds` must be positive

---

### 5. Deployment Result

Represents the outcome of a deployment attempt.

**Attributes**:

- `deployment_id`: Unique identifier
- `timestamp`: When deployment occurred
- `success`: Boolean indicating overall success
- `deployed_resources`: List of `Resource Dependencies` that were deployed
- `resource_group`: Azure resource group name
- `subscription_id`: Azure subscription ID
- `deployment_outputs`: Dictionary of all deployment outputs
- `error_messages`: List of error messages (if failures)
- `duration_seconds`: Time taken for deployment

**Relationships**:

- Part of `Validation Session`
- Contains multiple `Resource Dependencies`

**Validation Rules**:

- If `success` is false, `error_messages` must not be empty
- `duration_seconds` must be non-negative

---

### 6. Endpoint Test Result

Represents the outcome of testing a single endpoint.

**Attributes**:

- `test_id`: Unique identifier
- `endpoint_id`: Reference to tested endpoint
- `timestamp`: When test was executed
- `status`: Test outcome ("success", "failure", "timeout", "retry_exhausted")
- `status_code`: HTTP status code received
- `response_time_ms`: Response time in milliseconds
- `error_message`: Error description (if failed)
- `retry_count`: Number of retries attempted
- `response_body_preview`: First 500 chars of response (for debugging)

**Relationships**:

- Belongs to `Validation Endpoint`
- Part of `Validation Session`

**Validation Rules**:

- If `status` is "success", `status_code` must be in expected range (200-299)
- `response_time_ms` must be non-negative
- If `status` is "failure", `error_message` must not be empty

---

### 7. Validation Session

Represents a complete validation workflow execution.

**Attributes**:

- `session_id`: Unique identifier (GUID)
- `project_id`: Reference to validated project
- `start_time`: When validation started
- `end_time`: When validation completed
- `status`: Overall status ("in_progress", "success", "failed", "partial")
- `current_stage`: Current workflow stage
- `test_environment`: Target environment name
- `retry_attempts`: Number of fix-and-retry cycles
- `max_retries`: Maximum allowed retries (default 3)

**Relationships**:

- Belongs to `Project`
- Has one `Deployment Result`
- Has many `Endpoint Test Results`
- May have multiple `Fix Attempts`

**Validation Rules**:

- `start_time` must be before `end_time`
- `retry_attempts` must not exceed `max_retries`
- If `status` is "success", all test results must be successful

**State Transitions**:

```text
Initialized → Discovering → Analyzing → Deploying → Testing → Fixing → Completed
```

**Stages**:

1. **Discovering**: Finding projects and Bicep templates
2. **Analyzing**: Identifying app settings and dependencies
3. **Deploying**: Deploying resources and storing secrets
4. **Testing**: Testing API endpoints
5. **Fixing**: Attempting automated fixes (if issues found)
6. **Completed**: Validation finished (success or failure)

---

### 8. Fix Attempt

Represents an attempt to automatically fix a validation issue.

**Attributes**:

- `fix_id`: Unique identifier
- `session_id`: Reference to validation session
- `timestamp`: When fix was attempted
- `error_category`: Category of error being fixed
- `issue_description`: Detailed description of the issue
- `fix_strategy`: Strategy used to fix (e.g., "template_fix", "missing_app_setting")
- `success`: Boolean indicating if fix worked
- `applied_changes`: List of changes made
- `error_message`: Error message (if fix failed)

**Relationships**:

- Belongs to `Validation Session`

**Validation Rules**:

- `error_category` must be valid category
- If `success` is true, `applied_changes` must not be empty
- If `success` is false, `error_message` must not be empty

---

## Entity Relationships Diagram

```text
┌─────────────────┐
│     Project     │
│  - project_id   │
│  - name         │
│  - path         │
│  - framework    │
└────────┬────────┘
         │
         │ has many
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│ Application      │          │  Validation      │
│ Setting          │          │  Endpoint        │
│  - setting_id    │          │  - endpoint_id   │
│  - name          │          │  - path          │
│  - source_type   │          │  - method        │
│  - is_secure     │          │  - requires_auth │
└──────┬───────────┘          └────────┬─────────┘
       │                               │
       │ depends on                    │ produces
       │                               │
       ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  Resource        │          │  Endpoint Test   │
│  Dependency      │          │  Result          │
│  - resource_id   │          │  - test_id       │
│  - resource_type │          │  - status        │
│  - deploy_order  │          │  - status_code   │
└──────┬───────────┘          └────────┬─────────┘
       │                               │
       │ part of                       │ part of
       │                               │
       └───────────┬───────────────────┘
                   │
                   ▼
           ┌──────────────────┐
           │  Validation      │
           │  Session         │
           │  - session_id    │
           │  - status        │
           │  - current_stage │
           └────────┬─────────┘
                    │
                    │ has many
                    │
                    ▼
            ┌──────────────────┐
            │  Fix Attempt     │
            │  - fix_id        │
            │  - error_category│
            │  - fix_strategy  │
            └──────────────────┘
```

---

## Data Flow

### 1. Project Discovery Flow

```text
Workspace Root
    ↓ (scan for .bicep files)
List of Project paths
    ↓ (analyze each)
Project entities with metadata
```

### 2. Configuration Analysis Flow

```text
Project source code
    ↓ (framework-specific parsing)
Application Settings (raw)
    ↓ (dependency analysis)
Application Settings + Resource Dependencies graph
    ↓ (topological sort)
Ordered deployment sequence
```

### 3. Deployment Flow

```text
Resource Dependencies (ordered)
    ↓ (validate templates)
Validated Bicep templates
    ↓ (deploy via Azure CLI)
Deployed Resources + Outputs
    ↓ (extract connection strings)
Configuration values
    ↓ (store in Key Vault)
Key Vault secrets + App settings with references
```

### 4. Testing Flow

```text
Validation Endpoints (discovered)
    ↓ (resolve base URL from deployment)
Endpoints with full URLs
    ↓ (execute HTTP requests)
Endpoint Test Results
    ↓ (analyze failures)
Issues requiring fixes
```

### 5. Fix-and-Retry Flow

```text
Validation failures
    ↓ (classify errors)
Error categories
    ↓ (select fix strategy)
Fix Attempts
    ↓ (apply fixes)
Updated templates/configuration
    ↓ (retry validation)
New Validation Session
```

---

## Persistence Strategy

### In-Memory (Session State)

- Current `Validation Session`
- `Fix Attempts` (current session)
- Circuit breaker state
- Retry counters

### File System Cache

- Project discovery cache (`.bicep-cache.json`)
- Deployment outputs (`.validation-outputs.json`)
- Test results for review (`.validation-results.json`)

### Azure Resources

- Deployed resources (in Azure)
- Key Vault secrets
- Application configuration settings

### No Database Required

All data is ephemeral per validation session. No persistent database needed.

---

## Key Design Decisions

### Why No Database?

- Validation is a transient workflow (runs on-demand)
- Results are logged/displayed, not queried later
- File-based caching sufficient for performance
- Reduces complexity and deployment requirements

### Why In-Memory Session State?

- Single validation run completes in <15 minutes
- No need to persist state across runs
- Simplifies error handling (no stale state)
- Easier to test and debug

### Why File System Cache?

- Fast project discovery on subsequent runs
- Easy to clear (just delete cache file)
- No external dependencies
- Version control friendly (can be .gitignored)

---

**Data Model Complete**: All entities defined with attributes, relationships, and validation rules. Ready for contract generation.
