Describe "Lontrium Control launcher flow" {
    BeforeAll {
        . "$PSScriptRoot/../installer/Start-ClaimerControl.ps1" -Action start -Language en
    }

    BeforeEach {
        Mock Test-Path { $true }
        Mock Wait-DockerDesktop {}
        Mock Start-Application {}
        Mock Start-EconomyApplication {}
        Mock Start-SourceApplication {}
        Mock Install-DockerDesktop {}
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
    }

    It "offers exclusive economy and persistent-dashboard startup modes" {
        $installer = Get-Content -LiteralPath "$PSScriptRoot/../installer/ClaimerControl.iss" -Raw
        if ($installer -notmatch 'Name: "autostart\\economy";[^\r\n]+Flags: exclusive checkedonce') {
            throw "Economy mode is not the default exclusive startup choice"
        }
        if ($installer -notmatch 'Name: "autostart\\dashboard";[^\r\n]+Flags: exclusive') {
            throw "Persistent dashboard mode is not an exclusive startup choice"
        }
        if ($installer -notmatch '\{userstartup\}\\Lontrium Control[^\r\n]+-Action economy[^\r\n]+Tasks: autostart\\economy') {
            throw "The economy startup shortcut is not scoped to economy mode"
        }
        if ($installer -notmatch '\{userstartup\}\\Lontrium Control[^\r\n]+Start-ClaimerControl\.cmd[^\r\n]+Tasks: autostart\\dashboard') {
            throw "The persistent startup shortcut is not scoped to dashboard mode"
        }
        if ($installer -notmatch '\{autodesktop\}\\Lontrium Control[^\r\n]+Start-ClaimerControl\.cmd') {
            throw "The normal desktop shortcut should keep the dashboard running"
        }
        if ($installer -notmatch 'Type: files; Name: "\{userstartup\}\\Lontrium Control\.lnk"') {
            throw "Installer upgrades could leave the previously selected startup mode behind"
        }
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
