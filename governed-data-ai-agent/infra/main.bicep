@description('Deployment environment used for governed dev/test/prod promotion paths')
param environment string = 'dev'
param location string = resourceGroup().location
param prefix string = 'govai'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${prefix}${environment}data'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-${environment}-kv'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    publicNetworkAccess: 'Disabled'
  }
}

output storageAccountName string = storage.name
output keyVaultName string = keyVault.name
