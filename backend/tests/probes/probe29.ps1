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
    # An .exe: a batch file that runs a .cmd without "call" would never come back from it.
    Add-Type -TypeDefinition 'public class P { public static int Main() { return 0; } }' `
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
    $ok = ($code -eq 0) -and $made -and $noBom -and $named
    [void](Result 29 $ok "build.bat exit $code, backup folder made: $made, .env UTF-8 no BOM: $noBom, names the folder: $named")
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
