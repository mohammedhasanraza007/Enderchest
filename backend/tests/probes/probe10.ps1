# Probe 10: set meta.schema_version higher in a TEST database and start the app on it:
# locked / newer_data, and the database file is byte-for-byte untouched by that start.
# Uses its own throwaway test volume (enderchest_test_data_p10); it is kept, never removed.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$env:ENDERCHEST_TEST_VOLUME = 'enderchest_test_data_p10'
$env:ENDERCHEST_TEST_PORT = '8474'
$script:Project = 'enderchest-test-p10'
$script:Container = 'enderchest-test-p10-app-1'
$port = 8474
$vol = 'enderchest_test_data_p10'

function Hash-Db { return ((Dk run --rm -v "${vol}:/data" enderchest-app:latest sha256sum /data/db/enderchest.sqlite3) -split '\s+')[0] }

[void](Dc up -d --wait --wait-timeout 120)
if ((Wait-State 'ok' -P $port)) {
    # Single quotes only: Windows PowerShell 5.1 mangles embedded double quotes in native arguments.
    $py = "import sqlite3; c=sqlite3.connect('/data/db/enderchest.sqlite3'); c.execute('UPDATE meta SET value=? WHERE key=?',('99','schema_version')); c.commit(); c.close()"
    [void](Dk exec $script:Container python -c $py)
    [void](Dc stop)               # a clean stop checkpoints the WAL, so the file is stable
    $hash1 = Hash-Db
    [void](Dc up -d --wait --wait-timeout 120)
    $health = Wait-State 'locked' -P $port -Timeout 60
    $api = Api -Path '/api/v1/backups' -P $port
    [void](Dc stop)
    $hash2 = Hash-Db
    $ok = Result 10 ($health -and $health.reason -eq 'newer_data' -and $health.schema_found -eq 99 -and $api.Status -eq 503 -and $hash1 -and $hash1 -eq $hash2) "state=$($health.status)/$($health.reason) schema_found=$($health.schema_found); API $($api.Status); file hash unchanged=$($hash1 -eq $hash2)"
} else { [void](Result 10 $false 'the throwaway test stack did not start') }
exit $(if ($ok) { 0 } else { 1 })
