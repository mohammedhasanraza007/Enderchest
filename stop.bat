@echo off
REM The work is in :main, so that every "exit /b" comes back here and a double-clicked window stays
REM open to show its message.
call :main %*
set "CODE=%errorlevel%"
call :hold
exit /b %CODE%

:hold
if not "%ENDERCHEST_NO_PAUSE%"=="1" pause
exit /b 0

:main
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
