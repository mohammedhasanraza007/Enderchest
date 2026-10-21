@echo off
setlocal
cd /d "%~dp0"
REM Stop only. Never "down": that would remove the container and invite mistakes with volumes.
docker compose stop
if errorlevel 1 (
  echo Could not stop Enderchest. Is Docker Desktop running?
  exit /b 1
)
echo Enderchest stopped. Your data is untouched. Start it again with run.bat
exit /b 0
