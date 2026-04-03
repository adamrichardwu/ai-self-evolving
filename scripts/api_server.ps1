param(
    [ValidateSet("start", "stop", "restart", "status", "foreground")]
    [string]$Action = "start",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [int]$StartupTimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$controlDir = Join-Path $repoRoot "control"
$pidFile = Join-Path $controlDir "api_server.pid"
$stdoutLog = Join-Path $controlDir "api_server.out.log"
$stderrLog = Join-Path $controlDir "api_server.err.log"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$uvicornArgs = @("-m", "uvicorn", "apps.api.app.main:app", "--host", $BindHost, "--port", $Port.ToString())

function Ensure-ControlDir {
    if (-not (Test-Path $controlDir)) {
        New-Item -ItemType Directory -Path $controlDir | Out-Null
    }
}

function Read-Pid {
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $raw = (Get-Content -Path $pidFile -Raw).Trim()
    if (-not $raw) {
        return $null
    }

    $pidValue = 0
    if ([int]::TryParse($raw, [ref]$pidValue)) {
        return $pidValue
    }

    return $null
}

function Remove-PidFile {
    if (Test-Path $pidFile) {
        Remove-Item -Path $pidFile -Force
    }
}

function Get-RecordedProcess {
    $recordedPid = Read-Pid
    if (-not $recordedPid) {
        return $null
    }

    try {
        return Get-Process -Id $recordedPid -ErrorAction Stop
    }
    catch {
        Remove-PidFile
        return $null
    }
}

function Get-ListeningProcess {
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) {
        return $null
    }

    try {
        return Get-Process -Id $connection.OwningProcess -ErrorAction Stop
    }
    catch {
        return $null
    }
}

function Stop-ProcessIfRunning($process) {
    if ($null -eq $process) {
        return
    }

    try {
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
    }
    catch {
    }
}

function Wait-ForHealth {
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $healthUri = "http://${BindHost}:$Port/health"

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500

        try {
            $response = Invoke-WebRequest -Uri $healthUri -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
        }
    }

    return $false
}

function Show-Logs {
    if (Test-Path $stdoutLog) {
        Write-Host "--- stdout tail ---"
        Get-Content -Path $stdoutLog -Tail 20
    }
    if (Test-Path $stderrLog) {
        Write-Host "--- stderr tail ---"
        Get-Content -Path $stderrLog -Tail 20
    }
}

function Show-Status {
    $recorded = Get-RecordedProcess
    $listener = Get-ListeningProcess

    if ($recorded) {
        Write-Host "Recorded PID: $($recorded.Id)"
    }
    else {
        Write-Host "Recorded PID: none"
    }

    if ($listener) {
        Write-Host "Listening PID: $($listener.Id) ($($listener.ProcessName))"
    }
    else {
        Write-Host "Listening PID: none"
    }

    Write-Host "Health URL: http://${BindHost}:$Port/health"
    Write-Host "PID file: $pidFile"
    Write-Host "stdout log: $stdoutLog"
    Write-Host "stderr log: $stderrLog"
}

function Start-Server {
    if (-not (Test-Path $pythonExe)) {
        throw "Python virtual environment not found: $pythonExe"
    }

    $listener = Get-ListeningProcess
    if ($listener) {
        throw "Port $Port is already in use by PID $($listener.Id). Run stop or choose another port."
    }

    Ensure-ControlDir
    if (Test-Path $stdoutLog) {
        Remove-Item -Path $stdoutLog -Force
    }
    if (Test-Path $stderrLog) {
        Remove-Item -Path $stderrLog -Force
    }

    $process = Start-Process -FilePath $pythonExe -ArgumentList $uvicornArgs -WorkingDirectory $repoRoot -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru -WindowStyle Hidden
    Set-Content -Path $pidFile -Value $process.Id -Encoding ascii

    if (Wait-ForHealth) {
        Write-Host "API server started. PID=$($process.Id) URL=http://${BindHost}:$Port"
        return
    }

    Stop-ProcessIfRunning $process
    Remove-PidFile
    Write-Host "API server did not become healthy within ${StartupTimeoutSeconds}s."
    Show-Logs
    exit 1
}

function Stop-Server {
    $recorded = Get-RecordedProcess
    $listener = Get-ListeningProcess

    Stop-ProcessIfRunning $recorded

    if ($listener -and ($null -eq $recorded -or $listener.Id -ne $recorded.Id)) {
        Stop-ProcessIfRunning $listener
    }

    Remove-PidFile
    Write-Host "API server stopped."
}

switch ($Action) {
    "start" {
        Start-Server
    }
    "stop" {
        Stop-Server
    }
    "restart" {
        Stop-Server
        Start-Sleep -Seconds 1
        Start-Server
    }
    "status" {
        Show-Status
    }
    "foreground" {
        if (-not (Test-Path $pythonExe)) {
            throw "Python virtual environment not found: $pythonExe"
        }

        Set-Location $repoRoot
        & $pythonExe @uvicornArgs
    }
}