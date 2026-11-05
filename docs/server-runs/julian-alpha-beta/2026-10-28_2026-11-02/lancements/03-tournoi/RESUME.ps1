$ErrorActionPreference = 'Stop'
$launch = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'launch.json') -Raw | ConvertFrom-Json
$active = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -like '*screen_ab2_round_robin.py*' -and
    $_.CommandLine -like '*2026-10-29-round-robin*'
}
if ($active) { throw 'Campaign is already running; no second process started.' }
if (Test-Path -LiteralPath (Join-Path $launch.output 'completed.json')) {
    Write-Output 'Campaign already complete. Read SUMMARY.md.'
    exit
}
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$taskArguments = @($launch.arguments) + '--resume'
$process = Start-Process -FilePath $launch.python -ArgumentList $taskArguments -WorkingDirectory $launch.working_directory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot "resume-$stamp.stdout.log") -RedirectStandardError (Join-Path $PSScriptRoot "resume-$stamp.stderr.log") -PassThru
Write-Output "Resumed campaign, PID $($process.Id). Saved games will be skipped."

