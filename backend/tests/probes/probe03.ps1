# Probe 3: rebuild the image with --no-cache, start, data still there, and (from Phase 2) an
# item with its photo byte for byte the same. (Takes a few minutes.)
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    $item = Write-ItemWithPhoto
    $build = Dc build --no-cache app
    $built = ($script:LastExit -eq 0)
    [void](Start-TestStack)   # recreates the container from the new image
    [void](Wait-State 'ok')
    $after = Get-Report
    $kept = Test-ItemIntact $item
    $ok = Result 3 ($built -and (Same-Data $before $after) -and $kept) "no-cache build ok=$built; records before=$($before.rows) after=$($after.rows), consistent=$($after.consistent); item with photo intact=$kept"
    if (-not $built) { Write-Host $build }
} else { [void](Result 3 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
