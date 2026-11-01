@echo off
REM The work is in :main. This outer part saves everything to logs\build-<time>.txt and always keeps
REM the window open at the end; only ENDERCHEST_NO_PAUSE=1 (automation) turns that off.
if "%~1"=="--inner" goto :main
cd /d "%~dp0"
set "ENDERCHEST_SELF=%~f0"
set "STAMP=latest"
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "STAMP=%%T"
set "LOG=%~dp0logs\build-%STAMP%.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\logged.ps1" -Log "%LOG%"
set "CODE=%errorlevel%"
if exist "%LOG%" goto :logged
echo The log could not be started, so this run has no log file.
call :main
set "CODE=%errorlevel%"
goto :finish
:logged
echo.
echo Log saved: "%LOG%"
:finish
if not "%ENDERCHEST_NO_PAUSE%"=="1" pause
exit /b %CODE%

:main
REM Before delayed expansion: it would eat a "!" in a folder or user name.
cd /d "%~dp0"
set "BACKUPDIR=%USERPROFILE%\Enderchest-Backups"
REM .env decides these: a value left in the shell must not win over it.
set "ENDERCHEST_PORT="
set "ENDERCHEST_BACKUP_DIR="
setlocal enabledelayedexpansion
echo Enderchest build. Safe to run again at any time; it never deletes anything.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed. Install Docker Desktop, then run build.bat again.
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running, or this user cannot reach it. Start Docker Desktop, wait until it says the engine is running, then run build.bat again.
  echo What Docker says:
  docker version
  exit /b 1
)
set "ENGINE="
for /f "usebackq delims=" %%O in (`docker info --format "{{.OSType}}"`) do set "ENGINE=%%O"
if defined ENGINE if /i not "!ENGINE!"=="linux" (
  echo Docker is using !ENGINE! containers. Enderchest needs Linux containers: right-click the Docker icon and choose Switch to Linux containers.
  exit /b 1
)
docker compose version >nul 2>&1
if errorlevel 1 (
  echo Docker Compose is missing. Update Docker Desktop, then run build.bat again.
  exit /b 1
)
REM run.bat needs "up --wait-timeout", which came in Compose 2.17.
set "MAJOR=" & set "MINOR="
for /f "usebackq tokens=1,2 delims=.v" %%A in (`docker compose version --short`) do set "MAJOR=%%A" & set "MINOR=%%B"
if defined MAJOR (
  set /a "COMPOSE=MAJOR*1000+MINOR"
  if !COMPOSE! LSS 2017 (
    echo Docker Compose is too old: version !MAJOR!.!MINOR!. Enderchest needs 2.17 or newer. Update Docker Desktop, then run build.bat again.
    exit /b 1
  )
)

if not exist ".env" (
  REM UTF-8 without a BOM, as Docker Compose reads it: echo would write the console's old code page.
  powershell -NoProfile -Command "$utf8 = New-Object Text.UTF8Encoding $false; $dir = $env:BACKUPDIR -replace '\\','/'; [IO.File]::WriteAllLines((Join-Path $PWD '.env'), [string[]]@('ENDERCHEST_PORT=8470', ('ENDERCHEST_BACKUP_DIR=' + $dir)), $utf8)"
  if errorlevel 1 (
    echo Could not write the .env settings file.
    exit /b 1
  )
  echo Wrote .env with the backup folder !BACKUPDIR!
)
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\backup-folder.ps1"
if errorlevel 1 exit /b 1

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
  echo The build failed. Nothing was deleted. The first error above says why; a failed download usually means the internet connection, and "no space left" means the disk is full.
  exit /b 1
)
echo Build finished. Next: run.bat
exit /b 0
