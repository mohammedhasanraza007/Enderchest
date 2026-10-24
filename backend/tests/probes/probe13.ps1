# Probe 13: marker mismatch, both directions. A live-configured app on a test-marked database
# refuses, and a test-configured app on a live-marked database refuses. Both leave the file as it was.
# Uses one-off containers on test volumes only: enderchest_test_data (test marker) and a new
# throwaway enderchest_test_data_p13_<random> each run (live marker; a reused one would hold an
# older phase's database that waits for a pre-migration backup). The live volume is never named.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$a = 'enderchest-probe13a'; $b = 'enderchest-probe13b'; $c = 'enderchest-probe13c'
$portA = 8475; $portB = 8476
$p13 = 'enderchest_test_data_p13_' + [guid]::NewGuid().ToString('N').Substring(0, 6)

function Hash-Db {
    param([string]$Volume)
    return ((Dk run --rm -v "${Volume}:/data" enderchest-app-test:latest sha256sum /data/db/enderchest.sqlite3) -split '\s+')[0]
}

if (Reset-TestData) {
    [void](Dc stop)   # release the data lock, so the marker check is what refuses
    $hashTest1 = Hash-Db 'enderchest_test_data'

    # Direction 1: LIVE config on the TEST-marked volume.
    [void](Dk rm -f $a)
    [void](Dk run -d --name $a -p "127.0.0.1:${portA}:8470" -e ENDERCHEST_ENV=live -e "ENDERCHEST_PORT=$portA" -v enderchest_test_data:/data enderchest-app-test:latest)
    $h1 = Wait-State 'locked' -P $portA -Timeout 40
    [void](Dk rm -f $a)
    $hashTest2 = Hash-Db 'enderchest_test_data'

    # Direction 2: make a LIVE-marked database on a throwaway volume, then start TEST config on it.
    [void](Dk rm -f $b $c)
    [void](Dk run -d --name $b -p "127.0.0.1:${portB}:8470" -e ENDERCHEST_ENV=live -e "ENDERCHEST_PORT=$portB" -v "${p13}:/data" enderchest-app-test:latest)
    $made = Wait-State 'ok' -P $portB -Timeout 40
    [void](Dk stop $b); [void](Dk rm -f $b)
    $hashLive1 = Hash-Db $p13
    [void](Dk run -d --name $c -p "127.0.0.1:${portB}:8470" -e ENDERCHEST_ENV=test -e "ENDERCHEST_PORT=$portB" -v "${p13}:/data" enderchest-app-test:latest)
    $h2 = Wait-State 'locked' -P $portB -Timeout 40
    [void](Dk rm -f $c)
    $hashLive2 = Hash-Db $p13

    $good = $h1 -and $h1.reason -eq 'env_mismatch' -and $h2 -and $h2.reason -eq 'env_mismatch' -and $made -and ($hashTest1 -eq $hashTest2) -and ($hashLive1 -eq $hashLive2)
    $ok = Result 13 $good "live config on test data: $($h1.status)/$($h1.reason); test config on live-marked data: $($h2.status)/$($h2.reason); files unchanged: test=$($hashTest1 -eq $hashTest2) live-marked=$($hashLive1 -eq $hashLive2)"
    [void](Start-TestStack)
} else { [void](Result 13 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
