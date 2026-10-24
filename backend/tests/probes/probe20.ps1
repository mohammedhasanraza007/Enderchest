# Probe 20 (Phase 3 gate 3): the app works with the network disabled. A one-off container of the
# test image runs with `--network none` on a new throwaway volume each run (F-027), with Gemini at
# Google's real address: a photo is still read on this machine, and Gemini fails with a clear
# message that leaves the local result alone. The live volume is never named.
. "$PSScriptRoot\lib.ps1"
$name = 'enderchest-probe20'
$volume = 'enderchest_test_data_p20_' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$script = Join-Path $PSScriptRoot 'capture_probe.py'

[void](Dk rm -f $name)
[void](Dk run -d --name $name --network none -e ENDERCHEST_ENV=test -e ENDERCHEST_PORT=8470 -v "${volume}:/data" enderchest-app-test:latest)
$started = $script:LastExit -eq 0
[void](Dk cp $script "${name}:/tmp/capture_probe.py")
$out = Dk exec $name python /tmp/capture_probe.py offline
$passed = $started -and $script:LastExit -eq 0
[void](Dk rm -f $name)
$ok = Result 20 $passed "no network: $out"
exit $(if ($ok) { 0 } else { 1 })
