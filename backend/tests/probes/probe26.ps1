# Probe 26 (Phase 7 gates 2 and 3): /health stays under 200 ms while coach frames are read back to back, and a frame is never stored.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$script = Join-Path $PSScriptRoot 'coach_probe.py'
if (Reset-TestData) {
    [void](Dk cp $script "$($script:Container):/tmp/coach_probe.py")
    $out = Dk exec $script:Container python /tmp/coach_probe.py health
    $ok = Result 26 ($script:LastExit -eq 0) "coach frames: $out"
} else { [void](Result 26 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
