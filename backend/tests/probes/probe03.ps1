# Probe 3: rebuild the image with --no-cache, start, data still there. (Takes a few minutes.)
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    $build = Dc build --no-cache app
    $built = ($script:LastExit -eq 0)
    [void](Start-TestStack)   # recreates the container from the new image
    [void](Wait-State 'ok')
    $after = Get-Report
    $ok = Result 3 ($built -and (Same-Data $before $after)) "no-cache build ok=$built; records before=$($before.rows) after=$($after.rows), consistent=$($after.consistent)"
    if (-not $built) { Write-Host $build }
} else { [void](Result 3 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
