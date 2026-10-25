# Probe 27 (Phase 7 gates 2 and 3): ten coach frames at once: one is read, the rest are refused at once.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$script = Join-Path $PSScriptRoot 'coach_probe.py'
if (Reset-TestData) {
    [void](Dk cp $script "$($script:Container):/tmp/coach_probe.py")
    $out = Dk exec $script:Container python /tmp/coach_probe.py burst
    $ok = Result 27 ($script:LastExit -eq 0) "coach frames: $out"
} else { [void](Result 27 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
