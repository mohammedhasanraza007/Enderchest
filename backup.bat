@echo off
REM The work is in :main, so that every "exit /b" comes back here and a double-clicked window stays
REM open to show its message.
call :main %*
set "CODE=%errorlevel%"
call :hold
exit /b %CODE%

:hold
if defined ENDERCHEST_NO_PAUSE exit /b 0
setlocal enabledelayedexpansion
for %%A in (!cmdcmdline!) do if /i "%%~A"=="/c" set "DOUBLE_CLICKED=1"
if defined DOUBLE_CLICKED pause
endlocal
exit /b 0

:main
setlocal
cd /d "%~dp0"

set "PORT=8470"
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if "%%A"=="ENDERCHEST_PORT" set "PORT=%%B"
  )
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\post-backup.ps1" -Port %PORT%
if errorlevel 1 (
  echo Is Enderchest running? Start it with run.bat
  exit /b 1
)
exit /b 0
