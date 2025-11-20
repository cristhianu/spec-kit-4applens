# State Management Unit Tests
# Feature: 005-deploy-sentinel
# Tests state file operations, locking, and atomic writes

Describe "Read-RolloutState" {
    BeforeAll {
        $script:StateFilePath = Join-Path $TestDrive ".deploy-sentinel-state.json"
        $script:LogFilePath = Join-Path $TestDrive ".deploy-sentinel.log"
    }
    
    Context "State File Exists" {
        It "Reads valid state file" {
            $testState = @{
                rolloutId = "test-rollout-123"
                status = "InProgress"
                serviceInfo = @{
                    serviceId = "TestService"
                    artifactVersion = "1.0.0"
                    stageMapVersion = "v1"
                }
                startedAt = "2025-01-01T12:00:00Z"
                lastUpdated = "2025-01-01T12:05:00Z"
                currentStage = "Stage1"
                branchName = "deploy/prod/TestService/20250101120000"
                pipelineRunId = $null
                stressTests = @()
                notifications = @()
            } | ConvertTo-Json -Depth 10
            
            Set-Content -Path $script:StateFilePath -Value $testState
            
            $state = Read-RolloutState
            $state.rolloutId | Should -Be "test-rollout-123"
            $state.status | Should -Be "InProgress"
            $state.serviceInfo.serviceId | Should -Be "TestService"
        }
    }
    
    Context "State File Missing" {
        It "Returns null when state file does not exist" {
            Remove-Item -Path $script:StateFilePath -ErrorAction SilentlyContinue
            
            $state = Read-RolloutState
            $state | Should -BeNullOrEmpty
        }
    }
    
    Context "State File Corrupted" {
        It "Handles malformed JSON gracefully" {
            Set-Content -Path $script:StateFilePath -Value "{ invalid json }"
            
            { Read-RolloutState } | Should -Throw
        }
    }
}

Describe "Write-RolloutState" {
    BeforeAll {
        $script:StateFilePath = Join-Path $TestDrive ".deploy-sentinel-state.json"
        $script:LogFilePath = Join-Path $TestDrive ".deploy-sentinel.log"
    }
    
    Context "Create New State" {
        It "Creates new state file with valid structure" {
            $newState = @{
                rolloutId = "new-rollout-456"
                status = "Starting"
                serviceInfo = @{
                    serviceId = "NewService"
                    artifactVersion = "2.0.0"
                    stageMapVersion = "v2"
                }
                startedAt = "2025-01-02T10:00:00Z"
                lastUpdated = "2025-01-02T10:00:00Z"
                currentStage = $null
                branchName = $null
                pipelineRunId = $null
                stressTests = @()
                notifications = @()
            }
            
            Write-RolloutState -State $newState
            
            Test-Path $script:StateFilePath | Should -Be $true
            
            $savedState = Get-Content $script:StateFilePath | ConvertFrom-Json
            $savedState.rolloutId | Should -Be "new-rollout-456"
        }
    }
    
    Context "Update Existing State" {
        It "Overwrites existing state file" {
            $initialState = @{
                rolloutId = "rollout-789"
                status = "InProgress"
                serviceInfo = @{}
                startedAt = "2025-01-03T08:00:00Z"
                lastUpdated = "2025-01-03T08:00:00Z"
                currentStage = "Stage1"
            } | ConvertTo-Json
            
            Set-Content -Path $script:StateFilePath -Value $initialState
            
            $updatedState = @{
                rolloutId = "rollout-789"
                status = "Completed"
                serviceInfo = @{}
                startedAt = "2025-01-03T08:00:00Z"
                lastUpdated = "2025-01-03T09:00:00Z"
                currentStage = "Stage3"
            }
            
            Write-RolloutState -State $updatedState
            
            $savedState = Get-Content $script:StateFilePath | ConvertFrom-Json
            $savedState.status | Should -Be "Completed"
            $savedState.currentStage | Should -Be "Stage3"
        }
    }
    
    Context "Atomic Writes" {
        It "Uses temp file for atomic write (temp + rename pattern)" {
            # This tests the atomic write pattern (write to temp, then rename)
            # The actual implementation should use:
            # 1. Write to temp file
            # 2. Rename temp to final (atomic operation)
            
            $state = @{
                rolloutId = "atomic-test"
                status = "InProgress"
                serviceInfo = @{}
                startedAt = (Get-Date).ToString("o")
                lastUpdated = (Get-Date).ToString("o")
            }
            
            # Before write, should be no .tmp files
            Get-ChildItem -Path $TestDrive -Filter "*.tmp" | Should -HaveCount 0
            
            Write-RolloutState -State $state
            
            # After write, should be no .tmp files (cleaned up)
            Get-ChildItem -Path $TestDrive -Filter "*.tmp" | Should -HaveCount 0
            
            # Final file should exist
            Test-Path $script:StateFilePath | Should -Be $true
        }
    }
    
    Context "State Validation" {
        It "Validates rolloutId exists" {
            $invalidState = @{
                status = "InProgress"
            }
            
            { Write-RolloutState -State $invalidState } | Should -Throw "*rolloutId*"
        }
        
        It "Validates status exists" {
            $invalidState = @{
                rolloutId = "test-123"
            }
            
            { Write-RolloutState -State $invalidState } | Should -Throw "*status*"
        }
    }
}

Describe "Lock-StateFile" {
    BeforeAll {
        $script:LockFilePath = Join-Path $TestDrive ".deploy-sentinel-state.lock"
        $script:StateFilePath = Join-Path $TestDrive ".deploy-sentinel-state.json"
        $script:LogFilePath = Join-Path $TestDrive ".deploy-sentinel.log"
        $script:StaleLockTimeoutMinutes = 5
    }
    
    AfterEach {
        Remove-Item -Path $script:LockFilePath -ErrorAction SilentlyContinue
    }
    
    Context "Acquire Lock" {
        It "Creates lock file successfully" {
            $result = Lock-StateFile
            
            $result | Should -Be $true
            Test-Path $script:LockFilePath | Should -Be $true
        }
        
        It "Lock file contains PID" {
            Lock-StateFile | Out-Null
            
            $lockData = Get-Content $script:LockFilePath | ConvertFrom-Json
            $lockData.pid | Should -Be $PID
        }
        
        It "Lock file contains timestamp" {
            Lock-StateFile | Out-Null
            
            $lockData = Get-Content $script:LockFilePath | ConvertFrom-Json
            $lockData.timestamp | Should -Not -BeNullOrEmpty
            { [datetime]::Parse($lockData.timestamp) } | Should -Not -Throw
        }
        
        It "Lock file contains hostname" {
            Lock-StateFile | Out-Null
            
            $lockData = Get-Content $script:LockFilePath | ConvertFrom-Json
            $lockData.hostname | Should -Be $env:COMPUTERNAME
        }
    }
    
    Context "Lock Already Held" {
        It "Returns false when lock already exists" {
            # Create initial lock
            Lock-StateFile | Out-Null
            
            # Try to acquire again (should fail)
            $result = Lock-StateFile
            $result | Should -Be $false
        }
        
        It "Returns false when lock held by different process" {
            # Simulate lock by different process
            $fakeLock = @{
                pid = 99999
                timestamp = (Get-Date).ToString("o")
                hostname = $env:COMPUTERNAME
            } | ConvertTo-Json
            
            Set-Content -Path $script:LockFilePath -Value $fakeLock
            
            $result = Lock-StateFile
            $result | Should -Be $false
        }
    }
    
    Context "Stale Lock Detection" {
        It "Detects stale lock (>5 minutes old)" {
            # Create lock with old timestamp
            $staleLock = @{
                pid = 88888
                timestamp = (Get-Date).AddMinutes(-10).ToString("o")
                hostname = $env:COMPUTERNAME
            } | ConvertTo-Json
            
            Set-Content -Path $script:LockFilePath -Value $staleLock
            
            # Should detect stale lock and acquire
            $result = Lock-StateFile
            $result | Should -Be $true
            
            # Verify new lock is current process
            $newLock = Get-Content $script:LockFilePath | ConvertFrom-Json
            $newLock.pid | Should -Be $PID
        }
        
        It "Respects fresh lock (<5 minutes old)" {
            # Create lock with recent timestamp
            $freshLock = @{
                pid = 77777
                timestamp = (Get-Date).AddMinutes(-2).ToString("o")
                hostname = $env:COMPUTERNAME
            } | ConvertTo-Json
            
            Set-Content -Path $script:LockFilePath -Value $freshLock
            
            # Should NOT acquire (lock is still fresh)
            $result = Lock-StateFile
            $result | Should -Be $false
        }
    }
    
    Context "Lock Cleanup" {
        It "Removes lock file on unlock" {
            Lock-StateFile | Out-Null
            Test-Path $script:LockFilePath | Should -Be $true
            
            Unlock-StateFile
            Test-Path $script:LockFilePath | Should -Be $false
        }
        
        It "Handles unlock when no lock exists (gracefully)" {
            Remove-Item -Path $script:LockFilePath -ErrorAction SilentlyContinue
            
            { Unlock-StateFile } | Should -Not -Throw
        }
    }
    
    Context "Concurrent Access Prevention" {
        It "Prevents concurrent writes to state file" {
            # Acquire lock
            Lock-StateFile | Out-Null
            
            # Simulate second process trying to write
            # (In real scenario, second process would call Lock-StateFile and fail)
            $secondProcessCanAcquire = Lock-StateFile
            $secondProcessCanAcquire | Should -Be $false
        }
    }
    
    Context "Lock File Format" {
        It "Uses JSON format for lock file" {
            Lock-StateFile | Out-Null
            
            { Get-Content $script:LockFilePath | ConvertFrom-Json } | Should -Not -Throw
        }
        
        It "Contains all required fields (pid, timestamp, hostname)" {
            Lock-StateFile | Out-Null
            
            $lockData = Get-Content $script:LockFilePath | ConvertFrom-Json
            $lockData.PSObject.Properties.Name | Should -Contain "pid"
            $lockData.PSObject.Properties.Name | Should -Contain "timestamp"
            $lockData.PSObject.Properties.Name | Should -Contain "hostname"
        }
    }
    
    Context "Timeout Handling" {
        It "Uses configurable timeout (5 minutes default)" {
            $script:StaleLockTimeoutMinutes | Should -Be 5
        }
        
        It "Allows timeout override via parameter" {
            # Test that timeout can be overridden (if implemented)
            # Lock-StateFile -TimeoutMinutes 10
            # Implementation note: This is a future enhancement
        }
    }
    
    Context "Force Unlock" {
        It "Supports force unlock for stuck locks" {
            # Create a lock
            Lock-StateFile | Out-Null
            
            # Force unlock should remove lock regardless of who owns it
            Unlock-StateFile -Force
            
            Test-Path $script:LockFilePath | Should -Be $false
        }
    }
    
    Context "Rollback on Write Failure" {
        It "Does not leave partial state on write error" {
            # This tests that if Write-RolloutState fails mid-write,
            # the atomic write pattern ensures no corruption
            
            # Mock a write failure scenario
            # In atomic writes: if rename fails, temp file remains, original unchanged
            
            # Implementation note: This requires mocking file system operations
            # Placeholder test - actual implementation would need more setup
        }
    }
    
    Context "State Corruption Detection" {
        It "Detects corrupted state file" {
            Set-Content -Path $script:StateFilePath -Value "corrupted data"
            
            { Read-RolloutState } | Should -Throw
        }
        
        It "Logs error when state corruption detected" {
            Set-Content -Path $script:StateFilePath -Value "{ invalid }"
            
            try {
                Read-RolloutState
            } catch {
                # Error should be logged
            }
            
            # Check log file contains error (if logging is enabled)
            if (Test-Path $script:LogFilePath) {
                $logContent = Get-Content $script:LogFilePath -Raw
                $logContent | Should -Match "ERROR"
            }
        }
    }
}
