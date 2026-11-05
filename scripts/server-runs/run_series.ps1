param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [ValidateSet('thetrap.xml', 'testmap2.xml')][string[]]$Maps = @('thetrap.xml', 'testmap2.xml'),
    [int[]]$MaxPlays = @(40, 200),
    [string]$LogDir = "docs\server-runs\$(Get-Date -Format yyyy-MM-dd)",
    [string]$WorkDir
)
# For each MaxPlays and map: prepare the server, then play AlphaBeta against MCTS, OEP and
# Baseline in both connection orders. Defaults replay the full 24-game series.
# Games whose run summary already exists in WorkDir are skipped, so a stopped series resumes.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Archive = (Resolve-Path -LiteralPath $Archive).Path
$config = Join-Path $repo '.local\server\VampiresVSWerewolvesGameServer.exe.config'
if (-not $WorkDir) { $WorkDir = Join-Path $repo ".local\server-runs\$(Split-Path -Leaf $LogDir)" }
New-Item -ItemType Directory -Force $WorkDir | Out-Null

$opponents = @(@('MCTS', 'mcts'), @('OEP', 'oep'), @('Baseline', 'baseline'))
foreach ($plays in $MaxPlays) {
    foreach ($map in $Maps) {
        $mapTag = [IO.Path]::GetFileNameWithoutExtension($map)
        Push-Location $repo
        try {
            python scripts/setup_server.py $Archive --map $map --force
            if ($LASTEXITCODE) { throw 'setup_server.py failed' }
            python -I (Join-Path $PSScriptRoot 'set_config.py') $config MaxGameDuration=00:10:00 "MaxPlays=$plays"
            if ($LASTEXITCODE) { throw 'set_config.py failed' }
        } finally { Pop-Location }

        foreach ($opponent in $opponents) {
            $orders = @(
                @('AlphaBeta', 'alphabeta', $opponent[0], $opponent[1]),
                @($opponent[0], $opponent[1], 'AlphaBeta', 'alphabeta')
            )
            foreach ($o in $orders) {
                $tag = "p${plays}_${mapTag}_$($o[0])-then-$($o[2])"
                if (Test-Path (Join-Path $WorkDir "${tag}_run.json")) { "skip $tag"; continue }
                "=== $tag  $(Get-Date -Format HH:mm:ss)"
                & (Join-Path $PSScriptRoot 'run_game.ps1') -Tag $tag -FirstName $o[0] -FirstAgent $o[1] -SecondName $o[2] -SecondAgent $o[3] `
                    -MaxPlies $plays -LogDir $LogDir -WorkDir $WorkDir -TimeoutSec 900
                Start-Sleep -Seconds 2
            }
        }
        "series p$plays $mapTag done $(Get-Date -Format HH:mm:ss)"
    }
}
