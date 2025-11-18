# Bicep Learnings Database

**Purpose**: Shared learnings from Bicep deployments, validation failures, and architectural decisions  
**Format**: `[Timestamp] [Category] [Context] → [Issue] → [Solution]`  
**Usage**: Referenced by `/speckit.bicep` and `/speckit.validate` commands for context-aware guidance  
**Maintenance**: Auto-populated from errors + manually curated for quality

---

## Security

[2025-11-01T00:00:00Z] Security Azure Storage → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and use Private Endpoints
[2025-11-01T00:00:00Z] Security Azure Key Vault → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and configure Private Endpoints
[2025-11-01T00:00:00Z] Security Azure Key Vault → Access policies used instead of RBAC → Set enableRbacAuthorization: true in Key Vault properties for centralized IAM management
[2025-11-01T00:00:00Z] Security Azure SQL Database → TLS version not enforced → Set minimalTlsVersion: '1.2' in server properties
[2025-11-01T00:00:00Z] Security Azure App Service → Managed Identity not configured → Use managedIdentity for authentication instead of connection strings
[2025-11-01T00:00:00Z] Security Managed Identity → Configured but lacks required permissions → Grant Azure RBAC roles (e.g., Key Vault Secrets User, Storage Blob Data Contributor) to Managed Identity principal

---

## Compliance

[2025-11-01T00:00:00Z] Compliance All Resources → Missing diagnostic settings → Configure diagnosticSettings with Log Analytics workspace for audit compliance
[2025-11-01T00:00:00Z] Compliance Azure Key Vault → Key Vault operations not audited → Configure diagnosticSettings with Log Analytics workspace and enable AuditEvent logs for compliance

---

## Networking

[2025-11-01T00:00:00Z] Networking Azure Front Door → Used by default for global distribution → Only include when explicitly requested; prefer regional deployments with Private Endpoints
[2025-11-01T00:00:00Z] Networking Network Security Perimeter → Suggested for service-level isolation → Avoid in favor of Private Endpoints with VNet Integration (more granular control)
[2025-11-01T00:00:00Z] Networking VNet Integration → Missing for App Services → Configure vnetConfiguration with subnet delegation for secure backend access
[2025-11-01T00:00:00Z] Networking Subnet Configuration → Deployed without Network Security Group → Create NSG resource and attach via subnet's networkSecurityGroup property for traffic filtering
[2025-11-01T00:00:00Z] Networking Private DNS Zones → Not linked to Private Endpoints → Create privatelink DNS zones and link to VNet for name resolution
[2025-11-01T00:00:00Z] Networking Azure SQL Database → Service not accessible from Azure services → Add VNet integration with service endpoints OR firewall rule (startIpAddress: 0.0.0.0, endIpAddress: 0.0.0.0) if VNet not available

---

## Data Services

[2025-11-01T00:00:00Z] Data Services Cosmos DB → Missing throughput configuration → Specify throughput (RU/s) in database properties to avoid provisioning errors
[2025-11-01T00:00:00Z] Data Services Azure Storage → Blob public access allowed → Set allowBlobPublicAccess: false for storage account security
[2025-11-01T00:00:00Z] Data Services Azure SQL Database → Server firewall allows all Azure IPs → Remove 0.0.0.0 firewall rule, use VNet integration instead

---

## Compute

[2025-11-01T00:00:00Z] Compute Azure Functions → Not deployed within VNet → Configure vnetConfiguration for secure access to backend resources
[2025-11-01T00:00:00Z] Compute App Service → HTTP traffic allowed → Redirect HTTP to HTTPS with httpsOnly: true property
[2025-11-01T00:00:00Z] Compute Container Apps → Environment missing VNet integration → Configure vnetConfiguration in managedEnvironment for network isolation

---

## Configuration

[2025-11-01T00:00:00Z] Configuration Resource Naming → Inconsistent naming conventions → Follow naming convention: {resourceType}-{project}-{environment}-{region}-{instance}
[2025-11-01T00:00:00Z] Configuration API Versions → Outdated API versions used → Use latest stable API versions (avoid preview unless explicitly needed)
[2025-11-01T00:00:00Z] Configuration Tags → Missing required tags → Include tags: environment, project, costCenter, owner for resource governance

---

## Performance

[2025-11-01T00:00:00Z] Performance App Service Plan → Using Consumption tier for consistent workloads → Use Premium or Standard tier for production workloads with predictable traffic
[2025-11-01T00:00:00Z] Performance Cosmos DB → Autoscale not configured → Enable autoscale for throughput to handle variable workloads efficiently

---

## Operations

[2025-11-01T00:00:00Z] Operations All Resources → No alerts configured → Define alert rules for critical metrics (availability, performance, errors)
[2025-11-01T00:00:00Z] Operations Application Insights → Not linked to resources → Configure applicationInsights connection for telemetry collection

---

**Total Entries**: 27  
**Last Updated**: 2025-11-01T00:00:00Z  
**Semantic Similarity Threshold**: 60% (TF-IDF + Cosine Similarity)

<!-- 
Maintenance Notes:
- Manual additions: Follow format strictly [Timestamp] [Category] [Context] → [Issue] → [Solution]
- Duplicate detection: Automatic via semantic similarity (>60% = duplicate, will be rejected)
- Conflict resolution: Security/Compliance categories override all others, most recent timestamp wins within tier
- Performance limits: 250 entries = automatic category filtering, 200 entries = warning notification
- Error classification: Capture structural errors (missing property, invalid value), ignore transient errors (throttled, timeout)
-->
