# Secure Future Initiative (SFI) Best Practices Patterns

**Feature**: 004-bicep-learnings-database  
**Version**: 1.0.0  
**Status**: Draft  
**Purpose**: Document SFI-compliant architectural patterns for Bicep template generation

---

## Overview

The Secure Future Initiative (SFI) establishes security-first principles for Azure deployments. This document defines specific patterns that MUST be applied during Bicep template generation to ensure compliance with SFI requirements.

**Core SFI Principles**:
1. **Network Isolation**: Deploy all resources within private networks
2. **No Public Endpoints**: Disable public network access for all data services
3. **Private Connectivity**: Use Private Link/Private Endpoints for service-to-service communication
4. **Identity-Based Authentication**: Use Managed Identity instead of connection strings/keys
5. **Encryption Everywhere**: TLS 1.2+ for in-transit, customer-managed keys for at-rest

---

## Pattern 1: VNet Isolation

### Requirement
All resources MUST be deployed within the same Virtual Network (VNet) with proper subnet segmentation. No resources should have direct internet exposure.

### Bicep Pattern

```bicep
// Create VNet with multiple subnets for different resource types
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'vnet-${resourceToken}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'snet-appservices'
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'snet-data'
        properties: {
          addressPrefix: '10.0.2.0/24'
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
            }
            {
              service: 'Microsoft.Sql'
            }
          ]
        }
      }
      {
        name: 'snet-privateendpoints'
        properties: {
          addressPrefix: '10.0.3.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Networking VNet Isolation → Resources deployed without VNet integration → Deploy all resources within same VNet using subnet delegation and service endpoints
```

---

## Pattern 2: Disable Public Network Access

### Requirement
All data services (Storage Accounts, Key Vaults, databases) MUST have public network access disabled and use Private Endpoints exclusively.

### Bicep Pattern

```bicep
// Storage Account with public access disabled
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${resourceToken}'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}

// Key Vault with public access disabled
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${resourceToken}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}

// Azure SQL Database with public access disabled
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: 'sql-${resourceToken}'
  location: location
  properties: {
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Security Azure Storage → Public network access enabled by default → Set publicNetworkAccess: 'Disabled' and configure Private Endpoint
```

```
2025-10-31T15:00:00Z Security Azure Key Vault → Public network access not disabled → Set publicNetworkAccess: 'Disabled' and networkAcls.defaultAction: 'Deny'
```

```
2025-10-31T15:00:00Z Security Azure SQL → Public endpoint exposed → Set publicNetworkAccess: 'Disabled' and use Private Endpoint connectivity
```

---

## Pattern 3: Private Endpoints with DNS Integration

### Requirement
All service-to-service communication MUST use Private Link connectivity with proper private DNS zone integration for name resolution.

### Bicep Pattern

```bicep
// Private Endpoint for Storage Account
resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-storage-${resourceToken}'
  location: location
  properties: {
    subnet: {
      id: vnet.properties.subnets[2].id // snet-privateendpoints
    }
    privateLinkServiceConnections: [
      {
        name: 'storage-connection'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

// Private DNS Zone for Storage Blob
resource storageDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
}

// Link DNS Zone to VNet
resource storageDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: storageDnsZone
  name: 'vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

// DNS Zone Group for automatic DNS registration
resource storageDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: storagePrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config'
        properties: {
          privateDnsZoneId: storageDnsZone.id
        }
      }
    ]
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Networking Private Endpoints → Missing private DNS zone integration → Create privateDnsZone and privateDnsZoneGroups for automatic DNS registration
```

```
2025-10-31T15:00:00Z Networking Private Link → Service endpoints used instead of Private Endpoints → Replace service endpoints with Private Endpoints for data exfiltration protection
```

---

## Pattern 4: Managed Identity Authentication

### Requirement
All service-to-service authentication MUST use Managed Identity. Connection strings and access keys MUST NOT be used or stored.

### Bicep Pattern

```bicep
// App Service with System-Assigned Managed Identity
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'app-${resourceToken}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    vnetRouteAllEnabled: true
    virtualNetworkSubnetId: vnet.properties.subnets[0].id
  }
}

// Grant App Service access to Key Vault
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  parent: keyVault
  name: 'add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: appService.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

// Grant App Service access to Storage Account (RBAC)
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid(storageAccount.id, appService.id, 'Storage Blob Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Security Managed Identity → Connection strings stored in configuration → Use SystemAssigned identity and RBAC role assignments instead of connection strings
```

```
2025-10-31T15:00:00Z Security Authentication → Access keys used for Storage Account → Replace with Managed Identity and 'Storage Blob Data Contributor' role assignment
```

---

## Pattern 5: Encryption Configuration

### Requirement
All data services MUST enforce encryption in transit (TLS 1.2+) and support encryption at rest with customer-managed keys (CMK) when available.

### Bicep Pattern

```bicep
// Storage Account with encryption configuration
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${resourceToken}'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true // Enforce HTTPS
    minimumTlsVersion: 'TLS1_2'    // Minimum TLS 1.2
    encryption: {
      keySource: 'Microsoft.Keyvault' // Customer-managed keys
      keyvaultproperties: {
        keyname: 'storage-encryption-key'
        keyvaulturi: keyVault.properties.vaultUri
      }
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
      }
    }
  }
}

// Cosmos DB with encryption
resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'cosmos-${resourceToken}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    publicNetworkAccess: 'Disabled'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    encryption: {
      keyVaultKeyUri: '${keyVault.properties.vaultUri}keys/cosmos-encryption-key'
    }
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Security Encryption → TLS 1.0/1.1 allowed → Set minimumTlsVersion: 'TLS1_2' and supportsHttpsTrafficOnly: true
```

```
2025-10-31T15:00:00Z Compliance Customer-Managed Keys → Microsoft-managed encryption only → Configure encryption.keySource: 'Microsoft.Keyvault' with Key Vault key URI
```

---

## Pattern 6: App Service VNet Integration

### Requirement
App Services and Functions MUST use VNet integration to access private resources and route all outbound traffic through the VNet.

### Bicep Pattern

```bicep
// App Service Plan with VNet support
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'plan-${resourceToken}'
  location: location
  sku: {
    name: 'P1v3' // Premium v3 required for VNet integration
    tier: 'PremiumV3'
  }
  kind: 'linux'
}

// App Service with VNet integration
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: 'app-${resourceToken}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    vnetRouteAllEnabled: true // Route all outbound traffic through VNet
    virtualNetworkSubnetId: vnet.properties.subnets[0].id
    siteConfig: {
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      alwaysOn: true
    }
  }
}
```

### Learning Entry Format

```
2025-10-31T15:00:00Z Networking App Service → No VNet integration configured → Enable virtualNetworkSubnetId and vnetRouteAllEnabled for private resource access
```

```
2025-10-31T15:00:00Z Security App Service → Public access not restricted → Use VNet integration with vnetRouteAllEnabled: true to force all traffic through VNet
```

---

## Anti-Patterns to Avoid

### ❌ Azure Front Door by Default

**Problem**: Azure Front Door was previously included by default in architectures, but it's not always necessary and adds complexity.

**Solution**: Only include Azure Front Door when explicitly requested by the user for global distribution scenarios.

```
2025-10-31T15:00:00Z Configuration Azure Front Door → Included by default in architecture → Only include when explicitly requested - not required for single-region deployments
```

### ❌ Network Security Perimeter

**Problem**: Network Security Perimeter was previously recommended but Private Endpoints provide better security and are more widely supported.

**Solution**: Replace Network Security Perimeter with Private Endpoints and Private Links.

```
2025-10-31T15:00:00Z Networking Network Security Perimeter → Used for secure communications → Replace with Private Endpoints and Private Links for better security and broader service support
```

### ❌ Service Endpoints Instead of Private Endpoints

**Problem**: Service Endpoints don't prevent data exfiltration to other subscriptions/tenants.

**Solution**: Use Private Endpoints for true network isolation.

```
2025-10-31T15:00:00Z Security Service Endpoints → Used for network security → Replace with Private Endpoints to prevent data exfiltration attacks
```

---

## Validation Checklist

Use this checklist to verify SFI compliance in generated Bicep templates:

- [ ] All resources deployed within same VNet (no standalone public resources)
- [ ] All Storage Accounts have `publicNetworkAccess: 'Disabled'`
- [ ] All Key Vaults have `publicNetworkAccess: 'Disabled'`
- [ ] All databases (SQL, Cosmos, etc.) have `publicNetworkAccess: 'Disabled'`
- [ ] Private Endpoints created for all data services
- [ ] Private DNS zones configured with VNet links
- [ ] privateDnsZoneGroups configured for automatic DNS registration
- [ ] All services use System-Assigned Managed Identity
- [ ] RBAC role assignments configured (no connection strings in config)
- [ ] All resources enforce TLS 1.2 minimum (`minimumTlsVersion: 'TLS1_2'`)
- [ ] HTTPS-only traffic enforced (`httpsOnly: true`, `supportsHttpsTrafficOnly: true`)
- [ ] App Services have VNet integration enabled (`virtualNetworkSubnetId` set)
- [ ] App Services route all traffic through VNet (`vnetRouteAllEnabled: true`)
- [ ] No Azure Front Door resources (unless explicitly requested)
- [ ] No Network Security Perimeter resources (use Private Endpoints instead)

**Note**: This checklist maps to success criteria SC-006, SC-007, SC-008 in the feature specification.

---

## Related Documents

- [spec.md](../spec.md): Feature specification (FR-005, SC-006-SC-008)
- [learnings-format.md](./learnings-format.md): Learning entry format specification
- [Microsoft SFI Documentation](https://learn.microsoft.com/security/engineering/secure-future-initiative)

---

## Version History

- **1.0.0** (2025-10-31): Initial SFI patterns documented during /speckit.analyze remediation
  - Defined 6 core SFI patterns with Bicep examples
  - Added anti-patterns to avoid (Front Door, NSP, Service Endpoints)
  - Created validation checklist for SC-006/SC-007/SC-008 compliance
  - Provided learning entry format for each pattern
