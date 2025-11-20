# Azure DevOps MCP Server API Contract

**Feature**: 005-deploy-sentinel | **Contract Type**: External API | **Date**: 2025-11-19

## Overview

This contract defines the expected interactions with the Azure DevOps MCP Server via GitHub Copilot's MCP integration. The ADO MCP Server exposes Azure Pipelines operations as tools that can be invoked by the PowerShell script through the Copilot agent.

## Get Pipeline Definitions

**Tool**: `mcp_ado_pipelines_list`

**Purpose**: Retrieve list of available CI/CD pipelines for a project

**Input**:

```json
{
  "project": "AppLensProject"
}
```

**Expected Output**:

```json
{
  "pipelines": [
    {
      "id": 123,
      "name": "AppLens-CI-Build",
      "folder": "\\CI",
      "revision": 5
    },
    {
      "id": 124,
      "name": "AppLens-E2E-Tests",
      "folder": "\\Tests",
      "revision": 3
    }
  ]
}
```

**Success Criteria**:

- Returns all pipelines for the specified project
- Each pipeline has id, name, folder, revision
- List is sorted by name (alphabetical)

**Failure Scenarios**:

- Project not found: Error "Project 'AppLensProject' not found"
- Authentication error: Error "Authentication failed. Check Azure DevOps token"
- Permission denied: Error "User does not have read access to pipelines"

## Run Pipeline

**Tool**: `mcp_ado_pipelines_run_pipeline`

**Purpose**: Trigger execution of a specific pipeline with optional parameters

**Input**:

```json
{
  "project": "AppLensProject",
  "pipelineId": 123,
  "resources": {
    "repositories": {
      "self": {
        "refName": "refs/heads/005-deploy-sentinel",
        "version": "abc123def456"
      }
    }
  },
  "templateParameters": {
    "environment": "production",
    "region": "eastus"
  }
}
```

**Expected Output**:

```json
{
  "id": 98765,
  "name": "AppLens-CI-Build",
  "state": "InProgress",
  "createdDate": "2025-11-19T10:30:00Z",
  "url": "https://dev.azure.com/org/AppLensProject/_build/results?buildId=98765"
}
```

**Success Criteria**:

- Returns valid build id
- Initial state is "InProgress"
- URL is valid link to build results
- Build starts within 30 seconds

**Failure Scenarios**:

- Pipeline not found: Error "Pipeline {pipelineId} not found"
- Invalid branch: Error "Branch {refName} does not exist"
- Invalid parameters: Error "Required parameter {param} is missing"
- Pipeline queue full: Error "Pipeline queue is full. Retry later" (transient)

## Get Build Status

**Tool**: `mcp_ado_build_get`

**Purpose**: Retrieve current status and details of a pipeline run

**Input**:

```json
{
  "project": "AppLensProject",
  "buildId": 98765
}
```

**Expected Output**:

```json
{
  "id": 98765,
  "buildNumber": "20251119.1",
  "status": "InProgress",
  "result": null,
  "startTime": "2025-11-19T10:30:00Z",
  "finishTime": null,
  "sourceBranch": "refs/heads/005-deploy-sentinel",
  "sourceVersion": "abc123def456",
  "definition": {
    "id": 123,
    "name": "AppLens-CI-Build"
  },
  "logs": {
    "url": "https://dev.azure.com/org/AppLensProject/_apis/build/builds/98765/logs"
  }
}
```

**Success Criteria**:

- Returns complete build information
- status is one of: "NotStarted", "InProgress", "Completed"
- result is one of: null (in progress), "Succeeded", "Failed", "Canceled", "PartiallySucceeded"
- Completed builds have finishTime
- In-progress builds have null result and finishTime

**Failure Scenarios**:

- Build not found: Error "Build {buildId} not found"
- Project not found: Error "Project '{project}' not found"

## Get Build Logs

**Tool**: `mcp_ado_build_get_logs`

**Purpose**: Retrieve log output from a specific pipeline run

**Input**:

```json
{
  "project": "AppLensProject",
  "buildId": 98765,
  "logId": 1
}
```

**Expected Output**:

```json
{
  "logId": 1,
  "lineCount": 150,
  "content": [
    "Starting: Initialize job",
    "Agent name: 'Hosted Agent'",
    "Agent version: '3.218.0'",
    "...",
    "Finishing: Initialize job"
  ]
}
```

**Success Criteria**:

- Returns complete log content as array of lines
- Each line is a string
- Line count matches array length
- Content is in chronological order

**Failure Scenarios**:

- Build not found: Error "Build {buildId} not found"
- Log not found: Error "Log {logId} not found for build {buildId}"

## Cancel Build

**Tool**: `mcp_ado_build_update`

**Purpose**: Cancel an in-progress pipeline run

**Input**:

```json
{
  "project": "AppLensProject",
  "buildId": 98765,
  "status": "Cancelling"
}
```

**Expected Output**:

```json
{
  "id": 98765,
  "status": "Cancelling",
  "result": null,
  "finishTime": null
}
```

**Success Criteria**:

- Returns updated build status
- Status changes to "Cancelling" immediately
- Build stops within 60 seconds
- Final status becomes "Completed" with result "Canceled"

**Failure Scenarios**:

- Build not found: Error "Build {buildId} not found"
- Already completed: Error "Cannot cancel completed build"

## Create Git Branch

**Tool**: `mcp_ado_repo_create_branch`

**Purpose**: Create a new branch in a repository

**Input**:

```json
{
  "repositoryId": "12345678-1234-1234-1234-123456789abc",
  "branchName": "deploy/rollout-12345678",
  "sourceBranchName": "main",
  "sourceCommitId": null
}
```

**Expected Output**:

```json
{
  "name": "refs/heads/deploy/rollout-12345678",
  "objectId": "def456abc789",
  "creator": {
    "displayName": "User Name",
    "uniqueName": "user@example.com"
  },
  "url": "https://dev.azure.com/org/AppLensProject/_git/AppLens/refs?filter=refs/heads/deploy/rollout-12345678"
}
```

**Success Criteria**:

- Returns new branch reference
- objectId is valid commit SHA
- Branch is immediately available in repository
- Branch points to latest commit of source branch

**Failure Scenarios**:

- Repository not found: Error "Repository {repositoryId} not found"
- Branch already exists: Error "Branch {branchName} already exists"
- Source branch not found: Error "Source branch {sourceBranchName} does not exist"
- Permission denied: Error "User does not have create branch permission"

## Get Repository Information

**Tool**: `mcp_ado_repo_get`

**Purpose**: Retrieve repository details including default branch

**Input**:

```json
{
  "repositoryId": "12345678-1234-1234-1234-123456789abc"
}
```

**Expected Output**:

```json
{
  "id": "12345678-1234-1234-1234-123456789abc",
  "name": "AppLens",
  "defaultBranch": "refs/heads/main",
  "remoteUrl": "https://dev.azure.com/org/AppLensProject/_git/AppLens",
  "project": {
    "id": "87654321-4321-4321-4321-cba987654321",
    "name": "AppLensProject"
  }
}
```

**Success Criteria**:

- Returns complete repository information
- defaultBranch is valid reference
- remoteUrl is accessible
- Project information is included

**Failure Scenarios**:

- Repository not found: Error "Repository {repositoryId} not found"

## Error Handling

**Standard Error Response**:

```json
{
  "error": {
    "code": "PipelineNotFound",
    "message": "Pipeline 123 not found in project 'AppLensProject'",
    "timestamp": "2025-11-19T10:30:00Z"
  }
}
```

**Error Codes**:

- `ProjectNotFound`: Azure DevOps project does not exist
- `PipelineNotFound`: Pipeline does not exist in project
- `BuildNotFound`: Build does not exist
- `RepositoryNotFound`: Repository does not exist
- `BranchNotFound`: Branch does not exist
- `AuthenticationFailed`: Invalid or missing Azure DevOps token
- `PermissionDenied`: User lacks required permissions
- `InvalidParameter`: Parameter validation failed
- `QueueFull`: Pipeline queue at capacity (transient)
- `InternalError`: Azure DevOps service error (transient)

**Retry Policy**:

- Transient errors (`QueueFull`, `InternalError`, HTTP 503, 429): Retry with exponential backoff (max 3 attempts)
- Non-recoverable errors (authentication, not found, permission): Fail immediately
- Script should log all ADO API calls and responses for debugging

## Polling Strategy

For build status monitoring:

- Poll every 30 seconds (as specified in plan.md performance goals)
- Use `mcp_ado_build_get` to check status
- Continue until status="Completed"
- Check result field: "Succeeded", "Failed", "Canceled", "PartiallySucceeded"

**Example Polling Loop** (pseudocode):

```powershell
do {
    $build = mcp_ado_build_get -project $project -buildId $buildId
    if ($build.status -eq "Completed") {
        return $build.result
    }
    Start-Sleep -Seconds 30
} while ($true)
```

## Contract Tests

Contract tests will validate:

1. ✅ Get pipeline definitions returns list for valid project
2. ✅ Run pipeline starts build and returns build ID
3. ✅ Get build status returns complete build information
4. ✅ Get build logs returns log content as array of lines
5. ✅ Cancel build terminates in-progress build
6. ✅ Create git branch creates new branch from source
7. ✅ Get repository information returns repository details
8. ✅ Error responses follow standard format
9. ✅ Transient errors trigger retry logic
10. ✅ Non-recoverable errors fail fast
11. ✅ Polling loop terminates when build completes

**Test Strategy**: Mock Azure DevOps MCP Server responses in Pester tests using fixtures from `tests/fixtures/deploy-sentinel/mock-pipeline-responses.json`
