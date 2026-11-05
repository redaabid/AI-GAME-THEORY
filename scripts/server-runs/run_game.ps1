param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$FirstName,
    [Parameter(Mandatory = $true)][string]$FirstAgent,
    [Parameter(Mandatory = $true)][string]$SecondName,
    [Parameter(Mandatory = $true)][string]$SecondAgent,
    [Parameter(Mandatory = $true)][int]$MaxPlies,
    [Parameter(Mandatory = $true)][string]$LogDir,
    [Parameter(Mandatory = $true)][string]$WorkDir,
    [int]$TimeoutSec = 900
)
# One server game: start server, connect FirstName then SecondName, wait, capture, close.
# LogDir is relative to the repository (bot logs); WorkDir gets timeline, run summary and screenshot.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$server = Join-Path $repo '.local\server'
if ([IO.Path]::IsPathRooted($LogDir) -or $LogDir -match '\s') { throw 'LogDir must be relative to the repository, without spaces.' }
New-Item -ItemType Directory -Force (Join-Path $repo $LogDir) | Out-Null
New-Item -ItemType Directory -Force $WorkDir | Out-Null
$work = (Resolve-Path -LiteralPath $WorkDir).Path

if (Get-Process -Name VampiresVSWerewolvesGameServer -ErrorAction SilentlyContinue) { throw 'A server is already running.' }
if (Get-NetTCPConnection -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 5555 is busy.' }

$serverProcess = Start-Process -FilePath (Join-Path $server 'VampiresVSWerewolvesGameServer.exe') -WorkingDirectory $server -PassThru
$deadline = (Get-Date).AddSeconds(20)
while (-not (Get-NetTCPConnection -LocalPort 5555 -State Listen -ErrorAction SilentlyContinue)) {
    if ((Get-Date) -gt $deadline) { throw 'Server did not listen on 5555.' }
    Start-Sleep -Milliseconds 200
}

function Start-Bot($name, $agent) {
    $log = "$LogDir\${Tag}_$name.txt"
    $command = "python main.py --name $name --agent $agent --max-plies $MaxPlies 127.0.0.1 5555 > $log 2>&1"
    $process = Start-Process -FilePath cmd.exe -ArgumentList '/c', $command -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    return @{ name = $name; process = $process; log = (Join-Path $repo $log); command = $command; offset = 0; partial = '' }
}

$timeline = New-Object System.Collections.Generic.List[string]
function Read-New($bot) {
    if (-not (Test-Path -LiteralPath $bot.log)) { return }
    $stream = [System.IO.File]::Open($bot.log, 'Open', 'Read', 'ReadWrite')
    try {
        if ($stream.Length -le $bot.offset) { return }
        [void]$stream.Seek($bot.offset, 'Begin')
        $buffer = New-Object byte[] ($stream.Length - $bot.offset)
        $read = $stream.Read($buffer, 0, $buffer.Length)
        $bot.offset += $read
    } finally { $stream.Dispose() }
    $text = $bot.partial + [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
    $parts = $text -split "`r?`n"
    $bot.partial = $parts[-1]
    $stamp = (Get-Date).ToString('HH:mm:ss.fff')
    foreach ($line in $parts[0..($parts.Count - 2)]) { $timeline.Add("$stamp $($bot.name): $line") }
}

$started = Get-Date
$first = Start-Bot $FirstName $FirstAgent
$connectDeadline = (Get-Date).AddSeconds(15)
while (-not ($timeline | Where-Object { $_ -like "*$($FirstName): *Connected to*" })) {
    Read-New $first
    if ((Get-Date) -gt $connectDeadline -or $first.process.HasExited) { break }
    Start-Sleep -Milliseconds 50
}
Start-Sleep -Milliseconds 1000
$second = Start-Bot $SecondName $SecondAgent
$bots = @($first, $second)

$timedOut = $false
while (-not ($first.process.HasExited -and $second.process.HasExited)) {
    foreach ($bot in $bots) { Read-New $bot }
    if (((Get-Date) - $started).TotalSeconds -gt $TimeoutSec) { $timedOut = $true; break }
    Start-Sleep -Milliseconds 50
}
foreach ($bot in $bots) { Read-New $bot; if ($bot.partial) { $timeline.Add("(final) $($bot.name): $($bot.partial)") } }
$ended = Get-Date
Start-Sleep -Milliseconds 1500

$capture = 'ok'
try { & (Join-Path $PSScriptRoot 'winshot.ps1') -ProcessId $serverProcess.Id -OutBase (Join-Path $work "${Tag}_final") | Out-Null }
catch { $capture = "failed: $_" }
# Any extra top-level window of the server (e.g. an end-of-game dialog).
Add-Type -AssemblyName UIAutomationClient
$condition = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::ProcessIdProperty), $serverProcess.Id
$windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
$windowNames = @($windows | ForEach-Object { $_.Current.Name })

if ($timedOut) {
    foreach ($bot in $bots) {
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $($bot.process.Id)" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $bot.process.Id -Force -ErrorAction SilentlyContinue
    }
}
$serverAlive = -not $serverProcess.HasExited
if ($serverAlive) {
    [void]$serverProcess.CloseMainWindow()
    if (-not $serverProcess.WaitForExit(5000)) { Stop-Process -Id $serverProcess.Id -Force }
}

$timeline | Out-File -FilePath (Join-Path $work "${Tag}_timeline.txt") -Encoding utf8
$summary = [ordered]@{
    tag = $Tag; maxPlies = $MaxPlies; first = $FirstName; second = $SecondName
    firstCommand = $first.command; secondCommand = $second.command
    firstExit = $(if ($first.process.HasExited) { $first.process.ExitCode } else { $null })
    secondExit = $(if ($second.process.HasExited) { $second.process.ExitCode } else { $null })
    started = $started.ToString('HH:mm:ss'); seconds = [math]::Round(($ended - $started).TotalSeconds, 1)
    timedOut = $timedOut; serverAliveAtEnd = $serverAlive; capture = $capture; serverWindows = $windowNames
} | ConvertTo-Json
# Tee-Object would write UTF-16 under powershell.exe -File; analyze.py reads UTF-8.
$summary | Out-File -FilePath (Join-Path $work "${Tag}_run.json") -Encoding utf8
$summary
