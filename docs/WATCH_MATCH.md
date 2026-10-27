# Watch MCTS memory against AB2 or AB6

AB2 and AB6 are imported without edits from Julian's
[`c1bb526` source](https://github.com/redaabid/AI-GAME-THEORY/blob/c1bb52662bccb9a8dfdd670a5db64cc84207a965/agents/ab_variants.py),
with its ten regression tests. The source SHA256 is
`bed8077a39f16561f0cc666a007d19cfe92f2251559f33dbc7076f3415637ac8`.
They are the two priority candidates in the latest small server campaign;
neither is established as the overall champion. Both use the selected settings
from `tests-200-coups/selection.json` on that revision, shown explicitly below.
Original agents, including `alphabeta`, remain available.

## Start a visible match

Use PowerShell terminals inside the repository folder. The helper needs the
course `Softwares-20261008.zip`, by default in your Downloads folder. Add
`--archive "C:\path\to\Softwares-20261008.zip"` if it is elsewhere.

Terminal 1:

```powershell
python scripts/prepare_watch.py --map thetrap
Start-Process -FilePath ".\.local\watch-server\VampiresVSWerewolvesGameServer.exe" -WorkingDirectory ".\.local\watch-server"
```

This opens the graphical board. The prepared server listens on
`127.0.0.1:5560`, with two players, a two-second turn allowance, a 200-ply cap,
and a ten-minute game cap. Both bots think for up to 1.5 seconds per move.
Files go under `.local/watch-server/`; the original `.local/server/` demo is
preserved. Setup prepares all four comparison maps, then selects one for the GUI.

Terminal 2, our MCTS with both experimental features:

```powershell
python main.py --agent mcts-memory --iterations 100000 --name Memory --max-plies 200 --move-time 1.5 127.0.0.1 5560
```

Terminal 3, AB2:

```powershell
python main.py --agent "ab2:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000" --name AB2 --max-plies 200 --move-time 1.5 127.0.0.1 5560
```

The game begins after both bots connect. The board shows movement and battles;
the terminals show decisions, elapsed time, and AB search diagnostics.

For AB6, use this opponent command instead:

```powershell
python main.py --agent "ab6:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000" --name AB6 --max-plies 200 --move-time 1.5 127.0.0.1 5560
```

Run one opponent per match. Close the server and stop any remaining bots with
Ctrl+C before starting another match. A bot may wait for another game after
`Game ended`; this is normal protocol behavior.

## Switch between four maps

Close the server first. Run one preparation command, then repeat the server and
both bot commands above:

```powershell
python scripts/prepare_watch.py --map thetrap
python scripts/prepare_watch.py --map testmap2
python scripts/prepare_watch.py --map medium
python scripts/prepare_watch.py --map large
```

Choose one of these commands each time. Running all four in succession selects
the last map. The maps are:

| Choice | Dimensions | Source |
| --- | --- | --- |
| `thetrap` | 10 columns x 5 rows | Supplied course archive |
| `testmap2` | 29 columns x 15 rows | Supplied course archive |
| `medium` | 10 columns x 11 rows | Generated validation map, seed 1280000 |
| `large` | 21 columns x 14 rows | Generated validation map, seed 1290000 |

For one demo of the memory effect on a recorded board, without a server:
`python demo_mcts_memory.py`. That inspects a single decision; it is not a match.

## Automatic four-map comparison

After preparing once, these two commands run the comparisons in the CPU simulator
and print progress and results in the terminal. Each command runs 16 games:
four maps x both species x both first-player roles. The two commands together
give 32 MCTS games against the two opponents. Run them after closing the visual
match so it does not compete for CPU time.

```powershell
python campaign.py --opponent ab2
python campaign.py --opponent ab6
```

The runner uses the explicit selected opponent settings shown above, MCTS with
both features and an iteration cap of 100000, battle seed 20261028, and two workers.
The deadline is `2 - 0.5 = 1.5` seconds for both sides. The game cap is 200 plies;
larger population wins at that cap. Actual battles are sampled. Use one worker
on a busy machine (`--workers 1`, chosen when starting a new checkpoint).
Timed searches depend on machine load, so common battle seeds
and balanced roles do not make the complete campaign bit-for-bit reproducible.

The terminal prints its checkpoint folder immediately, prints progress after
each saved game, and prints a heartbeat during long parallel games. Results go
under `.local/campaigns/mcts-vs-ab2/` and `.local/campaigns/mcts-vs-ab6/`:

- `manifest.json`: complete game schedule, maps, settings, Python version and
  hashes of runtime source files, including both policies.
- `games/game-*.json`: one atomic checkpoint per finished game, with its result,
  timing, faults, and save time.
- `report.json` and `report.md`: cumulative results, marked PARTIAL until all
  16 games are complete. Rankings from an unfinished campaign can be unbalanced.

Record the map, opponent, win/draw/loss counts, timeouts, and faults. Sixteen games
per opponent are an initial comparison, not proof of an overall ranking. No neural
training runs.

## Run some games now, then continue later

To finish at most four **additional** games and stop automatically:

```powershell
python campaign.py --opponent ab2 --max-games 4
```

Later, run the same opponent command to continue the remaining games:

```powershell
python campaign.py --opponent ab2
```

The runner loads saved results and skips those games. Repeating `--max-games 4`
plays up to four more, rather than limiting the campaign to four in total. The
full schedule remains 16 games per opponent. Use `--opponent ab6` for the other
16-game campaign.

Ctrl+C stops the runner while retaining already-saved games. Games that were
still running or not yet saved restart from their beginning next time. A whole
game is the checkpoint boundary; there are no mid-game snapshots. Keep the
checkpoint folder and use the same computer and conditions for timed comparisons.
The runner refuses to mix changed code, Python, maps or settings into a checkpoint;
use `--checkpoint .local/campaigns/a-new-experiment` for a separate experiment.
An OS lock prevents two processes from writing the same campaign concurrently.

The original `tournament.py` command still writes results only after its entire
batch finishes, under `.local/tournaments/`. Adding this new runner does not change
an already-running process or recover its in-memory game results. A fully finished
legacy batch remains a valid separate report; it is not imported into these new
checkpoints. Let an existing legacy batch finish if you want to retain its games.
