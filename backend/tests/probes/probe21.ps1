# Probe 21 (Phase 3 gate 5): /health stays under 200 ms while OCR runs, and readings queued at
# once wait their turn without failing. Three drafts are made at the same moment on the test
# stack; /health is timed from inside the app container every 50 ms until all are read.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$script = Join-Path $PSScriptRoot 'capture_probe.py'
if (Reset-TestData) {
    [void](Dk cp $script "$($script:Container):/tmp/capture_probe.py")
    $out = Dk exec $script:Container python /tmp/capture_probe.py health
    $ok = Result 21 ($script:LastExit -eq 0) "readings queued at once: $out"
} else { [void](Result 21 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
