@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
REM test.bat [unit|integration|lint|probes|e2e|types|format|bakeoff|all]   (default: all)
REM Everything here uses the TEST stack (compose.test.yaml) or temporary folders in a container.
REM It never touches the live stack or the live volume.
REM   lint         ruff (Python), then tsc, eslint and prettier (frontend)
REM   unit         pytest unit tests, vitest, and a check that the generated API types are current
REM   integration  pytest integration tests on temporary folders
REM   probes       the Docker probes of docs/DATA_SAFETY.md 10 (and 15, 16) against the test stack
REM   e2e          Playwright: contrast, dead controls, theme, first run, backups (test stack)
REM   types        rewrite frontend/openapi.json and frontend/src/api/schema.d.ts from the backend
REM   format       rewrite the frontend files with prettier (lint only checks them)
REM   bakeoff      the Phase 3 OCR engine measurement on the owner's photos (D-099): builds the
REM                bakeoff image (four engines, models baked in) and runs it with no network

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
if /I "%WHAT%"=="types" goto types
if /I "%WHAT%"=="format" goto format
if /I "%WHAT%"=="bakeoff" goto bakeoff
if /I "%WHAT%"=="all" goto all
echo Usage: test.bat [unit^|integration^|lint^|probes^|e2e^|types^|format^|bakeoff^|all]
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
if errorlevel 1 exit /b 1
%DC% run --rm tools sh -c "cd /frontend && npx tsc --noEmit && npx eslint . && npx prettier --check ."
exit /b %errorlevel%

:unit
call :build || exit /b 1
%DC% run --rm tools pytest tests/unit -q -p no:cacheprovider
if errorlevel 1 exit /b 1
%DC% run --rm tools sh -c "cd /frontend && npx vitest run && npm run api-types:check"
exit /b %errorlevel%

:integration
call :build || exit /b 1
%DC% run --rm tools pytest tests/integration -q -p no:cacheprovider
exit /b %errorlevel%

:types
call :build || exit /b 1
%DC% run --rm -v "%~dp0frontend:/frontend-host" tools sh -c "python scripts/export_openapi.py /frontend-host/openapi.json && /frontend/node_modules/.bin/openapi-typescript /frontend-host/openapi.json -o /frontend-host/src/api/schema.d.ts"
exit /b %errorlevel%

:format
call :build || exit /b 1
%DC% run --rm -v "%~dp0frontend:/frontend-host" tools sh -c "cd /frontend-host && /frontend/node_modules/.bin/prettier --write ."
exit /b %errorlevel%

:probes
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\tests\probes\run-probes.ps1" %2 %3 %4 %5 %6 %7
exit /b %errorlevel%

:e2e
set "E2E=docker compose -f compose.test.yaml"
REM Rebuild the app image so the browser tests run against the current backend and frontend.
%E2E% build app
if errorlevel 1 exit /b 1
%E2E% --profile e2e build e2e
if errorlevel 1 exit /b 1
%E2E% up -d --wait app
if errorlevel 1 exit /b 1
%E2E% --profile e2e run --rm e2e
if errorlevel 1 exit /b 1
REM The second run needs an app without a /backups mount (the "folder not connected" banner).
REM Its data is a throwaway anonymous volume: a new one each run (--renew-anon-volumes makes a
REM new volume and deletes nothing), or a database from an older phase would wait for a
REM pre-migration backup that this app can never make.
%E2E% --profile e2e-nobackups up -d --wait --renew-anon-volumes app-nobackups
if errorlevel 1 exit /b 1
%E2E% --profile e2e-nobackups run --rm e2e-nobackups
exit /b %errorlevel%

:bakeoff
REM The photos are mounted read-only and never enter an image; the table lands in
REM docs\logs\raw\phase-3\bakeoff. Folders are made first: bind-mount folders only (F-028).
if not exist "tests\fixtures\private\phase3\labels.csv" (
  echo No photos yet: put the 20 photos and labels.csv in tests\fixtures\private\phase3 first.
  exit /b 2
)
if not exist "docs\logs\raw\phase-3\bakeoff" mkdir "docs\logs\raw\phase-3\bakeoff"
docker build --target bakeoff -t enderchest-bakeoff:latest .
if errorlevel 1 exit /b 1
docker run --rm --network none -v "%~dp0tests\fixtures\private\phase3:/photos:ro" -v "%~dp0docs\logs\raw\phase-3\bakeoff:/results" enderchest-bakeoff:latest
exit /b %errorlevel%

:all
call :lint || exit /b 1
call :unit || exit /b 1
call :integration || exit /b 1
call :e2e || exit /b 1
echo Lint, unit, integration and end-to-end passed. Run "test.bat probes" for the Docker probes.
exit /b 0
