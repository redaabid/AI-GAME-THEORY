param(
    [string]$ModelPath,
    [int]$Samples = 20000
)

# Optional Windows check against the course model; no GUI, network, or AI library.
$ErrorActionPreference = 'Stop'
$repositoryPath = Split-Path -Parent $PSScriptRoot
if (-not $ModelPath) { $ModelPath = Join-Path $repositoryPath '.local\server\VVSW.Model.dll' }
if ($Samples -lt 1000) { throw 'Use at least 1000 samples for the probability check.' }
$modelAssembly = [Reflection.Assembly]::LoadFrom((Resolve-Path -LiteralPath $ModelPath).Path)
$boardType = $modelAssembly.GetType('VVSW.Model.Board')
$moveType = $modelAssembly.GetType('VVSW.Model.Move')
$coordinateType = $modelAssembly.GetType('VVSW.Model.Coordinate')
$speciesType = $modelAssembly.GetType('VVSW.Model.Species')
$listDefinition = [type]'System.Collections.Generic.List`1'
$moveListType = $listDefinition.MakeGenericType($moveType)
$vampires = [Enum]::Parse($speciesType, 'Vampires')
$werewolves = [Enum]::Parse($speciesType, 'Werewolves')
$humans = [Enum]::Parse($speciesType, 'Humans')
$binding = [Reflection.BindingFlags]'Public,NonPublic,Instance,Static'
$checks = @()

function New-Board($records) {
    $board = [Activator]::CreateInstance($boardType, [object[]]@([byte]5, [byte]7))
    foreach ($record in $records) {
        # This .NET indexer uses (row, column), unlike protocol (x, y).
        $cell = $board.get_Item([byte]$record[1], [byte]$record[0])
        if ($record[2] -gt 0) { $cell.CellSpecies = $humans; $cell.Count = [byte]$record[2] }
        if ($record[3] -gt 0) { $cell.CellSpecies = $vampires; $cell.Count = [byte]$record[3] }
        if ($record[4] -gt 0) { $cell.CellSpecies = $werewolves; $cell.Count = [byte]$record[4] }
    }
    return ,$board
}

function New-Moves($records) {
    if ($records.Count -gt 0 -and $records[0] -isnot [array]) { $records = ,@($records) }
    $moves = [Activator]::CreateInstance($moveListType)
    foreach ($record in $records) {
        $source = [Activator]::CreateInstance($coordinateType, [object[]]@([int]$record[0], [int]$record[1]))
        $target = [Activator]::CreateInstance($coordinateType, [object[]]@([int]$record[3], [int]$record[4]))
        $move = [Activator]::CreateInstance($moveType, [object[]]@($source, $target, [byte]$record[2]))
        $moves.Add($move)
    }
    return ,$moves
}

$casesPath = Join-Path $repositoryPath 'tests\fixtures\server_turns.json'
$cases = Get-Content -LiteralPath $casesPath -Raw | ConvertFrom-Json
foreach ($case in $cases) {
    $board = New-Board $case.cells
    $moves = New-Moves $case.moves
    try {
        $null = $board.PerformMoves($vampires, $moves)
        $records = @()
        for ($x = 0; $x -lt $board.Columns; $x++) {
            for ($y = 0; $y -lt $board.Rows; $y++) {
                $cell = $board.get_Item([byte]$y, [byte]$x)
                if ($cell.Count -eq 0) { continue }
                $h = 0; $v = 0; $w = 0
                if ($cell.CellSpecies -eq $humans) { $h = [int]$cell.Count }
                if ($cell.CellSpecies -eq $vampires) { $v = [int]$cell.Count }
                if ($cell.CellSpecies -eq $werewolves) { $w = [int]$cell.Count }
                $records += ,@($x, $y, $h, $v, $w)
            }
        }
        $actual = ConvertTo-Json -InputObject $records -Compress -Depth 8
        $expected = ConvertTo-Json -InputObject $case.expected -Compress -Depth 8
        $checks += @{ name = $case.name; matched = (-not $case.rejected -and $actual -eq $expected); observed = $records }
    } catch {
        $cause = $_.Exception.GetBaseException()
        $checks += @{ name = $case.name; matched = ($case.rejected -and $cause.GetType().Name -eq 'BadMoveException'); error = $cause.Message }
    }
}

# Compare unconditional survivor means and probability of a surviving attacker.
# This also handles outcomes where the winning side has zero survivors.
$randomCases = @(
    @{ attackers = 12; defenders = 10; humanBattle = $false; probability = 0.7 },
    @{ attackers = 4; defenders = 8; humanBattle = $true; probability = 0.25 },
    @{ attackers = 1; defenders = 1; humanBattle = $false; probability = 0.5 },
    # Check the whole turn here: v3.2.1 does not guarantee the stronger defender wins.
    @{ attackers = 10; defenders = 15; humanBattle = $false; probability = (1.0/3); fullTurn = $true }
)
foreach ($case in $randomCases) {
    $board = New-Board @()
    $sharedRandom = [Random]::new(2026)
    $boardType.GetField('rnd', $binding).SetValue($board, $sharedRandom)
    $defenderSpecies = if ($case.humanBattle) { $humans } else { $werewolves }
    $attackerTotal = 0.0; $defenderTotal = 0.0; $attackerPresent = 0
    for ($i = 0; $i -lt $Samples; $i++) {
        if ($case.fullTurn) {
            $board = New-Board @(@(0,0,0,$case.attackers,0), @(1,1,0,0,$case.defenders))
            $boardType.GetField('rnd', $binding).SetValue($board, $sharedRandom)
            $moves = New-Moves @(@(0,0,$case.attackers,1,1))
            $null = $board.PerformMoves($vampires, $moves)
            $cell = $board.get_Item([byte]1, [byte]1)
            $survivorSpecies = $cell.CellSpecies; $survivorCount = $cell.Count
        } else {
            $battle = $board.PerformRandomBattle($vampires, [int]$case.attackers, $defenderSpecies, [int]$case.defenders)
            $survivorSpecies = $battle.SurvivorSpecies; $survivorCount = $battle.SurvivorCount
        }
        if ($survivorSpecies -eq $vampires) {
            $attackerTotal += $survivorCount
            if ($survivorCount -gt 0) { $attackerPresent++ }
        } else {
            $defenderTotal += $survivorCount
        }
    }
    $p = $case.probability
    $population = $case.attackers + $(if ($case.humanBattle) { $case.defenders } else { 0 })
    $expectedAttacker = $population * $p * $p
    $expectedDefender = $case.defenders * (1-$p) * (1-$p)
    $expectedPresence = $p * (1 - [Math]::Pow(1-$p, $population))
    $matched = [Math]::Abs($attackerTotal/$Samples - $expectedAttacker) -lt 0.15 -and [Math]::Abs($defenderTotal/$Samples - $expectedDefender) -lt 0.15 -and [Math]::Abs($attackerPresent/$Samples - $expectedPresence) -lt 0.02
    $checks += @{ name = "random_$($case.attackers)_$($case.defenders)_humans_$($case.humanBattle)"; matched = $matched; samples = $Samples; attackerMean = $attackerTotal/$Samples; defenderMean = $defenderTotal/$Samples; attackerPresence = $attackerPresent/$Samples }
}

$report = @{ modelSha256 = (Get-FileHash -LiteralPath $ModelPath -Algorithm SHA256).Hash.ToLower(); assemblyVersion = $modelAssembly.GetName().Version.ToString(); checks = $checks }
$reportDirectory = Join-Path $repositoryPath '.local'
$null = [IO.Directory]::CreateDirectory($reportDirectory)
$reportPath = Join-Path $reportDirectory 'server-model-check.json'
[IO.File]::WriteAllText($reportPath, (ConvertTo-Json -InputObject $report -Depth 10), [Text.UTF8Encoding]::new($false))
foreach ($check in $checks) { Write-Output "$($check.name): $($check.matched)" }
Write-Output "Report: $reportPath"
if (@($checks | Where-Object { -not $_.matched }).Count -gt 0) { exit 1 }
