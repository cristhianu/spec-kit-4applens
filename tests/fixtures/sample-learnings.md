# Sample Learnings for Testing

**Purpose**: Test fixtures for unit tests and integration tests  
**Format**: `[Timestamp] [Category] [Context] → [Issue] → [Solution]`

---

## Security

[2025-10-15T10:00:00Z] Security Azure Storage → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and use Private Endpoints
[2025-10-20T14:30:00Z] Security Azure Key Vault → Public network access enabled → Configure Private Endpoints and disable public access
[2025-10-25T08:15:00Z] Security Azure SQL Database → TLS version not enforced → Set minimalTlsVersion: '1.2' in server properties

---

## Networking

[2025-10-10T09:00:00Z] Networking Azure Front Door → Used by default for global distribution → Only include when explicitly requested; prefer regional deployments
[2025-10-18T16:45:00Z] Networking VNet Integration → Missing for App Services → Configure vnetConfiguration with subnet delegation
[2025-10-22T11:20:00Z] Networking Private DNS Zones → Not linked to Private Endpoints → Create privatelink DNS zones and link to VNet

---

## Data Services

[2025-10-12T13:00:00Z] Data Services Cosmos DB → Missing throughput configuration → Specify throughput (RU/s) in database properties
[2025-10-19T10:30:00Z] Data Services Azure Storage → Blob public access allowed → Set allowBlobPublicAccess: false

---

## Compute

[2025-10-14T15:00:00Z] Compute Azure Functions → Not deployed within VNet → Configure vnetConfiguration for secure access
[2025-10-21T09:45:00Z] Compute App Service → HTTP traffic allowed → Redirect HTTP to HTTPS with httpsOnly: true
[2025-10-23T14:00:00Z] Compute Container Apps → Environment missing VNet integration → Configure vnetConfiguration in managedEnvironment
[2025-10-24T11:30:00Z] Compute AKS Cluster → Public API server endpoint enabled → Use private cluster with privateClusterEnabled: true
[2025-10-26T16:20:00Z] Compute Virtual Machine → SSH port 22 exposed to internet → Restrict SSH access to specific IP ranges in NSG rules

---

## Configuration

[2025-10-13T10:00:00Z] Configuration Resource Naming → Inconsistent naming conventions → Follow pattern: {resourceType}-{project}-{env}-{region}
[2025-10-17T13:45:00Z] Configuration API Versions → Outdated API versions → Use latest stable API versions (avoid preview unless needed)
[2025-10-28T09:00:00Z] Configuration Tags → Missing required governance tags → Include: environment, project, costCenter, owner

---

## Performance

[2025-10-16T12:00:00Z] Performance App Service Plan → Using Consumption tier for steady workloads → Use Premium or Standard tier for production
[2025-10-27T15:30:00Z] Performance Cosmos DB → Fixed throughput for variable workloads → Enable autoscale for cost optimization

---

**Total Entries**: 20  
**Use Cases**:
- Semantic similarity testing (duplicates vs non-duplicates)
- Category filtering tests
- Timestamp-based conflict resolution tests
- Performance benchmarking (loading time)
