# Probe 14: interrupted backup. `docker kill` in the middle of a backup; after restart no
# `.partial` file is listed as a backup, and the next backup succeeds.
# The database is made large first so the backup takes long enough to interrupt. The probe
# reports whether a `.partial` was actually seen after a kill (proof of a mid-backup kill).
. "$PSScriptRoot\lib.ps1"
$ok = $false
$hostBackups = Join-Path $script:Root '.test-backups'
$attempts = 8

if (Reset-TestData) {
    # About 400k small rows (tens of MB) in scheduler_state, written by the app user in one go.
    $py = "import sqlite3; c=sqlite3.connect('/data/db/enderchest.sqlite3'); c.execute('BEGIN'); c.executemany('INSERT INTO scheduler_state VALUES (?,?)', ((f'p14:{i:07d}', 'x'*60) for i in range(400000))); c.commit(); c.close()"
    [void](Dk exec $script:Container python -c $py)
    $seenPartial = $false
    $listedPartial = $false
    for ($i = 1; $i -le $attempts -and -not $seenPartial; $i++) {
        $job = Start-Job -ScriptBlock { param($p) & curl.exe -s -m 120 -X POST -H 'X-Enderchest: 1' "http://127.0.0.1:$p/api/v1/backups" } -ArgumentList $script:Port
        Start-Sleep -Milliseconds (150 * $i)
        [void](Dk kill $script:Container)
        Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue
        if (Get-ChildItem $hostBackups -Filter '*.partial' -ErrorAction SilentlyContinue) { $seenPartial = $true }
        $stagePartial = Dk run --rm -v enderchest_test_data:/data enderchest-app:latest sh -c 'ls /data/backup-staging'
        if ($stagePartial -match 'partial') { $seenPartial = $true }
        [void](Start-TestStack)
        [void](Wait-State 'ok')
    }
    $listing = Api -Path '/api/v1/backups'
    $listedPartial = [bool]($listing.Json.items | Where-Object { $_.name -match 'partial' })
    $leftover = [bool](Get-ChildItem $hostBackups -Filter '*.partial' -ErrorAction SilentlyContinue)
    $next = Api -Method POST -Path '/api/v1/backups'
    $good = (-not $listedPartial) -and (-not $leftover) -and ($next.Status -eq 201)
    $ok = Result 14 $good "kills=$($i - 1); a .partial was seen after a kill=$seenPartial; listed as backup=$listedPartial; left after restart=$leftover; next backup status=$($next.Status)"
    if (-not $seenPartial) { Write-Host 'NOTE: no kill landed mid-copy in this run, so the partial-handling path was not exercised here (unit tests cover it).' }
} else { [void](Result 14 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
