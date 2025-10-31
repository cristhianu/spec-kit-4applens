# Feature Specification: Bicep Validate Command

**Feature Branch**: `003-bicep-validate-command`  
**Created**: October 28, 2025  
**Status**: Draft  
**Input**: User description: "Generate another command like speckit.bicep.prompt.md called validate. This command will start by listing the projects that have bicep template generated and prompt the user which one to focus on. Then it will review the corresponding code and templates to understand it: Understand the minimum App Settings that need to be configured and add them to Key Vault. If an app Setting/Connection string depends on a resource being deployed, it will deploy that resource first to be able to retrieve the setting. It will generate a list of API endpoints to test against to validate its working. Then will deploy it to a test corp environment along with its corresponding source code to validate that they work correctly. Every time it finds a problem related to the bicep template, it will call /speckit.bicep <issue explanation> to have them fixed. Once they are fixed it will try again until it's able to successfully validate the deployment. If user input is received ($ARGUMENTS), it will follow those special instructions to do the validation or will focus on the specific project provided."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Project Selection and Configuration Discovery (Priority: P1)

A developer has generated Bicep templates for one or more projects and needs to validate that the templates are deployable and functional. The validate command starts by discovering all projects with generated Bicep templates, presents them to the user for selection, and then analyzes the selected project to identify required application settings and their dependencies.

**Why this priority**: This is the foundation of the validation workflow. Without proper project selection and configuration discovery, subsequent validation steps cannot proceed. This delivers immediate value by helping developers understand what configuration is needed.

**Independent Test**: Can be fully tested by running the validate command, selecting a project from the list, and verifying that all required app settings and dependencies are correctly identified and displayed without requiring actual deployment.

**Acceptance Scenarios**:

1. **Given** multiple projects with generated Bicep templates exist, **When** user invokes the validate command, **Then** a list of all projects with Bicep templates is displayed with project names and paths
2. **Given** user is prompted to select a project, **When** user selects a project from the list, **Then** the system analyzes the project's source code and Bicep templates to identify required application settings
3. **Given** a project is selected, **When** the system discovers app settings that depend on deployed resources, **Then** the system identifies these dependencies and their deployment order
4. **Given** user provides a specific project name in $ARGUMENTS, **When** the validate command runs, **Then** the system skips the selection prompt and proceeds directly with that project
5. **Given** no projects with Bicep templates exist, **When** user invokes the validate command, **Then** the system displays a helpful error message explaining that no projects are available for validation

---

### User Story 2 - Automated Resource Deployment for Configuration (Priority: P2)

After identifying required application settings, the validate command automatically deploys prerequisite resources (such as databases, storage accounts, service buses) needed to obtain connection strings and configuration values. These values are securely stored in Key Vault and made available to the application.

**Why this priority**: This enables end-to-end validation by ensuring all dependencies are in place. It provides significant value by automating the tedious process of deploying dependencies and configuring connection strings.

**Independent Test**: Can be tested independently by providing a project with known resource dependencies, running validation, and verifying that prerequisite resources are deployed in the correct order and their configuration values are stored in Key Vault.

**Acceptance Scenarios**:

1. **Given** an app setting requires a database connection string, **When** validation runs, **Then** the database resource is deployed first and the connection string is retrieved and stored in Key Vault
2. **Given** multiple app settings have interdependent resources, **When** validation runs, **Then** resources are deployed in the correct dependency order
3. **Given** a resource deployment fails, **When** validation detects the failure, **Then** the system reports the error with diagnostic information and halts further dependent deployments
4. **Given** all prerequisite resources are successfully deployed, **When** configuration values are retrieved, **Then** all values are stored in Key Vault with appropriate access policies configured

---

### User Story 3 - Test Deployment and Endpoint Validation (Priority: P1)

Once configuration is complete, the validate command deploys the application and its Bicep templates to a test environment, then automatically tests the deployed endpoints to verify the application is functioning correctly. If issues are detected, the system iteratively fixes problems by calling the speckit.bicep command until validation succeeds.

**Why this priority**: This is the core value proposition - automated validation that the deployment actually works. It catches configuration and deployment issues before production, saving significant debugging time.

**Independent Test**: Can be fully tested by deploying a known-working project to a test environment and verifying that all identified endpoints are tested successfully, or by deploying a project with known issues and verifying the iterative fix process works.

**Acceptance Scenarios**:

1. **Given** configuration is complete, **When** validation proceeds to deployment, **Then** the Bicep templates and application code are deployed to the test corporate environment
2. **Given** the application is deployed, **When** the system tests the generated API endpoints, **Then** each endpoint is called and the response is validated for success (2xx status codes and expected response structure)
3. **Given** an endpoint test fails, **When** the failure is detected, **Then** the system analyzes the error, calls `/speckit.bicep <issue explanation>` to fix the template issue, and retries the deployment
4. **Given** template fixes are applied, **When** the system retries deployment, **Then** the process continues iteratively until all endpoint tests pass or a maximum retry limit is reached
5. **Given** all endpoint tests pass, **When** validation completes, **Then** the system reports success with a summary of deployed resources, tested endpoints, and configuration stored in Key Vault
6. **Given** user provides special validation instructions in $ARGUMENTS, **When** validation runs, **Then** the system follows those custom instructions while maintaining the overall validation workflow

---

### User Story 4 - Custom Validation Instructions (Priority: P3)

Users can provide custom validation instructions or specific projects to validate via the $ARGUMENTS parameter. This allows for targeted validation scenarios, such as testing specific endpoints, using custom test environments, or applying special deployment configurations.

**Why this priority**: This provides flexibility for advanced scenarios but is not required for basic validation workflow. Most users will use default validation behavior.

**Independent Test**: Can be tested by providing various custom instructions through $ARGUMENTS and verifying the system correctly interprets and executes them.

**Acceptance Scenarios**:

1. **Given** user provides a project name in $ARGUMENTS, **When** validation runs, **Then** the system validates only that specific project without prompting
2. **Given** user provides custom endpoint testing instructions in $ARGUMENTS, **When** endpoint validation runs, **Then** the system uses the custom test criteria instead of default validation
3. **Given** user provides environment-specific instructions in $ARGUMENTS, **When** deployment occurs, **Then** the system deploys to the specified environment with appropriate configuration

---

### Edge Cases

- What happens when a project has Bicep templates but the source code is missing or incomplete?
- How does the system handle circular dependencies between app settings and resources?
- What happens when deployment to test environment fails due to permission issues?
- How does the system handle timeouts during resource deployment or endpoint testing?
- What happens when Key Vault access is denied or Key Vault doesn't exist?
- How does the system handle projects with no identifiable API endpoints?
- What happens when the maximum retry limit for fixing template issues is reached?
- How does the system handle conflicting custom instructions in $ARGUMENTS?
- What happens when a prerequisite resource already exists in the target environment?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST discover and list all projects in the workspace that have generated Bicep templates
- **FR-002**: System MUST prompt user to select a project from the discovered list when no project is specified in $ARGUMENTS
- **FR-003**: System MUST analyze selected project's source code and Bicep templates to identify required application settings and connection strings
- **FR-004**: System MUST identify dependencies between app settings and Azure resources that must be deployed
- **FR-005**: System MUST determine the correct deployment order for dependent resources
- **FR-006**: System MUST deploy prerequisite resources to obtain required configuration values before deploying the main application
- **FR-007**: System MUST store all configuration values (connection strings, app settings) in Azure Key Vault
- **FR-008**: System MUST configure Key Vault access policies to allow the deployed application to retrieve secrets
- **FR-009**: System MUST generate a list of API endpoints to test based on the application's source code and configuration
- **FR-010**: System MUST deploy the application and its Bicep templates to a test corporate environment
- **FR-011**: System MUST test each identified endpoint by making HTTP requests and validating responses
- **FR-012**: System MUST detect failures in deployment or endpoint testing and capture diagnostic information
- **FR-013**: System MUST call `/speckit.bicep <issue explanation>` when deployment or template issues are detected
- **FR-014**: System MUST retry deployment after template fixes are applied
- **FR-015**: System MUST continue the fix-and-retry cycle until validation succeeds or maximum retry limit is reached
- **FR-016**: System MUST accept custom validation instructions through $ARGUMENTS parameter
- **FR-017**: System MUST accept a specific project name through $ARGUMENTS to bypass project selection
- **FR-018**: System MUST report validation progress at each stage (discovery, configuration, deployment, testing)
- **FR-019**: System MUST provide a comprehensive validation summary upon completion including deployed resources, tested endpoints, and stored configuration
- **FR-020**: System MUST handle errors gracefully and provide actionable error messages

### Key Entities

- **Project**: Represents a workspace project with generated Bicep templates, including project name, path, source code location, and Bicep template location
- **Application Setting**: Represents a configuration value required by the application, including name, value type, source (hardcoded, Key Vault reference, or deployment output), and resource dependency
- **Resource Dependency**: Represents an Azure resource that must be deployed to obtain configuration values, including resource type, deployment order, and dependent settings
- **Validation Endpoint**: Represents an API endpoint to test, including URL pattern, HTTP method, expected status codes, and validation criteria
- **Deployment Result**: Represents the outcome of a deployment attempt, including success status, deployed resources, error messages, and diagnostic information
- **Validation Session**: Represents a complete validation workflow, including selected project, deployment stages, test results, retry attempts, and final status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover and select from available projects with Bicep templates in under 30 seconds
- **SC-002**: System correctly identifies all required application settings and their resource dependencies with 95% accuracy
  - **Measurement**: Accuracy = (Correct Identifications / Total App Settings) × 100%
    - Correct Identification = App setting correctly identified AND resource dependency correctly identified
    - False Positive = Non-existent app setting identified
    - False Negative = Required app setting missed
  - **Test Method**: Run against 20+ test projects with documented app settings (ground truth)
    - Manually document all required app settings for each project
    - Run config analyzer to identify app settings
    - Compare discovered settings against ground truth
    - Calculate accuracy percentage
- **SC-003**: System successfully deploys prerequisite resources in the correct dependency order for 90% of standard Azure resource types
  - **Measurement**: Success Rate = (Successful Deployments / Total Deployment Attempts) × 100%
    - Successful Deployment = All resources deployed without errors AND dependencies deployed before dependents
    - Failed Deployment = Deployment error OR incorrect deployment order
    - Excludes: Deployment failures due to quota limits or permission issues
  - **Test Method**: Deploy templates across test environments
    - Test with 20+ resource type combinations (SQL + Storage, CosmosDB + Functions, etc.)
    - Verify deployment order matches dependency graph
    - Track success/failure outcomes
    - Calculate success rate across all attempts
- **SC-004**: All configuration values are securely stored in Key Vault and accessible to the deployed application within 5 minutes of validation start
- **SC-005**: System successfully identifies and tests at least 80% of valid API endpoints in the deployed application
  - **Measurement**: Detection Rate = (Detected Valid Endpoints / Total Valid Endpoints) × 100%
    - Valid Endpoint = HTTP endpoint that returns 2xx status code (or documented success code)
    - Detected Endpoint = Endpoint discovered by endpoint_discoverer AND successfully tested
    - Total Valid Endpoints = Ground truth from manual code review or documentation
  - **Test Method**: Deploy test applications with known endpoints
    - Manually document all API endpoints in test apps (ground truth)
    - Run endpoint discovery to extract URLs from code/config
    - Test each discovered endpoint for accessibility
    - Calculate detection rate: discovered endpoints / documented endpoints
    - Test across frameworks (ASP.NET, Express.js, FastAPI)
- **SC-006**: Validation workflow completes end-to-end (discovery through deployment to testing) in under 15 minutes for typical applications
- **SC-007**: System successfully fixes and retries deployment issues in 70% of cases without manual intervention
- **SC-008**: Users receive clear, actionable error messages that help resolve validation failures within 2 minutes of issue detection
- **SC-009**: System reduces manual validation time by at least 60% compared to manual deployment and testing
- **SC-010**: 95% of successful validations result in applications that are immediately deployable to production without additional configuration changes

## Assumptions

- Test corporate environment is pre-configured and accessible with appropriate permissions
- Azure Key Vault resource exists or can be created in the test environment
- Projects follow standard application structure with identifiable configuration patterns
- API endpoints follow RESTful conventions or are documented in standard formats (OpenAPI, etc.)
- Bicep templates follow Azure best practices and are compatible with the speckit.bicep command
- Test environment has sufficient quota and permissions to deploy all required resource types
- Network connectivity exists between test environment resources
- Default retry limit for fix-and-retry cycle is 3 attempts unless specified otherwise
- Endpoint validation considers 2xx HTTP status codes as success by default
- Connection strings and sensitive configuration are never logged or displayed in plain text

## Constraints

- Validation must be performed in test environment only, never directly in production
- All configuration values must be stored in Key Vault, not in application configuration files
- System cannot modify production resources or configurations
- Validation command execution time should not exceed 30 minutes for any single project
- Maximum of 50 endpoints can be tested per validation session to prevent excessive execution time
- System must respect Azure API rate limits and implement appropriate backoff strategies

## Dependencies

- Depends on existing `/speckit.bicep` command for template generation and fixes
- Requires Azure CLI or appropriate Azure SDK for resource deployment
- Requires access to Azure Key Vault for secrets management
- Requires permissions to deploy resources in test corporate environment
- May depend on existing Bicep template generation infrastructure from feature 002
- May require integration with project build/package tools (npm, dotnet, maven, etc.) to deploy source code

