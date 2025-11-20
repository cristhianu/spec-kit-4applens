# Research: EV2 Deployment Follower Agent

**Feature**: 005-deploy-sentinel | **Phase**: 0 (Outline & Research) | **Date**: 2025-11-19

## Research Tasks

This document consolidates findings from technical research to resolve unknowns and inform design decisions.

## 1. EV2 MCP Server Integration

**Research Question**: How does the EV2 MCP Server expose rollout operations? What are the available commands and expected payloads?

**Decision**: Use EV2 MCP Server via VS Code MCP integration with `mcp_ev2_mcp_serve_*` tools

**Rationale**:

- EV2 MCP Server installed via `dnx Ev2.McpServer` from <https://msazure.visualstudio.com/One/_git/Deployment-Ease>
- Exposes tools for:
  - `start_rollout`: Trigger new EV2 rollout with artifact version, stage map, and scope
  - `start_validation_rollout`: Test artifacts/stage maps without actual deployment
  - `get_latest_rollouts`: Retrieve recent rollout history
  - `get_rollout_details`: Get detailed info for specific rollout (status, stages, regions, errors)
  - `get_artifact_versions`: List available artifact versions for service
  - `get_stage_map_versions`: List available stage map versions
  - Service registration tools for managing services and service groups

**Alternatives Considered**:

- Direct EV2 REST API calls: Rejected due to complexity of authentication, endpoint discovery, and payload construction
- Azure CLI with EV2 extension: Not available; EV2 doesn't have standard Azure CLI integration

**Best Practices**:

- Always call `get_ev2_best_practices` tool FIRST before using any EV2 MCP tools (mandatory per tool documentation)
- Use `start_validation_rollout` for dry-run testing before actual deployments
- Query latest artifact/stage map versions rather than hardcoding
- Handle EV2 API errors explicitly - fail fast on authentication or configuration issues

**Implementation Notes**:

- MCP tools are available in GitHub Copilot context when `.vscode/mcp.json` is configured
- Tools return structured data (JSON) that can be parsed in PowerShell
- Endpoint parameter optional; defaults to configured endpoint in MCP settings

## 2. Azure DevOps MCP Server Integration

**Research Question**: How does the ADO MCP Server expose pipeline operations? What commands are available?

**Decision**: Use Azure DevOps MCP Server via VS Code MCP integration with `mcp_ado_pipelines_*` tools

**Rationale**:

- ADO MCP Server installed via npm: `npm install -g mcp-server-azuredevops` from <https://github.com/microsoft/azure-devops-mcp>
- Exposes tools for:
  - `run_pipeline`: Start pipeline run with parameters (project, pipelineId, branch, variables)
  - Get pipeline run status and logs
  - Retrieve project and repository information
  - Work item integration for deployment tracking

**Alternatives Considered**:

- Azure DevOps REST API: Rejected due to complexity and authentication overhead
- Azure CLI `az pipelines run`: Viable but requires Azure CLI installation; MCP server provides better integration

**Best Practices**:

- Query pipeline definition to validate it exists before attempting to trigger
- Pass environment-specific variables (environment, branch, artifactVersion) to pipeline runs
- Monitor pipeline status via polling (similar pattern to EV2 rollout monitoring)
- Retrieve logs on failure for actionable error messages

**Implementation Notes**:

- Requires Azure DevOps PAT (Personal Access Token) configured in MCP settings
- Tools available in GitHub Copilot context when MCP server is configured
- Pipeline runs are asynchronous - must poll for completion

## 3. PowerShell Cross-Platform Compatibility

**Research Question**: What are the key differences between PowerShell 5.1 and PowerShell Core 7+ that affect this implementation?

**Decision**: Write PowerShell code compatible with both versions using common cmdlets and testing both

**Rationale**:

- PowerShell 5.1 (Windows-only) still widely used in enterprise environments
- PowerShell Core 7+ (cross-platform) preferred for modern development
- Key compatibility considerations:
  - File paths: Use `Join-Path` and `$PSScriptRoot` (both versions)
  - JSON: `ConvertTo-Json -Depth 10` and `ConvertFrom-Json` (both versions)
  - HTTP requests: `Invoke-RestMethod` available in both (Teams webhooks)
  - Git operations: `git` command-line (external, available in both)

**Alternatives Considered**:

- PowerShell Core only: Rejected due to enterprise compatibility requirements (FR-051)
- Windows PowerShell only: Rejected due to cross-platform requirement

**Best Practices**:

- Avoid `$IsWindows`, `$IsLinux` variables (PS Core only) - use `$PSVersionTable.PSEdition` instead
- Test JSON depth serialization (PS 5.1 defaults to depth 2, PS 7 to depth 10)
- Use `-ErrorAction Stop` consistently for fail-fast behavior
- Avoid advanced features like pipeline chaining with `&&` (PS 7+ only)

**Implementation Notes**:

- Test in both environments during development
- CI pipeline should run tests in both PowerShell 5.1 and PowerShell Core 7+
- Document minimum version requirement: PowerShell 5.1

## 4. Idempotent State Management

**Research Question**: How should state be persisted to enable idempotent operations and recovery from interruption?

**Decision**: JSON state file (`.deploy-sentinel-state.json`) with file locking via PowerShell

**Rationale**:

- Simple, readable format (JSON)
- No external dependencies (no database, no Azure Storage)
- PowerShell native JSON serialization (`ConvertTo-Json`, `ConvertFrom-Json`)
- File locking via `[System.IO.File]::Open()` with exclusive access
- State includes: rolloutId, serviceId, environment, currentStage, timestamp, status

**Alternatives Considered**:

- Azure Table Storage: Rejected due to external dependency and authentication complexity
- SQLite database: Rejected due to external dependency (requires module installation)
- Environment variables: Rejected due to lack of persistence across script invocations

**Best Practices**:

- Write state file atomically (temp file + rename)
- Include version field for future schema evolution
- Clean up state file on successful completion
- Include timestamp for stale state detection (warn if >24 hours old)
- Lock file during operations to prevent concurrent execution

**Implementation Notes**:

- Lock pattern: Try-lock at start, fail fast if locked (another instance running)
- State schema: `{ version: 1, rolloutId, serviceId, environment, stage, status, timestamp, errors }`
- Resume logic: Check state file existence → validate still active → resume from last stage

## 5. Stress Testing Implementation

**Research Question**: How should stress testing be implemented in PowerShell without external dependencies?

**Decision**: Use `Invoke-RestMethod` with parallel jobs (`Start-Job`) for concurrent HTTP requests

**Rationale**:

- `Invoke-RestMethod` built into PowerShell (no external dependencies)
- `Start-Job` enables concurrent requests (simulate load)
- Measure response times via `Measure-Command`
- Support bearer token authentication via `-Headers` parameter
- Calculate percentiles (p50, p95, p99) via sorting and indexing

**Alternatives Considered**:

- External tools (Apache Bench, wrk): Rejected due to external dependency requirement
- PowerShell 7+ ForEach-Object -Parallel: Rejected due to PS 5.1 compatibility requirement
- Sequential requests: Rejected due to performance (can't achieve 100 requests in reasonable time)

**Best Practices**:

- Configurable request count and duration (defaults: 100 requests, 30 seconds)
- Retry logic for transient failures (max 3 retries per request)
- Collect all timing data before calculating percentiles
- Report: success rate, error rate, average, p50, p95, p99 latency
- Timeout per request (default: 10 seconds)

**Implementation Notes**:

- Use `Start-Job` scriptblock to send requests in parallel
- Wait for all jobs to complete before calculating statistics
- Parse `Measure-Command` output to get milliseconds
- Handle authentication headers: `@{ Authorization = "Bearer $token" }`

## 6. Teams Webhook Integration (Power Automate)

**Research Question**: What is the payload structure for Power Automate Workflow Webhooks?

**Decision**: Use Power Automate HTTP webhook trigger with flexible JSON payload defined by user's flow

**Rationale**:

- Power Automate Workflow Webhooks accept arbitrary JSON payloads
- User creates flow with "When an HTTP request is received" trigger
- Flow defines expected JSON schema (user-configurable)
- More flexible than deprecated Office 365 Connector Cards
- Allows custom routing, formatting, and approval workflows

**Alternatives Considered**:

- Office 365 Incoming Webhook (MessageCard): Deprecated by Microsoft, still works but not recommended
- Adaptive Cards via webhooks: Requires more complex payload structure, limited support in webhooks

**Best Practices**:

- Document recommended payload schema in quickstart guide
- Include: `title`, `status` (Success/Failed/Warning), `serviceGroupName`, `environment`, `rolloutId`, `deployedRegions`, `duration`, `errorSummary`, `dashboardUrl`
- User customizes flow to format as Adaptive Card or send to specific channels
- Fail gracefully if webhook unreachable (log locally, continue deployment)

**Implementation Notes**:

- HTTP POST with `Invoke-RestMethod -Method Post -Uri $webhookUrl -Body $json -ContentType 'application/json'`
- Webhook URL format: `https://prod-XX.logic.azure.com:443/workflows/{guid}/triggers/manual/paths/invoke?...`
- Response: 202 Accepted (async processing) or 200 OK
- Timeout: 10 seconds (webhook should respond quickly)

## 7. Git Branch Management in PowerShell

**Research Question**: How should git operations be handled in PowerShell for cross-platform compatibility?

**Decision**: Use git command-line tool directly (via `git` executable) with error handling

**Rationale**:

- Git CLI available on Windows, Linux, macOS
- PowerShell's native git integration (posh-git) not guaranteed to be installed
- Direct `git` commands work in both PowerShell 5.1 and 7+
- Simple error handling via `$LASTEXITCODE` and `-ErrorAction Stop`

**Alternatives Considered**:

- PowerGit module: Rejected due to external dependency
- LibGit2Sharp .NET library: Rejected due to external dependency and complexity
- posh-git: Not guaranteed to be installed, wrapper around git CLI

**Best Practices**:

- Validate git is in PATH before operations: `Get-Command git -ErrorAction Stop`
- Check git repository initialized: `git rev-parse --git-dir 2>$null`
- Create branch: `git checkout -b "deploy/PPE/ServiceGroup/$(Get-Date -Format 'yyyyMMdd-HHmmss')"`
- Handle branch exists: Check `git branch --list` before creating
- Capture git errors: Check `$LASTEXITCODE -ne 0` after each command

**Implementation Notes**:

- Branch naming pattern: `deploy/{environment}/{serviceGroupName}/{timestamp}`
- Timestamp format: ISO-like for sortability (yyyyMMdd-HHmmss)
- Don't commit/push automatically (user decides when to commit deployment changes)
- Fail fast if git operations fail (deployment should not proceed)

## 8. Error Handling and Retry Strategies

**Research Question**: What retry strategies should be implemented for different failure types?

**Decision**: Exponential backoff for transient failures, fail-fast for non-recoverable errors

**Rationale**:

- Transient failures (network, API throttling): Retry with exponential backoff (1s, 2s, 4s)
- Non-recoverable errors (authentication, invalid config): Fail immediately with clear message
- Max retry count: 3 attempts for transient failures
- Critical failures (deployment failure in production): Cancel remaining stages

**Alternatives Considered**:

- Fixed retry interval: Rejected due to potential for overwhelming services
- Unlimited retries: Rejected due to risk of infinite loops
- No retries: Rejected due to fragility with transient network issues

**Best Practices**:

- Classify errors: Transient (HTTP 429, 503, network timeout) vs Non-recoverable (401, 403, 404)
- Log retry attempts with backoff timing
- Distinguish between MCP server errors (fail fast) vs EV2 API transient failures (retry)
- Teams webhook failures: Non-critical, log locally and continue
- State file locking failures: Fail immediately (concurrent execution detected)

**Implementation Notes**:

- Retry loop: `for ($i = 1; $i -le 3; $i++) { try { ... } catch { Start-Sleep (2^$i); if ($i -eq 3) { throw } } }`
- Error classification via HTTP status codes or exception types
- Clear error messages: "Failed after 3 retries: {reason}. Last error: {details}"

## Summary

All technical unknowns resolved. Key decisions:

1. **EV2 Integration**: Use EV2 MCP Server with best practices tool call first
2. **ADO Integration**: Use ADO MCP Server for pipeline operations
3. **PowerShell Compatibility**: Target both 5.1 and Core 7+ with common cmdlets
4. **State Management**: JSON file with file locking for idempotency
5. **Stress Testing**: Invoke-RestMethod + Start-Job for concurrent requests
6. **Teams Webhooks**: Power Automate format with flexible user-defined schema
7. **Git Operations**: Direct git CLI with proper error handling
8. **Error Handling**: Exponential backoff for transient, fail-fast for critical

Ready to proceed to Phase 1 (Design & Contracts).
