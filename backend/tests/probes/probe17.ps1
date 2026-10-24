# Probe 17 (Phase 1 gate 4): the name saved at first run survives a stop and a start. Browser
# tests cannot restart a container, so this probe does what stop.bat then run.bat do on the test
# stack: `docker compose stop`, then `up`, and reads the profile back. It also checks that a theme
# chosen before the stop is still the stored one afterwards, and (Phase 2, D-093) that first run
# resumes at step 2 after the restart and completes when step 2 is finished.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Api -Path '/api/v1/profile'
    $saved = Api -Method PUT -Path '/api/v1/profile' -Body @{ name = 'Mohammed'; timezone = 'Asia/Kolkata'; theme = 'dark' }
    [void](Dc stop)
    $stopped = ($script:LastExit -eq 0)
    $down = Api -Path '/health'                       # nothing answers while stopped
    [void](Start-TestStack)
    $state = Wait-State 'ok'
    $after = Api -Path '/api/v1/profile'
    $done = Api -Method PATCH -Path '/api/v1/settings' -Body @{ first_run_step = 'done' }
    $final = Api -Path '/api/v1/profile'
    $good = $stopped -and ($before.Json.first_run_complete -eq $false) -and ($saved.Status -eq 200) -and
            ($down.Status -eq 0) -and $state -and ($after.Json.name -eq 'Mohammed') -and
            ($after.Json.timezone -eq 'Asia/Kolkata') -and ($after.Json.theme -eq 'dark') -and
            ($after.Json.first_run_step -eq 'categories') -and ($done.Status -eq 200) -and
            ($final.Json.first_run_complete -eq $true)
    $ok = Result 17 $good "first run before=$($before.Json.first_run_complete); stopped=$stopped; unreachable while stopped=$($down.Status -eq 0); after start: name=$($after.Json.name) timezone=$($after.Json.timezone) theme=$($after.Json.theme) step=$($after.Json.first_run_step); after step 2: first_run_complete=$($final.Json.first_run_complete)"
} else { [void](Result 17 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
