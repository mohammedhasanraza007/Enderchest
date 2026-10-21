@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
REM test.bat [unit|integration|lint|probes|e2e|all]   (default: all)
REM Everything here uses the TEST stack (compose.test.yaml) or temporary folders in a container.
REM It never touches the live stack or the live volume.

set "WHAT=%~1"
if "%WHAT%"=="" set "WHAT=all"

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, then run test.bat again.
  exit /b 1
)
if not exist "test-results" mkdir "test-results"
if not exist ".test-backups" mkdir ".test-backups"

set "DC=docker compose -f compose.test.yaml --profile tools"

if /I "%WHAT%"=="unit" goto unit
if /I "%WHAT%"=="integration" goto integration
if /I "%WHAT%"=="lint" goto lint
if /I "%WHAT%"=="probes" goto probes
if /I "%WHAT%"=="e2e" goto e2e
if /I "%WHAT%"=="all" goto all
echo Usage: test.bat [unit^|integration^|lint^|probes^|e2e^|all]
exit /b 2

:build
%DC% build tools
if errorlevel 1 (
  echo Building the test tools image failed.
  exit /b 1
)
exit /b 0

:lint
call :build || exit /b 1
%DC% run --rm tools ruff check .
exit /b %errorlevel%

:unit
call :build || exit /b 1
%DC% run --rm tools pytest tests/unit -q -p no:cacheprovider
exit /b %errorlevel%

:integration
call :build || exit /b 1
%DC% run --rm tools pytest tests/integration -q -p no:cacheprovider
exit /b %errorlevel%

:probes
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\tests\probes\run-probes.ps1" %2 %3 %4 %5 %6 %7
exit /b %errorlevel%

:e2e
echo There is no end-to-end suite yet. It starts in Phase 1, when the first screen exists.
exit /b 0

:all
call :lint || exit /b 1
call :unit || exit /b 1
call :integration || exit /b 1
call :e2e
echo Unit, integration and lint passed. Run "test.bat probes" for the Docker probes.
exit /b 0
