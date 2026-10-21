@echo off
setlocal
cd /d "%~dp0"
REM Fast iteration on the TEST stack: source mounted, uvicorn reloads on every edit, port 8471.
REM It refuses to run against the live volume. Vite serves the frontend and proxies the API.

if /I "%ENDERCHEST_TEST_VOLUME%"=="enderchest_data" (
  echo Refusing to run: ENDERCHEST_TEST_VOLUME points at the live volume.
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, then run dev.bat again.
  exit /b 1
)
if not exist ".test-backups" mkdir ".test-backups"

echo Starting the TEST stack: the app at http://127.0.0.1:8471, the frontend at http://127.0.0.1:5173 (Ctrl+C to stop).
docker compose -f compose.test.yaml --profile dev up --build dev vite
exit /b %errorlevel%
