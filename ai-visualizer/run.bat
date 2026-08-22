@echo off
rem ai-visualizer: give your AI agent a face.
rem Copyright (C) 2026 Jared Rhodenizer
rem
rem This program is free software: you can redistribute it and/or modify
rem it under the terms of the GNU Affero General Public License as published
rem by the Free Software Foundation, either version 3 of the License, or
rem (at your option) any later version.
rem
rem This program is distributed in the hope that it will be useful,
rem but WITHOUT ANY WARRANTY; without even the implied warranty of
rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
rem GNU Affero General Public License for more details.
rem
rem You should have received a copy of the GNU Affero General Public License
rem along with this program. If not, see <https://www.gnu.org/licenses/>.
rem
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem ai-visualizer launcher (Windows). Python standard library only.
rem   run.bat                  the real signal bus
rem   run.bat --mock speaking  a synthesized state, no voice line needed
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py server.py %*
) else (
  python server.py %*
)
