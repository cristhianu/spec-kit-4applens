// Sample SFI-compliant Bicep template for testing validation script
param location string = resourceGroup().location
param appName string
param sqlAdminLogin string
@secure()
param sqlAdminPassword string

// Virtual Network for isolation
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${appName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'app-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [
            {
              name: 'Microsoft.Web.serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'sql-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Storage Account with Private Endpoint
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${appName}store${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// SQL Server with Private Endpoint
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${appName}-sql'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
  }
}

// Private Endpoint for SQL
resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: '${appName}-sql-pe'
  location: location
  properties: {
    subnet: {
      id: vnet.properties.subnets[1].id
    }
    privateLinkServiceConnections: [
      {
        name: 'sql-connection'
        properties: {
          privateLinkServiceId: sqlServer.id
          groupIds: [
            'sqlServer'
          ]
        }
      }
    ]
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'P1V2'
    tier: 'PremiumV2'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// App Service with VNet Integration
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    virtualNetworkSubnetId: vnet.properties.subnets[0].id
    vnetRouteAllEnabled: true
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
  }
}
