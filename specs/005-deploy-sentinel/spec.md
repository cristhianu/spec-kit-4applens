# Feature Specification: EV2 Deployment Follower Agent

**Feature Branch**: `005-deploy-sentinel`  
**Created**: 2025-01-22  
**Status**: Draft  
**Input**: User description: "Add an EV2 deployment follower agent (/deploySentinel) to automate deployments: trigger new rollouts, create feature branches, stress-test endpoints, run deployment pipelines, handle approval gates, monitor rollouts, handle deployment issues, and post-deployment notifications via Teams webhook"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trigger EV2 Rollout (Priority: P1)

A developer needs to initiate a new EV2 deployment for their service. They invoke the deploySentinel agent with service configuration, and the agent discovers the latest artifact and stage map versions, then triggers an EV2 rollout with appropriate scope selection.

**Why this priority**: This is the core functionality that initiates the entire deployment workflow. Without this capability, no deployments can occur. It delivers immediate value by automating the complex EV2 rollout initiation process.

**Independent Test**: Can be fully tested by providing valid service configuration (serviceGroupName, serviceId, stageMapName, environment) and verifying that an EV2 rollout is successfully created with the correct artifact version and scope. Delivers value by automating what is currently a manual, error-prone process.

**Acceptance Scenarios**:

1. **Given** a valid service configuration with serviceGroupName, serviceId, and stageMapName, **When** the agent is invoked to trigger a rollout, **Then** the agent discovers the latest artifact version, retrieves the latest stage map version, constructs appropriate selection/exclusion scopes based on environment, and successfully initiates an EV2 rollout.
2. **Given** a service configuration missing required parameters, **When** the agent is invoked, **Then** the agent provides clear error messages indicating which parameters are missing and where to find them (e.g., "serviceId can be found in ServiceModel.json").
3. **Given** an invalid service configuration (non-existent service or stage map), **When** the agent attempts to trigger a rollout, **Then** the agent fails with a clear error message indicating the specific validation failure.

---

### User Story 2 - Create Feature Branch (Priority: P1)

Before deployment, the developer needs to create a properly named feature branch that follows project naming conventions. The agent automatically generates a branch name based on the deployment context and creates it.

**Why this priority**: Branch creation is a prerequisite for tracking deployment changes and maintaining traceability. It's part of the minimal viable workflow for any deployment automation. This enables proper version control and audit trails.

**Independent Test**: Can be tested independently by providing deployment metadata and verifying that a branch is created with the correct naming pattern (e.g., `deploy/[environment]/[serviceGroupName]/[timestamp]`). Delivers value by ensuring consistent branch naming and eliminating manual branch creation errors.

**Acceptance Scenarios**:

1. **Given** deployment metadata including environment and service information, **When** the agent creates a feature branch, **Then** a branch is created with the naming pattern `deploy/[environment]/[serviceGroupName]/[timestamp]` and the agent switches to that branch.
2. **Given** a branch with the same name already exists, **When** the agent attempts to create it, **Then** the agent either uses the existing branch or creates a uniquely named variant with a suffix.
3. **Given** git is not initialized in the current directory, **When** the agent attempts to create a branch, **Then** the agent fails with a clear error message indicating git must be initialized first.

---

### User Story 3 - Monitor Rollout Status (Priority: P1)

After triggering a deployment, the developer needs real-time visibility into the rollout progress. The agent continuously polls the EV2 rollout status and reports progress updates, including which regions/stages are being deployed and their current states.

**Why this priority**: Without monitoring, deployments become black boxes. This is essential for identifying issues early and maintaining operational awareness. It's part of the core deployment loop.

**Independent Test**: Can be tested by providing a valid rolloutId and verifying that the agent retrieves and displays current rollout status including stage progress, region status, and overall health. Delivers immediate value by eliminating the need to manually check EV2 dashboards.

**Acceptance Scenarios**:

1. **Given** a valid rolloutId from a triggered deployment, **When** the agent monitors the rollout, **Then** the agent polls EV2 at regular intervals and displays current status including: overall rollout state, active stages, completed regions, pending regions, and any errors or warnings.
2. **Given** a rollout encounters a wait action requiring human approval, **When** the agent detects this state, **Then** the agent alerts the user and provides instructions on how to approve or reject the wait action.
3. **Given** a rollout completes successfully, **When** the agent detects the completed state, **Then** the agent reports success and proceeds to post-deployment notifications.

---

### User Story 4 - Handle Deployment Issues (Priority: P2)

When a rollout encounters errors or failures, the developer needs automated detection and initial triage. The agent detects failures, retrieves error details from EV2, and provides actionable recommendations or automatically attempts recovery actions.

**Why this priority**: While not required for successful deployments, this is critical for handling failures gracefully. It's a P2 because monitoring (P1) can detect issues, but this story adds intelligent response capabilities that significantly reduce mean time to resolution.

**Independent Test**: Can be tested by simulating a failed rollout or intentionally triggering errors, then verifying the agent detects the failure, retrieves error logs, and presents actionable information or attempts recovery. Delivers value by reducing manual triage time.

**Acceptance Scenarios**:

1. **Given** a rollout that fails during deployment, **When** the agent detects the failure, **Then** the agent retrieves error details from EV2, identifies the failing component/region, and presents a summary with recommendations (e.g., "Region EastUS failed during stage 2: [error message]. Recommendation: Check service health in EastUS").
2. **Given** a transient failure that may be recoverable, **When** the agent detects it, **Then** the agent prompts the user to retry the failed stage or restart the rollout from the last known good state.
3. **Given** a critical failure requiring immediate attention, **When** the agent detects it, **Then** the agent sends an urgent notification via Teams webhook and cancels remaining deployment stages to prevent cascading failures.

---

### User Story 5 - Stress-Test Deployed Endpoints (Priority: P2)

After each stage of deployment completes, the developer needs automated validation that the deployed service is healthy and performing correctly. The agent runs stress tests against newly deployed endpoints to verify they meet performance and reliability requirements before proceeding to the next stage.

**Why this priority**: This is a P2 because deployment can complete without stress testing, but it's critical for production quality. It adds a safety net that catches performance regressions before they affect all regions.

**Independent Test**: Can be tested by providing deployed endpoint URLs and test configuration, then verifying the agent executes load tests and reports pass/fail based on response times, error rates, and throughput. Delivers value by automating what is often a manual or skipped validation step.

**Acceptance Scenarios**:

1. **Given** a successfully deployed stage with accessible endpoints, **When** the agent runs stress tests, **Then** the agent sends a configurable number of requests (e.g., 100 requests over 30 seconds), measures response times and error rates, and reports whether endpoints meet defined thresholds (e.g., 95% success rate, p95 latency < 500ms).
2. **Given** stress tests that fail due to high error rates or poor performance, **When** the agent completes testing, **Then** the agent halts further deployment progression and alerts the user with specific metrics that failed.
3. **Given** endpoints that are not yet accessible (still starting up), **When** the agent attempts stress testing, **Then** the agent retries with exponential backoff up to a maximum wait time before reporting failure.

---

### User Story 6 - Run Deployment Pipeline (Priority: P2)

For services that require build/compilation steps before deployment, the developer needs automated pipeline execution. The agent detects Azure DevOps pipeline configuration, triggers the pipeline, and monitors its execution to completion.

**Why this priority**: This is P2 because not all deployments require pipelines (some may deploy pre-built artifacts directly). For services that do require pipelines, this automates a critical prerequisite step.

**Independent Test**: Can be tested by providing ADO project/pipeline information and verifying the agent triggers the pipeline and monitors its progress. Delivers value by integrating build automation into the deployment workflow.

**Acceptance Scenarios**:

1. **Given** a valid Azure DevOps project and pipeline definition, **When** the agent triggers the pipeline, **Then** the agent starts the pipeline run with appropriate parameters (branch, environment) and monitors execution until completion or failure.
2. **Given** a pipeline that completes successfully, **When** the agent detects completion, **Then** the agent retrieves the built artifact information and proceeds with the deployment using that artifact.
3. **Given** a pipeline that fails during execution, **When** the agent detects the failure, **Then** the agent retrieves pipeline error logs and presents them to the user with recommendations.

---

### User Story 7 - Handle Approval Gates (Priority: P3)

Some deployments require human approval at certain stages (e.g., before deploying to production). The agent detects when a rollout reaches an approval gate, notifies the appropriate approvers, and waits for their decision before proceeding.

**Why this priority**: This is P3 because it's not required for all deployments. Many deployments can proceed fully automated. However, for production deployments requiring governance, this adds necessary human-in-the-loop control.

**Independent Test**: Can be tested by creating a rollout with wait actions/approval gates, verifying the agent detects them, sends notifications, and correctly handles approve/reject responses. Delivers value by automating the notification and waiting process.

**Acceptance Scenarios**:

1. **Given** a rollout that reaches a wait action requiring approval, **When** the agent detects this state, **Then** the agent sends a Teams notification to the configured approvers channel with rollout details and approve/reject instructions.
2. **Given** an approver responds with approval, **When** the agent receives the response, **Then** the agent calls the EV2 API to stop the wait action and allows the rollout to proceed.
3. **Given** an approver responds with rejection, **When** the agent receives the response, **Then** the agent cancels the rollout and reports the reason for cancellation.

---

### User Story 8 - Post-Deployment Notifications (Priority: P3)

After a deployment completes (successfully or with failure), stakeholders need to be informed of the results. The agent sends formatted notifications to Teams channels with deployment summary, status, duration, and relevant links.

**Why this priority**: This is P3 because deployment can complete without notifications. However, it's valuable for team awareness and audit trails. It's the final step in a complete deployment workflow.

**Independent Test**: Can be tested by completing a deployment (or simulating completion) and verifying that Teams notifications are sent with correct information formatted appropriately. Delivers value by automating status reporting.

**Acceptance Scenarios**:

1. **Given** a successfully completed rollout, **When** the agent sends post-deployment notifications, **Then** a Teams message is posted with: service name, environment, rollout ID, duration, deployed regions, artifact version, and a link to the EV2 rollout dashboard.
2. **Given** a failed rollout, **When** the agent sends post-deployment notifications, **Then** a Teams message is posted with: service name, environment, rollout ID, failure stage, error summary, and recommendations for remediation.
3. **Given** Teams webhook configuration is missing or invalid, **When** the agent attempts to send notifications, **Then** the agent logs the notification content locally and reports a warning that notifications could not be sent.

---

### Edge Cases

- What happens when the EV2 MCP server is unavailable or returns errors?
  - Agent should fail fast with clear error messages and not proceed with deployment
  - Agent should retry transient failures with exponential backoff (max 3 retries)
- What happens when a rollout is already in progress for the same service?
  - Agent should detect existing rollout and prompt user to either monitor the existing rollout or cancel and start a new one
- What happens when git operations fail (branch creation, checkout)?
  - Agent should provide clear error messages with git troubleshooting steps
  - Agent should not proceed with deployment if branch operations fail
- What happens when Teams webhook is unreachable or returns errors?
  - Agent should log notification content locally as fallback
  - Agent should continue with deployment (notifications are non-critical)
  - Agent should report warning that notifications failed
- What happens when stress test endpoints are behind authentication?
  - Agent should support passing bearer tokens (Azure AD/OAuth2) via configuration parameter or Azure credential chain
  - Agent should retrieve tokens from MSI, service principals, or user credentials
- What happens when multiple environments/stages fail simultaneously?
  - Agent should report all failures together with prioritization (production failures first)
  - Agent should recommend whether to cancel entire rollout or retry individual stages
- What happens when the agent is invoked multiple times concurrently for the same service?
  - Agent should detect concurrent execution and prevent conflicting operations
  - Agent should use file-based locking or similar mechanism to prevent race conditions

## Requirements *(mandatory)*

### Functional Requirements

#### Core Deployment Management

- **FR-001**: Agent MUST integrate with EV2 MCP Server to trigger, monitor, and manage EV2 rollouts
- **FR-002**: Agent MUST integrate with Azure DevOps MCP Server to trigger pipelines and retrieve work item information
- **FR-003**: Agent MUST accept service configuration parameters: serviceGroupName, serviceId, stageMapName, and environment (e.g., PPE, PROD)
- **FR-004**: Agent MUST automatically discover the latest registered artifact version for the specified service
- **FR-005**: Agent MUST automatically discover the latest registered stage map version
- **FR-006**: Agent MUST construct appropriate selection and exclusion scopes based on the target environment
- **FR-007**: Agent MUST trigger EV2 rollouts with the discovered artifact version, stage map version, and constructed scopes
- **FR-008**: Agent MUST persist rollout state information to enable resumption after interruption or failure (idempotent design)

#### Branch Management

- **FR-009**: Agent MUST create a feature branch following the naming pattern: `deploy/[environment]/[serviceGroupName]/[timestamp]`
- **FR-010**: Agent MUST validate git repository exists and is initialized before creating branches
- **FR-011**: Agent MUST handle existing branch names by either using the existing branch or creating a uniquely named variant

#### Monitoring and Status Reporting

- **FR-012**: Agent MUST poll EV2 rollout status at configurable intervals (default: every 30 seconds)
- **FR-013**: Agent MUST display rollout progress including: overall state, active stages, completed/pending regions, and errors/warnings
- **FR-014**: Agent MUST detect wait actions requiring human approval and alert the user with instructions
- **FR-015**: Agent MUST detect rollout completion (success or failure) and proceed to appropriate next steps

#### Error Handling and Recovery

- **FR-016**: Agent MUST detect rollout failures and retrieve detailed error information from EV2
- **FR-017**: Agent MUST provide actionable error messages with recommendations for remediation
- **FR-018**: Agent MUST support retry operations for transient failures (max 3 retries with exponential backoff)
- **FR-019**: Agent MUST fail fast on non-recoverable errors with clear error messages
- **FR-020**: Agent MUST cancel remaining deployment stages on critical failures to prevent cascading issues

#### Validation and Testing

- **FR-021**: Agent MUST support stress testing deployed endpoints after each stage completion
- **FR-022**: Agent MUST send configurable load (number of requests, duration) to test endpoints
- **FR-023**: Agent MUST measure and report response times, error rates, and throughput
- **FR-024**: Agent MUST compare stress test results against defined thresholds (success rate, latency percentiles)
- **FR-025**: Agent MUST halt deployment progression if stress tests fail to meet thresholds
- **FR-026**: Agent MUST support bearer token authentication (Azure AD/OAuth2) when testing secured endpoints, accepting tokens via parameter or retrieving from Azure credential chain (MSI, service principals, user credentials)

#### Pipeline Integration

- **FR-027**: Agent MUST detect Azure DevOps pipeline configuration for the service
- **FR-028**: Agent MUST trigger ADO pipelines with appropriate parameters (branch, environment, artifact version)
- **FR-029**: Agent MUST monitor pipeline execution and wait for completion before proceeding with deployment
- **FR-030**: Agent MUST retrieve pipeline execution logs on failure and present them to the user

#### Approval Gates

- **FR-031**: Agent MUST detect wait actions in EV2 rollouts that require human approval
- **FR-032**: Agent MUST send Teams notifications to configured approvers with rollout details and action instructions
- **FR-033**: Agent MUST call EV2 API to stop wait actions when approval is granted
- **FR-034**: Agent MUST cancel rollouts when approval is rejected

#### Notifications

- **FR-035**: Agent MUST send post-deployment notifications via Teams webhooks
- **FR-036**: Notifications MUST include: service name, environment, rollout ID, status, duration, regions, artifact version, and EV2 dashboard link
- **FR-037**: Agent MUST log notification content locally if Teams webhook is unavailable
- **FR-038**: Agent MUST continue deployment operations even if notifications fail (non-critical)
- **FR-039**: Teams webhook URL MUST be configurable via parameter or configuration file, using Power Automate Workflow Webhook format with structured JSON payload

#### Configuration and Discoverability

- **FR-040**: Agent MUST provide help text indicating where to find required parameters (e.g., "serviceId is in ServiceModel.json", "rollout information in .azure/[env]/ev2/rollouts.json")
- **FR-041**: Agent MUST validate all required parameters are provided before starting operations
- **FR-042**: Agent MUST load configuration from a configuration file (JSON or YAML format) if present
- **FR-043**: Agent MUST support command-line parameter overrides for all configuration values

#### Resilience and Idempotency

- **FR-044**: Agent MUST be fully idempotent - can be safely run multiple times with the same parameters
- **FR-045**: Agent MUST resume from the last known good state if interrupted or restarted
- **FR-046**: Agent MUST persist state information in a local file (e.g., `.deploy-sentinel-state.json`)
- **FR-047**: Agent MUST prevent concurrent execution for the same service using file-based locking
- **FR-048**: Agent MUST clean up state files after successful completion

#### Implementation Constraints

- **FR-049**: Agent MUST be implemented as a single PowerShell script (no external dependencies beyond MCP servers)
- **FR-050**: Agent MUST require only EV2 MCP Server and Azure DevOps MCP Server as external dependencies
- **FR-051**: Agent MUST work on both Windows PowerShell 5.1+ and PowerShell Core 7+
- **FR-052**: Agent MUST log all operations with timestamps for audit and debugging purposes
- **FR-053**: Agent MUST detect stale state files (timestamp >24 hours old) and warn user to validate rollout status before resuming operations

### Key Entities

- **RolloutState**: Represents the current state of an EV2 rollout being managed by the agent. Key attributes include: rolloutId (unique identifier), serviceGroupName, serviceId, environment, currentStage, deployedRegions (list), pendingRegions (list), overallStatus (InProgress/Completed/Failed), errors (list), startTime, lastUpdateTime, artifactVersion, stageMapVersion. This is persisted to enable idempotent operations and recovery.

- **DeploymentConfig**: Represents the configuration for a deployment operation. Key attributes include: serviceGroupName (identifying the service group), serviceId (GUID), stageMapName (name of the rollout stages definition), environment (target environment like PPE/PROD), selectionScope (regions/steps/stamps to include), exclusionScope (regions/steps/stamps to exclude), teamsWebhookUrl (for notifications), stressTestConfig (endpoints and thresholds), pipelineConfig (ADO project and pipeline details). This can be loaded from a file or provided via parameters.

- **ServiceInfo**: Represents metadata about the service being deployed. Key attributes include: serviceGroupName, serviceId, latestArtifactVersion (discovered from EV2), latestStageMapVersion (discovered from EV2), serviceModel (path to ServiceModel.json if present), rolloutSpec (path to RolloutSpec.json if present), scopeBindings (path to ScopeBindings.json if present). Used for service discovery and validation.

- **StressTestResult**: Represents the results of stress testing a deployed endpoint. Key attributes include: endpointUrl, totalRequests, successfulRequests, failedRequests, errorRate (percentage), averageResponseTime, p50ResponseTime, p95ResponseTime, p99ResponseTime, testDuration, timestamp, passed (boolean based on threshold comparison). Used to determine whether to proceed with deployment.

- **NotificationMessage**: Represents a notification to be sent via Teams webhook. Key attributes include: title, status (Success/Failed/Warning), serviceGroupName, environment, rolloutId, duration, deployedRegions (list), artifactVersion, errorSummary (if failed), ev2DashboardUrl, timestamp. Formatted as an Adaptive Card or simple message card for Teams.

## Assumptions

1. **MCP Server Availability**: EV2 MCP Server and Azure DevOps MCP Server are properly installed and configured in `.vscode/mcp.json` before agent execution
2. **Service Configuration**: Services follow standard EV2 structure with ServiceModel.json, RolloutSpec.json, and ScopeBindings.json in predictable locations (`.azure/[env]/ev2/`)
3. **Git Repository**: Agent is invoked from within a git repository initialized for the service being deployed
4. **Authentication**: Developer running the agent has appropriate Azure credentials and permissions for EV2 operations and ADO pipeline access
5. **Teams Webhook**: Teams webhook URL follows Power Automate Workflow Webhook format and accepts structured JSON payloads defined by the user's flow configuration
6. **Network Connectivity**: Agent has network access to EV2 endpoints, ADO endpoints, and deployed service endpoints for stress testing
7. **Environment Naming**: Environments follow standard naming conventions (PPE, PROD) consistent with EV2 configuration
8. **Default Retry Policy**: Transient failures are retried 3 times with exponential backoff (1s, 2s, 4s) unless configured otherwise
9. **Default Polling Interval**: Rollout status is polled every 30 seconds unless configured otherwise
10. **Default Stress Test Configuration**: If not specified, stress tests send 100 requests over 30 seconds with thresholds: 95% success rate, p95 latency < 500ms
11. **Branch Naming Convention**: Feature branches use `deploy/[environment]/[serviceGroupName]/[timestamp]` pattern unless configured otherwise
12. **State File Location**: Deployment state is persisted in `.deploy-sentinel-state.json` in the current working directory
13. **Error Recovery**: Critical failures (authentication errors, invalid service configuration) are not automatically retried and require manual intervention

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can trigger a complete EV2 rollout from start to finish using a single command with minimal manual intervention (target: 0 manual steps for standard deployments)
- **SC-002**: Agent successfully discovers service configuration (artifact versions, stage maps) without requiring developer to manually look up these values (target: 100% automatic discovery for properly configured services)
- **SC-003**: Agent detects and reports deployment failures within 1 minute of the failure occurring in EV2 (target: ≤60 seconds detection latency)
- **SC-004**: Agent can resume interrupted deployments from the last known good state without requiring full restart (target: 100% successful resumption after interruption)
- **SC-005**: Stress tests complete within 2 minutes per stage and accurately identify performance regressions (target: ≤120 seconds per test, 95% accuracy in detecting issues)
- **SC-006**: Post-deployment notifications reach stakeholders within 5 minutes of deployment completion (target: ≤5 minutes notification latency)
- **SC-007**: Agent reduces deployment time by automating manual steps that typically take 15-30 minutes per deployment (target: 50% reduction in total deployment time)
- **SC-008**: Agent handles transient failures gracefully with automatic retry, achieving 90% success rate on retry for transient issues (target: 90% retry success rate)
- **SC-009**: Developer can understand deployment status and any issues without needing to check multiple dashboards or logs (target: all relevant information displayed in agent output)
- **SC-010**: Agent prevents deployment errors caused by incorrect parameter combinations or missing configuration (target: 80% reduction in configuration-related deployment failures)
