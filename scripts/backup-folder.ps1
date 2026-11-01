# Used by build.bat: reads the backup folder from .env (UTF-8, so any user name is safe), refuses an
# empty value or the placeholder of .env.example, and makes the folder if it is missing.
$line = [IO.File]::ReadAllLines((Join-Path $PWD '.env'), [Text.Encoding]::UTF8) |
    Where-Object { $_ -match '^\s*ENDERCHEST_BACKUP_DIR=' } | Select-Object -First 1
$folder = if ($line) { ($line -split '=', 2)[1].Trim().Trim('"', "'") } else { '' }
if (-not $folder -or $folder -match 'YOUR_NAME') {
    Write-Output "The backup folder in .env is not set: ENDERCHEST_BACKUP_DIR=$folder"
    Write-Output 'Put a real folder there, or delete .env and run build.bat again to get the default.'
    exit 1
}
try {
    if (-not (Test-Path -LiteralPath $folder)) {
        New-Item -ItemType Directory -Force -Path $folder -ErrorAction Stop | Out-Null
        Write-Output "Created the backup folder $folder"
    }
} catch {
    Write-Output "Could not create the backup folder $folder : $($_.Exception.Message)"
    exit 1
}
exit 0
