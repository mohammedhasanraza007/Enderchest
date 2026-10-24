# Probe 23 (Phase 4 gate 8, D-107): the browser-notification claim is atomic in the real server.
# Ten requests to POST /notifications/{id}/shown arrive at the same moment (as two tabs and a
# reload could send them): exactly one answers {"claimed": true}, the rest {"claimed": false},
# and the count no longer lists the row as unshown.
. "$PSScriptRoot\lib.ps1"
$ok = $false
Add-Type -AssemblyName System.Net.Http

if (Reset-TestData) {
    [void](Api -Method PUT -Path '/api/v1/profile' -Body @{ name = 'Probe'; timezone = 'UTC' })
    $today = (Api -Path '/api/v1/test/clock').Json.local_date
    $task = Api -Method POST -Path '/api/v1/tasks' -Body @{ title = 'Probe chore'; first_due = $today }
    $before = (Api -Path '/api/v1/notifications/count').Json
    $id = if (@($before.unshown).Count -eq 1) { $before.unshown[0].id } else { -1 }

    $client = New-Object System.Net.Http.HttpClient
    $url = "http://127.0.0.1:$($script:Port)/api/v1/notifications/$id/shown"
    $sent = 1..10 | ForEach-Object {
        $message = New-Object System.Net.Http.HttpRequestMessage ([System.Net.Http.HttpMethod]::Post), $url
        $message.Headers.Add('X-Enderchest', '1')
        $client.SendAsync($message)
    }
    [System.Threading.Tasks.Task]::WaitAll([System.Threading.Tasks.Task[]]$sent)
    $answers = $sent | ForEach-Object { ($_.Result.Content.ReadAsStringAsync().Result | ConvertFrom-Json).claimed }
    $statuses = $sent | ForEach-Object { [int]$_.Result.StatusCode }
    $client.Dispose()
    $claimed = @($answers | Where-Object { $_ -eq $true }).Count
    $refused = @($answers | Where-Object { $_ -eq $false }).Count
    $after = (Api -Path '/api/v1/notifications/count').Json

    $good = ($task.Status -eq 201) -and ($id -gt 0) -and (@($statuses | Where-Object { $_ -ne 200 }).Count -eq 0) -and
        ($claimed -eq 1) -and ($refused -eq 9) -and (@($after.unshown).Count -eq 0) -and ($after.open -eq 1)
    $ok = Result 23 $good "row $id unshown before=$(@($before.unshown).Count); 10 concurrent claims: claimed=$claimed not claimed=$refused, all HTTP 200=$((@($statuses | Where-Object { $_ -ne 200 }).Count -eq 0)); unshown after=$(@($after.unshown).Count), still open=$($after.open)"
    [void](Api -Method POST -Path '/api/v1/test/reset')
} else { [void](Result 23 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
