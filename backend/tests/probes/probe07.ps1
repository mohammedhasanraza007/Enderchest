# Probe 7: volume detached. Run the image with NO volume; it must answer locked / no_data_volume
# and create nothing under /data.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$name = 'enderchest-probe7'
$port = 8472
[void](Dk rm -f $name)
[void](Dk run -d --name $name -p "127.0.0.1:${port}:8470" -e ENDERCHEST_ENV=test -e "ENDERCHEST_PORT=$port" enderchest-app:latest)
if ($script:LastExit -eq 0) {
    $health = Wait-State 'locked' -P $port -Timeout 40
    $listing = (Dk exec $name ls -A /data)
    $created = if ($script:LastExit -eq 0) { $listing.Trim() } else { 'cannot list' }
    $api = Api -Path '/api/v1/backups' -P $port
    $ok = Result 7 ($health -and $health.reason -eq 'no_data_volume' -and $created -eq '' -and $api.Status -eq 503) "state=$($health.status)/$($health.reason); /data contents=[$created]; API status $($api.Status)"
} else { [void](Result 7 $false 'could not start the container without a volume') }
[void](Dk rm -f $name)
exit $(if ($ok) { 0 } else { 1 })
