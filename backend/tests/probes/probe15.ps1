# Probe 15: the real script behind backup.bat. scripts\post-backup.ps1 runs against the TEST stack
# and must print the backup's name, exit 0, and leave a new manual-* file in the test backup
# folder that the API also lists. Probes 1 to 14 post with curl, so none of them could see a
# script that the security middleware refuses (found in the Phase 0 verification, F-1).
# It never calls backup.bat itself: that reads .env and would talk to the LIVE port.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$hostBackups = Join-Path $script:Root '.test-backups'
if (Reset-TestData) {
    $before = @(Get-ChildItem $hostBackups -Filter 'manual-*.sqlite3' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    $helper = Join-Path $script:Root 'scripts\post-backup.ps1'
    $output = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $helper -Port $script:Port 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    $after = @(Get-ChildItem $hostBackups -Filter 'manual-*.sqlite3' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    $new = @($after | Where-Object { $before -notcontains $_ })
    $printed = $new.Count -eq 1 -and (($output -join ' ') -like "*$($new[0])*")
    $listing = Api -Path '/api/v1/backups'
    $listed = $new.Count -eq 1 -and [bool]($listing.Json.items | Where-Object { "$($_.name).sqlite3" -eq $new[0] })
    $good = ($code -eq 0) -and ($new.Count -eq 1) -and $printed -and $listed
    $ok = Result 15 $good "script exit=$code; new manual files=$($new.Count); name printed=$printed; listed by the API=$listed; output=[$($output -join ' | ')]"
} else { [void](Result 15 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
