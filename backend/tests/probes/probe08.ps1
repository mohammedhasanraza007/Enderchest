# Probe 8: delete the database file in the TEST volume with a backup present: the recovery page
# appears, restore works, data matches.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    $backup = Api -Method POST -Path '/api/v1/backups'
    if ($backup.Status -eq 201) {
        $deleted = Api -Method POST -Path '/api/v1/test/delete-db'
        $boot = (Api -Path '/api/v1/boot').Json
        $page = (& curl.exe -s "http://127.0.0.1:$($script:Port)/") -join ''
        $recoveryPage = ($page -match 'Enderchest') -and ($page -notmatch 'Foundation status')  # the boot page, not the status page
        $restore = Api -Method POST -Path '/api/v1/boot/restore' -Body @{ name = $backup.Json.name; confirm = 'RESTORE' }
        $health = Wait-State 'ok'
        $after = Get-Report
        $ok = Result 8 (($deleted.Json.state -eq 'recovery') -and ($boot.backups.Count -ge 1) -and $recoveryPage -and ($restore.Status -eq 200) -and $health -and (Same-Data $before $after)) "after delete state=$($deleted.Json.state); backups offered=$($boot.backups.Count); restore status=$($restore.Status); records before=$($before.rows) after=$($after.rows)"
    } else { [void](Result 8 $false "could not make a backup: $($backup.Text)") }
} else { [void](Result 8 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
