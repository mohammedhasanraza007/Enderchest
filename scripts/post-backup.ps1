# Used by backup.bat: POST /api/v1/backups with the safety header, print what happened.
param([int]$Port = 8470)

try {
    # PowerShell sends a bodiless POST as a form; the API accepts JSON only, so say so explicitly.
    $result = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/api/v1/backups" `
        -Headers @{ 'X-Enderchest' = '1' } -ContentType 'application/json' -Body '{}' -TimeoutSec 300
    $kb = [Math]::Max(1, [Math]::Round($result.bytes / 1024))
    Write-Output "Backup made and verified: $($result.name).sqlite3 ($kb KB)"
    Write-Output "Folder: $($result.folder_hint)"
    exit 0
} catch {
    $message = $_.ErrorDetails.Message
    if ($message) {
        try { $message = ($message | ConvertFrom-Json).error.message } catch { }
    } else { $message = $_.Exception.Message }
    Write-Output "No backup was made. $message"
    exit 1
}
