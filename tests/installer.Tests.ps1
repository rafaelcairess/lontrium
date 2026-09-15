Describe "Lontrium Control launcher flow" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action start -Language en
    }

    BeforeEach {
        Mock Test-Path { $true }
        Mock Wait-DockerDesktop {}
        Mock Start-Application {}
        Mock Start-EconomyApplication {}
        Mock Start-ScheduledApplication {}
        Mock Start-SourceApplication {}
        Mock Install-DockerDesktop {}
        Mock Test-DockerReady { $false }
        Mock Test-LontriumContainerRunning { $false }
    }

    It "starts directly when Docker is installed" {
        Mock Test-DockerCommandAvailable { $true }
        $result = Invoke-ClaimerControl
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Install-DockerDesktop -Times 0 -Exactly -Scope It
        Assert-MockCalled Wait-DockerDesktop -Times 1 -Exactly -Scope It
        Assert-MockCalled Start-Application -Times 1 -Exactly -Scope It
    }

    It "waits for Docker when the command exists but the engine is stopped" {
        Mock Test-DockerCommandAvailable { $true }
        $result = Invoke-ClaimerControl
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Wait-DockerDesktop -Times 1 -Exactly -Scope It
        Assert-MockCalled Start-Application -Times 1 -Exactly -Scope It
    }

    It "installs Docker before starting when Docker is absent" {
        Mock Test-DockerCommandAvailable { $false }
        $result = Invoke-ClaimerControl
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Install-DockerDesktop -Times 1 -Exactly -Scope It
        Assert-MockCalled Wait-DockerDesktop -Times 1 -Exactly -Scope It
        Assert-MockCalled Start-Application -Times 1 -Exactly -Scope It
    }

    It "uses the local source flow from a repository checkout" {
        Mock Test-DockerCommandAvailable { $true }
        $result = Invoke-ClaimerControl -RequestedAction source
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Start-SourceApplication -Times 1 -Exactly -Scope It
        Assert-MockCalled Start-Application -Times 0 -Exactly -Scope It
    }

    It "uses economy mode for unattended Windows startup" {
        Mock Test-DockerCommandAvailable { $true }
        $result = Invoke-ClaimerControl -RequestedAction economy
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Start-EconomyApplication -Times 1 -Exactly -Scope It
        Assert-MockCalled Start-Application -Times 0 -Exactly -Scope It
    }

    It "uses the scheduled flow with resource ownership information" {
        Mock Test-DockerCommandAvailable { $true }
        Mock Test-DockerReady { $true }
        Mock Test-LontriumContainerRunning { $true }
        $result = Invoke-ClaimerControl -RequestedAction scheduled
        if ($result -ne 0) { throw "Expected launcher exit code 0, got $result" }
        Assert-MockCalled Start-ScheduledApplication -Times 1 -Exactly -Scope It -ParameterFilter {
            $DockerWasRunning -and $AppWasRunning
        }
    }
}

Describe "Legacy Docker data discovery" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action start -Language en
    }

    It "finds the named data volume without using a Docker format template" {
        $json = @'
[
  {
    "Mounts": [
      {"Type": "volume", "Name": "fgc-remaster_fgc-data", "Destination": "/fgc/data"},
      {"Type": "bind", "Source": "C:\\example", "Destination": "/tmp/example"}
    ]
  }
]
'@
        $volume = Get-LegacyDataVolumeFromInspect $json
        if ($volume -ne "fgc-remaster_fgc-data") { throw "Unexpected legacy volume: $volume" }
    }

    It "returns an empty value when the expected mount is absent" {
        [string]$volume = Get-LegacyDataVolumeFromInspect '[{"Mounts":[]}]'
        if ($volume -ne "") { throw "Expected no legacy volume, got $volume" }
    }

    It "treats a missing legacy container as a clean installation" {
        Mock docker {
            $global:LASTEXITCODE = 1
            Write-Error "Error: No such object: fgc-remaster"
        } -ParameterFilter { $args[0] -eq "inspect" }
        Mock Confirm-DefaultYes { throw "The migration prompt must not be shown" }

        $threw = $false
        try { Adopt-LegacyData } catch { $threw = $true }
        if ($threw) { throw "A missing legacy container must not stop the launcher" }
        Assert-MockCalled Confirm-DefaultYes -Times 0 -Exactly -Scope It
    }

    It "replaces the legacy container while preserving its named data volume" {
        $launcher = Get-Content -LiteralPath "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Raw
        if ($launcher -notmatch '& docker stop fgc-remaster') { throw "Legacy container is not stopped" }
        if ($launcher -notmatch '& docker rm fgc-remaster') { throw "Legacy container is not replaced" }
        if ($launcher -notmatch 'Set-EnvironmentValue "CLAIMER_DATA_VOLUME"') { throw "Legacy volume is not adopted" }
    }
}

Describe "Local dashboard readiness" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action start -Language en
    }

    It "uses the explicit IPv4 loopback address" {
        Mock Invoke-WebRequest { [pscustomobject]@{StatusCode = 200} }
        Wait-Panel
        Assert-MockCalled Invoke-WebRequest -Times 1 -Exactly -ParameterFilter {
            $Uri -eq "http://127.0.0.1:8080/api/status"
        }
    }
}

Describe "Application identity" {
    It "uses the Lontrium Control icon for setup and shortcuts" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        if ($installer -notmatch 'SetupIconFile=Lontrium\.ico') { throw "Setup icon is not configured" }
        if ($installer -notmatch 'IconFilename: "\{app\}\\Lontrium\.ico"') { throw "Shortcut icon is not configured" }
        if (-not (Test-Path -LiteralPath "$PSScriptRoot/../installer/Lontrium.ico")) { throw "Installer icon is missing" }
    }

    It "packages and starts the native Windows notification helper" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        $launcher = Get-Content -LiteralPath "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Raw
        if ($installer -notmatch 'Lontrium\.Notifier\.exe') { throw "Native notifier is not packaged" }
        if ($installer -notmatch 'AppUserModelID: "RafaelCaires\.LontriumControl"') { throw "Toast AppUserModelID is missing" }
        if ($launcher -notmatch 'Start-WindowsNotifier') { throw "Launcher does not start the notifier" }
    }

    It "registers Lontrium updates and preserves the former protocol alias" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        if ($installer -notmatch 'Software\\Classes\\lontrium') { throw "Lontrium update protocol is not configured" }
        if ($installer -notmatch 'Software\\Classes\\claimer-control') { throw "Legacy update protocol alias is missing" }
    }

    It "does not overwrite the local data-volume configuration during upgrades" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        if ($installer -notmatch 'Source: "claimer\.env";[^\r\n]+onlyifdoesntexist') {
            throw "Installer upgrades could replace the user's persistent volume configuration"
        }
        if ($installer -notmatch '-InstallTag ""\{#MyImageTag\}""') {
            throw "Installer upgrades could keep running an older application image"
        }
    }

    It "offers exclusive economy and persistent-dashboard startup modes" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        if ($installer -notmatch 'Name: "autostart\\economy";[^\r\n]+Flags: exclusive checkedonce') {
            throw "Economy mode is not the default exclusive startup choice"
        }
        if ($installer -notmatch 'Name: "autostart\\dashboard";[^\r\n]+Flags: exclusive') {
            throw "Persistent dashboard mode is not an exclusive startup choice"
        }
        if ($installer -match 'Name: "\{userstartup\}\\Lontrium Control"') {
            throw "Legacy Startup-folder shortcuts can conflict with the native scheduled task"
        }
        if ($installer -notmatch '-Action configure-economy[^\r\n]+Tasks: autostart\\economy') {
            throw "The installer does not persist the selected economy mode"
        }
        if ($installer -notmatch '-Action configure-dashboard[^\r\n]+Tasks: autostart\\dashboard') {
            throw "The installer does not persist the selected dashboard mode"
        }
        if ($installer -notmatch '-Action configure-manual[^\r\n]+Tasks: not autostart') {
            throw "Declining Windows automation would leave an old scheduled task active"
        }
        if ($installer -notmatch '\{autodesktop\}\\Lontrium Control[^\r\n]+Start-ClaimerControl\.cmd') {
            throw "The normal desktop shortcut should keep the dashboard running"
        }
        if ($installer -notmatch 'Type: files; Name: "\{userstartup\}\\Lontrium Control\.lnk"') {
            throw "Installer upgrades could leave the previously selected startup mode behind"
        }
    }

    It "leaves the packaged container lifecycle to Windows Task Scheduler" {
        $compose = Get-Content -LiteralPath "$PSScriptRoot/../installer/docker-compose.yml" -Raw
        if ($compose -notmatch 'restart:\s+"no"') {
            throw "The packaged container could restart itself and keep Docker resident"
        }
    }
}

Describe "Windows Task Scheduler automation" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action start -Language en
    }

    BeforeEach {
        Mock Get-DashboardJson {
            [pscustomobject]@{values = [pscustomobject]@{
                WINDOWS_ECONOMY_SCHEDULE = $true
                WINDOWS_WAKE_ON_AC = $true
                RUN_ON_STARTUP = $true
                SCHEDULER_FIXED_TIMES = "12:00,16:00,19:00"
            }}
        }
        Mock Unregister-ScheduledTask {}
        Mock Register-ScheduledTask {}
    }

    It "registers logon and three daily triggers without overlapping runs" {
        Sync-WindowsSchedule
        Assert-MockCalled Register-ScheduledTask -Times 1 -Exactly -Scope It -ParameterFilter {
            $TaskName -eq "Lontrium Control - Automatic Collection" -and
            @($Trigger).Count -eq 4 -and
            $Settings.StartWhenAvailable -and
            $Settings.WakeToRun -and
            [string]$Settings.MultipleInstances -eq "IgnoreNew" -and
            $Action.Arguments -match '-Action scheduled'
        }
    }

    It "removes only the Lontrium scheduled task" {
        Remove-WindowsSchedule
        Assert-MockCalled Unregister-ScheduledTask -Times 1 -Exactly -Scope It -ParameterFilter {
            $TaskName -eq "Lontrium Control - Automatic Collection"
        }
    }
}

Describe "Scheduled collection ownership" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action scheduled -Language en
    }

    BeforeEach {
        Mock Adopt-LegacyData {}
        Mock Write-Step {}
        Mock Invoke-Compose {}
        Mock Wait-Panel {}
        Mock Start-WindowsNotifier {}
        Mock Sync-WindowsSchedule {}
        Mock Get-DashboardJson { [pscustomobject]@{setup = [pscustomobject]@{required = $true; complete = $true}} }
        Mock Invoke-ScheduledDashboardRun { [pscustomobject]@{accepted = $true; runId = ("a" * 32); stores = @("epic")} }
        Mock Wait-ScheduledRun { $true }
        Mock Stop-DockerAfterEconomyRun {}
        Mock Start-Process {}
    }

    It "does not stop a dashboard or Docker engine that the user already had open" {
        Start-ScheduledApplication -DockerWasRunning $true -AppWasRunning $true
        Assert-MockCalled Stop-DockerAfterEconomyRun -Times 1 -Exactly -Scope It -ParameterFilter {
            -not $StopApp -and -not $StopDocker -and -not $StopNotifier
        }
    }

    It "stops all resources that the scheduled run started" {
        Start-ScheduledApplication -DockerWasRunning $false -AppWasRunning $false
        Assert-MockCalled Stop-DockerAfterEconomyRun -Times 1 -Exactly -Scope It -ParameterFilter {
            $StopApp -and $StopDocker -and $StopNotifier
        }
    }

    It "opens setup and leaves resources available when onboarding is incomplete" {
        Mock Get-DashboardJson { [pscustomobject]@{setup = [pscustomobject]@{required = $true; complete = $false}} }
        Start-ScheduledApplication -DockerWasRunning $false -AppWasRunning $false
        Assert-MockCalled Start-Process -Times 1 -Exactly -Scope It -ParameterFilter {
            $FilePath -eq "http://127.0.0.1:8080"
        }
        Assert-MockCalled Invoke-ScheduledDashboardRun -Times 0 -Exactly -Scope It
        Assert-MockCalled Stop-DockerAfterEconomyRun -Times 0 -Exactly -Scope It
    }
}

Describe "Economy mode" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action economy -Language en
    }

    It "keeps Docker running while initial setup is pending" {
        Mock Get-DashboardJson { [pscustomobject]@{setup = [pscustomobject]@{required = $true; complete = $false}} }
        Mock Start-Process {}
        $result = Wait-EconomyRun
        if ($result) { throw "Economy mode must not stop Docker before setup is complete" }
        Assert-MockCalled Start-Process -Times 1 -Exactly -Scope It
    }

    It "finishes when an observed automatic run becomes idle" {
        $script:dashboardResponses = [System.Collections.Queue]::new()
        $script:dashboardResponses.Enqueue([pscustomobject]@{setup = [pscustomobject]@{required = $true; complete = $true}})
        $script:dashboardResponses.Enqueue([pscustomobject]@{running = $true; startedAt = "2026-09-07T00:00:00Z"; finishedAt = $null})
        $script:dashboardResponses.Enqueue([pscustomobject]@{running = $false; startedAt = "2026-09-07T00:00:00Z"; finishedAt = "2026-09-07T00:01:00Z"})
        Mock Get-DashboardJson { $script:dashboardResponses.Dequeue() }
        Mock Start-Sleep {}
        $result = Wait-EconomyRun
        if (-not $result) { throw "Economy mode should finish after the run becomes idle" }
        if ($script:dashboardResponses.Count -ne 0) { throw "Not all dashboard states were checked" }
    }

    It "does not stop Docker Desktop when another container is running" {
        Mock Invoke-Compose {}
        Mock Get-RunningContainerIds { "another-container-id" }
        Stop-DockerAfterEconomyRun
        Assert-MockCalled Get-RunningContainerIds -Times 1 -Exactly -Scope It
    }
}

Describe "Stop all action" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action stop -Language en
    }

    It "does not start Docker when it is already unavailable" {
        Mock Test-DockerCommandAvailable { $false }
        Mock Test-DockerReady { throw "must not be called" }
        Mock Stop-WindowsNotifier {}
        Mock Stop-DockerAfterEconomyRun {}

        $result = Invoke-ClaimerControl -RequestedAction stop

        if ($result -ne 0) { throw "Stop should be idempotent" }
        Assert-MockCalled Stop-WindowsNotifier -Times 1 -Exactly -Scope It
        Assert-MockCalled Stop-DockerAfterEconomyRun -Times 0 -Exactly -Scope It
    }

    It "stops Lontrium and Docker through the guarded economy cleanup" {
        Mock Test-DockerCommandAvailable { $true }
        Mock Test-DockerReady { $true }
        Mock Stop-DockerAfterEconomyRun {}

        $result = Invoke-ClaimerControl -RequestedAction stop

        if ($result -ne 0) { throw "Stop should succeed" }
        Assert-MockCalled Stop-DockerAfterEconomyRun -Times 1 -Exactly -Scope It
    }
}
