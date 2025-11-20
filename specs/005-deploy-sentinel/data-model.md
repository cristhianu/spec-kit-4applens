# Data Model: EV2 Deployment Follower Agent

**Feature**: 005-deploy-sentinel | **Phase**: 1 (Design & Contracts) | **Date**: 2025-11-19

## Overview

This document defines the data structures and their relationships for the EV2 Deployment Follower Agent. All entities are represented as PowerShell objects (hashtables/PSCustomObjects) and serialized to JSON when persisted.

## Entity Definitions

### 1. RolloutState

**Purpose**: Represents the current state of an active EV2 rollout being managed by the agent. This is the primary entity for idempotent operations and recovery.

**Attributes**:

| Name | Type | Required | Description | Validation Rules |
|------|------|----------|-------------|------------------|
| version | int | Yes | Schema version for future compatibility | Must be 1 |
| rolloutId | string | Yes | EV2 rollout unique identifier (GUID) | Must be valid GUID |
| serviceGroupName | string | Yes | Service group identifier | Non-empty string |
| serviceId | string | Yes | Service unique identifier (GUID) | Must be valid GUID |
| environment | string | Yes | Target environment (PPE, PROD, etc.) | Must match: ^[A-Z]+$ |
| currentStage | string | Yes | Current deployment stage/region | Non-empty string |
| deployedRegions | string[] | Yes | List of successfully deployed regions | Array (may be empty) |
| pendingRegions | string[] | Yes | List of regions awaiting deployment | Array (may be empty) |
| overallStatus | string | Yes | Rollout state | Enum: InProgress, Completed, Failed, Cancelled |
| errors | object[] | Yes | List of errors encountered | Array of error objects |
| startTime | datetime | Yes | Rollout initiation timestamp (ISO 8601) | Valid ISO 8601 datetime |
| lastUpdateTime | datetime | Yes | Last state update timestamp (ISO 8601) | Valid ISO 8601 datetime |
| artifactVersion | string | Yes | Deployed artifact version | Non-empty string |
| stageMapVersion | string | Yes | Stage map version used | Non-empty string |
| branchName | string | No | Git branch created for deployment | Optional string |

**Relationships**:

- Referenced by DeploymentConfig during initialization
- Contains ServiceInfo metadata (serviceGroupName, serviceId)
- Persisted to `.deploy-sentinel-state.json`

**State Transitions**:

```text
[Initial] → InProgress → Completed
                      ↓
                   Failed → [Retry?] → InProgress
                      ↓
                   Cancelled
```

**Example**:

```json
{
  "version": 1,
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "serviceGroupName": "AppLensService",
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "environment": "PPE",
  "currentStage": "Stage2-WestUS",
  "deployedRegions": ["EastUS", "CentralUS"],
  "pendingRegions": ["WestUS", "NorthEurope"],
  "overallStatus": "InProgress",
  "errors": [],
  "startTime": "2025-11-19T10:30:00Z",
  "lastUpdateTime": "2025-11-19T10:45:00Z",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "branchName": "deploy/PPE/AppLensService/20251119-103000"
}
```

### 2. DeploymentConfig

**Purpose**: Represents configuration for a deployment operation. Can be loaded from file or provided via command-line parameters.

**Attributes**:

| Name | Type | Required | Description | Validation Rules |
|------|------|----------|-------------|------------------|
| serviceGroupName | string | Yes | Service group identifier | Non-empty string |
| serviceId | string | Yes | Service GUID | Must be valid GUID |
| stageMapName | string | Yes | Stage map name (not version) | Non-empty string |
| environment | string | Yes | Target environment | Must match: ^[A-Z]+$ |
| selectionScope | string | No | EV2 selection scope syntax | Valid scope syntax |
| exclusionScope | string | No | EV2 exclusion scope syntax | Valid scope syntax |
| teamsWebhookUrl | string | No | Teams webhook URL for notifications | Valid HTTPS URL or null |
| stressTestConfig | object | No | Stress test configuration | See StressTestConfig |
| pipelineConfig | object | No | ADO pipeline configuration | See PipelineConfig |
| pollingInterval | int | No | Status poll interval in seconds | Default: 30, Range: 10-300 |
| maxRetries | int | No | Max retry attempts for transient failures | Default: 3, Range: 1-10 |

**Nested Objects**:

**StressTestConfig**:

```json
{
  "enabled": true,
  "endpointUrl": "https://applens.azureedge.net/health",
  "requestCount": 100,
  "durationSeconds": 30,
  "timeoutSeconds": 10,
  "authToken": null,
  "thresholds": {
    "successRatePercent": 95.0,
    "p95LatencyMs": 500
  }
}
```

**Example Endpoint URLs**:
- Health endpoint: `https://applens.azureedge.net/health`
- API endpoint: `https://applens-api.azurewebsites.net/api/diagnostics`
- Region-specific: `https://applens-eastus.azureedge.net/api/status`
- Authenticated: `https://applens-internal.azure.net/api/metrics` (requires bearer token)
```

**PipelineConfig**:

```json
{
  "enabled": true,
  "project": "One",
  "pipelineId": 12345,
  "branch": null,
  "parameters": {}
}
```

**Relationships**:

- Loaded from config file (`.deploy-sentinel-config.json`) or command-line parameters
- Used to initialize RolloutState
- Referenced by ServiceInfo for service discovery

**Example**:

```json
{
  "serviceGroupName": "AppLensService",
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "stageMapName": "AppLensStageMap",
  "environment": "PPE",
  "selectionScope": "regions(EastUS,WestUS).steps(*).stamps(*).actions(*)",
  "exclusionScope": null,
  "teamsWebhookUrl": "https://prod-12.logic.azure.com:443/workflows/{guid}/triggers/manual/paths/invoke?...",
  "stressTestConfig": { "enabled": true, "endpointUrl": "https://applens.azureedge.net/health" },
  "pipelineConfig": { "enabled": false },
  "pollingInterval": 30,
  "maxRetries": 3
}
```

### 3. ServiceInfo

**Purpose**: Represents metadata about the service being deployed, discovered from EV2 and local files.

**Attributes**:

| Name | Type | Required | Description | Validation Rules |
|------|------|----------|-------------|------------------|
| serviceGroupName | string | Yes | Service group identifier | Non-empty string |
| serviceId | string | Yes | Service GUID | Must be valid GUID |
| latestArtifactVersion | string | Yes | Latest registered artifact version | Non-empty string |
| latestStageMapVersion | string | Yes | Latest registered stage map version | Non-empty string |
| serviceModelPath | string | No | Path to ServiceModel.json if found | Valid file path or null |
| rolloutSpecPath | string | No | Path to RolloutSpec.json if found | Valid file path or null |
| scopeBindingsPath | string | No | Path to ScopeBindings.json if found | Valid file path or null |
| discoveryTimestamp | datetime | Yes | When metadata was discovered | Valid ISO 8601 datetime |

**Relationships**:

- Discovered via EV2 MCP Server queries
- Used to populate RolloutState
- Local file paths discovered via filesystem search (`.azure/*/ev2/`)

**Example**:

```json
{
  "serviceGroupName": "AppLensService",
  "serviceId": "87654321-4321-4321-4321-cba987654321",
  "latestArtifactVersion": "1.2.3",
  "latestStageMapVersion": "v2",
  "serviceModelPath": "C:\\repos\\applens\\.azure\\PPE\\ev2\\ServiceModel.json",
  "rolloutSpecPath": "C:\\repos\\applens\\.azure\\PPE\\ev2\\RolloutSpec.json",
  "scopeBindingsPath": "C:\\repos\\applens\\.azure\\PPE\\ev2\\ScopeBindings.json",
  "discoveryTimestamp": "2025-11-19T10:30:00Z"
}
```

### 4. StressTestResult

**Purpose**: Represents the results of stress testing a deployed endpoint.

**Attributes**:

| Name | Type | Required | Description | Validation Rules |
|------|------|----------|-------------|------------------|
| endpointUrl | string | Yes | Tested endpoint URL | Valid HTTPS URL |
| totalRequests | int | Yes | Total requests sent | Must be > 0 |
| successfulRequests | int | Yes | Successful responses (2xx) | Must be ≥ 0 |
| failedRequests | int | Yes | Failed responses (non-2xx or timeout) | Must be ≥ 0 |
| errorRate | decimal | Yes | Percentage of failed requests | Range: 0.0-100.0 |
| averageResponseTime | int | Yes | Average response time in milliseconds | Must be ≥ 0 |
| p50ResponseTime | int | Yes | 50th percentile (median) latency in ms | Must be ≥ 0 |
| p95ResponseTime | int | Yes | 95th percentile latency in ms | Must be ≥ 0 |
| p99ResponseTime | int | Yes | 99th percentile latency in ms | Must be ≥ 0 |
| testDuration | int | Yes | Actual test duration in seconds | Must be > 0 |
| timestamp | datetime | Yes | When test completed | Valid ISO 8601 datetime |
| passed | bool | Yes | Whether test met thresholds | Boolean |
| failureReason | string | No | Reason for failure if passed=false | Optional string |

**Relationships**:

- Created after each deployment stage
- Used to determine if deployment should proceed to next stage
- Logged in deployment output and stored in RolloutState.errors if failed

**Example**:

```json
{
  "endpointUrl": "https://applens.azureedge.net/health",
  "totalRequests": 100,
  "successfulRequests": 98,
  "failedRequests": 2,
  "errorRate": 2.0,
  "averageResponseTime": 245,
  "p50ResponseTime": 230,
  "p95ResponseTime": 450,
  "p99ResponseTime": 580,
  "testDuration": 32,
  "timestamp": "2025-11-19T10:50:00Z",
  "passed": true,
  "failureReason": null
}
```

### 5. NotificationMessage

**Purpose**: Represents a notification to be sent via Teams webhook (Power Automate format).

**Attributes**:

| Name | Type | Required | Description | Validation Rules |
|------|------|----------|-------------|------------------|
| title | string | Yes | Notification title | Non-empty string |
| status | string | Yes | Deployment status | Enum: Success, Failed, Warning |
| serviceGroupName | string | Yes | Service group identifier | Non-empty string |
| environment | string | Yes | Target environment | Non-empty string |
| rolloutId | string | Yes | EV2 rollout ID | Must be valid GUID |
| duration | string | Yes | Deployment duration (human-readable) | Format: "1h 23m" |
| deployedRegions | string[] | Yes | Successfully deployed regions | Array of strings |
| artifactVersion | string | Yes | Deployed artifact version | Non-empty string |
| errorSummary | string | No | Error summary if status=Failed | Optional string |
| ev2DashboardUrl | string | Yes | Link to EV2 rollout dashboard | Valid HTTPS URL |
| timestamp | datetime | Yes | Notification timestamp | Valid ISO 8601 datetime |

**Relationships**:

- Generated from RolloutState upon completion
- Sent to Teams webhook as JSON payload
- Logged locally if webhook fails

**Example (Success)**:

```json
{
  "title": "✅ Deployment Successful: AppLensService to PPE",
  "status": "Success",
  "serviceGroupName": "AppLensService",
  "environment": "PPE",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "duration": "1h 23m",
  "deployedRegions": ["EastUS", "WestUS", "CentralUS"],
  "artifactVersion": "1.2.3",
  "errorSummary": null,
  "ev2DashboardUrl": "https://ev2portal.azure.net/rollouts/12345678-1234-1234-1234-123456789abc",
  "timestamp": "2025-11-19T11:53:00Z"
}
```

**Example (Failed)**:

```json
{
  "title": "❌ Deployment Failed: AppLensService to PPE",
  "status": "Failed",
  "serviceGroupName": "AppLensService",
  "environment": "PPE",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "duration": "45m",
  "deployedRegions": ["EastUS"],
  "artifactVersion": "1.2.3",
  "errorSummary": "Stage2-WestUS failed: Service health check returned 503. Recommendation: Check WestUS service logs.",
  "ev2DashboardUrl": "https://ev2portal.azure.net/rollouts/12345678-1234-1234-1234-123456789abc",
  "timestamp": "2025-11-19T11:15:00Z"
}
```

## Validation Rules Summary

**Cross-Entity Constraints**:

1. RolloutState.serviceId must match DeploymentConfig.serviceId
2. RolloutState.artifactVersion must come from ServiceInfo.latestArtifactVersion (or explicitly specified)
3. StressTestResult.passed determines if deployment continues (FR-025)
4. NotificationMessage.status must reflect RolloutState.overallStatus

**State Consistency**:

1. deployedRegions + pendingRegions = all regions in stage map
2. overallStatus=Completed implies pendingRegions is empty
3. overallStatus=Failed implies errors array is non-empty
4. lastUpdateTime must be ≥ startTime

**File Locking**:

1. Only one RolloutState per serviceId + environment combination allowed
2. Enforced via file lock on `.deploy-sentinel-state.json`
3. Lock held for duration of deployment script execution

## Serialization Format

All entities serialized as JSON with:

- `ConvertTo-Json -Depth 10` (ensure nested objects fully serialized)
- ISO 8601 datetime format: `"2025-11-19T10:30:00Z"`
- Pretty-printed for readability (development) or compact (production)
- UTF-8 encoding without BOM

## Persistence Strategy

**RolloutState**: Persisted to `.deploy-sentinel-state.json` in current directory

- Written after initialization, after each polling update, after stage completion
- Atomic write via temp file + rename pattern
- File locked during script execution
- Deleted on successful completion (overallStatus=Completed)
- Retained on failure for debugging and retry

**DeploymentConfig**: Loaded from `.deploy-sentinel-config.json` (optional)

- If not present, all parameters via command-line
- Command-line parameters override config file values
- Not modified during execution

**ServiceInfo**: Ephemeral (not persisted)

- Discovered fresh at start of each deployment
- Cached in memory during execution

**StressTestResult**: Logged to output, included in RolloutState.errors if failed

- Not persisted separately
- Available in script output for analysis

**NotificationMessage**: Sent to Teams webhook, logged locally if webhook fails

- Not persisted separately
- Fallback: Write to `.deploy-sentinel-notifications.log` if webhook unreachable
