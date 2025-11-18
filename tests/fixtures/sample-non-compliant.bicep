// Sample NON-compliant Bicep template for testing validation script
param location string = resourceGroup().location
param appName string

// Azure Front Door (anti-pattern - should not be included by default)
resource frontDoor 'Microsoft.Cdn/profiles@2021-06-01' = {
  name: '${appName}-fd'
  location: 'global'
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
}

// Storage Account with public access ENABLED (violation)
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${appName}store${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Enabled'  // VIOLATION: Should be 'Disabled'
    allowBlobPublicAccess: true     // VIOLATION: Should be false
    minimumTlsVersion: 'TLS1_0'     // VIOLATION: Should be TLS1_2
  }
}

// SQL Server without private endpoint and weak TLS
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${appName}-sql'
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: 'P@ssw0rd123!'
    // publicNetworkAccess not set - WARNING (defaults to Enabled)
    minimalTlsVersion: '1.0'  // VIOLATION: Should be 1.2
  }
}

// Network Security Perimeter (anti-pattern - should use Private Endpoints)
resource nsp 'Microsoft.Network/networkSecurityPerimeters@2021-02-01-preview' = {
  name: '${appName}-nsp'
  location: location
  properties: {
    description: 'Network security perimeter for app isolation'
  }
}

// App Service without HTTPS enforcement
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
}

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  // No managed identity - WARNING
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: false  // VIOLATION: Should be true
    // No VNet integration - WARNING
    siteConfig: {
      minTlsVersion: '1.1'  // VIOLATION: Should be 1.2
    }
  }
}
