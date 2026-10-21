# Probe 9: build three times in a row, then start three times: no error, no data change.
# Default: the TEST stack. `-Live` runs the real build.bat x3 and run.bat x3 (touches the live
# stack, so the owner runs it on purpose; the owner compares the status page before and after).
param([switch]$Live)
. "$PSScriptRoot\lib.ps1"
$ok = $false
if ($Live) {
    $codes = @()
    Push-Location $script:Root
    try {
        1..3 | ForEach-Object { cmd /c build.bat | Out-Host; $codes += "build:$LASTEXITCODE" }
        1..3 | ForEach-Object { cmd /c run.bat | Out-Host; $codes += "run:$LASTEXITCODE" }
    } finally { Pop-Location }
    $bad = @($codes | Where-Object { $_ -notmatch ':0$' })
    $ok = Result 9 ($bad.Count -eq 0) "live: $($codes -join ' ')"
} elseif (Reset-TestData) {
    $before = Write-Records -Seconds 2
    $codes = @()
    1..3 | ForEach-Object { [void](Dc build app); $codes += "build:$($script:LastExit)" }
    1..3 | ForEach-Object { [void](Dc up -d --wait --wait-timeout 120); $codes += "up:$($script:LastExit)" }
    [void](Wait-State 'ok')
    $after = Get-Report
    $bad = @($codes | Where-Object { $_ -notmatch ':0$' })
    $ok = Result 9 (($bad.Count -eq 0) -and (Same-Data $before $after)) "test stack: $($codes -join ' '); records before=$($before.rows) after=$($after.rows)"
} else { [void](Result 9 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
