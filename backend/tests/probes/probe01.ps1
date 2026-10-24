# Probe 1: write records and (from Phase 2) an item with a photo, `docker compose stop`,
# `docker compose up -d`, data still there and the photo byte for byte the same.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    $item = Write-ItemWithPhoto
    if ($before.rows -gt 0 -and $item) {
        [void](Dc stop)
        [void](Start-TestStack)
        [void](Wait-State 'ok')
        $after = Get-Report
        $kept = Test-ItemIntact $item
        $ok = Result 1 ((Same-Data $before $after) -and $kept) "records before=$($before.rows) after stop/up=$($after.rows), consistent=$($after.consistent), quick_check=$($after.quick_check); item $($item.PublicId) with photo intact=$kept"
    } else { [void](Result 1 $false "the write loop wrote $($before.rows) rows; item with photo made=$([bool]$item)") }
} else { [void](Result 1 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
