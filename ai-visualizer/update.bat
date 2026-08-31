@echo off
rem ai-visualizer — update to the newest version, showing what changed first.
rem Copyright (C) 2026 Jared Rhodenizer
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem
rem Your ai-visualizer.json is yours: nothing in this script can touch or overwrite it.
rem Safe to run any time; when nothing is new it just says so.

rem NO SELF-RELAUNCH, and the reason is worth keeping.
rem
rem cmd reads a .bat by byte offset, so a script that pulls a new copy of
rem ITSELF mid-run can garble from that point on. This used to guard against
rem that by copying itself into LOCALAPPDATA and running the copy.
rem
rem Copying yourself somewhere and running the copy is a shape security
rem software is built to distrust, and it cannot see why you did it. On
rem some machines that stopped the install outright: the scanner held this
rem file open and the unpack could not write it.
rem
rem The guard was never worth that. It only mattered on an update that
rem changed this very script, and by then the pull had already succeeded.
rem The worst case now is an odd looking line at the very end. If you ever
rem see one, just run this again.


setlocal
cd /d "%~dp0"
set CFG=ai-visualizer.json

if exist ".git\" goto havegit
rem this folder arrived as a zip: wire it to updates, once, keeping the config
if exist "%CFG%" copy /y "%CFG%" "%CFG%.mine" >nul
git init -b main
git remote add origin https://github.com/jaredrhod/ai-visualizer
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
