# Probe 25 (Phase 6 gates 3 and 4, D-114): honest answers and no silent writes, in the real image.
# A one-off container on a new throwaway volume: no answer or page says "certain", "you own this"
# or "100%"; four checks change no item, draft or saving; savings without a positive typed price
# are refused; the totals equal the confirmed entries. The live volume is never named.
. "$PSScriptRoot\lib.ps1"
$name = 'enderchest-probe25'
$volume = 'enderchest_test_data_p25_' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$script = Join-Path $PSScriptRoot 'ownership_probe.py'

[void](Dk rm -f $name)
[void](Dk run -d --name $name --network none -e ENDERCHEST_ENV=test -e ENDERCHEST_PORT=8470 -v "${volume}:/data" enderchest-app-test:latest)
$started = $script:LastExit -eq 0
[void](Dk cp $script "${name}:/tmp/ownership_probe.py")
$out = Dk exec $name python /tmp/ownership_probe.py honest
$passed = $started -and $script:LastExit -eq 0
[void](Dk rm -f $name)
$ok = Result 25 $passed "honest and read-only: $out"
exit $(if ($ok) { 0 } else { 1 })
