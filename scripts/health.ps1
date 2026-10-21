# Used by run.bat and restore.bat. Prints the app's boot state (starting, ok, recovery, locked,
# failed) and, when it is not ok, a one-line reason. Exit code 0 when the app answered.
param([int]$Port = 8470, [int]$WaitSeconds = 60)

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$health = $null
do {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
        if ($health.status -ne 'starting') { break }
    } catch { $health = $null }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

if ($null -eq $health) { Write-Output 'unreachable'; exit 1 }
if ($health.reason) { Write-Output "$($health.status) $($health.reason)" } else { Write-Output $health.status }
exit 0
