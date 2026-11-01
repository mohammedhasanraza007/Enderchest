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
REM Before delayed expansion: it would eat a "!" in a folder or user name.
cd /d "%~dp0"
set "BACKUPDIR=%USERPROFILE%\Enderchest-Backups"
setlocal enabledelayedexpansion
echo Enderchest build. Safe to run again at any time; it never deletes anything.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed. Install Docker Desktop, then run build.bat again.
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running. Start Docker Desktop, wait until it says the engine is running, then run build.bat again.
  exit /b 1
)

REM Always !BACKUPDIR! in these blocks: a ")" in a user name would end a block if expanded early.
if not exist "!BACKUPDIR!" (
  mkdir "!BACKUPDIR!"
  if errorlevel 1 (
    echo Could not create the backup folder !BACKUPDIR!.
    exit /b 1
  )
  echo Created the backup folder !BACKUPDIR!
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
  echo The build failed. Nothing was deleted. Read the message above.
  exit /b 1
)
echo Build finished. Next: run.bat
exit /b 0
