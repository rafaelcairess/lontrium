[CmdletBinding()]
param(
    [ValidateSet("start", "economy", "source", "update", "uninstall", "check")]
    [string]$Action = "start",
    [ValidateSet("auto", "en", "pt-BR", "es")]
    [string]$Language = "auto",
    [switch]$RemoveData
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$Messages = @{
    en = @{
        Title = "Lontrium Control"
        DockerMissing = "Docker Desktop is required. Lontrium Control can install it from the official source now."
        InstallPrompt = "Install Docker Desktop? [Y/n]"
        InstallCancelled = "Installation cancelled. No changes were made."
        InstallingWinget = "Installing Docker Desktop with Windows Package Manager..."
        DownloadingDocker = "Windows Package Manager is unavailable. Downloading Docker Desktop from Docker's official website..."
        InvalidSignature = "The Docker installer does not have a valid Docker Inc. digital signature. Installation was stopped."
        RestartNeeded = "Windows must restart to finish Docker setup. Lontrium Control will continue automatically after sign-in."
        StartingDocker = "Starting Docker Desktop..."
        WaitingDocker = "Waiting for Docker Desktop to become ready"
        DockerTimeout = "Docker Desktop did not become ready in time. Open Docker Desktop, finish its first-run screens, then use the Lontrium Control shortcut again."
        Pulling = "Downloading the Lontrium Control application..."
        Starting = "Starting Lontrium Control..."
        StartingSource = "Building and starting Lontrium Control from this source folder..."
        WaitingPanel = "Waiting for the local dashboard"
        PanelTimeout = "The container started, but the local dashboard did not respond. Open Docker Desktop and check the claimer-control container."
        Ready = "Lontrium Control is ready. Opening the local dashboard..."
        EconomyWaiting = "Economy mode: waiting for the automatic run to finish"
        EconomyComplete = "Automatic run finished. Releasing Docker and WSL memory..."
        EconomyNoRun = "No automatic run is due. Releasing Docker and WSL memory..."
        EconomySetup = "Initial setup is not complete. The dashboard will remain open."
        EconomyTimeout = "The automatic run did not finish in time. Docker will remain running so you can inspect the dashboard."
        EconomySharedDocker = "Another container is running. Lontrium was stopped, but Docker will remain available for the other application."
        UpdateCheck = "Checking the official Lontrium Control Release..."
        UpToDate = "Lontrium Control is already up to date."
        UpdatePrompt = "Update from {0} to {1}? [Y/n]"
        Updating = "Installing update {0}..."
        UpdateInvalid = "GitHub returned an invalid version. The update was stopped."
        LegacyFound = "An existing Free Games Claimer installation was found. Reuse its local accounts and browser sessions? [Y/n]"
        LegacyAdopted = "Existing local data will be reused. The old container was replaced; its local data was preserved."
        CheckOk = "Launcher files are valid."
        Failed = "Lontrium Control could not finish: {0}"
    }
    "pt-BR" = @{
        Title = "Lontrium Control"
        DockerMissing = "O Docker Desktop é necessário. O Lontrium Control pode instalá-lo agora pela fonte oficial."
        InstallPrompt = "Instalar o Docker Desktop? [S/n]"
        InstallCancelled = "Instalação cancelada. Nenhuma alteração foi feita."
        InstallingWinget = "Instalando o Docker Desktop pelo Gerenciador de Pacotes do Windows..."
        DownloadingDocker = "O Gerenciador de Pacotes não está disponível. Baixando o Docker Desktop pelo site oficial da Docker..."
        InvalidSignature = "O instalador do Docker não possui uma assinatura digital válida da Docker Inc. A instalação foi interrompida."
        RestartNeeded = "O Windows precisa reiniciar para concluir o Docker. O Lontrium Control continuará automaticamente após o login."
        StartingDocker = "Iniciando o Docker Desktop..."
        WaitingDocker = "Aguardando o Docker Desktop ficar pronto"
        DockerTimeout = "O Docker Desktop não ficou pronto a tempo. Abra o Docker Desktop, conclua as telas iniciais e use novamente o atalho do Lontrium Control."
        Pulling = "Baixando o aplicativo Lontrium Control..."
        Starting = "Iniciando o Lontrium Control..."
        StartingSource = "Preparando e iniciando o Lontrium Control a partir desta pasta..."
        WaitingPanel = "Aguardando o painel local"
        PanelTimeout = "O container iniciou, mas o painel local não respondeu. Abra o Docker Desktop e verifique o container claimer-control."
        Ready = "Lontrium Control pronto. Abrindo o painel local..."
        EconomyWaiting = "Modo econômico: aguardando a coleta automática terminar"
        EconomyComplete = "Coleta automática concluída. Liberando a memória do Docker e do WSL..."
        EconomyNoRun = "Nenhuma coleta automática está pendente. Liberando a memória do Docker e do WSL..."
        EconomySetup = "A configuração inicial ainda não terminou. O painel permanecerá aberto."
        EconomyTimeout = "A coleta automática não terminou a tempo. O Docker permanecerá ligado para você verificar o painel."
        EconomySharedDocker = "Outro container está em execução. O Lontrium foi parado, mas o Docker continuará disponível para o outro aplicativo."
        UpdateCheck = "Consultando a Release oficial do Lontrium Control..."
        UpToDate = "O Lontrium Control já está atualizado."
        UpdatePrompt = "Atualizar da versão {0} para {1}? [S/n]"
        Updating = "Instalando a atualização {0}..."
        UpdateInvalid = "O GitHub retornou uma versão inválida. A atualização foi interrompida."
        LegacyFound = "Uma instalação anterior do Free Games Claimer foi encontrada. Reutilizar contas e sessões locais? [S/n]"
        LegacyAdopted = "Os dados locais existentes serão reutilizados. O container antigo foi substituído; os dados locais foram preservados."
        CheckOk = "Os arquivos do inicializador são válidos."
        Failed = "O Lontrium Control não conseguiu concluir: {0}"
    }
    es = @{
        Title = "Lontrium Control"
        DockerMissing = "Docker Desktop es necesario. Lontrium Control puede instalarlo ahora desde la fuente oficial."
        InstallPrompt = "¿Instalar Docker Desktop? [S/n]"
        InstallCancelled = "Instalación cancelada. No se realizó ningún cambio."
        InstallingWinget = "Instalando Docker Desktop con el Administrador de paquetes de Windows..."
        DownloadingDocker = "El Administrador de paquetes no está disponible. Descargando Docker Desktop desde el sitio oficial de Docker..."
        InvalidSignature = "El instalador de Docker no tiene una firma digital válida de Docker Inc. La instalación se detuvo."
        RestartNeeded = "Windows debe reiniciarse para completar Docker. Lontrium Control continuará automáticamente después de iniciar sesión."
        StartingDocker = "Iniciando Docker Desktop..."
        WaitingDocker = "Esperando a que Docker Desktop esté listo"
        DockerTimeout = "Docker Desktop no estuvo listo a tiempo. Ábrelo, completa sus pantallas iniciales y vuelve a usar el acceso directo de Lontrium Control."
        Pulling = "Descargando la aplicación Lontrium Control..."
        Starting = "Iniciando Lontrium Control..."
        StartingSource = "Preparando e iniciando Lontrium Control desde esta carpeta..."
        WaitingPanel = "Esperando el panel local"
        PanelTimeout = "El contenedor se inició, pero el panel local no respondió. Abre Docker Desktop y comprueba el contenedor claimer-control."
        Ready = "Lontrium Control está listo. Abriendo el panel local..."
        EconomyWaiting = "Modo económico: esperando a que termine la ejecución automática"
        EconomyComplete = "La ejecución automática terminó. Liberando la memoria de Docker y WSL..."
        EconomyNoRun = "No hay ninguna ejecución automática pendiente. Liberando la memoria de Docker y WSL..."
        EconomySetup = "La configuración inicial no ha terminado. El panel permanecerá abierto."
        EconomyTimeout = "La ejecución automática no terminó a tiempo. Docker seguirá activo para que puedas revisar el panel."
        EconomySharedDocker = "Hay otro contenedor en ejecución. Lontrium se detuvo, pero Docker seguirá disponible para la otra aplicación."
        UpdateCheck = "Consultando la Release oficial de Lontrium Control..."
        UpToDate = "Lontrium Control ya está actualizado."
        UpdatePrompt = "¿Actualizar de la versión {0} a {1}? [S/n]"
        Updating = "Instalando la actualización {0}..."
        UpdateInvalid = "GitHub devolvió una versión no válida. La actualización se detuvo."
        LegacyFound = "Se encontró una instalación anterior de Free Games Claimer. ¿Reutilizar sus cuentas y sesiones locales? [S/n]"
        LegacyAdopted = "Se reutilizarán los datos locales existentes. Se reemplazó el contenedor anterior y se conservaron sus datos locales."
        CheckOk = "Los archivos del iniciador son válidos."
        Failed = "Lontrium Control no pudo finalizar: {0}"
    }
}

function Resolve-Language {
    if ($Language -ne "auto") { return $Language }
    $culture = [System.Globalization.CultureInfo]::CurrentUICulture.Name.ToLowerInvariant()
    if ($culture.StartsWith("pt")) { return "pt-BR" }
    if ($culture.StartsWith("es")) { return "es" }
    return "en"
}

$Script:Locale = Resolve-Language
$Script:Text = $Messages[$Script:Locale]
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
$EnvironmentFile = Join-Path $PSScriptRoot "claimer.env"
if ($Action -eq "source") {
    $sourceRoot = Split-Path -Parent $PSScriptRoot
    $ComposeFile = Join-Path $sourceRoot "docker-compose.yml"
    $EnvironmentFile = Join-Path $sourceRoot ".env"
}
$PanelUrl = "http://127.0.0.1:8080"
$ReleaseApi = "https://api.github.com/repos/rafaelcairess/lontrium/releases/latest"

function Write-Step([string]$Message) {
    Write-Host "`n> $Message" -ForegroundColor Cyan
}

function Confirm-DefaultYes([string]$Prompt) {
    $answer = Read-Host $Prompt
    return [string]::IsNullOrWhiteSpace($answer) -or $answer -match "^(y|yes|s|sim|sí|si)$"
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Test-DockerReady {
    try {
        & docker info *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-DockerCommandAvailable {
    return $null -ne (Get-Command docker.exe -ErrorAction SilentlyContinue)
}

function Set-ResumeAfterRestart {
    $runOnce = "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
    New-Item -Path $runOnce -Force | Out-Null
    $command = 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "{0}" -Action start -Language {1}' -f $PSCommandPath, $Script:Locale
    New-ItemProperty -Path $runOnce -Name "ClaimerControlResume" -Value $command -PropertyType String -Force | Out-Null
}

function Install-DockerDesktop {
    Write-Host $Script:Text.DockerMissing -ForegroundColor Yellow
    if (-not (Confirm-DefaultYes $Script:Text.InstallPrompt)) {
        Write-Host $Script:Text.InstallCancelled
        exit 2
    }

    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Step $Script:Text.InstallingWinget
        $process = Start-Process -FilePath $winget.Source -ArgumentList @(
            "install", "--id", "Docker.DockerDesktop", "--exact",
            "--accept-package-agreements", "--accept-source-agreements"
        ) -Wait -PassThru
        if ($process.ExitCode -notin @(0, 3010, 1641)) {
            throw "winget exit code $($process.ExitCode)"
        }
        if ($process.ExitCode -in @(3010, 1641)) {
            Set-ResumeAfterRestart
            Write-Host $Script:Text.RestartNeeded -ForegroundColor Yellow
            exit 3010
        }
    } else {
        Write-Step $Script:Text.DownloadingDocker
        $download = Join-Path $env:TEMP "DockerDesktopInstaller-ClaimerControl.exe"
        if (Test-Path -LiteralPath $download) { Remove-Item -LiteralPath $download -Force }
        Invoke-WebRequest -UseBasicParsing -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -OutFile $download
        $signature = Get-AuthenticodeSignature -LiteralPath $download
        if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notmatch "Docker Inc") {
            Remove-Item -LiteralPath $download -Force
            throw $Script:Text.InvalidSignature
        }
        $process = Start-Process -FilePath $download -ArgumentList @("install", "--accept-license") -Wait -PassThru
        Remove-Item -LiteralPath $download -Force
        if ($process.ExitCode -notin @(0, 3010, 1641)) { throw "Docker installer exit code $($process.ExitCode)" }
        if ($process.ExitCode -in @(3010, 1641)) {
            Set-ResumeAfterRestart
            Write-Host $Script:Text.RestartNeeded -ForegroundColor Yellow
            exit 3010
        }
    }
    Refresh-Path
}

function Wait-DockerDesktop {
    if (Test-DockerReady) { return }
    Write-Step $Script:Text.StartingDocker
    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $desktop)) { throw "Docker Desktop executable not found" }
    Start-Process -FilePath $desktop -WindowStyle Hidden | Out-Null
    Write-Step $Script:Text.WaitingDocker
    for ($attempt = 1; $attempt -le 120; $attempt++) {
        if (Test-DockerReady) { Write-Host " OK" -ForegroundColor Green; return }
        if (($attempt % 5) -eq 0) { Write-Host "." -NoNewline }
        Start-Sleep -Seconds 3
    }
    throw $Script:Text.DockerTimeout
}

function Set-EnvironmentValue([string]$Name, [string]$Value) {
    if ($Name -notmatch "^[A-Z_]+$" -or $Value -match "[`r`n]") { throw "Invalid environment value" }
    $content = Get-Content -LiteralPath $EnvironmentFile -Encoding UTF8
    $pattern = "^$([regex]::Escape($Name))="
    $found = $false
    $updated = foreach ($line in $content) {
        if ($line -match $pattern) { $found = $true; "$Name=$Value" } else { $line }
    }
    if (-not $found) { $updated += "$Name=$Value" }
    Set-Content -LiteralPath $EnvironmentFile -Value $updated -Encoding UTF8
}

function Get-EnvironmentValue([string]$Name) {
    $line = Get-Content -LiteralPath $EnvironmentFile -Encoding UTF8 | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($line) { return ($line -split "=", 2)[1].Trim() }
    return ""
}

function Get-LegacyDataVolumeFromInspect([string]$Json) {
    if ([string]::IsNullOrWhiteSpace($Json)) { return "" }
    try {
        $containers = @(ConvertFrom-Json -InputObject $Json)
        $mount = @($containers[0].Mounts | Where-Object { $_.Destination -eq "/fgc/data" })[0]
        if ($null -eq $mount) { return "" }
        return [string]$mount.Name
    } catch {
        return ""
    }
}

function Adopt-LegacyData {
    # A missing legacy container is expected on a clean installation. PowerShell 7
    # can promote native stderr to a terminating error while the launcher uses
    # ErrorActionPreference=Stop, so allow this probe to fail normally.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $inspect = & docker inspect fgc-remaster 2>$null
        if ($LASTEXITCODE -ne 0) { return }
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $legacy = (Get-LegacyDataVolumeFromInspect ($inspect -join [Environment]::NewLine)).Trim()
    if ($legacy -notmatch "^[A-Za-z0-9][A-Za-z0-9_.-]+$") { return }
    if ($legacy -eq (Get-EnvironmentValue "CLAIMER_DATA_VOLUME")) { return }
    if (Confirm-DefaultYes $Script:Text.LegacyFound) {
        & docker stop fgc-remaster *> $null
        if ($LASTEXITCODE -ne 0) { throw "Could not stop the existing fgc-remaster container" }
        & docker rm fgc-remaster *> $null
        if ($LASTEXITCODE -ne 0) { throw "Could not replace the existing fgc-remaster container" }
        Set-EnvironmentValue "CLAIMER_DATA_VOLUME" $legacy
        Write-Host $Script:Text.LegacyAdopted -ForegroundColor Green
    }
}

function Invoke-Compose([string[]]$Arguments) {
    if ($Action -eq "source") {
        & docker compose --env-file $EnvironmentFile -f $ComposeFile @Arguments
    } else {
        & docker compose --project-name claimer-control --env-file $EnvironmentFile -f $ComposeFile @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($Arguments -join ' ') failed" }
}

function Wait-Panel {
    Write-Step $Script:Text.WaitingPanel
    for ($attempt = 1; $attempt -le 90; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$PanelUrl/api/status" -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        if (($attempt % 5) -eq 0) { Write-Host "." -NoNewline }
        Start-Sleep -Seconds 2
    }
    throw $Script:Text.PanelTimeout
}

function Get-LatestReleaseTag {
    Write-Step $Script:Text.UpdateCheck
    $release = Invoke-RestMethod -Uri $ReleaseApi -Headers @{Accept = "application/vnd.github+json"; "User-Agent" = "lontrium-launcher/1.2.1"} -TimeoutSec 15
    $tag = [string]$release.tag_name
    if ($tag -notmatch "^v\d+\.\d+\.\d+$") { throw $Script:Text.UpdateInvalid }
    return $tag
}

function Start-Application {
    Adopt-LegacyData
    Write-Step $Script:Text.Pulling
    Invoke-Compose @("pull", "app")
    Write-Step $Script:Text.Starting
    Invoke-Compose @("up", "-d", "app")
    Wait-Panel
    Write-Host $Script:Text.Ready -ForegroundColor Green
    Start-Process $PanelUrl | Out-Null
}

function Start-SourceApplication {
    Write-Step $Script:Text.StartingSource
    Invoke-Compose @("up", "-d", "--build", "app")
    Wait-Panel
    Write-Host $Script:Text.Ready -ForegroundColor Green
    Start-Process $PanelUrl | Out-Null
}

function Get-DashboardJson([string]$Path) {
    return Invoke-RestMethod -Uri "$PanelUrl$Path" -Method Get -TimeoutSec 5
}

function Wait-EconomyRun {
    $config = Get-DashboardJson "/api/config"
    if ($config.setup.required -and -not $config.setup.complete) {
        Write-Host $Script:Text.EconomySetup -ForegroundColor Yellow
        Start-Process $PanelUrl | Out-Null
        return $false
    }

    Write-Step $Script:Text.EconomyWaiting
    $observedRun = $false
    for ($attempt = 1; $attempt -le 15; $attempt++) {
        $status = Get-DashboardJson "/api/status"
        if ($status.running) {
            $observedRun = $true
            break
        }
        if ($status.startedAt -and $status.finishedAt) {
            Write-Host " OK" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
    }

    if (-not $observedRun) {
        Write-Host $Script:Text.EconomyNoRun -ForegroundColor Green
        return $true
    }

    for ($attempt = 1; $attempt -le 720; $attempt++) {
        $status = Get-DashboardJson "/api/status"
        if (-not $status.running) {
            Write-Host " OK" -ForegroundColor Green
            Write-Host $Script:Text.EconomyComplete -ForegroundColor Green
            return $true
        }
        if (($attempt % 6) -eq 0) { Write-Host "." -NoNewline }
        Start-Sleep -Seconds 5
    }

    Write-Host $Script:Text.EconomyTimeout -ForegroundColor Yellow
    Start-Process $PanelUrl | Out-Null
    return $false
}

function Get-RunningContainerIds {
    $containers = @(& docker ps --quiet)
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect running Docker containers" }
    return $containers
}

function Stop-DockerAfterEconomyRun {
    Invoke-Compose @("stop", "app")
    $otherContainers = @(Get-RunningContainerIds)
    if ($otherContainers.Count -gt 0) {
        Write-Host $Script:Text.EconomySharedDocker -ForegroundColor Yellow
        return
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & docker desktop stop --force *> $null
        if ($LASTEXITCODE -ne 0) {
            $dockerCli = Join-Path $env:ProgramFiles "Docker\Docker\DockerCli.exe"
            if (Test-Path -LiteralPath $dockerCli) {
                & $dockerCli -Shutdown *> $null
            }
        }
        # Terminate only Docker's WSL distribution. Other Linux distributions
        # (for example Ubuntu with unsaved work) must never be interrupted.
        & wsl.exe --terminate docker-desktop *> $null
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Start-EconomyApplication {
    Adopt-LegacyData
    Write-Step $Script:Text.Starting
    Invoke-Compose @("up", "-d", "app")
    Wait-Panel
    if (Wait-EconomyRun) {
        Stop-DockerAfterEconomyRun
    }
}

function Update-Application {
    $latest = Get-LatestReleaseTag
    $current = Get-EnvironmentValue "CLAIMER_TAG"
    if ($current -eq $latest) { Write-Host $Script:Text.UpToDate -ForegroundColor Green; return }
    if (-not (Confirm-DefaultYes ($Script:Text.UpdatePrompt -f $current, $latest))) { return }
    Write-Step ($Script:Text.Updating -f $latest)
    Set-EnvironmentValue "CLAIMER_TAG" $latest
    Invoke-Compose @("pull", "app")
    Invoke-Compose @("up", "-d", "app")
    Wait-Panel
    Start-Process $PanelUrl | Out-Null
}

function Invoke-ClaimerControl(
    [ValidateSet("start", "economy", "source", "update", "uninstall", "check")]
    [string]$RequestedAction = $Action
) {
    try {
        $host.UI.RawUI.WindowTitle = $Script:Text.Title
        if (-not (Test-Path -LiteralPath $ComposeFile) -or -not (Test-Path -LiteralPath $EnvironmentFile)) {
            throw "Required launcher files are missing"
        }
        if ($RequestedAction -eq "check") { Write-Host $Script:Text.CheckOk -ForegroundColor Green; return 0 }
        if (-not (Test-DockerCommandAvailable)) { Install-DockerDesktop }
        Wait-DockerDesktop
        if ($RequestedAction -eq "update") { Update-Application }
        elseif ($RequestedAction -eq "economy") { Start-EconomyApplication }
        elseif ($RequestedAction -eq "source") { Start-SourceApplication }
        elseif ($RequestedAction -eq "uninstall") {
            Invoke-Compose @("down")
            if ($RemoveData) {
                $volume = Get-EnvironmentValue "CLAIMER_DATA_VOLUME"
                if ($volume -notmatch "^[A-Za-z0-9][A-Za-z0-9_.-]+$") { throw "Invalid data volume name" }
                & docker volume rm $volume
                if ($LASTEXITCODE -ne 0) { throw "Could not remove data volume $volume" }
            }
        } else { Start-Application }
        return 0
    } catch {
        Write-Host ($Script:Text.Failed -f $_.Exception.Message) -ForegroundColor Red
        return 1
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    exit (Invoke-ClaimerControl)
}
