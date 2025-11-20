# Microsoft Teams Webhook API Contract

**Feature**: 005-deploy-sentinel | **Contract Type**: External API | **Date**: 2025-11-19

## Overview

This contract defines the expected interactions with Microsoft Teams via Power Automate Workflow Webhooks. The webhook format is user-defined in the Power Automate flow (per clarification Q2 answer B), allowing flexibility in payload structure while maintaining consistency with deployment status notifications.

## Webhook Configuration

**Webhook URL Format**: `https://prod-xx.region.logic.azure.com:443/workflows/{workflow-id}/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig={signature}`

**HTTP Method**: POST

**Content-Type**: application/json

**Authentication**: None (signature embedded in URL query parameter)

## Notification Payload Structure

The payload structure follows the recommended format for deployment notifications with user-defined schema in Power Automate. The flow designer defines the schema using "Parse JSON" action.

**Recommended Schema** (Power Automate):

```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "rolloutId": {
      "type": "string"
    },
    "service": {
      "type": "string"
    },
    "artifactVersion": {
      "type": "string"
    },
    "stageMapVersion": {
      "type": "string"
    },
    "regions": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "timestamp": {
      "type": "string"
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "stage": {
            "type": "string"
          },
          "message": {
            "type": "string"
          }
        }
      }
    },
    "actionUrl": {
      "type": "string"
    }
  }
}
```

## Notification Types

### 1. Rollout Started

**Trigger**: After successful rollout initiation via EV2 MCP

**Payload**:

```json
{
  "title": "EV2 Rollout Started",
  "status": "InProgress",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS", "WestUS", "CentralUS"],
  "timestamp": "2025-11-19T10:30:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel within 5 seconds
- All fields correctly displayed in Teams message card

### 2. Stage Completed

**Trigger**: After successful completion of a rollout stage

**Payload**:

```json
{
  "title": "Stage Completed: Stage1-EastUS",
  "status": "StageCompleted",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS"],
  "timestamp": "2025-11-19T10:45:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel
- Stage name visible in message card

### 3. Approval Required (Wait Action)

**Trigger**: When rollout reaches manual approval gate

**Payload**:

```json
{
  "title": "Approval Required: Stage3-CentralUS",
  "status": "WaitingForApproval",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["CentralUS"],
  "timestamp": "2025-11-19T11:00:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel
- Status clearly indicates manual approval required
- Action URL allows one-click access to approval portal

### 4. Rollout Failed

**Trigger**: When rollout encounters errors or failure condition

**Payload**:

```json
{
  "title": "EV2 Rollout Failed",
  "status": "Failed",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS", "WestUS"],
  "timestamp": "2025-11-19T10:55:00Z",
  "errors": [
    {
      "stage": "Stage2-WestUS",
      "message": "Health endpoint returned 503. Recommendation: Check WestUS service logs."
    }
  ],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel with error indicators
- Error details visible in message card
- Errors array contains stage and message for each failure

### 5. Rollout Completed

**Trigger**: When rollout successfully completes all stages

**Payload**:

```json
{
  "title": "EV2 Rollout Completed Successfully",
  "status": "Completed",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS", "WestUS", "CentralUS"],
  "timestamp": "2025-11-19T11:30:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel with success indicators
- All regions listed in notification

### 6. Rollout Cancelled

**Trigger**: When rollout is manually cancelled

**Payload**:

```json
{
  "title": "EV2 Rollout Cancelled",
  "status": "Cancelled",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["EastUS", "WestUS"],
  "timestamp": "2025-11-19T11:10:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc"
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel
- Cancellation reason visible if provided

### 7. Stress Test Results

**Trigger**: After completion of endpoint stress testing

**Payload**:

```json
{
  "title": "Stress Test Results: Stage2-WestUS",
  "status": "StressTestCompleted",
  "rolloutId": "12345678-1234-1234-1234-123456789abc",
  "service": "AppLensService",
  "artifactVersion": "1.2.3",
  "stageMapVersion": "v2",
  "regions": ["WestUS"],
  "timestamp": "2025-11-19T10:50:00Z",
  "errors": [],
  "actionUrl": "https://ev2portal.azure.net/rollout/12345678-1234-1234-1234-123456789abc",
  "stressTestResults": {
    "endpoint": "https://westus-applens.azurewebsites.net/api/health",
    "totalRequests": 100,
    "successfulRequests": 98,
    "failedRequests": 2,
    "successRate": 98.0,
    "avgLatencyMs": 125.5,
    "p50LatencyMs": 110.0,
    "p95LatencyMs": 180.0,
    "p99LatencyMs": 250.0,
    "passed": true,
    "reason": "Success rate 98.00% >= 95.00% threshold"
  }
}
```

**Success Criteria**:

- HTTP 200/202 response
- Notification appears in Teams channel
- Stress test metrics visible in message card
- Pass/fail status clearly indicated

## HTTP Response Codes

**Expected Responses**:

- `200 OK`: Webhook processed successfully (synchronous)
- `202 Accepted`: Webhook accepted for processing (asynchronous)
- `400 Bad Request`: Invalid payload structure
- `401 Unauthorized`: Invalid signature in URL
- `404 Not Found`: Webhook URL does not exist
- `429 Too Many Requests`: Rate limit exceeded (transient)
- `500 Internal Server Error`: Power Automate flow error (transient)
- `503 Service Unavailable`: Azure Logic Apps temporarily unavailable (transient)

## Error Handling

**Retry Policy**:

- Transient errors (429, 500, 503): Retry with exponential backoff (1s, 2s, 4s) up to 3 attempts
- Non-recoverable errors (400, 401, 404): Log error and continue (do not fail deployment)
- Network timeouts (>10s): Retry with exponential backoff up to 3 attempts

**Error Logging**:

- Log all webhook requests (URL, payload, response code)
- Log retry attempts with delay and attempt number
- Log final failure if all retries exhausted

**Graceful Degradation**:

- Webhook failures should NOT block rollout operations
- Script should log webhook errors but continue monitoring/operations
- User Story US-008 specifies "optional" notifications to Teams

## PowerShell Implementation

**Recommended Implementation**:

```powershell
function Send-TeamsNotification {
    param(
        [string]$WebhookUrl,
        [hashtable]$Payload
    )
    
    $maxRetries = 3
    $retryDelay = 1
    
    for ($attempt = 1; $attempt -le $maxRetries; $attempt++) {
        try {
            $body = $Payload | ConvertTo-Json -Depth 5
            $response = Invoke-RestMethod `
                -Uri $WebhookUrl `
                -Method Post `
                -ContentType "application/json" `
                -Body $body `
                -TimeoutSec 10
            
            Write-Verbose "Teams notification sent successfully (attempt $attempt)"
            return $true
        }
        catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            
            # Non-recoverable errors
            if ($statusCode -in @(400, 401, 404)) {
                Write-Warning "Teams notification failed with non-recoverable error: $statusCode"
                return $false
            }
            
            # Transient errors - retry
            if ($attempt -lt $maxRetries) {
                Write-Warning "Teams notification failed (attempt $attempt/$maxRetries). Retrying in $retryDelay seconds..."
                Start-Sleep -Seconds $retryDelay
                $retryDelay *= 2  # Exponential backoff
            }
            else {
                Write-Warning "Teams notification failed after $maxRetries attempts"
                return $false
            }
        }
    }
}
```

## Power Automate Flow Setup

**Flow Steps** (User-defined):

1. **Trigger**: When a HTTP request is received
2. **Parse JSON**: Parse incoming payload using schema above
3. **Condition**: Branch based on status field
4. **Post message**: Send adaptive card to Teams channel

**Adaptive Card Example** (for Power Automate designer):

```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "@{triggerBody()?['title']}",
      "weight": "Bolder",
      "size": "Large"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Status", "value": "@{triggerBody()?['status']}"},
        {"title": "Service", "value": "@{triggerBody()?['service']}"},
        {"title": "Artifact", "value": "@{triggerBody()?['artifactVersion']}"},
        {"title": "Regions", "value": "@{join(triggerBody()?['regions'], ', ')}"},
        {"title": "Time", "value": "@{triggerBody()?['timestamp']}"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View Rollout",
      "url": "@{triggerBody()?['actionUrl']}"
    }
  ]
}
```

## Contract Tests

Contract tests will validate:

1. ✅ Webhook accepts rollout started notification
2. ✅ Webhook accepts stage completed notification
3. ✅ Webhook accepts approval required notification
4. ✅ Webhook accepts rollout failed notification with errors array
5. ✅ Webhook accepts rollout completed notification
6. ✅ Webhook accepts rollout cancelled notification
7. ✅ Webhook accepts stress test results notification
8. ✅ Retry logic handles transient errors (429, 500, 503)
9. ✅ Non-recoverable errors (400, 401, 404) fail fast without retries
10. ✅ Webhook failures do not block rollout operations

**Test Strategy**: Mock Teams webhook responses in Pester tests using fixtures from `tests/fixtures/deploy-sentinel/mock-teams-responses.json`. Test both success and error scenarios including retry logic.

**Manual Validation**: Document setup of Power Automate flow in quickstart.md with schema and adaptive card template.
