# Used by build.bat and run.bat: runs the script again with --inner, shows every line and saves it
# to a .txt log, and returns its exit code. The path comes through %ENDERCHEST_SELF% so that "&" and
# brackets in a folder name stay inside cmd's own quotes.
param([string]$Log)

New-Item -ItemType Directory -Force -Path (Split-Path -LiteralPath $Log) | Out-Null
$writer = New-Object IO.StreamWriter($Log, $false, (New-Object Text.UTF8Encoding $false))
$writer.AutoFlush = $true
$writer.WriteLine("Enderchest log, $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $([Environment]::OSVersion.VersionString)")
cmd /c 'call "%ENDERCHEST_SELF%" --inner 2>&1' | ForEach-Object {
    [Console]::Out.WriteLine($_)
    $writer.WriteLine($_)
}
$code = $LASTEXITCODE
$writer.WriteLine("Exit code: $code")
$writer.Close()
exit $code
