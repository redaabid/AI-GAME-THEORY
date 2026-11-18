$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python='C:\Users\sebju\miniconda3\python.exe'
$out=Join-Path $root 'wpf-run-2026-11-17'
if (Test-Path -LiteralPath $out) { throw 'Existing WPF run preserved.' }
New-Item -ItemType Directory -Path $out | Out-Null
$listener=Get-NetTCPConnection -LocalPort 5555 -State Listen
$server=Get-Process -Id $listener.OwningProcess
if ($server.ProcessName -ne 'VampiresVSWerewolvesGameServer') { throw 'Unexpected port owner.' }
$one=Start-Process -FilePath $python -ArgumentList @('-u','-B','main_candidate.py','--name','AB-Replies','--max-plies','200','127.0.0.1','5555') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $out 'ab.stdout.log') -RedirectStandardError (Join-Path $out 'ab.stderr.log') -PassThru
$connected=$false
for ($i=0;$i -lt 20;$i++) {
    if (Get-NetTCPConnection -LocalPort 5555 -State Established -ErrorAction SilentlyContinue | Where-Object {$_.OwningProcess -eq $server.Id}) {$connected=$true;break}
    if ($one.HasExited) { throw 'First bot exited before connection.' }
    Start-Sleep -Milliseconds 300
}
if (-not $connected) { throw 'First bot connection not confirmed.' }
$two=Start-Process -FilePath $python -ArgumentList @('-u','-B','main_v6.py','--name','MCTS-V6','--max-plies','200','127.0.0.1','5555') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $out 'mcts.stdout.log') -RedirectStandardError (Join-Path $out 'mcts.stderr.log') -PassThru
@{server=$server.Id;ab=$one.Id;mcts=$two.Id} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'pids.json') -Encoding utf8
$clock=[Diagnostics.Stopwatch]::StartNew()
while ((-not $one.HasExited -or -not $two.HasExited) -and $clock.Elapsed.TotalSeconds -lt 720) {
    Start-Sleep -Seconds 1
    $one.Refresh();$two.Refresh()
}
@{seconds=$clock.Elapsed.TotalSeconds;abExited=$one.HasExited;mctsExited=$two.HasExited;abExitCode=$(if($one.HasExited){$one.ExitCode}else{$null});mctsExitCode=$(if($two.HasExited){$two.ExitCode}else{$null})} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'completed.json') -Encoding utf8

