@echo off
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
