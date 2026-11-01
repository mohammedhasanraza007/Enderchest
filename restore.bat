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
REM Before delayed expansion: it would eat a "!" in the folder name.
cd /d "%~dp0"
setlocal enabledelayedexpansion
echo Enderchest restore.
echo Your current data is copied to a safety backup first. Old files are moved aside, never deleted.
echo.

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, then run restore.bat again.
  exit /b 1
)
if not exist ".env" (
  echo There is no .env file. Run build.bat first.
  exit /b 1
)

set "PORT=8470"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if "%%A"=="ENDERCHEST_PORT" set "PORT=%%B"
)

echo Backups found:
set "COUNT=0"
for /f "usebackq tokens=1-5 delims=|" %%A in (`docker compose run --rm --no-deps -T app python -m app.backup.cli list`) do (
  set /a COUNT+=1
  set "NAME[%%A]=%%B"
  set /a "KB=(%%E+512)/1024"
  echo   %%A. %%D  %%C  !KB! KB  [%%B]
)
if "%COUNT%"=="0" (
  echo   none found. Nothing can be restored.
  exit /b 1
)

echo.
set "CHOICE="
set /p "CHOICE=Number of the backup to restore (anything else cancels): "
if not defined NAME[%CHOICE%] (
  echo Cancelled. Nothing was changed.
  exit /b 1
)
set "PICKED=!NAME[%CHOICE%]!"
echo You chose: !PICKED!
set "CONFIRM="
set /p "CONFIRM=Type RESTORE (capital letters) to continue: "
if not "!CONFIRM!"=="RESTORE" (
  echo Cancelled. Nothing was changed.
  exit /b 1
)

docker compose stop
if errorlevel 1 (
  echo Could not stop Enderchest. Nothing was changed.
  exit /b 1
)
docker compose run --rm --no-deps -T app python -m app.backup.cli restore !PICKED!
if errorlevel 1 (
  echo The restore did not complete. Read the message above. Your previous data was not deleted.
  exit /b 1
)
docker compose up -d --wait --wait-timeout 120
if errorlevel 1 (
  echo The restore finished but Enderchest did not start cleanly. Restart Docker Desktop, then run run.bat.
  exit /b 1
)
set "STATE=unreachable"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\health.ps1" -Port %PORT%`) do set "STATE=%%S"
echo Restore finished. Enderchest state: !STATE!
start "" "http://127.0.0.1:%PORT%"
exit /b 0
