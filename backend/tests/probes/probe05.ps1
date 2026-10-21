# Probe 5: `docker compose rm -sf` (never `down`), then `up -d`, data still there.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    [void](Dc rm -sf)
    $gone = (Dk ps -a --filter "name=^$($script:Container)$" --format '{{.Names}}') -eq ''
    [void](Start-TestStack)
    [void](Wait-State 'ok')
    $after = Get-Report
    $ok = Result 5 ($gone -and (Same-Data $before $after)) "container removed=$gone; records before=$($before.rows) after=$($after.rows), consistent=$($after.consistent)"
} else { [void](Result 5 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
