# spec-kit-4applens Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-21

## Active Technologies
- PowerShell 5.1+ and Python 3.11+ (for MCP Server integration) + Azure MCP Server, Azure CLI, Bicep CLI, PowerShell modules (Az.Resources, Az.Profile) (002-bicep-generator-command)
- Python 3.11+ (leveraging existing Specify CLI infrastructure) + Azure CLI, httpx (async HTTP), azure-identity, azure-keyvault-secrets, pathlib, AST parsers (003-bicep-validate-command)
- File system for project discovery and template analysis, Azure Key Vault for secrets, Azure Resource Manager for deployments (003-bicep-validate-command)

## Project Structure
```
src/
tests/
```

## Commands
cd src; pytest; ruff check .

## Code Style
PowerShell 5.1+ and Python 3.11+ (for MCP Server integration): Follow standard conventions

## Recent Changes
- 003-bicep-validate-command: Added Python 3.11+ (leveraging existing Specify CLI infrastructure) + Azure CLI, httpx (async HTTP), azure-identity, azure-keyvault-secrets, pathlib, AST parsers
- 003-bicep-validate-command: Added Python 3.11+ (leveraging existing Specify CLI infrastructure) + Azure CLI, httpx (async HTTP), azure-identity, azure-keyvault-secrets, pathlib, AST parsers
- 002-bicep-generator-command: Added PowerShell 5.1+ and Python 3.11+ (for MCP Server integration) + Azure MCP Server, Azure CLI, Bicep CLI, PowerShell modules (Az.Resources, Az.Profile)

<!-- MANUAL ADDITIONS START -->
## Bicep Generator - Ev2 Integration

When working with the Bicep Generator (`/speckit.bicep` command or `specify bicep` CLI):

### Ev2 Detection
- The generator automatically scans for existing Ev2 configuration files:
  - `RolloutSpec*.json` - Orchestration and rollout stages
  - `ServiceModel*.json` - Service topology and resource definitions
  - `Parameters*.json` - Environment-specific configuration
  - `ScopeBindings*.json` - Deployment targets (subscriptions, regions)
  - `*.armtemplate` - Existing ARM template resources

### Context-Aware Questions
- If Ev2 configuration exists: Asks questions about resource gaps, naming alignment, deployment strategy
- If NO Ev2: Asks about deployment targets, environments, and future Ev2 plans
- All questions are context-aware based on detected Ev2 configuration and project dependencies

### Output Structure
Generated Bicep templates follow Ev2-compatible structure:
```
bicep-templates/
├── main.bicep
├── parameters/ (Ev2-compatible format)
├── modules/ (modular Bicep templates)
├── ev2-integration/ (ServiceModel/RolloutSpec templates + integration guide)
└── README.md
```

### Integration Guidance
- **Existing Ev2**: Provides guidance for adding ExtensionResource entries to ServiceModel
- **No Ev2**: Offers two paths (direct Azure CLI deployment or Ev2 setup with templates)

See `EV2-INTEGRATION-SUMMARY.md` for complete details.
<!-- MANUAL ADDITIONS END -->
