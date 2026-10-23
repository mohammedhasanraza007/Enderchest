# Probe 18 (dev.bat): an edit made on Windows reaches the dev stack. Vite and uvicorn watch the
# bind-mounted source; file events from a Windows folder do not reach a Linux container, so the
# watchers must poll. The probe brings up the dev services the way dev.bat does, writes a
# throwaway module under frontend/src, changes it, and needs Vite to serve the new text. The
# module is deleted afterwards and the normal test app is started again.
. "$PSScriptRoot\lib.ps1"
$ok = $false
$module = Join-Path $script:Root 'frontend\src\probe18-watch.ts'
$url = 'http://127.0.0.1:5173/src/probe18-watch.ts'

function Served {
    $text = & curl.exe -s -m 10 $url 2>$null
    return ($text -join "`n")
}

try {
    [void](Dc stop app app-nobackups)                    # the dev app takes the test port 8471
    [IO.File]::WriteAllText($module, "export const probe18 = `"first`";`n")
    [void](Dc --profile dev up -d --build dev vite)
    $up = ($script:LastExit -eq 0)
    $deadline = (Get-Date).AddSeconds(120)
    do { $first = Served; if ($first -match 'first') { break }; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline)
    $before = $first -match 'first'

    [IO.File]::WriteAllText($module, "export const probe18 = `"second`";`n")
    $deadline = (Get-Date).AddSeconds(15)
    do { $now = Served; if ($now -match 'second') { break }; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline)
    $after = $now -match 'second'

    $ok = Result 18 ($up -and $before -and $after) "dev services up=$up; first version served=$before; edit served within 15 s=$after"
} finally {
    Remove-Item $module -Force -ErrorAction SilentlyContinue
    [void](Dc --profile dev stop dev vite)
    [void](Start-TestStack)
}
exit $(if ($ok) { 0 } else { 1 })
