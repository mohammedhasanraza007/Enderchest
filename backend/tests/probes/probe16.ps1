# Probe 16 (Phase 0 verification, V9): an idle database must not be backed up again just because
# time passes. Every backup writes its own backup_log row after it starts; if that write counts as
# "the database changed", the "changed" rule (DATA_SAFETY 7) would fire every hour for ever.
#   1. one manual backup is the newest good backup;
#   2. the TEST clock moves 90 minutes on (never across 03:00 UTC, which would make the daily
#      rule fire for a legitimate reason) and two scheduler ticks pass: NO new auto backup;
#   3. control: a real write (the test write loop), then the same wait: one auto backup, so the
#      rule does work when data changed and the scheduler really was running.
. "$PSScriptRoot\lib.ps1"
$ok = $false

function Auto-Count {
    $listing = Api -Path '/api/v1/backups'
    return @($listing.Json.items | Where-Object { $_.kind -eq 'auto' }).Count
}
function Wait-ForAuto {
    param([int]$Above, [int]$Seconds = 80)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if ((Auto-Count) -gt $Above) { return $true }
        Start-Sleep -Seconds 5
    }
    return $false
}
function Set-Clock { param([datetime]$Moment)
    return (Api -Method POST -Path '/api/v1/test/clock' -Body @{ now = $Moment.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') })
}

if (Reset-TestData) {
    $first = Api -Method POST -Path '/api/v1/backups'
    $stamp = ($first.Json.name -replace '^manual-', '')
    $last = [datetime]::ParseExact($stamp, 'yyyyMMddTHHmmssZ', [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::AssumeUniversal -bor [Globalization.DateTimeStyles]::AdjustToUniversal)

    # Pick a clock target that cannot trigger the daily rule (clock >= 03:00 and last < 03:00).
    $target = $null
    foreach ($minutes in 90, 61) {
        $candidate = $last.AddMinutes($minutes)
        $threeAm = $candidate.Date.AddHours(3)
        if (-not (($candidate -ge $threeAm) -and ($last -lt $threeAm))) { $target = $candidate; break }
    }
    if ($null -eq $target) {
        $ok = Result 16 $false "NOT RUN: the time of day ($($last.ToString('HH:mm'))Z) would let the daily rule fire; rerun outside 01:30 to 03:00 UTC"
    } else {
        [void](Set-Clock $target)
        $before = Auto-Count
        $idleBackup = Wait-ForAuto -Above $before
        $afterIdle = Auto-Count

        # Control: a real change, then the same wait. The write loop's rows are written by the
        # app at real time; the clock is already far enough ahead for "old enough" and "quiet".
        [void](Api -Method POST -Path '/api/v1/test/write-loop' -Body @{ seconds = 1 })
        Start-Sleep -Seconds 3
        $controlBackup = Wait-ForAuto -Above $afterIdle

        $logText = Dk logs $script:Container   # one string; split it into lines before searching
        $reasons = (($logText -split "`n") | Where-Object { $_ -match '"event": "backup_due"' } |
            ForEach-Object { ($_ -replace '.*"reason": "([a-z]+)".*', '$1') }) -join ','
        [void](Set-Clock ([datetime]::UtcNow))   # put the clock back on real time
        $good = (-not $idleBackup) -and $controlBackup
        $detail = "baseline $($first.Json.name); clock moved to $($target.ToString('HH:mm'))Z; auto backups on an idle database after two ticks: $($afterIdle - $before); " +
                  "after a real write: control backup made=$controlBackup; backup_due reasons in the log=[$reasons]"
        $ok = Result 16 $good $detail
    }
} else { [void](Result 16 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
