# Probe 1: write records, `docker compose stop`, `docker compose up -d`, data still there.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    if ($before.rows -gt 0) {
        [void](Dc stop)
        [void](Start-TestStack)
        [void](Wait-State 'ok')
        $after = Get-Report
        $ok = Result 1 (Same-Data $before $after) "records before=$($before.rows) after stop/up=$($after.rows), consistent=$($after.consistent), quick_check=$($after.quick_check)"
    } else { [void](Result 1 $false 'the write loop wrote nothing') }
} else { [void](Result 1 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
