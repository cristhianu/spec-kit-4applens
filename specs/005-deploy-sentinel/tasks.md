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

- [ ] T001 Create `.github/prompts/speckit.deploySentinel.prompt.md` for GitHub Copilot agent definition
- [ ] T002 [P] Create `tests/deploy-sentinel/contract/` directory structure
- [ ] T003 [P] Create `tests/deploy-sentinel/integration/` directory structure
- [ ] T004 [P] Create `tests/deploy-sentinel/unit/` directory structure
- [ ] T005 [P] Create `tests/fixtures/deploy-sentinel/` directory for test fixtures
- [ ] T006 [P] Create `.deploy-sentinel-config.json` configuration template in project root
- [ ] T007 [P] Update `.vscode/mcp.json` with EV2 and Azure DevOps MCP server configurations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create PowerShell module structure in `scripts/powershell/deploy-sentinel.ps1` with main entry point
- [ ] T009 [P] Implement configuration loading function `Load-DeploymentConfig` in deploy-sentinel.ps1 (reads .json, validates required params, supports env var substitution)
- [ ] T010 [P] Implement state file management functions `Read-RolloutState`, `Write-RolloutState`, `Lock-StateFile` in deploy-sentinel.ps1
- [ ] T011 [P] Implement logging infrastructure function `Write-DeploymentLog` with timestamps in deploy-sentinel.ps1
- [ ] T012 [P] Implement retry logic function `Invoke-WithRetry` with exponential backoff in deploy-sentinel.ps1
- [ ] T013 Implement MCP tool wrapper function `Invoke-McpTool` for error handling and logging in deploy-sentinel.ps1
- [ ] T014 Create test fixture `tests/fixtures/deploy-sentinel/mock-rollout-responses.json` with EV2 response samples
- [ ] T015 [P] Create test fixture `tests/fixtures/deploy-sentinel/mock-pipeline-responses.json` with ADO response samples
- [ ] T016 [P] Create test fixture `tests/fixtures/deploy-sentinel/test-service-config.json` with valid configuration examples

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Trigger EV2 Rollout (Priority: P1) 🎯 MVP

**Goal**: Initiate EV2 deployments by discovering artifact/stage map versions and triggering rollout

**Independent Test**: Provide valid service configuration → verify rollout created with correct versions and scope

### Contract Tests for User Story 1

> **TDD: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Contract test for EV2 best practices tool in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify best practices returned)
- [ ] T018 [P] [US1] Contract test for get artifact versions in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify latest version discovery)
- [ ] T019 [P] [US1] Contract test for get stage map versions in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify latest version discovery)
- [ ] T020 [P] [US1] Contract test for start rollout in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify rollout creation with valid params)

### Implementation for User Story 1

- [ ] T021 [P] [US1] Implement `Get-Ev2BestPractices` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_ev2_best_practices, logs output)
- [ ] T022 [P] [US1] Implement `Get-LatestArtifactVersion` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_artifact_versions, returns latest)
- [ ] T023 [P] [US1] Implement `Get-LatestStageMapVersion` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_stage_map_versions, returns latest)
- [ ] T024 [US1] Implement `New-ServiceInfo` function in deploy-sentinel.ps1 (creates ServiceInfo entity from discovery, depends on T022, T023)
- [ ] T025 [US1] Implement `Build-SelectionScope` function in deploy-sentinel.ps1 (constructs EV2 scope from environment/config)
- [ ] T026 [US1] Implement `Start-Ev2Rollout` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_start_rollout with artifact/stage map versions)
- [ ] T026b [US5] Implement `Get-AzureAuthToken` function in deploy-sentinel.ps1 (Azure credential chain: MSI, service principals, user credentials for stress test authentication per FR-026)
- [ ] T027 [US1] Implement main workflow function `Invoke-TriggerRollout` in deploy-sentinel.ps1 (orchestrates T021-T026, creates RolloutState)
- [ ] T028 [US1] Add parameter validation and error messages to `Invoke-TriggerRollout` (missing params, invalid GUIDs)
- [ ] T029 [US1] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (end-to-end rollout trigger)

**Checkpoint**: User Story 1 complete - can trigger rollouts independently

---

## Phase 4: User Story 2 - Create Feature Branch (Priority: P1)

**Goal**: Automatically create properly named deployment branch

**Independent Test**: Provide deployment metadata → verify branch created with correct naming pattern

### Contract Tests for User Story 2

- [ ] T030 [P] [US2] Unit test for git availability check in `tests/deploy-sentinel/unit/BranchCreation.Tests.ps1` (verify git command exists)
- [ ] T031 [P] [US2] Unit test for branch name generation in `tests/deploy-sentinel/unit/BranchCreation.Tests.ps1` (verify naming pattern)

### Implementation for User Story 2

- [ ] T032 [P] [US2] Implement `Test-GitRepository` function in deploy-sentinel.ps1 (validates git initialized, has remotes)
- [ ] T033 [P] [US2] Implement `New-DeploymentBranchName` function in deploy-sentinel.ps1 (generates deploy/{env}/{service}/{timestamp} name)
- [ ] T034 [US2] Implement `New-DeploymentBranch` function in deploy-sentinel.ps1 (creates git branch, handles existing branch, depends on T032, T033)
- [ ] T035 [US2] Integrate branch creation into `Invoke-TriggerRollout` workflow (call after rollout started, store branchName in RolloutState)
- [ ] T036 [US2] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify branch creation in workflow)

**Checkpoint**: User Stories 1 AND 2 complete - can trigger rollouts with branch tracking

---

## Phase 5: User Story 3 - Monitor Rollout Status (Priority: P1)

**Goal**: Continuous polling of EV2 rollout status with real-time progress updates

**Independent Test**: Provide rolloutId → verify agent retrieves and displays status including stages, regions, errors

### Contract Tests for User Story 3

- [ ] T037 [P] [US3] Contract test for get rollout details in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify status structure returned)
- [ ] T038 [P] [US3] Contract test for wait action detection in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify wait actions identified)

### Implementation for User Story 3

- [ ] T039 [P] [US3] Implement `Get-RolloutStatus` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_get_rollout_details)
- [ ] T040 [P] [US3] Implement `Format-RolloutStatusDisplay` function in deploy-sentinel.ps1 (formats status for console output with stages/regions)
- [ ] T041 [P] [US3] Implement `Test-RolloutComplete` function in deploy-sentinel.ps1 (checks if rollout reached terminal state)
- [ ] T042 [US3] Implement `Watch-Ev2Rollout` function in deploy-sentinel.ps1 (polling loop with configurable interval, depends on T039-T041)
- [ ] T043 [US3] Integrate monitoring into workflow - add `Invoke-MonitorRollout` function in deploy-sentinel.ps1 (starts after rollout trigger or standalone)
- [ ] T044 [US3] Add integration test in `tests/deploy-sentinel/integration/StateManagement.Tests.ps1` (verify state updates during monitoring)

**Checkpoint**: User Stories 1, 2, AND 3 complete - full MVP workflow (trigger + track)

---

## Phase 6: User Story 4 - Handle Deployment Issues (Priority: P2)

**Goal**: Detect failures, retrieve error details, provide actionable recommendations

**Independent Test**: Simulate failed rollout → verify agent detects failure, retrieves errors, presents recommendations

### Contract Tests for User Story 4

- [ ] T045 [P] [US4] Contract test for error response parsing in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify error details extracted)
- [ ] T046 [P] [US4] Contract test for cancel rollout in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify cancellation succeeds)

### Implementation for User Story 4

- [ ] T047 [P] [US4] Implement `Get-RolloutErrors` function in deploy-sentinel.ps1 (extracts errors from rollout details)
- [ ] T048 [P] [US4] Implement `Get-ErrorRecommendation` function in deploy-sentinel.ps1 (generates recommendations based on error type)
- [ ] T049 [US4] Implement `Stop-Ev2Rollout` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_cancel_rollout, updates RolloutState)
- [ ] T050 [US4] Implement error detection in `Watch-Ev2Rollout` function (detect failures, call T047-T048, prompt user for action)
- [ ] T051 [US4] Add integration test in `tests/deploy-sentinel/integration/ErrorRecovery.Tests.ps1` (simulate failure, verify error handling)

**Checkpoint**: Failure handling complete - robust error detection and recovery

---

## Phase 7: User Story 5 - Stress-Test Deployed Endpoints (Priority: P2)

**Goal**: Automated stress testing of deployed endpoints after each stage

**Independent Test**: Provide endpoint URL and thresholds → verify agent executes stress test and reports pass/fail

### Contract Tests for User Story 5

- [ ] T052 [P] [US5] Unit test for concurrent request execution in `tests/deploy-sentinel/unit/StressTesting.Tests.ps1` (verify Start-Job usage)
- [ ] T053 [P] [US5] Unit test for latency percentile calculation in `tests/deploy-sentinel/unit/StressTesting.Tests.ps1` (verify p50/p95/p99 correct)

### Implementation for User Story 5

- [ ] T054 [P] [US5] Implement `Invoke-EndpointRequest` function in deploy-sentinel.ps1 (single HTTP request with timing)
- [ ] T055 [P] [US5] Implement `Start-ConcurrentRequests` function in deploy-sentinel.ps1 (uses Start-Job for parallel execution)
- [ ] T056 [P] [US5] Implement `Measure-LatencyPercentiles` function in deploy-sentinel.ps1 (calculates p50, p95, p99 from timing data)
- [ ] T057 [US5] Implement `Invoke-StressTest` function in deploy-sentinel.ps1 (orchestrates T054-T056, creates StressTestResult entity)
- [ ] T058 [US5] Implement `Test-StressTestPassed` function in deploy-sentinel.ps1 (compares results against thresholds)
- [ ] T059 [US5] Integrate stress testing into `Watch-Ev2Rollout` function (run after each stage completion if enabled)
- [ ] T060 [US5] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify stress testing in workflow)

**Checkpoint**: Stress testing complete - automated validation after deployment stages

---

## Phase 8: User Story 6 - Run Deployment Pipeline (Priority: P2)

**Goal**: Trigger and monitor Azure DevOps pipelines as part of deployment workflow

**Independent Test**: Provide ADO project and pipeline ID → verify pipeline triggered and monitored to completion

### Contract Tests for User Story 6

- [ ] T061 [P] [US6] Contract test for list pipelines in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (verify pipeline discovery)
- [ ] T062 [P] [US6] Contract test for run pipeline in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (verify pipeline triggered)
- [ ] T063 [P] [US6] Contract test for get build status in `tests/deploy-sentinel/contract/AdoMcpServer.Tests.ps1` (verify status polling)

### Implementation for User Story 6

- [ ] T064 [P] [US6] Implement `Get-AdoPipelines` function in deploy-sentinel.ps1 (calls mcp_ado_pipelines_list)
- [ ] T065 [P] [US6] Implement `Start-AdoPipeline` function in deploy-sentinel.ps1 (calls mcp_ado_pipelines_run_pipeline with parameters)
- [ ] T066 [P] [US6] Implement `Get-AdoBuildStatus` function in deploy-sentinel.ps1 (calls mcp_ado_build_get)
- [ ] T067 [US6] Implement `Watch-AdoPipeline` function in deploy-sentinel.ps1 (polls build status until completion, depends on T066)
- [ ] T068 [US6] Implement `Get-AdoBuildLogs` function in deploy-sentinel.ps1 (retrieves logs on failure via mcp_ado_build_get_logs)
- [ ] T069 [US6] Integrate pipeline execution into workflow - add `Invoke-DeploymentPipeline` in deploy-sentinel.ps1 (orchestrates T064-T068)
- [ ] T070 [US6] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify pipeline execution in workflow)

**Checkpoint**: Pipeline integration complete - can run CI/CD pipelines as deployment prerequisite

---

## Phase 9: User Story 7 - Handle Approval Gates (Priority: P3)

**Goal**: Detect wait actions, notify approvers, process approval decisions

**Independent Test**: Create rollout with wait action → verify agent detects, sends notification, handles approval

### Contract Tests for User Story 7

- [ ] T071 [P] [US7] Contract test for stop wait action in `tests/deploy-sentinel/contract/Ev2McpServer.Tests.ps1` (verify wait action approval)
- [ ] T072 [P] [US7] Contract test for Teams notification in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify approval notification sent)

### Implementation for User Story 7

- [ ] T073 [P] [US7] Implement `Get-WaitActions` function in deploy-sentinel.ps1 (extracts wait actions from rollout details)
- [ ] T074 [P] [US7] Implement `Send-ApprovalNotification` function in deploy-sentinel.ps1 (sends Teams webhook for approval request)
- [ ] T075 [US7] Implement `Stop-WaitAction` function in deploy-sentinel.ps1 (calls mcp_ev2_mcp_serve_stop_wait_action)
- [ ] T076 [US7] Implement wait action handling in `Watch-Ev2Rollout` function (detect wait actions, call T074, wait for user approval decision, call T075)
- [ ] T077 [US7] Add CLI parameter for approval decision in deploy-sentinel.ps1 (`-ApproveWaitAction`, `-RejectWaitAction` with `-ActionId`)
- [ ] T078 [US7] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify approval gate handling)

**Checkpoint**: Approval gates complete - human-in-the-loop control for critical deployments

---

## Phase 10: User Story 8 - Post-Deployment Notifications (Priority: P3)

**Goal**: Send formatted deployment summaries to Teams channels via webhook

**Independent Test**: Complete deployment → verify Teams notification sent with correct information

### Contract Tests for User Story 8

- [ ] T079 [P] [US8] Contract test for all notification types in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify 7 notification formats)
- [ ] T080 [P] [US8] Contract test for webhook retry logic in `tests/deploy-sentinel/contract/TeamsWebhook.Tests.ps1` (verify exponential backoff)

### Implementation for User Story 8

- [ ] T081 [P] [US8] Implement `New-NotificationMessage` function in deploy-sentinel.ps1 (creates NotificationMessage entity from RolloutState)
- [ ] T082 [P] [US8] Implement `Send-TeamsNotification` function in deploy-sentinel.ps1 (posts JSON to webhook with retry logic)
- [ ] T083 [P] [US8] Implement `Write-NotificationLog` function in deploy-sentinel.ps1 (fallback logging if webhook fails)
- [ ] T084 [US8] Integrate notifications into workflow - call after rollout completion, stage completion, and failures (depends on T081-T083)
- [ ] T085 [US8] Add notification types: Rollout Started, Stage Completed, Approval Required, Rollout Failed, Rollout Completed, Rollout Cancelled, Stress Test Results
- [ ] T086 [US8] Add integration test in `tests/deploy-sentinel/integration/DeploymentWorkflow.Tests.ps1` (verify notifications sent at appropriate times)

**Checkpoint**: All user stories complete - full deployment automation with notifications

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T087 [P] Create `docs/deploy-sentinel/README.md` user documentation (getting started, commands, examples)
- [ ] T088 [P] Create `docs/deploy-sentinel/mcp-setup.md` MCP server installation guide (EV2 via dnx, ADO via npm)
- [ ] T089 [P] Create `docs/deploy-sentinel/troubleshooting.md` common issues and solutions
- [ ] T091 Add comprehensive error messages and help text to all functions (where to find serviceId, rolloutId, etc.)
- [ ] T092 [P] Add verbose logging support (`-Verbose` parameter) for all MCP tool calls and state changes
- [ ] T093 Performance optimization - reduce polling frequency after initial deployment stages complete
- [ ] T094 Security hardening - validate all user inputs, sanitize config file paths, secure state file permissions
- [ ] T095 [P] Add unit tests for configuration validation in `tests/deploy-sentinel/unit/ConfigValidation.Tests.ps1`
- [ ] T096 [P] Add unit tests for state persistence in `tests/deploy-sentinel/unit/StateManagement.Tests.ps1`
- [ ] T097 Run quickstart.md validation - execute all examples from quickstart guide
- [ ] T098 Code cleanup and refactoring - extract common patterns, improve function names
- [ ] T099 Add PowerShell 5.1 and PowerShell Core 7+ compatibility testing to CI pipeline
- [ ] T100 Final integration test - complete deployment workflow from trigger to completion with all features enabled

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
