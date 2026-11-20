@echo off
setlocal enabledelayedexpansion
title AURA AI Assistant - Release Builder

echo ================================================================
echo           AURA AI Assistant - Standalone Release Builder         
echo ================================================================
echo.

cd /d "%~dp0\.."

:: 1. Compile Root Launcher AURA.exe
echo [*] Compiling native AURA.exe launcher...
if exist "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" (
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /target:winexe /win32icon:app_icon.ico /out:AURA.exe AURA_Launcher.cs
    echo [OK] AURA.exe built.
) else (
    echo [WARNING] C# compiler csc.exe not found.
)

:: 2. Build Frontend & NSIS Windows Installer
echo.
echo [*] Packaging Standalone NSIS Windows Installer...
cd frontend
call npm run dist:installer
cd ..

if exist "frontend\dist-electron\AURA Setup 1.0.0.exe" (
    if not exist "release" mkdir release
    copy "frontend\dist-electron\AURA Setup 1.0.0.exe" "release\AURA-Setup.exe" >nul
    echo.
    echo [OK] Distributable installer generated at: release\AURA-Setup.exe
)

echo.
echo ================================================================
echo Build finished! Ready for distribution and GitHub Releases.
echo ================================================================
pause
