@echo off
rem backtalk — update to the newest version, showing what changed first.
rem Copyright (C) 2026 Jared Rhodenizer
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem
rem Your backtalk.json is yours: nothing in this script can touch or overwrite it.
rem Safe to run any time; when nothing is new it just says so.

rem run from a temp copy so updating this very file mid-run cannot garble it
if "%~1"=="__run__" goto run
copy /y "%~f0" "%TEMP%\backtalk-update.bat" >nul
call "%TEMP%\backtalk-update.bat" __run__ "%~dp0"
exit /b %errorlevel%

:run
setlocal
cd /d "%~2"
set CFG=backtalk.json

if exist ".git\" goto havegit
rem this folder arrived as a zip: wire it to updates, once, keeping the config
if exist "%CFG%" copy /y "%CFG%" "%CFG%.mine" >nul
git init -b main
git remote add origin https://github.com/jaredrhod/backtalk
git fetch -q origin
git reset --hard origin/main
git branch --set-upstream-to=origin/main main
if exist "%CFG%.mine" move /y "%CFG%.mine" "%CFG%" >nul
echo wired this folder to updates.
:havegit

git fetch -q origin 2>nul
git log --oneline "..@{u}" 2>nul

rem one-time migration: the config moved out of git tracking. If git here
rem still tracks the old copy, lift yours aside, let the pull retire the
rem tracked one, then put yours back exactly as it was.
set MIGRATE=0
if not exist "%CFG%" goto pull
git ls-files --error-unmatch "%CFG%" >nul 2>nul
if errorlevel 1 goto pull
copy /y "%CFG%" "%CFG%.mine" >nul
git checkout -- "%CFG%"
set MIGRATE=1

:pull
git pull --ff-only
if errorlevel 1 echo   (couldn't fast-forward; your local edits win.)
if "%MIGRATE%"=="1" if exist "%CFG%.mine" move /y "%CFG%.mine" "%CFG%" >nul
echo update complete.
