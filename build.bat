@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo Enderchest build. Safe to run again at any time; it never deletes anything.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed. Install Docker Desktop, then run build.bat again.
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, wait until it says the engine is running, then run build.bat again.
  exit /b 1
)

set "BACKUPDIR=%USERPROFILE%\Enderchest-Backups"
if not exist "%BACKUPDIR%" (
  mkdir "%BACKUPDIR%"
  if errorlevel 1 (
    echo Could not create the backup folder %BACKUPDIR%.
    exit /b 1
  )
  echo Created the backup folder %BACKUPDIR%
)

if not exist ".env" (
  set "FWD=!BACKUPDIR:\=/!"
  > ".env" echo ENDERCHEST_PORT=8470
  >> ".env" echo ENDERCHEST_BACKUP_DIR=!FWD!
  echo Wrote .env with the backup folder %BACKUPDIR%
)

REM The data volume is created once and never touched again. If it already exists, nothing happens.
docker volume inspect enderchest_data >nul 2>&1
if errorlevel 1 (
  docker volume create enderchest_data >nul
  if errorlevel 1 (
    echo Could not create the data volume.
    exit /b 1
  )
  echo Created the data volume.
) else (
  echo The data volume already exists. Left as it is.
)

REM The image reports this date in Settings, About. Without it the page says it is not recorded.
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"`) do set "BUILD_DATE=%%D"
docker compose build app
if errorlevel 1 (
  echo The build failed. Nothing was deleted. Read the message above.
  exit /b 1
)
echo Build finished. Next: run.bat
exit /b 0
