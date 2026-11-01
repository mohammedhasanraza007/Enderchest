@echo off
REM The work is in :main. This outer part saves everything to logs\run-<time>.txt and keeps the window
REM open on a problem; a good start closes by itself, the browser has opened. ENDERCHEST_NO_PAUSE=1
REM (automation) never waits.
if "%~1"=="--inner" goto :main
cd /d "%~dp0"
set "ENDERCHEST_SELF=%~f0"
set "STAMP=latest"
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "STAMP=%%T"
set "LOG=%~dp0logs\run-%STAMP%.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\logged.ps1" -Log "%LOG%"
set "CODE=%errorlevel%"
if exist "%LOG%" goto :logged
echo The log could not be started, so this run has no log file.
call :main
set "CODE=%errorlevel%"
goto :finish
:logged
if not "%CODE%"=="0" echo Log saved: "%LOG%"
:finish
if not "%CODE%"=="0" if not "%ENDERCHEST_NO_PAUSE%"=="1" pause
exit /b %CODE%

:main
REM Before delayed expansion: it would eat a "!" in the folder name.
cd /d "%~dp0"
REM .env decides these: a value left in the shell must not win over it.
set "ENDERCHEST_PORT="
set "ENDERCHEST_BACKUP_DIR="
setlocal enabledelayedexpansion

where docker >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install-docker.ps1" -StartOnly
  if errorlevel 1 (
    echo Docker Desktop is not installed. Double-click build.bat: it installs it for you.
    exit /b 1
  )
)
REM A docker already found still wins: this is added last.
set "PATH=%PATH%;%ProgramFiles%\Docker\Docker\resources\bin"
docker info >nul 2>&1
if errorlevel 1 powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install-docker.ps1" -StartOnly
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running, or this user cannot reach it. Start Docker Desktop, then run run.bat again.
  echo What Docker says:
  docker version
  exit /b 1
)
if not exist ".env" (
  echo There is no .env file yet. Run build.bat first.
  exit /b 1
)
docker image inspect enderchest-app:latest >nul 2>&1
if errorlevel 1 (
  echo The Enderchest image is not built yet. Run build.bat first.
  exit /b 1
)
docker volume inspect enderchest_data >nul 2>&1
if errorlevel 1 (
  echo The data volume does not exist. Run build.bat first. Nothing was started, so nothing empty was created.
  exit /b 1
)

set "PORT=8470"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if "%%A"=="ENDERCHEST_PORT" set "PORT=%%B"
)

REM If our own container is not running, the port must be free.
set "RUNNING="
for /f %%I in ('docker compose ps -q --status running app 2^>nul') do set "RUNNING=%%I"
if defined RUNNING goto :port_free
REM Docker can hold the port for a few seconds after stop.bat, so a busy port gets 30 seconds first.
set "TRIES=0"
:port_check
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if errorlevel 1 goto :port_free
if "%TRIES%"=="0" echo Port %PORT% is busy. Waiting up to 30 seconds for it to free up...
set /a "TRIES+=1"
if %TRIES% GEQ 15 goto :port_busy
ping -n 3 127.0.0.1 >nul
goto :port_check
:port_busy
echo Port %PORT% is still in use by another program. Close it, or change ENDERCHEST_PORT in .env, then run run.bat again.
exit /b 1
:port_free

docker compose up -d --wait --wait-timeout 120
if errorlevel 1 (
  echo.
  echo Enderchest did not start. Your data has not been changed. The error above says why. What Docker shows now:
  docker compose ps -a
  docker compose logs --tail 40 app
  exit /b 1
)

set "STATE=unreachable"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\health.ps1" -Port %PORT%`) do set "STATE=%%S"

if "!STATE!"=="ok" (
  start "" "http://127.0.0.1:%PORT%"
  echo Enderchest is running at http://127.0.0.1:%PORT%
) else (
  start "" "http://127.0.0.1:%PORT%"
  echo.
  echo Enderchest opened its safety page instead of the app. Your data has not been changed.
  echo This is normal if this PC has older Enderchest backups. The page says what to do.
  echo Details: !STATE!
)
echo To stop it: stop.bat    To back up now: backup.bat
exit /b 0
