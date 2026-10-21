# Probe 2: remove the container (docker rm -f), start again, data still there.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $before = Write-Records -Seconds 2
    [void](Dk rm -f $script:Container)
    $removed = (Dk ps -a --filter "name=^$($script:Container)$" --format '{{.Names}}') -eq ''
    [void](Start-TestStack)
    [void](Wait-State 'ok')
    $after = Get-Report
    $ok = Result 2 ($removed -and (Same-Data $before $after)) "container removed=$removed; records before=$($before.rows) after=$($after.rows), consistent=$($after.consistent)"
} else { [void](Result 2 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
