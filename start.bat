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
where py >nul 2>nul && set "PYCMD=py"
if "%PYCMD%"=="" where python >nul 2>nul && set "PYCMD=python"
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

rem Launch Unified Web Dashboard & 3D Face (Port 8790)
if exist "ai-visualizer" (
  echo [1/2] Launching Unified Web Dashboard on http://127.0.0.1:8790/ ...
  start "JARVIS Web Dashboard & 3D Face" %PYCMD% ai-visualizer\server.py
  ping 127.0.0.1 -n 2 >nul
  start http://127.0.0.1:8790/
)

rem Barehands Air Board (Port 8794)
if exist "barehands" (
  if not "%1"=="voice" (
    echo [2/3] Launching Barehands Air Board on http://127.0.0.1:8794/stage.html ...
    start "JARVIS Barehands" %PYCMD% barehands\server.py
    ping 127.0.0.1 -n 2 >nul
  )
)

rem Launch Voice Engine (Backtalk)
if exist "backtalk" (
  if not "%1"=="web" (
    echo [3/3] Starting Voice Engine in this window...
    echo       Hold your talk key (RIGHT ALT by default) or use hands-free.
    echo       Press Ctrl-C or say goodbye jarvis to exit.
    echo.
    cd /d "%~dp0backtalk"
    if exist ".venv\Scripts\python.exe" (
      ".venv\Scripts\python.exe" -m backtalk.main
    ) else (
      where uv >nul 2>nul
      if errorlevel 1 (
        %PYCMD% -m backtalk.main
      ) else (
        uv run python -m backtalk.main
      )
    )
  ) else (
    echo Web dashboard is running at http://127.0.0.1:8790/
    echo Press any key to close this window.
    pause >nul
  )
) else (
  echo Web dashboard is running at http://127.0.0.1:8790/
  echo Press any key to close this window.
  pause >nul
)
