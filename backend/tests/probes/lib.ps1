# Shared helpers for the Phase 0 gate probes (docs/DATA_SAFETY.md 10).
# Probes run on the Windows host with PowerShell, curl.exe and Docker only. They talk to the
# TEST stack (project enderchest-test, port 8471). They never touch the live volume and never
# call down -v, volume rm or prune: the deny rules in .claude/settings.json forbid those.

$ErrorActionPreference = 'Continue'
$script:Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$script:Project = 'enderchest-test'
$script:Port = 8471
$script:Container = 'enderchest-test-app-1'
$script:LastExit = 0

function Dk {
    # Run docker, return its combined output as one string; exit code in $script:LastExit.
    $out = & docker @args 2>&1 | ForEach-Object { "$_" }
    $script:LastExit = $LASTEXITCODE
    return ($out -join "`n")
}

function Dc {
    # docker compose against the test stack, from the project root (or $script:ComposeDir).
    $dir = if ($script:ComposeDir) { $script:ComposeDir } else { $script:Root }
    # Probe 4 leaves the project name out on purpose, to prove the file pins it.
    $project = if ($script:NoProjectFlag) { @() } else { @('-p', $script:Project) }
    Push-Location $dir
    try {
        $out = & docker compose @project -f compose.test.yaml @args 2>&1 | ForEach-Object { "$_" }
        $script:LastExit = $LASTEXITCODE
    } finally { Pop-Location }
    return ($out -join "`n")
}

function Api {
    param([string]$Method = 'GET', [string]$Path, $Body = $null, [int]$P = $script:Port,
          [string[]]$Extra = @(), [switch]$NoHeader, [switch]$RawBody)
    $url = "http://127.0.0.1:$P$Path"
    $curlArgs = @('-s', '-S', '-m', '180', '-X', $Method, '-w', "`n%{http_code}") + $Extra
    $tmp = $null
    if ($Method -ne 'GET' -and -not $NoHeader) {
        $curlArgs += @('-H', 'X-Enderchest: 1')
    }
    if ($null -ne $Body) {
        $tmp = [IO.Path]::GetTempFileName()
        $payload = if ($RawBody) { [string]$Body } else { $Body | ConvertTo-Json -Compress }
        [IO.File]::WriteAllText($tmp, $payload)
        if (-not $RawBody) { $curlArgs += @('-H', 'Content-Type: application/json') }
        $curlArgs += @('--data-binary', "@$tmp")
    }
    $raw = & curl.exe @curlArgs $url 2>&1 | ForEach-Object { "$_" }
    if ($tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    $lines = @($raw)
    $status = 0
    if ($lines.Count -gt 0) { [void][int]::TryParse($lines[-1], [ref]$status) }
    $text = ($lines | Select-Object -First ([Math]::Max(0, $lines.Count - 1))) -join "`n"
    $json = $null
    try { $json = $text | ConvertFrom-Json } catch { }
    return [pscustomobject]@{ Status = $status; Text = $text; Json = $json }
}

function Wait-State {
    param([string]$State, [int]$P = $script:Port, [int]$Timeout = 90)
    $deadline = (Get-Date).AddSeconds($Timeout)
    do {
        $r = Api -Path '/health' -P $P
        if ($r.Json -and $r.Json.status -eq $State) { return $r.Json }
        Start-Sleep -Milliseconds 700
    } while ((Get-Date) -lt $deadline)
    return $null
}

function Start-TestStack {
    [void](Dc up -d --wait --wait-timeout 120)
    return ($script:LastExit -eq 0)
}

function Reset-TestData {
    # POST /test/reset: wipes the TEST database, photos and test backups; never a volume.
    if (-not (Start-TestStack)) { return $false }
    if (-not (Wait-State 'ok')) { return $false }
    $r = Api -Method POST -Path '/api/v1/test/reset'
    return ($r.Status -eq 200)
}

function Write-Records {
    # Run the test write loop to completion and return the report.
    param([int]$Seconds = 2)
    [void](Api -Method POST -Path '/api/v1/test/write-loop' -Body @{ seconds = $Seconds })
    Start-Sleep -Seconds ($Seconds + 1)
    return (Api -Path '/api/v1/test/write-loop').Json
}

function Get-Report { return (Api -Path '/api/v1/test/write-loop').Json }

function Same-Data {
    param($Before, $After)
    return ($After -and $After.consistent -and $After.quick_check -eq 'ok' -and
            $After.rows -eq $Before.rows -and $After.counter -eq $Before.counter)
}

$script:Results = @()
function Result {
    param([int]$Number, [bool]$Ok, [string]$Detail)
    $verdict = if ($Ok) { 'PASS' } else { 'FAIL' }
    $line = "PROBE ${Number}: $verdict - $Detail"
    Write-Host $line
    $script:Results += $line
    return $Ok
}
