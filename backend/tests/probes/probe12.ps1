# Probe 12: localhost hardening over real HTTP. Wrong Host, missing X-Enderchest header,
# foreign Origin and text/plain bodies are refused; no CORS header appears on any response.
. "$PSScriptRoot\lib.ps1"
$ok = $false
if (Reset-TestData) {
    $checks = @()

    $r = Api -Path '/health' -Extra @('-H', 'Host: evil.example:8471')
    $checks += [pscustomobject]@{ Name = 'wrong Host'; Pass = ($r.Status -eq 403 -and $r.Json.error.code -eq 'forbidden_host') }

    $r = Api -Method POST -Path '/api/v1/backups' -NoHeader
    $checks += [pscustomobject]@{ Name = 'no X-Enderchest header'; Pass = ($r.Status -eq 403 -and $r.Json.error.code -eq 'forbidden_host') }

    $r = Api -Method POST -Path '/api/v1/backups' -Extra @('-H', 'Origin: http://evil.example')
    $checks += [pscustomobject]@{ Name = 'foreign Origin'; Pass = ($r.Status -eq 403 -and $r.Json.error.code -eq 'forbidden_host') }

    $r = Api -Method POST -Path '/api/v1/boot/start-empty' -Body '{"confirm":"START EMPTY"}' -RawBody -Extra @('-H', 'Content-Type: text/plain')
    $checks += [pscustomobject]@{ Name = 'text/plain body'; Pass = ($r.Status -eq 422 -and $r.Json.error.code -eq 'validation_error') }

    # Nothing above may have made a backup.
    $listing = Api -Path '/api/v1/backups'
    $checks += [pscustomobject]@{ Name = 'refused requests changed nothing'; Pass = ($listing.Json.items.Count -eq 0) }

    # No CORS header on any response, including a cross-origin preflight and a refusal.
    $base = "http://127.0.0.1:$($script:Port)"
    $dump = @()   # flat list of header lines from four different requests
    $dump += & curl.exe -s -D - -o NUL "$base/health"
    $dump += & curl.exe -s -D - -o NUL -H 'Origin: http://evil.example' "$base/api/v1/boot"
    $dump += & curl.exe -s -D - -o NUL -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: POST' "$base/api/v1/backups"
    $dump += & curl.exe -s -D - -o NUL -H 'Host: evil.example' "$base/health"
    $statusLines = @($dump | Where-Object { $_ -match '^HTTP/' })
    $cors = @($dump | Where-Object { $_ -match '^(?i)access-control-' })
    $checks += [pscustomobject]@{ Name = 'no CORS headers'; Pass = ($statusLines.Count -eq 4) -and ($cors.Count -eq 0) }

    $failed = @($checks | Where-Object { -not $_.Pass } | ForEach-Object { $_.Name })
    $ok = Result 12 ($failed.Count -eq 0) $(if ($failed.Count) { "failed: $($failed -join ', ')" } else { "all $($checks.Count) checks refused or clean as required" })
} else { [void](Result 12 $false 'could not start and reset the test stack') }
exit $(if ($ok) { 0 } else { 1 })
