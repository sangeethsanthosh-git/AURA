@echo off
setlocal enabledelayedexpansion
title AURA AI Assistant - Quick Setup

echo ================================================================
echo           AURA AI Desktop Assistant - Environment Setup          
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
echo [*] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10 or higher from: https://www.python.org/downloads/
    echo Make sure to check 'Add Python to PATH' during installation.
    pause
    exit /b 1
)
python --version

:: 2. Check Node.js
echo.
echo [*] Checking Node.js installation...
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js was not found in PATH!
    echo Please install Node.js LTS from: https://nodejs.org/
    pause
    exit /b 1
)
node -v

:: 3. Check Ollama
echo.
echo [*] Checking Ollama installation...
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if not exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        echo [WARNING] Ollama is not installed in standard locations.
        echo For local offline intelligence, install Ollama from: https://ollama.com/
        echo Then run: ollama pull llama3.2:3b
    ) else (
        echo [OK] Ollama detected in AppData.
    )
) else (
    echo [OK] Ollama CLI detected.
)

:: 4. Create Python Virtual Environment
echo.
echo [*] Setting up Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Existing virtual environment found.
)

:: 5. Install Python Dependencies
echo.
echo [*] Installing Python dependencies from requirements.txt...
call .\.venv\Scripts\python.exe -m pip install --upgrade pip
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some Python packages encountered issues. Retrying core dependencies...
    call .\.venv\Scripts\python.exe -m pip install fastapi uvicorn websockets pydantic requests httpx faster-whisper edge-tts piper-tts pyautogui pywinauto pywin32 winsdk psutil mss pillow pyperclip
)

:: 6. Setup Frontend
echo.
echo [*] Installing and building desktop frontend UI...
cd frontend
if not exist "node_modules" (
    call npm install
)
call npm run build
call npm run dist:exe
cd ..

:: 7. Setup Environment Variables
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env configuration from .env.example...
        copy ".env.example" ".env" >nul
    )
)

:: 8. Compile Native Launcher AURA.exe
if exist "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" (
    echo.
    echo [*] Compiling native Windows AURA.exe launcher...
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /target:winexe /win32icon:app_icon.ico /out:AURA.exe AURA_Launcher.cs >nul 2>&1
    if exist "AURA.exe" (
        echo [OK] Native AURA.exe launcher successfully built.
    )
)

echo.
echo ================================================================
echo           [SUCCESS] AURA Setup Completed Successfully!          
echo ================================================================
echo.
echo You can now run AURA at any time by double-clicking:
echo   --^> AURA.exe
echo.
pause
exit /b 0
