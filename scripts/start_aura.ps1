# AURA Voice Assistant Launcher Script (Windows 11)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           Launching AURA Voice Assistant V1               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Verify Ollama is running
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Ollama server is running (v$($ollamaCheck.version))." -ForegroundColor Green
} catch {
    Write-Host "[!] Ollama is not running. Starting Ollama in background..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# 2. Start FastAPI WebSocket Backend
Write-Host "[*] Starting FastAPI Backend on ws://127.0.0.1:8000..." -ForegroundColor Cyan
$backendProcess = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "backend.api.app:app", "--host", "127.0.0.1", "--port", "8000" -PassThru -WindowStyle Hidden

# 3. Wait for backend to be ready
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 -ErrorAction Stop
        if ($res.status -eq "online") {
            $backendReady = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $backendReady) {
    Write-Host "[Error] Backend failed to start. Terminating." -ForegroundColor Red
    if ($backendProcess) { Stop-Process -Id $backendProcess.Id -Force }
    exit 1
}

Write-Host "[OK] Backend is online!" -ForegroundColor Green

# 4. Launch Desktop UI (Electron + Vite)
Write-Host "[*] Launching AURA Electron Desktop App..." -ForegroundColor Cyan
Set-Location "$projectRoot\frontend"

try {
    npm run desktop
} finally {
    # Clean up background backend process when Electron closes
    Write-Host "[*] Shutting down AURA backend..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
    Write-Host "[OK] AURA closed cleanly." -ForegroundColor Green
}
