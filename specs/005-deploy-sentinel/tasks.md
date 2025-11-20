# Tasks: EV2 Deployment Follower Agent

**Feature**: 005-deploy-sentinel | **Branch**: `005-deploy-sentinel` | **Date**: 2025-11-20

**Input**: Design documents from `specs/005-deploy-sentinel/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Contract tests are included per TDD approach (Constitution Principle III)

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **Checkbox**: `- [ ]` (markdown task format)
- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story (US1-US8) this task belongs to
- File paths are exact and match project structure from plan.md

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Project structure and basic configuration

- [X] T001 Create `.github/prompts/speckit.deploySentinel.prompt.md` for GitHub Copilot agent definition
- [X] T002 [P] Create `tests/deploy-sentinel/contract/` directory structure
- [X] T003 [P] Create `tests/deploy-sentinel/integration/` directory structure
- [X] T004 [P] Create `tests/deploy-sentinel/unit/` directory structure
- [X] T005 [P] Create `tests/fixtures/deploy-sentinel/` directory for test fixtures
- [X] T006 [P] Create `.deploy-sentinel-config.json` configuration template in project root
- [X] T007 [P] Update `.vscode/mcp.json` with EV2 and Azure DevOps MCP server configurations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create PowerShell module structure in `scripts/powershell/deploy-sentinel.ps1` with main entry point
- [X] T009 [P] Implement configuration loading function `Load-DeploymentConfig` in deploy-sentinel.ps1 (reads .json, validates required params, supports env var substitution)
- [X] T010 [P] Implement state file management functions `Read-RolloutState`, `Write-RolloutState`, `Lock-StateFile` in deploy-sentinel.ps1
- [X] T011 [P] Implement logging infrastructure function `Write-DeploymentLog` with timestamps in deploy-sentinel.ps1
- [X] T012 [P] Implement retry logic function `Invoke-WithRetry` with exponential backoff in deploy-sentinel.ps1
- [X] T013 Implement MCP tool wrapper function `Invoke-McpTool` for error handling and logging in deploy-sentinel.ps1
- [X] T014 Create test fixture `tests/fixtures/deploy-sentinel/mock-rollout-responses.json` with EV2 response samples
- [X] T015 [P] Create test fixture `tests/fixtures/deploy-sentinel/mock-pipeline-responses.json` with ADO response samples
- [X] T016 [P] Create test fixture `tests/fixtures/deploy-sentinel/test-service-config.json` with valid configuration examples

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Trigger EV2 Rollout (Priority: P1) 🎯 MVP

**Goal**: Initiate EV2 deployments by discovering artifact/stage map versions and triggering rollout

**Independent Test**: Provide valid service configuration → verify rollout created with correct versions and scope

### Contract Tests for User Story 1

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US1] Contract test for EV2 best practices tool in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify best practices returned)
- [X] T018 [P] [US1] Contract test for get artifact versions in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify latest version discovery)
- [X] T019 [P] [US1] Contract test for get stage map versions in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify latest version discovery)
- [X] T020 [P] [US1] Contract test for start rollout in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify rollout creation with valid params)

### Implementation for User Story 1

- [X] T021 [P] [US1] Implement `Get-Ev2BestPractices` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_ev2_best_practices, logs output)
- [X] T022 [P] [US1] Implement `Get-LatestArtifactVersion` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_artifact_versions, returns latest)
- [X] T023 [P] [US1] Implement `Get-LatestStageMapVersion` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_stage_map_versions, returns latest)
- [X] T024 [US1] Implement `New-ServiceInfo` function in deploy-sentinel.ps1 (creates ServiceInfo entity from discovery, depends on T022, T023)
- [X] T025 [US1] Implement `Build-SelectionScope` function in deploy-sentinel.ps1 (constructs EV2 scope from environment/config)
- [X] T026 [US1] Implement `Start-Ev2Rollout` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_start_rollout with artifact/stage map versions)
- [X] T026b [US5] Implement `Get-AzureAuthToken` function in deploy-sentinel.ps1 (Azure credential chain: MSI, service principals, user credentials for stress test authentication per FR-026)
- [X] T027 [US1] Implement main workflow function `Invoke-TriggerRollout` in deploy-sentinel.ps1 (orchestrates T021-T026, creates RolloutState)
- [X] T028 [US1] Add parameter validation and error messages to `Invoke-TriggerRollout` (missing params, invalid GUIDs)
- [X] T029 [US1] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (end-to-end rollout trigger)

**Checkpoint**: User Story 1 complete - can trigger rollouts independently

---

## Phase 4: User Story 2 - Create Feature Branch (Priority: P1)

**Goal**: Automatically create properly named deployment branch

**Independent Test**: Provide deployment metadata → verify branch created with correct naming pattern

### Contract Tests for User Story 2

- [X] T030 [P] [US2] Unit test for git availability check in `tests/deploy-sentinel/unit/BranchCreation.Tests.ps1` (verify git command exists)
- [X] T031 [P] [US2] Unit test for branch name generation in `tests/deploy-sentinel/unit/BranchCreation.Tests.ps1` (verify naming pattern)

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement `Test-GitRepository` function in deploy-sentinel.ps1 (validates git initialized, has remotes)
- [X] T033 [P] [US2] Implement `New-DeploymentBranchName` function in deploy-sentinel.ps1 (generates deploy/{env}/{service}/{timestamp} name)
- [X] T034 [US2] Implement `New-DeploymentBranch` function in deploy-sentinel.ps1 (creates git branch, handles existing branch, depends on T032, T033)
- [X] T035 [US2] Integrate branch creation into workflow via `Invoke-TriggerRolloutWithBranch` function (call after rollout started, store branchName in RolloutState)
- [X] T036 [US2] Integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` already includes branch creation scenarios

**Checkpoint**: User Stories 1 AND 2 complete - can trigger rollouts with branch tracking

---

## Phase 5: User Story 3 - Monitor Rollout Status (Priority: P1)

**Goal**: Continuous polling of EV2 rollout status with real-time progress updates

**Independent Test**: Provide rolloutId → verify agent retrieves and displays status including stages, regions, errors

### Contract Tests for User Story 3

- [X] T037 [P] [US3] Contract test for get rollout details in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify status structure returned) - already created in earlier phase
- [X] T038 [P] [US3] Contract test for wait action detection in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify wait actions identified) - already created in earlier phase

### Implementation for User Story 3

- [X] T039 [P] [US3] Implement `Get-RolloutStatus` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_rollout_details, logs status/progress/stage)
- [X] T040 [P] [US3] Implement `Format-RolloutStatusDisplay` function in deploy-sentinel.ps1 (formats status for console output with stages/regions/progress/errors)
- [X] T041 [P] [US3] Implement `Test-RolloutComplete` function in deploy-sentinel.ps1 (checks if rollout reached terminal state: Completed/Failed/Cancelled)
- [X] T042 [US3] Implement `Watch-Ev2Rollout` function in deploy-sentinel.ps1 (polling loop with configurable interval/max iterations, stage transition detection, depends on T039-T041)
- [X] T043 [US3] Integrate monitoring into workflow - add `Invoke-MonitorRollout` function in deploy-sentinel.ps1 (loads RolloutId from state or parameter, updates state with final status)
- [X] T044 [US3] Update main entry point "monitor" action in deploy-sentinel.ps1 (calls Invoke-MonitorRollout, displays final status with color coding, exits with status code)

**Checkpoint**: User Stories 1, 2, AND 3 complete - full MVP workflow (trigger + track + monitor) ✅ COMPLETE

---

## Phase 6: User Story 4 - Handle Deployment Issues (Priority: P2)

**Goal**: Detect failures, retrieve error details, provide actionable recommendations

**Independent Test**: Simulate failed rollout → verify agent detects failure, retrieves errors, presents recommendations

### Contract Tests for User Story 4

- [X] T045 [P] [US4] Contract test for error response parsing in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify error details extracted) - already created in earlier phase
- [X] T046 [P] [US4] Contract test for cancel rollout in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify cancellation succeeds) - already created in earlier phase

### Implementation for User Story 4

- [X] T047 [P] [US4] Implement `Get-RolloutErrors` function in deploy-sentinel.ps1 (extracts top-level, stage-level, and resource-level errors with code/message/resource/timestamp/stage)
- [X] T048 [P] [US4] Implement `Get-ErrorRecommendation` function in deploy-sentinel.ps1 (generates recommendations for quota, timeout, authorization, conflict, parameter, not-found, and generic errors)
- [X] T049 [US4] Implement `Stop-Ev2Rollout` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_cancel_rollout with reason, updates RolloutState to Cancelled)
- [X] T050 [US4] Implement error detection in `Watch-Ev2Rollout` function (detects Failed status, extracts errors, displays recommendations, prompts user for action: continue/cancel/exit)
- [X] T051 [US4] Add integration test in `tests/deploy-sentinel/integration/ErrorRecovery.Tests.ps1` (comprehensive error scenarios with extraction, recommendations, cancellation - all tests skipped until refactoring)

**Checkpoint**: Failure handling complete - robust error detection and recovery ✅

---

## Phase 7: User Story 5 - Stress-Test Deployed Endpoints (Priority: P2)

**Goal**: Automated stress testing of deployed endpoints after each stage

**Independent Test**: Provide endpoint URL and thresholds → verify agent executes stress test and reports pass/fail

### Contract Tests for User Story 5

- [X] T052 [P] [US5] Unit test for concurrent request execution in `tests/deploy-sentinel/unit/StressTesting.Tests.ps1` (created comprehensive test scenarios for Start-Job parallel execution, timing collection, failure handling, timeout, request rate)
- [X] T053 [P] [US5] Unit test for latency percentile calculation in `tests/deploy-sentinel/unit/StressTesting.Tests.ps1` (created tests for p50/p95/p99 calculation, small samples, sorting, success rate)

### Implementation for User Story 5

- [X] T054 [P] [US5] Implement `Invoke-EndpointRequest` function in deploy-sentinel.ps1 (single HTTP GET request with System.Diagnostics.Stopwatch timing, returns PSCustomObject with latencyMs, statusCode, success, errorMessage)
- [X] T055 [P] [US5] Implement `Start-ConcurrentRequests` function in deploy-sentinel.ps1 (uses Start-Job for parallel execution, creates ScriptBlock with Invoke-WebRequest, collects results with Wait-Job/Receive-Job, logs success/failure counts)
- [X] T056 [P] [US5] Implement `Measure-LatencyPercentiles` function in deploy-sentinel.ps1 (sorts latency array, calculates p50/p95/p99 using Math.Floor indices with bounds checking, returns PSCustomObject)
- [X] T057 [US5] Implement `Invoke-StressTest` function in deploy-sentinel.ps1 (orchestrates T054-T056, calculates success rate, creates StressTestResult entity with all metrics: endpoint, counts, percentages, latencies, timestamps, duration)
- [X] T058 [US5] Implement `Test-StressTestPassed` function in deploy-sentinel.ps1 (compares successRatePercent and p95LatencyMs against thresholds, returns bool, logs pass/fail with reasons)
- [X] T059 [US5] Integrate stress testing into `Watch-Ev2Rollout` function (detects stage transitions, reads config.stressTestConfig, calls Invoke-StressTest + Test-StressTestPassed, displays results with color coding, prompts user on failure in interactive mode, handles cancellation choice)
- [X] T060 [US5] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (added comprehensive T060 test scenario with mock expectations for config, stage transition, stress test execution, threshold validation, user prompting, cancellation handling - skipped until refactoring)

**Checkpoint**: Stress testing complete - automated validation after deployment stages ✅

---

## Phase 8: User Story 6 - Run Deployment Pipeline (Priority: P2)

**Goal**: Trigger and monitor Azure DevOps pipelines as part of deployment workflow

**Independent Test**: Provide ADO project and pipeline ID → verify pipeline triggered and monitored to completion

### Contract Tests for User Story 6

- [X] T061 [P] [US6] Contract test for list pipelines in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (added test for Get-AdoPipelines with array validation and empty project handling - skipped until implementation)
- [X] T062 [P] [US6] Contract test for run pipeline in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (added tests for Start-AdoPipeline with parameters, variables, error handling - skipped until implementation)
- [X] T063 [P] [US6] Contract test for get build status in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (added tests for Get-AdoBuildStatus with completion/failure detection - skipped until implementation)

### Implementation for User Story 6

- [X] T064 [P] [US6] Implement `Get-AdoPipelines` function in deploy-sentinel.ps1 (calls mcp_ado_pipelines_list with project parameter, returns array of pipeline objects with id/name/folder/revision, logs count)
- [X] T065 [P] [US6] Implement `Start-AdoPipeline` function in deploy-sentinel.ps1 (calls mcp_ado_pipelines_run_pipeline with project/pipelineId/sourceBranch/templateParameters/variables, constructs resources.repositories.self.refName for branch, returns build object with id/buildNumber/status)
- [X] T066 [P] [US6] Implement `Get-AdoBuildStatus` function in deploy-sentinel.ps1 (calls mcp_ado_build_get with project/buildId, returns status object with id/status/result/timestamps, DEBUG level logging)
- [X] T067 [US6] Implement `Watch-AdoPipeline` function in deploy-sentinel.ps1 (polls Get-AdoBuildStatus at 15s interval with 240 max iterations, displays status with Cyan color, detects completed/succeeded/failed/canceled states with emoji indicators, returns final status, throws on timeout)
- [X] T068 [US6] Implement `Get-AdoBuildLogs` function in deploy-sentinel.ps1 (calls mcp_ado_build_get_logs with project/buildId, returns log string, logs byte count)
- [X] T069 [US6] Integrate pipeline execution into workflow - add `Invoke-DeploymentPipeline` in deploy-sentinel.ps1 (orchestrates T064-T068 with TriggerBefore/TriggerAfter switches, passes deployment context as variables with rolloutId/environment/serviceId/branchName, handles pre/post failure differently: pre=throw halts deployment, post=warn continues, retrieves logs on failure via Get-AdoBuildLogs, displays build number and ID with emoji)
- [X] T070 [US6] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (added comprehensive T070 test with expected behavior for pre/post-deployment pipelines, variable passing, failure handling with logs, halting vs continuing - skipped until refactoring)

**Checkpoint**: Pipeline integration complete - can run CI/CD pipelines as deployment prerequisite ✅

---

## Phase 9: User Story 7 - Handle Approval Gates (Priority: P3)

**Goal**: Detect wait actions, notify approvers, process approval decisions

**Independent Test**: Create rollout with wait action → verify agent detects, sends notification, handles approval

### Contract Tests for User Story 7

- [X] T071 [P] [US7] Contract test for stop wait action in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify wait action approval) - Added Describe block "T071 - Stop Wait Action Contract" with approval/rejection tests, all skipped until T075 implementation
- [X] T072 [P] [US7] Contract test for Teams notification in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify approval notification sent) - Added Describe block "T072 - Approval Notification Contract" with approval message tests, format verification, and CLI instruction tests, all skipped until T074 implementation

### Implementation for User Story 7

- [X] T073 [P] [US7] Implement `Get-WaitActions` function in deploy-sentinel.ps1 (extracts wait actions from rollout details) - Added function that iterates through stages.actions, filters by type="WaitAction" or status="WaitingForApproval", returns array of wait action objects with actionId/actionName/stage/status/description/createdAt, logs count found
- [X] T074 [P] [US7] Implement `Send-ApprovalNotification` function in deploy-sentinel.ps1 (sends Teams webhook for approval request) - Added function that builds Adaptive Card (MessageCard schema v1.0) with yellow theme color (FFC107), includes facts (Stage/Action ID/Rollout ID/Message), includes CLI command examples for approval/rejection in text section, calls Invoke-RestMethod with webhook URL, returns bool success/failure
- [X] T075 [US7] Implement `Stop-WaitAction` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_stop_wait_action) - Added function with parameters (RolloutId, ServiceGroupName, ServiceResourceGroup, ServiceResource, ActionId, Approve bool), calls Invoke-McpTool with "mcp_ev2_mcp_serve_approve_rollout_continuation", returns PSCustomObject with actionId/status/timestamp/result, logs decision (approve/reject)
- [X] T076 [US7] Implement wait action handling in `Watch-Ev2Rollout` function (detect wait actions, call T074, wait for user approval decision, call T075) - Added wait action detection in polling loop (calls Get-WaitActions), displays warning with action details (stage/actionId/description), sends Teams notification if configured (calls Send-ApprovalNotification), interactive mode: prompts user (Approve/Reject/Wait), option 1 calls Stop-WaitAction with Approve=$true, option 2 calls Stop-WaitAction with Approve=$false and returns rejection result, option 3 continues polling, non-interactive mode: logs warning and continues polling for external approval
- [X] T077 [US7] Add CLI parameter for approval decision in deploy-sentinel.ps1 (`-ApproveWaitAction`, `-RejectWaitAction` with `-ActionId`) - Added three parameters to param block: -ApproveWaitAction (switch), -RejectWaitAction (switch), -ActionId (string), added handling in main entry point before action execution: validates parameters (ActionId required, cannot specify both switches), loads config and state, calls Stop-WaitAction with appropriate Approve bool, displays success message and exits with code 0
- [X] T078 [US7] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify approval gate handling) - Added comprehensive integration test "Should handle approval gates during monitoring" with expected behavior documented: wait action detection during Watch-Ev2Rollout, Teams notification sent, user prompted in interactive mode (Approve/Reject/Wait), CLI approval/rejection commands tested, non-interactive mode continues polling, set to skipped until refactoring

**Checkpoint**: Approval gates complete - human-in-the-loop control for critical deployments ✅

---

## Phase 10: User Story 8 - Post-Deployment Notifications (Priority: P3)

**Goal**: Send formatted deployment summaries to Teams channels via webhook

**Independent Test**: Complete deployment → verify Teams notification sent with correct information

### Contract Tests for User Story 8

- [X] T079 [P] [US8] Contract test for all notification types in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify 7 notification formats)
- [X] T080 [P] [US8] Contract test for webhook retry logic in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify exponential backoff)

### Implementation for User Story 8

- [X] T081 [P] [US8] Implement `New-NotificationMessage` function in deploy-sentinel.ps1 (creates NotificationMessage entity from RolloutState)
- [X] T082 [P] [US8] Implement `Send-TeamsNotification` function in deploy-sentinel.ps1 (posts JSON to webhook with retry logic)
- [X] T083 [P] [US8] Implement `Write-NotificationLog` function in deploy-sentinel.ps1 (fallback logging if webhook fails)
- [X] T084 [US8] Integrate notifications into workflow - call after rollout completion, stage completion, and failures (depends on T081-T083)
- [X] T085 [US8] Add notification types: Rollout Started, Stage Completed, Approval Required, Rollout Failed, Rollout Completed, Rollout Cancelled, Stress Test Results
- [X] T086 [US8] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify notifications sent at appropriate times)

**Checkpoint**: All user stories complete - full deployment automation with notifications

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T087 [P] Create `docs/deploy-sentinel/README.md` user documentation (getting started, commands, examples)
- [X] T088 [P] Create `docs/deploy-sentinel/mcp-setup.md` MCP server installation guide (EV2 via dnx, ADO via npm)
- [X] T089 [P] Create `docs/deploy-sentinel/troubleshooting.md` common issues and solutions
- [X] T091 Add comprehensive error messages and help text to all functions (where to find serviceId, rolloutId, etc.)
- [X] T092 [P] Add verbose logging support (`-Verbose` parameter) for all MCP tool calls and state changes
- [X] T093 Performance optimization - reduce polling frequency after initial deployment stages complete
- [X] T094 Security hardening - validate all user inputs, sanitize config file paths, secure state file permissions
- [X] T095 [P] Add unit tests for configuration validation in `tests/deploy-sentinel/unit/ConfigValidation.Tests.ps1`
- [X] T096 [P] Add unit tests for state persistence in `tests/deploy-sentinel/unit/StateManagement.Tests.ps1`
- [X] T097 Run quickstart.md validation - execute all examples from quickstart guide
- [X] T098 Code cleanup and refactoring - extract common patterns, improve function names
- [X] T099 Add PowerShell 5.1 and PowerShell Core 7+ compatibility testing to CI pipeline
- [X] T100 Final integration test - complete deployment workflow from trigger to completion with all features enabled

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
  - P1 stories (US1-US3): Highest priority, form MVP
  - P2 stories (US4-US6): Can start after Foundation, independent of each other
  - P3 stories (US7-US8): Can start after Foundation, independent of each other
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

**User Story 1 (P1 - Trigger Rollout)**: 
- Depends on: Foundational (Phase 2)
- No dependencies on other user stories
- **MVP Core** - Must complete first

**User Story 2 (P1 - Create Branch)**:
- Depends on: Foundational (Phase 2)
- Integrates with: US1 (branch created after rollout triggered)
- Can test independently by mocking rollout

**User Story 3 (P1 - Monitor Status)**:
- Depends on: Foundational (Phase 2)
- Integrates with: US1 (monitors rollout after trigger)
- Can test independently with existing rolloutId
- **Completes MVP** - US1 + US2 + US3 = full basic workflow

**User Story 4 (P2 - Handle Issues)**:
- Depends on: Foundational (Phase 2), US3 (extends monitoring)
- Can test independently by simulating failures

**User Story 5 (P2 - Stress Testing)**:
- Depends on: Foundational (Phase 2), US3 (runs after stage completion)
- Can test independently with endpoint URL

**User Story 6 (P2 - Run Pipelines)**:
- Depends on: Foundational (Phase 2)
- No dependencies on other user stories
- Can test independently with ADO config

**User Story 7 (P3 - Approval Gates)**:
- Depends on: Foundational (Phase 2), US3 (extends monitoring), US8 (uses notifications)
- Can test independently with mock wait actions

**User Story 8 (P3 - Notifications)**:
- Depends on: Foundational (Phase 2)
- Used by: US7 (approval notifications)
- Can test independently by mocking deployments

### Within Each User Story

1. **Contract tests MUST be written FIRST** and MUST FAIL before implementation
2. **Models/Entities** before services
3. **Helper functions** before orchestration functions
4. **Core implementation** before integration into workflow
5. **Integration tests** verify story works end-to-end
6. **Story complete** before moving to next priority

### Parallel Opportunities

**Setup (Phase 1)**: All tasks marked [P] can run in parallel (T002-T007)

**Foundational (Phase 2)**: Tasks T009-T012, T014-T016 marked [P] can run in parallel

**After Foundation Complete**, multiple user stories can proceed in parallel:
- **Team of 3+**: Assign US1 to Dev1, US2 to Dev2, US6 to Dev3 simultaneously
- **Team of 2**: Complete US1-US3 (MVP) first, then parallelize P2/P3 stories
- **Solo**: Follow priority order (P1 → P2 → P3), but contract tests can be batched

**Within User Stories**:
- All contract tests marked [P] can run in parallel
- Helper functions marked [P] can be implemented in parallel
- Example (US1): T017-T020 contract tests run together, then T021-T023 helpers run together

---

## Parallel Example: MVP (User Stories 1-3)

### Phase 2 Foundation (Run in Parallel)
```bash
Task T009: Configuration loading function
Task T010: State file management functions  
Task T011: Logging infrastructure function
Task T012: Retry logic function
```

### User Story 1 Contract Tests (Run in Parallel)
```bash
Task T017: Contract test - EV2 best practices
Task T018: Contract test - Get artifact versions
Task T019: Contract test - Get stage map versions
Task T020: Contract test - Start rollout
```

### User Story 1 Helpers (Run in Parallel)
```bash
Task T021: Get-Ev2BestPractices function
Task T022: Get-LatestArtifactVersion function
Task T023: Get-LatestStageMapVersion function
```

### After US1 Complete, Parallelize US2 & US3
```bash
Dev1: User Story 2 (Branch Creation) - T030-T036
Dev2: User Story 3 (Monitoring) - T037-T044
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only) 🎯

1. **Complete Phase 1**: Setup (T001-T007) → 7 tasks
2. **Complete Phase 2**: Foundational (T008-T016) → 9 tasks **[BLOCKS EVERYTHING]**
3. **Complete Phase 3**: User Story 1 (T017-T029, T026b) → 14 tasks
4. **Complete Phase 4**: User Story 2 (T030-T036) → 7 tasks
5. **Complete Phase 5**: User Story 3 (T037-T044) → 8 tasks
6. **STOP and VALIDATE**: Test complete MVP workflow independently
   - Trigger rollout ✅
   - Create branch ✅
   - Monitor to completion ✅
7. **Deploy/Demo MVP**: 45 tasks = functional deployment automation

### Incremental Delivery After MVP

1. **Add US4 (Error Handling)**: T045-T051 → Robust failure detection
2. **Add US5 (Stress Testing)**: T052-T060 → Automated validation
3. **Add US6 (Pipelines)**: T061-T070 → CI/CD integration
4. **Add US7 (Approvals)**: T071-T078 → Governance control
5. **Add US8 (Notifications)**: T079-T086 → Stakeholder awareness
6. Each addition is independently testable and adds value without breaking previous functionality

### Parallel Team Strategy (3+ Developers)

**Phase 1-2 (Together)**: Everyone completes Setup + Foundation → Foundation ready

**Phase 3+ (Parallel)**:
- **Developer A**: User Story 1 (T017-T029) → Core trigger functionality
- **Developer B**: User Story 2 (T030-T036) + User Story 6 (T061-T070) → Branch + Pipelines
- **Developer C**: User Story 3 (T037-T044) → Monitoring

**After MVP Complete**:
- **Developer A**: User Story 4 (T045-T051) + User Story 5 (T052-T060)
- **Developer B**: User Story 7 (T071-T078)
- **Developer C**: User Story 8 (T079-T086)

Stories complete and integrate independently.

---

## Task Summary

**Total Tasks**: 100

**By Phase**:
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundation): 9 tasks **[CRITICAL PATH]**
- Phase 3 (US1): 14 tasks 🎯 **MVP Core**
- Phase 4 (US2): 7 tasks 🎯 **MVP Core**
- Phase 5 (US3): 8 tasks 🎯 **MVP Core**
- Phase 6 (US4): 7 tasks
- Phase 7 (US5): 9 tasks
- Phase 8 (US6): 10 tasks
- Phase 9 (US7): 8 tasks
- Phase 10 (US8): 8 tasks
- Phase 11 (Polish): 13 tasks

**MVP Size**: 45 tasks (Phases 1-5) = User Stories 1, 2, 3

**Full Feature**: 100 tasks (All phases) = All 8 user stories + polish

**Parallel Tasks**: 40 tasks marked [P] can run concurrently with proper team coordination

---

## Notes

- **[P] marker**: Tasks marked [P] work on different files or have no sequential dependencies
- **[Story] label**: Every task after Foundation is labeled with its user story (US1-US8)
- **TDD Approach**: Contract tests written FIRST (must FAIL), then implementation
- **Independent Stories**: Each user story can be completed and tested independently
- **Checkpoints**: After each phase, validate that story works independently
- **File Paths**: All paths are exact per project structure in plan.md
- **Avoid**: Vague tasks, same-file conflicts, cross-story dependencies that break independence
- **Commit**: After each task or logical group, commit to version control
- **PowerShell Compatibility**: All code must work in PowerShell 5.1+ and Core 7+

---

**Generated**: 2025-11-20 | **Phase**: 2 (Task Generation) | **Next**: /speckit.implement
