# Used by build.bat and run.bat (D-148): gets Docker ready so a new user has nothing to set up.
# Installed but stopped: starts it and waits. Not installed: asks once, then installs Docker Desktop
# and WSL with winget. Exit 0 means Docker answers. It never touches a volume or any app data.
# ENDERCHEST_NO_INSTALL=1 (automation) only prints the manual steps.
param([switch]$StartOnly)

$desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$cli = Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'

function Say([string]$text) { [Console]::Out.WriteLine($text) }

function Manual-Steps {
    Say ''
    Say 'Docker Desktop is not installed. Enderchest runs inside it. To install it by hand:'
    Say '  1. Download it: https://www.docker.com/products/docker-desktop/'
    Say '  2. Run the installer with its default settings, and restart Windows if it asks.'
    Say '  3. Open Docker Desktop, wait until the engine is running, then run this again.'
}

function Wait-ForDocker {
    if (-not (Test-Path -LiteralPath $desktop)) { return $false }
    Say 'Starting Docker. This can take a few minutes the first time.'
    Say 'If Docker shows a terms screen, click Accept. If it asks you to sign in, a free account is enough.'
    Start-Process -FilePath $desktop
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline) {
        & $cli info *> $null
        if ($LASTEXITCODE -eq 0) {
            Say 'Docker is ready.'
            return $true
        }
        Start-Sleep -Seconds 5
    }
    Say 'Docker did not become ready within 5 minutes. Open Docker Desktop, see what it says, then run this again.'
    return $false
}

if ($env:ENDERCHEST_NO_INSTALL -eq '1') {
    if (-not $StartOnly) { Manual-Steps }
    exit 1
}
if (Test-Path -LiteralPath $cli) {
    if (Wait-ForDocker) { exit 0 }
    exit 1
}
if ($StartOnly) { exit 1 }

$virtual = (Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled
$hypervisor = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
if ($virtual -eq $false -and -not $hypervisor) {
    Say 'Virtualization is turned off in this PC''s BIOS, and Docker needs it. Turn it on (often called'
    Say 'Intel VT-x or AMD-V), then run this again. Nothing was changed on this computer.'
    exit 1
}
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Manual-Steps
    exit 1
}

Say ''
Say 'Enderchest needs Docker Desktop, which is free for personal use, and it is not on this PC.'
Say 'It is a large download. Windows will ask for permission, and it may need one restart.'
Say 'Install it now? Type Y and press Enter (anything else cancels):'
if ([Console]::In.ReadLine() -notmatch '^\s*[Yy]') {
    Say 'Cancelled. Nothing was changed on this computer.'
    Manual-Steps
    exit 1
}

Say 'Installing Docker Desktop. Please approve the Windows permission prompt if it appears.'
& winget install --exact --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
if (-not (Test-Path -LiteralPath $cli)) {
    Say "The Docker install did not finish (winget exit code $LASTEXITCODE)."
    Manual-Steps
    exit 1
}

& wsl.exe --status *> $null
if ($LASTEXITCODE -ne 0) {
    Say 'Installing WSL, which Docker needs. Please approve the Windows permission prompt.'
    Start-Process -FilePath wsl.exe -ArgumentList '--install', '--no-distribution' -Verb RunAs -Wait
    Say ''
    Say 'Almost done. Restart Windows, then double-click build.bat again. It carries on from here.'
    exit 1
}

if (Wait-ForDocker) { exit 0 }
Say 'If Docker asks for a restart, restart Windows, then double-click build.bat again.'
exit 1
