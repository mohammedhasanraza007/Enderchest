# Runs the Phase 0 gate probes (docs/DATA_SAFETY.md 10) against the TEST stack, one fresh
# PowerShell process per probe, and writes the results to test-results\probes.txt.
#   run-probes.ps1                run probes 1 to 14
#   run-probes.ps1 -Only 6,12     run only those
#   run-probes.ps1 -Live          probes 4 and 9 use the live build.bat/run.bat (the owner's choice)
param([int[]]$Only = @(), [switch]$Live)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$numbers = if ($Only.Count) { $Only } else { 1..14 }
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
