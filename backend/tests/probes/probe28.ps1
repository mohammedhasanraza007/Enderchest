# Probe 28 (Phase 9, D-134): the assistant sends Gemini only the question and its tools' rows,
# and changes nothing. A one-off container of the test image runs with `--network none` on a new
# throwaway volume, with Gemini's address pointed at a recorder inside the container that plays a
# function call: the rows carry only the six allowed fields, never notes, prices, attributes or an
# unmatched item, and the database is unchanged. The live volume is never named.
. "$PSScriptRoot\lib.ps1"
$name = 'enderchest-probe28'
$volume = 'enderchest_test_data_p28_' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$script = Join-Path $PSScriptRoot 'assistant_probe.py'

[void](Dk rm -f $name)
[void](Dk run -d --name $name --network none -e ENDERCHEST_ENV=test -e ENDERCHEST_PORT=8470 -e ENDERCHEST_GEMINI_URL=http://127.0.0.1:9911/v1beta -v "${volume}:/data" enderchest-app-test:latest)
$started = $script:LastExit -eq 0
[void](Dk cp $script "${name}:/tmp/assistant_probe.py")
$out = Dk exec $name python /tmp/assistant_probe.py
$passed = $started -and $script:LastExit -eq 0
[void](Dk rm -f $name)
$ok = Result 28 $passed "only the rows leave: $out"
exit $(if ($ok) { 0 } else { 1 })
