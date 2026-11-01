# Probe 29 (final UX test, D-142): the install drive, the folder and the Windows user name are
# free. The real build.bat runs from the temp folder on the system drive (the repo is usually on
# another), in a folder with spaces and brackets, for a user whose name has a bracket and a
# non-English letter. `docker` is a stand-in earlier on PATH, so nothing here reaches Docker or
# names a real volume. It must finish, make the backup folder, and write a .env that is UTF-8
# without a BOM and names that folder.
. "$PSScriptRoot\lib.ps1"
$base = Join-Path ([IO.Path]::GetTempPath()) ('enderchest-p29-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
$folder = Join-Path $base 'Ender Test (x86) Co'
$user = Join-Path $base ('user (work) Jos' + [char]0xE9)
$stand = Join-Path $base 'stand-in'
$ok = $false
$savedProfile = $env:USERPROFILE
$savedPath = $env:PATH
try {
    foreach ($dir in @($folder, $user, $stand)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item -LiteralPath (Join-Path $script:Root 'build.bat') -Destination $folder
    New-Item -ItemType Directory -Force -Path (Join-Path $folder 'scripts') | Out-Null
    foreach ($helper in 'logged.ps1', 'backup-folder.ps1', 'install-docker.ps1') {
        Copy-Item -LiteralPath (Join-Path $script:Root "scripts\$helper") -Destination (Join-Path $folder 'scripts')
    }
    # An .exe: a batch file that runs a .cmd without "call" would never come back from it.
    Add-Type -TypeDefinition 'public class P { public static int Main() { return System.Environment.GetEnvironmentVariable("STAND_IN_FAILS") == "1" ? 1 : 0; } }' `
        -OutputAssembly (Join-Path $stand 'docker.exe') -OutputType ConsoleApplication
    $env:USERPROFILE = $user
    $env:PATH = "$stand;$savedPath"
    $bat = Join-Path $folder 'build.bat'
    $output = cmd /c "`"$bat`" 2>&1"
    $code = $LASTEXITCODE
    $env:USERPROFILE = $savedProfile
    $env:PATH = $savedPath
    $output | ForEach-Object { Write-Host $_ }

    $backups = Join-Path $user 'Enderchest-Backups'
    $envFile = Join-Path $folder '.env'
    $made = Test-Path -LiteralPath $backups
    $text = ''
    $noBom = $false
    if (Test-Path -LiteralPath $envFile) {
        $bytes = [IO.File]::ReadAllBytes($envFile)
        $noBom = -not ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
        $text = (New-Object Text.UTF8Encoding($false, $true)).GetString($bytes)
    }
    $wanted = 'ENDERCHEST_BACKUP_DIR=' + ($backups -replace '\\', '/')
    $named = ($text -split "`r?`n") -contains $wanted

    # D-143: a failure keeps a double-clicked window open and keeps its exit code. A piped line
    # stands in for the key, and `cmd /c` looks like a double click to the script.
    $env:USERPROFILE = $user
    $env:PATH = "$stand;$savedPath"
    $env:STAND_IN_FAILS = '1'
    Remove-Item Env:ENDERCHEST_NO_PAUSE -ErrorAction SilentlyContinue
    $failed = 'y' | cmd /c "`"$bat`" 2>&1"
    $failCode = $LASTEXITCODE
    $env:ENDERCHEST_NO_PAUSE = '1'
    $quiet = cmd /c "`"$bat`" 2>&1"
    $quietCode = $LASTEXITCODE
    Remove-Item Env:STAND_IN_FAILS
    $env:USERPROFILE = $savedProfile
    $env:PATH = $savedPath
    $failedText = $failed -join ' '
    $quietText = $quiet -join ' '
    $held = ($failCode -eq 1) -and ($failedText -match 'Docker is not running') -and ($failedText -match 'Press any key')
    $free = ($quietCode -eq 1) -and ($quietText -match 'Docker is not running') -and ($quietText -notmatch 'Press any key')

    # D-145: every run leaves a .txt log holding the failure; the .env.example placeholder is refused.
    $logs = @(Get-ChildItem -LiteralPath (Join-Path $folder 'logs') -Filter 'build-*.txt' -ErrorAction SilentlyContinue)
    $logged = ($logs | Where-Object { (Get-Content -LiteralPath $_.FullName -Raw) -match 'Docker is not running' }).Count -ge 1
    Set-Content -LiteralPath $envFile -Value "ENDERCHEST_PORT=8470`nENDERCHEST_BACKUP_DIR=C:/Users/YOUR_NAME/Enderchest-Backups" -Encoding ascii
    $env:PATH = "$stand;$savedPath"
    $placeholder = cmd /c "`"$bat`" 2>&1"
    $placeholderCode = $LASTEXITCODE
    $env:PATH = $savedPath
    $refused = ($placeholderCode -eq 1) -and (($placeholder -join ' ') -match 'not set')

    # D-147: with no Docker at all, each script says so instead of "not running".
    Copy-Item -LiteralPath (Join-Path $script:Root 'run.bat') -Destination $folder
    $env:PATH = "$env:SystemRoot\system32;$env:SystemRoot\system32\WindowsPowerShell\v1.0"
    $noDockerBuild = (cmd /c "`"$bat`" 2>&1") -join ' '
    $noDockerRun = (cmd /c "`"$(Join-Path $folder 'run.bat')`" 2>&1") -join ' '
    $env:PATH = $savedPath
    $absent = ($noDockerBuild -match 'docker-desktop') -and ($noDockerRun -match 'not installed') -and ($noDockerRun -notmatch 'not running')
    $refused = $refused -and $absent

    $ok = ($code -eq 0) -and $made -and $noBom -and $named -and $held -and $free -and $logged -and $refused
    [void](Result 29 $ok "build.bat exit $code, backup folder made: $made, .env UTF-8 no BOM: $noBom, names the folder: $named; on failure the window waits: $held, and not when told: $free; log kept: $logged; placeholder refused: $refused")
}
catch {
    [void](Result 29 $false "error: $_")
}
finally {
    $env:USERPROFILE = $savedProfile
    $env:PATH = $savedPath
    Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction SilentlyContinue
}
exit $(if ($ok) { 0 } else { 1 })
