# Probe 24 (Phase 6, CLAUDE.md 6): the ownership check never sends the inventory anywhere. A
# one-off container of the test image runs with `--network none` on a new throwaway volume, with
# Gemini's address pointed at a recorder inside the container and a key set, Gemini on `auto` and
# photo sharing on: text and photo checks reach the recorder zero times and answer offline, while
# Test connection reaches it (the recorder works). The live volume is never named.
. "$PSScriptRoot\lib.ps1"
$name = 'enderchest-probe24'
$volume = 'enderchest_test_data_p24_' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$script = Join-Path $PSScriptRoot 'ownership_probe.py'

[void](Dk rm -f $name)
[void](Dk run -d --name $name --network none -e ENDERCHEST_ENV=test -e ENDERCHEST_PORT=8470 -e ENDERCHEST_GEMINI_URL=http://127.0.0.1:9911/v1beta -v "${volume}:/data" enderchest-app-test:latest)
$started = $script:LastExit -eq 0
[void](Dk cp $script "${name}:/tmp/ownership_probe.py")
$out = Dk exec $name python /tmp/ownership_probe.py private
$passed = $started -and $script:LastExit -eq 0
[void](Dk rm -f $name)
$ok = Result 24 $passed "no inventory leaves: $out"
exit $(if ($ok) { 0 } else { 1 })
