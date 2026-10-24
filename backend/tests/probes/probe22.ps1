# Probe 22 (Phase 4 gate 1 and 2, F-019): reminders are reconciled, never fired, so real restarts
# and a clock that moves forward and back create no duplicates and lose nothing.
#   1. day D (today on the test clock): an item expiring on D+2 and a task due D+1; one row;
#   2. the container restarts (its start-up reconcile runs on the real clock, day D), then the
#      test clock moves to D+1: the task's row appears, the expiry row is the same row;
#   3. restart again (the clock is back at D: the task's row is superseded), then D+3: the item
#      has expired (an `expired` row; the old `expiry_soon` superseded) and the task's row is
#      the SAME row reopened, two days overdue;
#   4. every dedupe key has exactly one row, and a reconcile run twice changes nothing.
. "$PSScriptRoot\lib.ps1"
$ok = $false

function Set-Day { param([string]$Day)
    return (Api -Method POST -Path '/api/v1/test/clock' -Body @{ local_date = $Day })
}
function All-Rows { return @((Api -Path '/api/v1/notifications?status=all&limit=200').Json.items) }
function Restart-App {
    [void](Dk restart $script:Container)
    return [bool](Wait-State 'ok' -Timeout 90)
}

if (Reset-TestData) {
    [void](Api -Method PUT -Path '/api/v1/profile' -Body @{ name = 'Probe'; timezone = 'UTC' })
    $today = (Api -Path '/api/v1/test/clock').Json.local_date
    $d0 = [datetime]::ParseExact($today, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $day = { param([int]$n) $d0.AddDays($n).ToString('yyyy-MM-dd') }
    [void](Set-Day (& $day 0))
    $item = Api -Method POST -Path '/api/v1/items' -Body @{ name = 'Probe milk'; expiry_date = (& $day 2) }
    $task = Api -Method POST -Path '/api/v1/tasks' -Body @{ title = 'Probe chore'; first_due = (& $day 1); interval_days = 7 }
    $step1 = All-Rows
    $firstId = if ($step1.Count -eq 1) { $step1[0].id } else { -1 }

    $up1 = Restart-App
    [void](Set-Day (& $day 1))
    $step2 = All-Rows
    $soon2 = @($step2 | Where-Object { $_.kind -eq 'expiry_soon' })
    $task2 = @($step2 | Where-Object { $_.kind -eq 'task_due' -and $_.status -eq 'open' })

    $up2 = Restart-App            # start-up reconcile on the real clock: day D, the task is not due
    $back = @(All-Rows | Where-Object { $_.kind -eq 'task_due' })
    [void](Set-Day (& $day 3))
    $step3 = All-Rows
    $expired = @($step3 | Where-Object { $_.kind -eq 'expired' -and $_.status -eq 'open' })
    $soon3 = @($step3 | Where-Object { $_.kind -eq 'expiry_soon' })
    $task3 = @($step3 | Where-Object { $_.kind -eq 'task_due' })
    $keys = $step3 | ForEach-Object { "$($_.kind)|$($_.item.public_id)|$($_.task.id)|$($_.due_date)" }
    $unique = (@($keys | Select-Object -Unique).Count -eq $keys.Count)
    $again = All-Rows
    $stable = (($again | ConvertTo-Json -Depth 6) -eq ($step3 | ConvertTo-Json -Depth 6))

    $good = ($item.Status -eq 201) -and ($task.Status -eq 201) -and ($step1.Count -eq 1) -and
        $up1 -and $up2 -and ($soon2.Count -eq 1) -and ($soon2[0].id -eq $firstId) -and ($task2.Count -eq 1) -and
        ($back.Count -eq 1) -and ($back[0].resolution -eq 'superseded') -and
        ($expired.Count -eq 1) -and ($soon3.Count -eq 1) -and ($soon3[0].resolution -eq 'superseded') -and
        ($task3.Count -eq 1) -and ($task3[0].id -eq $task2[0].id) -and ($task3[0].status -eq 'open') -and
        ($task3[0].word -eq '2 days overdue') -and ($step3.Count -eq 3) -and $unique -and $stable
    $ok = Result 22 $good "day D rows=$($step1.Count); after restart + D+1: expiry_soon same row=$($soon2.Count -eq 1 -and $soon2[0].id -eq $firstId), task rows=$($task2.Count); after restart (real clock D): task row=$($back[0].resolution); at D+3: expired=$($expired.Count), old expiry_soon=$($soon3[0].resolution), task row reopened=$($task3[0].id -eq $task2[0].id) '$($task3[0].word)'; rows=$($step3.Count), keys unique=$unique, second read unchanged=$stable"
    [void](Api -Method POST -Path '/api/v1/test/reset')
} else { [void](Result 22 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
