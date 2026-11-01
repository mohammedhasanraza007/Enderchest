# Runs the Phase 0 gate probes (docs/DATA_SAFETY.md 10) against the TEST stack, one fresh
# PowerShell process per probe, and writes the results to test-results\probes.txt.
# Probes 15 to 18 are not DATA_SAFETY gate probes (D-083): 15 runs the real backup.bat helper
# script, 16 moves the test clock and checks an idle database is not backed up again, 17 checks
# that the first-run name survives a stop and a start (Phase 1 gate 4), 18 checks that dev.bat's
# Vite sees an edit made on Windows, 19 checks that a test build never retags the live image.
# Probes 20 and 21 are Phase 3 gates: 20 reads a photo with the network disabled (gate 3), 21
# times /health while readings queue (gate 5). Probes 22 and 23 are Phase 4 gates: 22 restarts the
# container and moves the test clock forward and back (no duplicate or lost reminder), 23 sends ten
# browser-notification claims at once (exactly one wins). Probes 24 and 25 are Phase 6 gates;
# 26 and 27 are Phase 7 gates: /health under coach frames (none stored), ten frames at once.
# 28 is a Phase 9 gate: the assistant sends only its tools' rows and changes nothing.
# 29 is the final UX test: build.bat works from any folder for any Windows user name (D-142).
#   run-probes.ps1                run probes 1 to 29
#   run-probes.ps1 -Only "6,12"   run only those
#   run-probes.ps1 -Live          probes 4 and 9 use the live build.bat/run.bat (the owner's choice)
param([string]$Only = '', [switch]$Live)   # -Only is a string: "6,12" (powershell -File does not build arrays)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$env:ENDERCHEST_NO_PAUSE = '1'    # the .bat files otherwise wait for a key
$env:ENDERCHEST_NO_INSTALL = '1'  # and they otherwise offer to install or start Docker
$numbers = if ($Only) { @($Only -split ',' | ForEach-Object { [int]$_ }) } else { 1..29 }
$out = Join-Path $root 'test-results'
New-Item -ItemType Directory -Force $out | Out-Null
New-Item -ItemType Directory -Force (Join-Path $root '.test-backups') | Out-Null

$lines = @("Enderchest Phase 0 probes, $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$failed = @()
foreach ($n in $numbers) {
    $file = Join-Path $PSScriptRoot ('probe{0:D2}.ps1' -f $n)
    Write-Host "--- probe $n ---"
    $extra = if ($Live -and ($n -eq 4 -or $n -eq 9)) { @('-Live') } else { @() }
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $file @extra 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    $lines += $output
    if ($code -ne 0) { $failed += $n }
}
$lines += $(if ($failed.Count) { "FAILED: $($failed -join ', ')" } else { "ALL PASSED: $($numbers -join ', ')" })
$lines | Set-Content (Join-Path $out 'probes.txt') -Encoding utf8
Write-Host $lines[-1]
exit $(if ($failed.Count) { 1 } else { 0 })
