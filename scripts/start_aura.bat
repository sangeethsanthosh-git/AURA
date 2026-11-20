@echo off
title AURA Voice Assistant Launcher
cd /d "%~dp0\.."
powershell -ExecutionPolicy Bypass -File "%~dp0start_aura.ps1"
pause
