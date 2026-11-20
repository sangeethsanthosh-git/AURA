@echo off
setlocal enabledelayedexpansion
title AURA Desktop Assistant Launcher

echo ===================================================
echo           AURA Desktop Assistant Launcher          
echo ===================================================

cd /d "%~dp0"

:: 1. Check Python Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv!
    pause
    exit /b 1
)

:: 2. Ensure Ollama Daemon
echo [*] Checking Ollama AI model engine...
tasklist /fi "imagename eq ollama.exe" 2>NUL | find /i /n "ollama.exe" >NUL
if "%ERRORLEVEL%"=="1" (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        echo [*] Launching Ollama daemon...
        start "" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve >nul 2>&1
        timeout /t 2 /nobreak >nul
    ) else (
        echo [!] Warning: Ollama not found in default path. Please ensure Ollama is installed.
    )
) else (
    echo [OK] Ollama is active.
)

:: 3. Ensure Frontend Build
if not exist "frontend\dist\index.html" (
    echo [*] Building frontend bundle...
    cd frontend
    call npm run build
    cd ..
)

:: 4. Start Python FastAPI Backend in background
echo [*] Checking AURA Backend Service...
powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).State" 2>nul | find /i "Listen" >nul
if "%ERRORLEVEL%"=="1" (
    echo [*] Starting AURA backend service on port 8000...
    start "AURA Backend" /B ".venv\Scripts\python.exe" -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 >nul 2>&1
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] AURA backend service is active.
)

:: 5. Launch Native Desktop App Executable (.exe)
echo [*] Launching AURA Native Desktop Assistant Window...
if exist "frontend\dist-electron\win-unpacked\AURA.exe" (
    start "" "frontend\dist-electron\win-unpacked\AURA.exe"
) else (
    cd frontend
    call npx electron electron/main.cjs
    cd ..
)

exit /b 0
