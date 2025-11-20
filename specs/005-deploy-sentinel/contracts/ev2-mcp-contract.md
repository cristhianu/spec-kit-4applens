# EV2 MCP Server API Contract

**Feature**: 005-deploy-sentinel | **Contract Type**: External API | **Date**: 2025-11-19

## Overview

This contract defines the expected interactions with the EV2 MCP Server via GitHub Copilot's MCP integration. The EV2 MCP Server exposes EV2 operations as tools that can be invoked by the PowerShell script through the Copilot agent.

## Best Practices Tool (Mandatory First Call)

**Tool**: `mcp_ev2_mcp_serve_get_ev2_best_practices`

**Purpose**: MUST be called before any other EV2 operations per tool documentation

**Input**: None

**Expected Output**: Markdown document with EV2 deployment best practices, mandatory steps, and tool sequencing requirements

**Success Criteria**:

- Returns comprehensive best practices documentation
- Must be called synchronously before any rollout operations
- Script acknowledges best practices in output

## Get Artifact Versions

**Tool**: `mcp_ev2_mcp_serve_get_artifact_versions`

**Purpose**: Retrieve list of registered artifact versions for a service

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "serviceGroupName": "AppLensService",
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "artifacts": [
    {
      "versionNumber": "1.2.3",
      "registrationDate": "2025-11-19T10:00:00Z",
      "status": "Active"
    },
    {
      "versionNumber": "1.2.2",
      "registrationDate": "2025-11-18T14:30:00Z",
      "status": "Active"
    }
  ]
}
```

**Success Criteria**:

- Returns list ordered by registration date (newest first)
- Latest version is artifacts[0]
- All versions have "Active" status

**Failure Scenarios**:

- Service not found: Returns error with message "Service {serviceId} not found"
- Authentication error: Returns error with message "Authentication failed"
- Invalid endpoint: Returns error with message "Invalid endpoint: {endpoint}"

## Get Stage Map Versions

**Tool**: `mcp_ev2_mcp_serve_get_stage_map_versions`

**Purpose**: Retrieve list of registered stage map versions for a service

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "serviceGroupName": "AppLensService",
  "stageMapName": "AppLensStageMap",
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "stageMaps": [
    {
      "version": "v2",
      "registrationDate": "2025-11-15T09:00:00Z",
      "status": "Active"
    },
    {
      "version": "v1",
      "registrationDate": "2025-11-01T08:00:00Z",
      "status": "Active"
    }
  ]
}
```

**Success Criteria**:

- Returns list ordered by registration date (newest first)
- Latest version is stageMaps[0]
- All versions have "Active" status

**Failure Scenarios**:

- Stage map not found: Returns error with message "Stage map {stageMapName} not found"
- Service not found: Returns error with message "Service {serviceId} not found"

## Start Rollout

**Tool**: `mcp_ev2_mcp_serve_start_rollout`

**Purpose**: Trigger a new EV2 rollout with specified artifact and stage map versions

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "serviceGroupName": "AppLensService",
  "stageMapName": "AppLensStageMap",
  "stageMapVersion": "v2",
  "artifactVersionNumber": "1.2.3",
  "selectionScope": [
    "regions(EastUS,WestUS).steps(*).stamps(*).actions(*)"
  ],
  "exclusionScope": [],
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "status": "InProgress",
  "createdTimestamp": "2025-11-19T10:30:00Z"
}
```

**Success Criteria**:

- Returns valid GUID rolloutId
- Initial status is "InProgress"
- Timestamp is current UTC time

**Failure Scenarios**:

- Invalid artifact version: Error "Artifact version {version} not found"
- Invalid stage map version: Error "Stage map version {version} not found"
- Invalid selection scope: Error "Invalid scope syntax: {scope}"
- Concurrent rollout exists: Error "Rollout already in progress for service {serviceId}"

## Get Rollout Details

**Tool**: `mcp_ev2_mcp_serve_get_rollout_details`

**Purpose**: Retrieve current status and detailed information for a specific rollout

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "overallStatus": "InProgress",
  "currentStage": "Stage2-WestUS",
  "stages": [
    {
      "name": "Stage1-EastUS",
      "status": "Completed",
      "startTime": "2025-11-19T10:30:00Z",
      "endTime": "2025-11-19T10:45:00Z",
      "regions": ["EastUS"]
    },
    {
      "name": "Stage2-WestUS",
      "status": "InProgress",
      "startTime": "2025-11-19T10:45:00Z",
      "endTime": null,
      "regions": ["WestUS"]
    },
    {
      "name": "Stage3-CentralUS",
      "status": "Pending",
      "startTime": null,
      "endTime": null,
      "regions": ["CentralUS"]
    }
  ],
  "errors": [],
  "waitActions": [],
  "lastUpdateTime": "2025-11-19T10:50:00Z"
}
```

**Success Criteria**:

- Returns complete rollout state
- stages array ordered by execution sequence
- overallStatus matches aggregate of stage statuses
- Completed stages have endTime
- Pending stages have null startTime/endTime

**Failure Scenarios**:

- Rollout not found: Error "Rollout {rolloutId} not found"
- Service ID mismatch: Error "Rollout {rolloutId} does not belong to service {serviceId}"

**Wait Actions** (if present):

```json
{
  "waitActions": [
    {
      "actionId": "wait-12345",
      "stage": "Stage3-CentralUS",
      "reason": "ManualApproval",
      "waitingSince": "2025-11-19T11:00:00Z",
      "status": "Waiting"
    }
  ]
}
```

**Error Details** (if present):

```json
{
  "errors": [
    {
      "stage": "Stage2-WestUS",
      "timestamp": "2025-11-19T10:55:00Z",
      "errorCode": "ServiceHealthCheckFailed",
      "message": "Health endpoint returned 503. Recommendation: Check WestUS service logs."
    }
  ]
}
```

## Stop Wait Action

**Tool**: `mcp_ev2_mcp_serve_stop_wait_action`

**Purpose**: Approve a wait action to allow rollout to proceed

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "actionId": "wait-12345",
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "success": true,
  "actionId": "wait-12345",
  "status": "Approved",
  "timestamp": "2025-11-19T11:05:00Z"
}
```

**Success Criteria**:

- Returns success=true
- Wait action removed from rollout's waitActions list
- Rollout proceeds to next stage

**Failure Scenarios**:

- Action not found: Error "Wait action {actionId} not found"
- Already approved: Error "Wait action {actionId} already approved"

## Cancel Rollout

**Tool**: `mcp_ev2_mcp_serve_cancel_rollout`

**Purpose**: Cancel an in-progress rollout

**Input**:

```json
{
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "reason": "Critical failure detected in Stage2",
  "endpoint": "Prod"
}
```

**Expected Output**:

```json
{
  "success": true,
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "status": "Cancelled",
  "timestamp": "2025-11-19T11:10:00Z"
}
```

**Success Criteria**:

- Returns success=true
- Rollout status changes to "Cancelled"
- No further stages execute

**Failure Scenarios**:

- Rollout not found: Error "Rollout {rolloutId} not found"
- Already completed: Error "Cannot cancel completed rollout"

## Error Handling

**Standard Error Response**:

```json
{
  "error": {
    "code": "ServiceNotFound",
    "message": "Service 87654321-4321-4321-4321-cba987654321 not found",
    "timestamp": "2025-11-19T10:30:00Z"
  }
}
```

**Error Codes**:

- `ServiceNotFound`: Service does not exist in EV2
- `AuthenticationFailed`: Invalid or missing credentials
- `InvalidParameter`: Parameter validation failed
- `ConcurrentRollout`: Rollout already in progress for service
- `RolloutNotFound`: Specified rollout does not exist
- `InternalError`: EV2 service error (transient, retry)

**Retry Policy**:

- Transient errors (`InternalError`, HTTP 503, 429): Retry with exponential backoff (max 3 attempts)
- Non-recoverable errors (authentication, not found): Fail immediately
- Script should log all EV2 API calls and responses for debugging

## Contract Tests

Contract tests will validate:

1. ✅ Best practices tool returns documentation before any operations
2. ✅ Get artifact versions returns ordered list with latest first
3. ✅ Get stage map versions returns ordered list with latest first
4. ✅ Start rollout returns valid rolloutId
5. ✅ Get rollout details returns complete state structure
6. ✅ Stop wait action approves and removes wait action
7. ✅ Cancel rollout terminates in-progress rollout
8. ✅ Error responses follow standard format
9. ✅ Transient errors trigger retry logic
10. ✅ Non-recoverable errors fail fast

**Test Strategy**: Mock EV2 MCP Server responses in Pester tests using fixtures from `tests/fixtures/deploy-sentinel/mock-rollout-responses.json`
