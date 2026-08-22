@echo off
rem fullstack-agent: Local AI Agent with Memory, Voice, Face, and Hands.
rem Copyright (C) 2026 Jared Rhodenizer, local AI edition.
rem SPDX-License-Identifier: AGPL-3.0-or-later

cd /d "%~dp0"
title JARVIS - Fullstack Local AI Agent

echo =========================================================
echo   JARVIS - FULLSTACK LOCAL AI AGENT (Ollama Edition)
echo =========================================================
echo.

rem Detect Python Command
set "PYCMD="
if exist "%~dp0backtalk\.venv\Scripts\python.exe" (
  set "PYCMD=%~dp0backtalk\.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul && set "PYCMD=py"
  if "%PYCMD%"=="" where python >nul 2>nul && set "PYCMD=python"
)
if "%PYCMD%"=="" (
  echo [ERROR] Python was not found on PATH. Please install Python 3.10+ or add it to PATH.
  pause
  exit /b 1
)

rem Check Ollama connectivity
echo [*] Checking local Ollama connection...
curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
  echo [WARNING] Ollama is not responding at http://127.0.0.1:11434!
  echo           Please launch Ollama Desktop or run ollama serve.
) else (
  echo [OK] Ollama is running and ready.
)
echo.

rem Ensure Memory Vault is initialized
echo [*] Initializing Memory Vault...
%PYCMD% vault_manager.py >nul 2>nul

rem Clean up any leftover server on port 8790
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8790" ^| findstr "LISTENING"') do (
  taskkill /f /pid %%a >nul 2>nul
)

rem Launch Unified Web Dashboard & Air Board (Port 8790) in background (same window)
if exist "ai-visualizer" (
  echo [1/2] Launching Unified Web Dashboard on http://127.0.0.1:8790/ ...
  start /b "" %PYCMD% ai-visualizer\server.py
  ping 127.0.0.1 -n 2 >nul
  start http://localhost:8790/
)

rem Launch Voice Engine (Backtalk) in this terminal
if not exist "backtalk" goto no_backtalk
if "%1"=="web" goto web_only

echo [2/2] Starting Voice Engine in this window...
echo       Hold your talk key or speak in hands-free mode.
echo       Press Ctrl-C or say goodbye jarvis to exit.
echo.

cd /d "%~dp0backtalk"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m backtalk.main
  goto cleanup
)
where uv >nul 2>nul
if errorlevel 1 (
  %PYCMD% -m backtalk.main
) else (
  uv run python -m backtalk.main
)
goto cleanup

:web_only
echo Web dashboard is running at http://localhost:8790/
echo Press any key to close this window.
pause >nul
goto cleanup

:no_backtalk
echo Web dashboard is running at http://localhost:8790/
echo Press any key to close this window.
pause >nul

:cleanup
echo.
echo [*] Stopping background services...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8790" ^| findstr "LISTENING"') do (
  taskkill /f /pid %%a >nul 2>nul
)
echo [OK] Agent stopped cleanly.

:done
