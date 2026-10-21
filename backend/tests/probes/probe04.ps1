# Probe 4: folder move. Copy the project to a differently named sibling, bring the stack up
# from the copy, data still there. Proves the pinned project name and pinned volume name.
# Default: the TEST stack. `-Live` runs the real build.bat and run.bat from the copy instead
# (that touches the live stack, so the owner runs it on purpose).
param([switch]$Live)
. "$PSScriptRoot\lib.ps1"
$ok = $false
$copy = Join-Path (Split-Path $script:Root -Parent) ('Enderchest-moved-' + [guid]::NewGuid().ToString('N').Substring(0, 6))

function Copy-Project {
    # Never rename the folder Claude works in: copy it, without git history or local data.
    $null = robocopy $script:Root $copy /E /XD .git node_modules .test-backups test-results private /XF .env /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { return $false }
    return $true
}

if ($Live) {
    if (-not (Copy-Project)) { [void](Result 4 $false 'copy failed'); exit 1 }
    Copy-Item (Join-Path $script:Root '.env') (Join-Path $copy '.env') -ErrorAction SilentlyContinue
    Push-Location $copy
    try {
        cmd /c build.bat | Out-Host
        $b = $LASTEXITCODE
        cmd /c run.bat | Out-Host
        $r = $LASTEXITCODE
    } finally { Pop-Location }
    $ok = Result 4 (($b -eq 0) -and ($r -eq 0)) "live stack from the copy: build.bat exit $b, run.bat exit $r (the owner checks the data by eye)"
} elseif (Reset-TestData) {
    $before = Write-Records -Seconds 2
    [void](Dc stop)   # free port 8471 for the copy
    if (Copy-Project) {
        $script:ComposeDir = $copy
        $script:NoProjectFlag = $true   # the copy's compose file must find the project by itself
        [void](Dc up -d --wait --wait-timeout 120)
        $up = ($script:LastExit -eq 0)
        [void](Wait-State 'ok')
        $after = Get-Report
        # (not named $project: PowerShell variables are case-insensitive and lib.ps1 owns $script:Project)
        $sameProject = Dk ps --filter "label=com.docker.compose.project=enderchest-test" --format '{{.Names}}'
        [void](Dc stop)
        $script:ComposeDir = $null
        $script:NoProjectFlag = $false
        $ok = Result 4 ($up -and (Same-Data $before $after)) "copy at $(Split-Path $copy -Leaf): up=$up; same project containers=[$sameProject]; records before=$($before.rows) after=$($after.rows)"
    } else { [void](Result 4 $false 'copy failed') }
    [void](Start-TestStack)
} else { [void](Result 4 $false 'could not start and reset the test stack') }

if (Test-Path $copy) { Remove-Item $copy -Recurse -Force -ErrorAction SilentlyContinue }
exit $(if ($ok) { 0 } else { 1 })
