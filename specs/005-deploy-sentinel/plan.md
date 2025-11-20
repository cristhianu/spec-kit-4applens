# Implementation Plan: EV2 Deployment Follower Agent

**Branch**: `005-deploy-sentinel` | **Date**: 2025-11-20 | **Spec**: [specs/005-deploy-sentinel/spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-deploy-sentinel/spec.md`

## Summary

Automate EV2 rollout orchestration through PowerShell-based agent that monitors deployment progress, handles failures, and runs stress tests. Primary approach: Single PowerShell script leveraging EV2 MCP Server and Azure DevOps MCP Server for API integration, with JSON-based state persistence and Pester testing framework.

## Technical Context

**Language/Version**: PowerShell 5.1+ and PowerShell Core 7+ (dual compatibility required)  
**Primary Dependencies**: 
- EV2 MCP Server (dnx package) - mandatory best practices call before all operations
- Azure DevOps MCP Server (npm package) - pipeline and build management
- Native PowerShell cmdlets (Invoke-RestMethod, Start-Job)

**Storage**: JSON state file (`.deploy-sentinel-state.json`) with file locking for idempotency  
**Testing**: Pester framework with contract/integration/unit test structure  
**Target Platform**: Windows (PowerShell 5.1+) and cross-platform (PowerShell Core 7+)  
**Project Type**: Single project - PowerShell script with supporting test infrastructure  
**Performance Goals**: 
- Poll EV2 rollout status every 30 seconds
- Stress test endpoints with configurable concurrency (default 10 requests)
- Complete stress test within 60 seconds per endpoint

**Constraints**: 
- Must work in both PowerShell 5.1 and Core 7+ environments
- Non-blocking execution for long-running rollouts
- Graceful degradation if Teams notifications fail
- State file must survive process crashes (atomic writes)

**Scale/Scope**: 
- Single service deployment per execution
- Monitor rollouts with up to 50 stages
- Support stress testing up to 10 endpoints per stage
- Handle concurrent pipeline execution (up to 5 pipelines)

### State Management Strategy

**Persistence Pattern**: Atomic write using temporary file + rename operation

1. **Write Frequency**:
   - After initialization (rollout triggered)
   - After each status poll (every 30 seconds)
   - After stage completion
   - After rollout reaches terminal state (Completed/Failed/Cancelled)

2. **Atomic Write Implementation**:
   ```powershell
   # Write to temporary file first
   $tempFile = ".deploy-sentinel-state.tmp"
   $stateJson | Out-File -FilePath $tempFile -Encoding UTF8
   
   # Atomic rename (overwrites existing state file)
   Move-Item -Path $tempFile -Destination ".deploy-sentinel-state.json" -Force
   ```

3. **State Schema Versioning**: Include `schemaVersion: "1.0"` field in RolloutState entity for future evolution

4. **Recovery**: On startup, read existing state file if present; validate schema version; resume monitoring if rollout is InProgress

### File Locking Mechanism

**Purpose**: Prevent concurrent execution of deploy-sentinel against the same service

**Lock File Location**: `.deploy-sentinel.lock` (same directory as state file)

**Locking Method**:
```powershell
# Acquire exclusive lock
$lockFile = [System.IO.File]::Open(
    ".deploy-sentinel.lock",
    [System.IO.FileMode]::OpenOrCreate,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)
```

**Stale Lock Detection**:
- Lock file timestamp >1 hour old triggers warning
- User prompted to validate rollout status before proceeding
- Warning message: "Lock file is stale (created >1 hour ago). Another process may have crashed. Verify rollout status before continuing."

**Force Unlock Option**: `-Force` parameter bypasses lock check (use with caution)

**Lock Release**: 
- Automatic on successful completion
- Automatic on controlled cancellation
- Manual via `-Force` parameter if process crashed

### Stage Completion Detection

**How Agent Detects Stage Completion**:

1. **Polling EV2 Rollout Details**: Agent calls `mcp_ev2_mcp_serve_get_rollout_details` every 30 seconds
2. **Stage Status Analysis**: Parses rollout response for stage objects with status field (InProgress/Completed/Failed)
3. **Completion Criteria**: Stage marked complete when:
   - Stage status = "Completed"
   - All regions in stage show successful deployment
   - No blocking errors present
4. **Triggers**: On stage completion detection:
   - Stress tests executed (if enabled)
   - State file updated with new currentStage
   - Teams notification sent (if configured)
   - Agent proceeds to monitor next stage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Simplicity Gate ✅ PASS
- **Project Count**: 1 (single PowerShell script project)
- **Justification**: Single script architecture sufficient for automation workflow

### Anti-Abstraction Gate ✅ PASS
- **No unnecessary layers**: Direct MCP tool calls without abstraction frameworks
- **Plain PowerShell entities**: Using PSCustomObject for RolloutState, DeploymentConfig, ServiceInfo, StressTestResult, NotificationMessage (no custom classes)
- **File-based persistence**: JSON serialization without database or ORM

### Integration-First Gate ✅ PASS
- **3 External dependencies identified**:
  1. EV2 MCP Server - complete contract in `contracts/ev2-mcp-contract.md`
  2. Azure DevOps MCP Server - complete contract in `contracts/ado-mcp-contract.md`
  3. Microsoft Teams Webhook - complete contract in `contracts/teams-webhook-contract.md`
- **Contract tests**: Defined in Phase 3-10 tasks (T017-T020, T061-T063, T071-T072, T079-T080)
- **Test-First approach**: Contract tests written before implementation per Constitution Principle III

## Project Structure

### Documentation (this feature)

```text
specs/005-deploy-sentinel/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 technical research decisions
├── data-model.md        # Phase 1 entity definitions
├── quickstart.md        # Phase 1 usage examples
├── contracts/           # Phase 1 external API contracts
│   ├── ev2-mcp-contract.md
│   ├── ado-mcp-contract.md
│   └── teams-webhook-contract.md
└── tasks.md             # Phase 2 implementation breakdown (100 tasks)
```

### Source Code (repository root)

```text
scripts/powershell/
└── deploy-sentinel.ps1         # Single script with all functions

tests/deploy-sentinel/
├── contract/                    # External API contract tests
│   ├── Ev2McpServer.Tests.ps1
│   ├── AdoMcpServer.Tests.ps1
│   └── TeamsWebhook.Tests.ps1
├── integration/                 # End-to-end workflow tests
│   ├── DeploymentWorkflow.Tests.ps1
│   ├── StateManagement.Tests.ps1
│   └── ErrorRecovery.Tests.ps1
└── unit/                        # Function-level tests
    ├── BranchCreation.Tests.ps1
    ├── StressTesting.Tests.ps1
    ├── ConfigValidation.Tests.ps1
    └── StateManagement.Tests.ps1

tests/fixtures/deploy-sentinel/  # Test data
├── mock-rollout-responses.json
├── mock-pipeline-responses.json
└── test-service-config.json

docs/deploy-sentinel/            # User documentation
├── README.md
├── mcp-setup.md
└── troubleshooting.md

.github/prompts/
└── speckit.deploySentinel.prompt.md  # GitHub Copilot agent prompt
```

**Structure Decision**: Single project structure selected because:
- Feature is a standalone automation script (not a service or application)
- All functionality contained in one PowerShell script file
- No need for separate frontend/backend or multi-language components
- Tests organized by type (contract/integration/unit) per TDD approach
- Minimal complexity aligns with Constitution Simplicity Gate

## Complexity Tracking

> **No violations to justify** - all Constitution gates passed
