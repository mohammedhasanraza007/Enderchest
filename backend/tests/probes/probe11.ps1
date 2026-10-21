# Probe 11: backup round trip as the non-root user. A backup appears in the host folder, is
# verified, restores into a FRESH test volume, and the photo file matches by SHA-256.
# Before Phase 2 there are no app photos: a real file is written into /data/photos as the app
# user to prove the photo mirror (this is a file-level check, not an upload check).
. "$PSScriptRoot\lib.ps1"
$ok = $false
# A new volume name per run so the volume is genuinely fresh. Volumes are never deleted by the
# probes (the guard forbids it), so each run leaves one tiny test volume behind.
$fresh = 'enderchest_test_data_p11_' + (Get-Date -Format 'yyyyMMddHHmmss')
$freshPort = 8473
$hostBackups = Join-Path $script:Root '.test-backups'

if (Reset-TestData) {
    $uid = (Dk exec $script:Container id -u).Trim()
    $before = Write-Records -Seconds 2
    $photoText = 'probe-11-photo-bytes-' + [guid]::NewGuid().ToString('N')
    [void](Dk exec $script:Container sh -c "printf '%s' $photoText > /data/photos/probe11.jpg")
    $srcHash = ((Dk exec $script:Container sha256sum /data/photos/probe11.jpg) -split '\s+')[0]

    $backup = Api -Method POST -Path '/api/v1/backups'
    $hostFile = if ($backup.Json) { Join-Path $hostBackups "$($backup.Json.name).sqlite3" } else { '' }
    $onHost = ($hostFile -ne '') -and (Test-Path $hostFile) -and ((Get-Item $hostFile).Length -eq $backup.Json.bytes)
    $hostPhoto = Test-Path (Join-Path $hostBackups 'photos\probe11.jpg')
    $noPartial = -not (Get-ChildItem $hostBackups -Filter '*.partial' -ErrorAction SilentlyContinue)

    # A fresh volume: its own project, port and volume name; the same backup folder.
    $env:ENDERCHEST_TEST_VOLUME = $fresh
    $env:ENDERCHEST_TEST_PORT = "$freshPort"
    $script:Project = 'enderchest-test-p11'
    [void](Dc up -d --wait --wait-timeout 120)
    $recovery = Wait-State 'recovery' -P $freshPort -Timeout 60
    $restore = Api -Method POST -Path '/api/v1/boot/restore' -P $freshPort -Body @{ name = $backup.Json.name; confirm = 'RESTORE' }
    $health = Wait-State 'ok' -P $freshPort -Timeout 60
    $report = (Api -Path '/api/v1/test/write-loop' -P $freshPort).Json
    $dstHash = ((Dk exec 'enderchest-test-p11-app-1' sha256sum /data/photos/probe11.jpg) -split '\s+')[0]
    [void](Dc stop)

    $good = ($uid -eq '10001') -and ($backup.Status -eq 201) -and $onHost -and $hostPhoto -and $noPartial -and $recovery -and ($restore.Status -eq 200) -and $health -and (Same-Data $before $report) -and ($srcHash -ne '') -and ($srcHash -eq $dstHash)
    $ok = Result 11 $good "app uid=$uid; backup on host=$onHost; photo mirrored=$hostPhoto; fresh volume state=recovery:$([bool]$recovery); restore status=$($restore.Status); records before=$($before.rows) after=$($report.rows); photo sha256 equal=$($srcHash -eq $dstHash)"
} else { [void](Result 11 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
