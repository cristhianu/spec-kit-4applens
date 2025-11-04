# Implementation Plan: Bicep Validate Command

**Branch**: `003-bicep-validate-command` | **Date**: October 28, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-bicep-validate-command/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a new GitHub Copilot command that automates end-to-end validation of generated Bicep templates by discovering projects, analyzing configuration requirements, deploying prerequisite resources to test environments, extracting configuration values to Azure Key Vault, deploying applications with their templates, testing API endpoints, and iteratively fixing issues through integration with the existing `/speckit.bicep` command. The system will support both interactive project selection and direct targeting via command arguments.

## Technical Context

**Language/Version**: Python 3.11+ (leveraging existing Specify CLI infrastructure)  
**Primary Dependencies**: Azure CLI, httpx (async HTTP), azure-identity, azure-keyvault-secrets, pathlib, AST parsers  
**Storage**: File system for project discovery and template analysis, Azure Key Vault for secrets, Azure Resource Manager for deployments  
**Testing**: pytest with async support, pytest-httpx for endpoint testing, pytest-mock for Azure CLI mocking  
**Target Platform**: Windows, macOS, Linux (cross-platform Python support)
**Project Type**: CLI tool integration with GitHub Copilot (extends existing Specify CLI)  
**Performance Goals**: Project discovery under 5 seconds, configuration analysis under 2 minutes, full validation workflow under 15 minutes  
**Constraints**: Must work with test environments only, never production; must respect Azure API rate limits; maximum 30 minutes per validation session  
**Scale/Scope**: Support workspaces with 100+ projects, analyze projects up to 1000 files, handle 50 endpoints per validation, support 3+ parallel resource deployments

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Compliance

- **✅ Code Simplicity and Clarity**: Python CLI extending existing Specify structure, clear separation of concerns (discovery → analysis → deployment → testing), functional approach with focused utility functions
- **✅ Root Cause Solutions**: Addresses fundamental need for automated validation of infrastructure templates before production deployment, eliminating manual testing cycles
- **✅ Explicit Failure Over Silent Defaults**: Validation fails explicitly when projects missing, resources fail to deploy, endpoints return errors; no silent fallbacks or assumptions
- **✅ Early and Fatal Error Handling**: Clear error messages when Azure CLI unavailable, Key Vault inaccessible, or deployment fails; complete tracebacks preserved for debugging
- **✅ Iterative Development Approach**: MVP focuses on P1 features (project discovery, deployment, endpoint testing), then P2 (resource orchestration), then P3 (custom instructions)
- **✅ Minimal and Focused Changes**: Single command focused on Bicep template validation, clear scope boundaries with `/speckit.bicep` command for fixes
- **✅ Engineering Excellence Through Simplicity**: Leverages existing Specify CLI infrastructure, reuses Azure CLI for deployments, functional approach for analyzers and validators

### Constitutional Compliance Re-evaluation (Post-Design)

**✅ All principles maintained after detailed design**:

- **Code Simplicity**: Clear module structure (discovery, analyzer, deployer, validator, tester), each with single responsibility
- **Root Cause Solutions**: Validates actual deployment and functionality, not just syntax; fixes issues at source through `/speckit.bicep` integration
- **Explicit Failures**: Each validation stage fails clearly with actionable error messages, no silent fallbacks in configuration or deployment
- **Early Error Handling**: Validation occurs at each stage (project discovery, configuration analysis, resource deployment, endpoint testing) with immediate feedback
- **Iterative Development**: Phased approach (P1: core validation, P2: resource orchestration, P3: custom instructions) enables incremental delivery
- **Minimal Changes**: Focused scope on validation workflow, clear integration points with existing Bicep generator
- **Engineering Excellence**: Follows Azure SDK best practices, implements retry patterns with circuit breakers, uses structured error handling

**No constitutional violations introduced during design phase.**

## Project Structure

### Documentation (this feature)

```text
specs/003-bicep-validate-command/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── project-discovery-api.yaml      # Project discovery service contract
│   ├── configuration-analysis-api.yaml # App settings analysis contract
│   ├── deployment-orchestration-api.yaml # Resource deployment contract
│   └── validation-testing-api.yaml     # Endpoint testing contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── specify_cli/
│   ├── commands/
│   │   └── bicep_validate.py          # New validation command entry point
│   ├── bicep/
│   │   ├── validator.py                # Existing validator (may extend)
│   │   └── cli_simple.py               # Existing CLI (may extend)
│   ├── validation/                     # New validation module
│   │   ├── __init__.py
│   │   ├── project_discovery.py        # Project and Bicep template discovery
│   │   ├── config_analyzer.py          # App settings and dependency analysis
│   │   ├── resource_deployer.py        # Azure resource deployment orchestration
│   │   ├── keyvault_manager.py         # Key Vault secret management
│   │   ├── endpoint_discoverer.py      # API endpoint discovery from code
│   │   ├── endpoint_tester.py          # HTTP endpoint testing with retry
│   │   ├── fix_orchestrator.py         # Integration with /speckit.bicep for fixes
│   │   └── validation_session.py       # Validation workflow orchestration
│   └── utils/
│       ├── azure_cli_wrapper.py        # Azure CLI command execution wrapper
│       ├── dependency_graph.py         # Topological sort for resource ordering
│       └── retry_policies.py           # Exponential backoff and circuit breaker

scripts/
├── powershell/
│   ├── bicep-validate.ps1              # PowerShell entry point for validation
│   └── bicep-deploy-test.ps1           # Test environment deployment helper
└── bash/
    ├── bicep-validate.sh               # Bash entry point for validation
    └── bicep-deploy-test.sh            # Test environment deployment helper

templates/
└── commands/
    └── speckit.validate.prompt.md      # GitHub Copilot command definition

tests/
├── validation/                          # New test module
│   ├── test_project_discovery.py        # Project discovery tests
│   ├── test_config_analyzer.py          # Configuration analysis tests
│   ├── test_resource_deployer.py        # Deployment orchestration tests
│   ├── test_keyvault_manager.py         # Key Vault integration tests
│   ├── test_endpoint_discoverer.py      # Endpoint discovery tests
│   ├── test_endpoint_tester.py          # Endpoint testing tests
│   ├── test_fix_orchestrator.py         # Fix integration tests
│   └── test_validation_session.py       # End-to-end workflow tests
└── fixtures/
    └── sample_projects/                 # Test projects with Bicep templates
        ├── dotnet-api/
        │   ├── Program.cs
        │   ├── appsettings.json
        │   └── bicep-templates/
        ├── nodejs-express/
        │   ├── server.js
        │   ├── .env.example
        │   └── bicep-templates/
        └── python-fastapi/
            ├── main.py
            ├── config.py
            └── bicep-templates/
```

**Structure Decision**: Extended the existing Specify CLI Python structure to include a new `validation/` module that handles all validation-related functionality. This approach:

- Reuses existing Bicep infrastructure (`src/specify_cli/bicep/`)
- Maintains separation of concerns (validation is independent module)
- Follows existing CLI command pattern (`bicep_validate.py` similar to `bicep_generator.py`)
- Enables incremental development with clear module boundaries
- Supports cross-platform execution through PowerShell and Bash scripts

## Complexity Tracking

No constitutional violations detected - complexity tracking not required.

---

## Phase 0: Research ✅ COMPLETE

**Status**: Complete  
**Artifacts**: `research.md` (1000+ lines covering 7 technical areas)

### Research Completed

✅ **Project Discovery Patterns**: pathlib + glob for cross-platform file discovery, file-based caching (.bicep-cache.json), framework detection via signature files  
✅ **App Settings Analysis**: Framework-specific parsers (appsettings.json, .env, config.py), AST-based code analysis, secure value detection patterns  
✅ **Deployment Orchestration**: Azure CLI subprocess wrapper, topological sort (Kahn's algorithm) for dependency ordering, parallel deployment with max 4 concurrent  
✅ **Key Vault Integration**: Managed Identity + RBAC for authentication, Azure naming conventions, Key Vault reference format for App Service  
✅ **API Endpoint Discovery**: OpenAPI/Swagger parsing, code-based route extraction (ASP.NET, Express, FastAPI), endpoint metadata extraction  
✅ **Endpoint Testing**: httpx async HTTP client, exponential backoff with jitter, circuit breaker pattern, retry policies  
✅ **Fix-and-Retry Patterns**: Error classification (timeout, auth, server error, template issue), fix strategies per category, integration with `/speckit.bicep`

### Technology Decisions

- **Project Discovery**: pathlib (cross-platform), glob patterns, file-based caching
- **Configuration Analysis**: Framework-specific parsers, AST inspection, dependency graph construction
- **Resource Deployment**: Azure CLI (subprocess), topological sort, async parallel execution
- **Secret Management**: azure-identity + azure-keyvault-secrets, Managed Identity, RBAC
- **Endpoint Testing**: httpx (async HTTP), exponential backoff, circuit breaker
- **Error Handling**: Structured exceptions, error classification, automated fix dispatch

---

## Phase 1: Design & Contracts ✅ COMPLETE

**Status**: Complete  
**Artifacts**: `data-model.md`, `contracts/module-interfaces.md`, `quickstart.md`

### Data Model Complete

✅ **8 Core Entities Defined**:
- Project: Discovered projects with Bicep templates
- ApplicationSetting: Configuration requirements with security classification
- ResourceDependency: Infrastructure dependencies with deployment order
- ValidationEndpoint: API endpoints with test parameters
- DeploymentResult: Resource deployment outcomes with outputs
- EndpointTestResult: HTTP test results with performance metrics
- ValidationSession: Complete workflow state with stage tracking
- FixAttempt: Automated fix results with success tracking

✅ **Relationships Mapped**: Project → Settings → Dependencies → Resources, Project → Endpoints → Tests, Session → Results → Fixes

✅ **Validation Rules**: Required fields, format constraints, state transitions, business rules

✅ **Data Flow Diagrams**: Request flow, dependency resolution, validation workflow, fix-and-retry cycle

### API Contracts Complete

✅ **8 Module Interfaces Defined**:
- ProjectDiscovery: discover_projects(), get_project_by_name(), clear_cache()
- ConfigAnalyzer: analyze_project(), build_dependency_graph()
- ResourceDeployer: deploy_resources(), validate_template(), rollback_deployment()
- KeyVaultManager: store_secret(), get_secret(), store_multiple_secrets(), build_app_setting_reference()
- EndpointDiscoverer: discover_endpoints(), parse_openapi_spec()
- EndpointTester: test_endpoint(), test_multiple_endpoints()
- FixOrchestrator: attempt_fix(), fix_template_issue()
- ValidationSession: run(), get_current_stage(), get_progress()

✅ **Error Handling Contract**: 6 exception types, error response format, retry policies

✅ **Testing Contract**: Unit tests, integration tests, mock fixtures, example usage

### User Guide Complete

✅ **Quickstart.md Created** (650+ lines):
- Prerequisites and installation
- Basic usage examples (4 common scenarios)
- Workflow stages (9 detailed stages with sample output)
- Common scenarios (4 real-world examples)
- Troubleshooting guide (5 common issues with solutions)
- Advanced usage (custom environments, verbose output, retry tuning)
- Integration patterns (with /speckit.bicep, /speckit.plan, /speckit.tasks)
- Best practices (5 recommended practices)
- Performance tips (caching, parallel execution)
- Security considerations (managed identity, secret storage, audit trails)
- FAQ (6 frequently asked questions)

---

## Phase 2: Implementation Tasks

**Status**: Pending - Use `/speckit.tasks` command to generate tasks.md

**Note**: Phase 2 (Implementation Tasks) is NOT generated by `/speckit.plan`. The `/speckit.tasks` command is a separate workflow that reads this plan and generates a detailed task breakdown.

**Command to run next**:

```powershell
/speckit.tasks
```

This will:
1. Read `plan.md` and `spec.md`
2. Generate detailed task breakdown in `tasks.md`
3. Create implementation checklist with priority, effort estimates, dependencies
4. Provide step-by-step instructions for implementation

---

## Plan Completion Summary

### Artifacts Generated

✅ **Phase 0 - Research**:
- `research.md` (1000+ lines) - Comprehensive technology research covering 7 areas with code examples

✅ **Phase 1 - Design & Contracts**:
- `data-model.md` (350+ lines) - 8 entities with relationships, validation rules, state transitions
- `contracts/module-interfaces.md` (700+ lines) - 8 Python module interfaces with usage examples
- `quickstart.md` (650+ lines) - Complete user guide with examples, troubleshooting, best practices

### Readiness Check

✅ **Technical Foundation**: All technology decisions documented with rationale  
✅ **Data Model**: All entities, relationships, and validation rules defined  
✅ **API Contracts**: All module interfaces specified with error handling  
✅ **User Experience**: Complete user guide with examples and troubleshooting  
✅ **Constitutional Compliance**: No violations detected  
✅ **Project Structure**: Clear directory layout and module organization

**Status**: Ready for `/speckit.tasks` command to generate implementation breakdown

### Next Steps

1. **Generate Implementation Tasks**:
   ```powershell
   /speckit.tasks
   ```
   This will create `tasks.md` with detailed task breakdown

2. **Update Agent Context** (after tasks.md created):
   ```powershell
   scripts/powershell/update-agent-context.ps1 -AgentType copilot
   ```

3. **Begin Implementation** (after tasks.md created):
   Follow tasks.md checklist for implementation sequence

---

**Plan Complete** ✅  
**Date**: October 28, 2025  
**Ready For**: `/speckit.tasks` command execution

