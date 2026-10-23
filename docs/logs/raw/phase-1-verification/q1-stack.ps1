# Phase 1 verification Q1 (and Phase 0 cold start and SIGTERM timing): a brand-new TEST volume.
# Project enderchest-test-q1, port 8475, its own empty backup folder. Never the live stack.
# Usage: q1-stack.ps1 up | restart | status
param([Parameter(Mandatory)][ValidateSet('up', 'restart', 'status')][string]$Step)

$root = Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')
$state = Join-Path $root 'test-results\q1-volume.txt'
if (-not (Test-Path $state)) {
    'enderchest_test_data_q1_' + (Get-Date -Format 'yyyyMMddHHmmss') | Set-Content -Encoding ascii $state
}
$env:ENDERCHEST_TEST_VOLUME = (Get-Content $state).Trim()
$env:ENDERCHEST_TEST_PORT = '8475'
$backups = Join-Path $root 'test-results\q1-backups'
New-Item -ItemType Directory -Force $backups | Out-Null
$env:ENDERCHEST_TEST_BACKUP_DIR = $backups -replace '\\', '/'
$dc = @('compose', '-p', 'enderchest-test-q1', '-f', (Join-Path $root 'compose.test.yaml'))

function Health {
    try { Invoke-RestMethod -TimeoutSec 2 -Headers @{ Host = '127.0.0.1:8475' } 'http://127.0.0.1:8475/health' } catch { $null }
}

function Wait-Ok([datetime]$from) {
    while (((Get-Date) - $from).TotalSeconds -lt 90) {
        $h = Health
        if ($h -and $h.status -eq 'ok') { return [math]::Round(((Get-Date) - $from).TotalSeconds, 1) }
        Start-Sleep -Milliseconds 250
    }
    return -1
}

"volume $env:ENDERCHEST_TEST_VOLUME, backup folder $backups ($((Get-ChildItem $backups).Count) files)"
switch ($Step) {
    'up' {
        $t = Get-Date
        & docker @dc up -d app 2>&1 | ForEach-Object { "  $_" }
        "seconds from 'up' to state ok (new database): $(Wait-Ok $t)"
    }
    'restart' {
        $stop = Measure-Command { & docker @dc stop app 2>&1 | Out-Null }
        "seconds for 'docker compose stop' (SIGTERM to exit): $([math]::Round($stop.TotalSeconds, 1))"
        $id = (& docker @dc ps -a -q app)
        "exit code after stop: $(& docker inspect -f '{{.State.ExitCode}}' $id)"
        "last log lines:"; & docker logs --tail 4 $id 2>&1 | ForEach-Object { "  $_" }
        $t = Get-Date
        & docker @dc start app 2>&1 | Out-Null
        "seconds from 'start' to state ok (existing database): $(Wait-Ok $t)"
    }
}
$h = Health
"health: status=$($h.status) reason=$($h.reason) schema=$($h.schema_found)"
"profile: $(Invoke-RestMethod -Headers @{ Host = '127.0.0.1:8475' } 'http://127.0.0.1:8475/api/v1/profile' | ConvertTo-Json -Compress)"
