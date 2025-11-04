// Sample Bicep template for .NET API infrastructure
@description('Location for all resources')
param location string = resourceGroup().location

@description('Environment name (e.g., dev, test, prod)')
param environment string = 'test-corp'

@description('SQL Server administrator password')
@secure()
param sqlAdminPassword string

var appName = 'dotnet-api'
var sqlServerName = '${appName}-sql-${environment}'
var databaseName = 'mydatabase'
var storageAccountName = replace('${appName}${environment}', '-', '')
var keyVaultName = '${appName}-kv-${environment}'

// SQL Server
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
  }
}

// SQL Database
resource database 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648
  }
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enableRbacAuthorization: true
  }
}

output sqlServerName string = sqlServer.name
output databaseName string = database.name
output storageAccountName string = storageAccount.name
output keyVaultName string = keyVault.name
