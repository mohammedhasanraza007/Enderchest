# Probe 6: `docker kill` during the write loop; restart; quick_check passes; no half-written record.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$rounds = 3
if (Reset-TestData) {
    $good = 0
    $detail = @()
    for ($i = 1; $i -le $rounds; $i++) {
        [void](Api -Method POST -Path '/api/v1/test/write-loop' -Body @{ seconds = 60 })
        Start-Sleep -Milliseconds (700 + 300 * $i)
        $mid = Get-Report
        [void](Dk kill $script:Container)
        [void](Start-TestStack)
        $state = Wait-State 'ok'
        $after = Get-Report
        $fine = ($state -and $after.consistent -and $after.quick_check -eq 'ok' -and $after.rows -ge $mid.rows)
        if ($fine) { $good++ }
        $detail += "round $i killed at ~$($mid.rows) rows, after restart rows=$($after.rows) consistent=$($after.consistent) quick_check=$($after.quick_check)"
    }
    $ok = Result 6 ($good -eq $rounds) ($detail -join '; ')
} else { [void](Result 6 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
