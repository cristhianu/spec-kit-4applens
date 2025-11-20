# Config Validation Unit Tests
# Feature: 005-deploy-sentinel
# Tests configuration loading and validation logic

Describe "Load-DeploymentConfig" {
    BeforeAll {
        # Mock paths
        $script:TestConfigPath = Join-Path $TestDrive "test-config.json"
        $script:StateFilePath = Join-Path $TestDrive ".state.json"
        $script:LogFilePath = Join-Path $TestDrive ".log"
        
        # Source function (assumes script is dot-sourced or loaded)
        # In actual testing, would dot-source the script:
        # . "$PSScriptRoot/../../scripts/powershell/deploy-sentinel.ps1"
    }
    
    Context "Valid Configuration" {
        It "Loads valid JSON configuration" {
            $validConfig = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                region = "eastus"
                subscriptionId = "12345678-1234-1234-1234-123456789012"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $validConfig
            
            { $config = Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Not -Throw
        }
        
        It "Sets default values for optional parameters" {
            $minimalConfig = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $minimalConfig
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.pollingInterval | Should -Be 30
            $config.maxRetries | Should -Be 3
        }
    }
    
    Context "Environment Variable Substitution" {
        It "Substitutes environment variables in config" {
            $env:TEST_SERVICE_GROUP = "EnvServiceGroup"
            $env:TEST_SUBSCRIPTION = "87654321-4321-4321-4321-210987654321"
            
            $configWithEnvVars = @{
                serviceGroupName = '${TEST_SERVICE_GROUP}'
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                subscriptionId = '${TEST_SUBSCRIPTION}'
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithEnvVars
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.serviceGroupName | Should -Be "EnvServiceGroup"
            $config.subscriptionId | Should -Be "87654321-4321-4321-4321-210987654321"
        }
        
        It "Warns when environment variable not found" {
            $configWithMissingEnvVar = @{
                serviceGroupName = '${NONEXISTENT_VAR}'
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithMissingEnvVar
            
            # Should warn but not throw
            { $config = Load-DeploymentConfig -Path $script:TestConfigPath -WarningAction SilentlyContinue } | Should -Not -Throw
        }
    }
    
    Context "Invalid Configuration" {
        It "Throws when config file not found" {
            { Load-DeploymentConfig -Path "nonexistent-config.json" } | Should -Throw "*Configuration file not found*"
        }
        
        It "Throws when JSON is malformed" {
            Set-Content -Path $script:TestConfigPath -Value "{ invalid json }"
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw
        }
        
        It "Throws when required field missing: serviceGroupName" {
            $invalidConfig = @{
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $invalidConfig
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw "*serviceGroupName*"
        }
        
        It "Throws when required field missing: serviceId" {
            $invalidConfig = @{
                serviceGroupName = "TestGroup"
                stageMapName = "TestStageMap"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $invalidConfig
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw "*serviceId*"
        }
        
        It "Throws when required field missing: stageMapName" {
            $invalidConfig = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $invalidConfig
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw "*stageMapName*"
        }
        
        It "Throws when required field missing: environment" {
            $invalidConfig = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $invalidConfig
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw "*environment*"
        }
        
        It "Throws when required field is empty string" {
            $invalidConfig = @{
                serviceGroupName = ""
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $invalidConfig
            
            { Load-DeploymentConfig -Path $script:TestConfigPath } | Should -Throw "*serviceGroupName*"
        }
    }
    
    Context "Optional Fields" {
        It "Accepts configuration with all optional fields" {
            $fullConfig = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                region = "westus"
                subscriptionId = "12345678-1234-1234-1234-123456789012"
                pollingInterval = 60
                maxRetries = 5
                createBranch = $true
                stressTestConfig = @{
                    enabled = $true
                    endpointUrl = "https://test.example.com/health"
                    requestCount = 50
                    minSuccessRatePercent = 95
                    maxP95LatencyMs = 500
                    timeoutSeconds = 60
                }
                pipelineConfig = @{
                    enabled = $true
                    project = "TestProject"
                    pipelineId = 123
                    preDeploy = $true
                    postDeploy = $true
                    critical = $false
                }
                teamsWebhookUrl = "https://outlook.office.com/webhook/test"
            } | ConvertTo-Json -Depth 10
            
            Set-Content -Path $script:TestConfigPath -Value $fullConfig
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.region | Should -Be "westus"
            $config.pollingInterval | Should -Be 60
            $config.stressTestConfig.enabled | Should -Be $true
            $config.pipelineConfig.pipelineId | Should -Be 123
        }
    }
    
    Context "Stress Test Configuration" {
        It "Validates stress test config structure" {
            $configWithStressTest = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                stressTestConfig = @{
                    enabled = $true
                    endpointUrl = "https://api.test.com"
                    requestCount = 25
                    minSuccessRatePercent = 90
                    maxP95LatencyMs = 1000
                    timeoutSeconds = 30
                }
            } | ConvertTo-Json -Depth 10
            
            Set-Content -Path $script:TestConfigPath -Value $configWithStressTest
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.stressTestConfig.endpointUrl | Should -Be "https://api.test.com"
            $config.stressTestConfig.requestCount | Should -Be 25
        }
    }
    
    Context "Pipeline Configuration" {
        It "Validates pipeline config structure" {
            $configWithPipeline = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                pipelineConfig = @{
                    enabled = $true
                    project = "MyProject"
                    pipelineId = 456
                    preDeploy = $false
                    postDeploy = $true
                    critical = $true
                }
            } | ConvertTo-Json -Depth 10
            
            Set-Content -Path $script:TestConfigPath -Value $configWithPipeline
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.pipelineConfig.project | Should -Be "MyProject"
            $config.pipelineConfig.pipelineId | Should -Be 456
            $config.pipelineConfig.critical | Should -Be $true
        }
    }
    
    Context "Webhook URL Validation" {
        It "Accepts valid Teams webhook URL" {
            $configWithWebhook = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                teamsWebhookUrl = "https://outlook.office.com/webhook/abc123/IncomingWebhook/def456"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithWebhook
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.teamsWebhookUrl | Should -Match "^https://outlook\.office\.com/webhook/"
        }
    }
    
    Context "Region and Subscription Validation" {
        It "Accepts valid Azure region" {
            $configWithRegion = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                region = "northeurope"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithRegion
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.region | Should -Be "northeurope"
        }
        
        It "Accepts valid subscription ID format" {
            $configWithSubscription = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                subscriptionId = "abcdef01-2345-6789-abcd-ef0123456789"
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithSubscription
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.subscriptionId | Should -Match "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
        }
    }
    
    Context "Polling Interval Bounds" {
        It "Accepts valid polling interval (15-300 seconds)" {
            $configWithPolling = @{
                serviceGroupName = "TestGroup"
                serviceId = "TestService"
                stageMapName = "TestStageMap"
                environment = "test"
                pollingInterval = 60
            } | ConvertTo-Json
            
            Set-Content -Path $script:TestConfigPath -Value $configWithPolling
            
            $config = Load-DeploymentConfig -Path $script:TestConfigPath
            $config.pollingInterval | Should -BeGreaterOrEqual 15
            $config.pollingInterval | Should -BeLessOrEqual 300
        }
    }
    
    Context "Path Sanitization (Security)" {
        It "Rejects config path with directory traversal attempt" {
            # Security test: Path sanitization should prevent directory traversal
            # This test verifies that Load-DeploymentConfig sanitizes paths
            
            $maliciousPath = "../../etc/passwd"
            
            # The function should either resolve to absolute path or reject non-.json files
            { Load-DeploymentConfig -Path $maliciousPath } | Should -Throw
        }
        
        It "Requires .json file extension" {
            $nonJsonPath = Join-Path $TestDrive "config.txt"
            Set-Content -Path $nonJsonPath -Value '{"test": "value"}'
            
            { Load-DeploymentConfig -Path $nonJsonPath } | Should -Throw "*json extension*"
        }
    }
}
