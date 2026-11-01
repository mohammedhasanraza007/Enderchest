@echo off
REM The work is in :main, so that every "exit /b" comes back here and a double-clicked window stays
REM open to show its message.
call :main %*
set "CODE=%errorlevel%"
call :hold
exit /b %CODE%

:hold
if defined ENDERCHEST_NO_PAUSE exit /b 0
setlocal enabledelayedexpansion
for %%A in (!cmdcmdline!) do if /i "%%~A"=="/c" set "DOUBLE_CLICKED=1"
if defined DOUBLE_CLICKED pause
endlocal
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
