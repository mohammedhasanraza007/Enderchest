@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, then run run.bat again.
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
if not defined RUNNING (
  netstat -ano | findstr /R /C:"127.0.0.1:%PORT% .*LISTENING" >nul
  if not errorlevel 1 (
    echo Port %PORT% is already in use by another program. Close it, or change ENDERCHEST_PORT in .env, then run run.bat again.
    exit /b 1
  )
)

docker compose up -d --wait --wait-timeout 120
if errorlevel 1 (
  echo Enderchest did not become ready within 2 minutes. See: docker compose logs app
  exit /b 1
)

set "STATE=unreachable"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\health.ps1" -Port %PORT%`) do set "STATE=%%S"

if "!STATE!"=="ok" (
  start "" "http://127.0.0.1:%PORT%"
  echo Enderchest is running at http://127.0.0.1:%PORT%
) else (
  start "" "http://127.0.0.1:%PORT%"
  echo.
  echo WARNING: Enderchest started but its state is: !STATE!
  echo Your data has not been changed. The page that just opened explains what is wrong and what to do.
)
echo To stop it: stop.bat    To back up now: backup.bat
exit /b 0
