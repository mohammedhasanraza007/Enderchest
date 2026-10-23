# Runs the Phase 0 gate probes (docs/DATA_SAFETY.md 10) against the TEST stack, one fresh
# PowerShell process per probe, and writes the results to test-results\probes.txt.
# Probes 15 to 18 are not DATA_SAFETY gate probes (D-083): 15 runs the real backup.bat helper
# script, 16 moves the test clock and checks an idle database is not backed up again, 17 checks
# that the first-run name survives a stop and a start (Phase 1 gate 4), 18 checks that dev.bat's
# Vite sees an edit made on Windows, 19 checks that a test build never retags the live image.
#   run-probes.ps1                run probes 1 to 19
#   run-probes.ps1 -Only "6,12"   run only those
#   run-probes.ps1 -Live          probes 4 and 9 use the live build.bat/run.bat (the owner's choice)
param([string]$Only = '', [switch]$Live)   # -Only is a string: "6,12" (powershell -File does not build arrays)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$numbers = if ($Only) { @($Only -split ',' | ForEach-Object { [int]$_ }) } else { 1..19 }
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
