$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
while (-not (Test-Path -LiteralPath 'tests-completed.json')) {
    if (-not (Get-Process -Id 18708 -ErrorAction SilentlyContinue)) { throw 'Verification stopped before completion.' }
    Start-Sleep -Seconds 1
}
$tests=Get-Content -LiteralPath 'tests-completed.json' -Raw | ConvertFrom-Json
if (-not $tests.success) { throw 'Tests failed; no matches launched.' }
& 'C:\Users\sebju\miniconda3\python.exe' -u -B validate_matches.py *> matches-live.log
@{exitCode=$LASTEXITCODE} | ConvertTo-Json | Set-Content -LiteralPath 'runner-exit.json' -Encoding utf8

