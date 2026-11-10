# MCTS team handoff - 10 November 2026

The latest MCTS work is on **`feat/mcts-memory`**. Julian's November 4 alpha-beta
work is already merged into this branch. V6 remains the reference; V9 is the
new recruitment-planning experiment. There is no neural network in these agents.

## Get the branch and verify your installation

Save any local work first. From your existing clone:

```powershell
git fetch origin
git switch feat/mcts-memory
git pull --ff-only origin feat/mcts-memory
python -m unittest discover -s tests -v
```

For a new clone:

```powershell
git clone --branch feat/mcts-memory https://github.com/redaabid/AI-GAME-THEORY.git
cd AI-GAME-THEORY
python -m unittest discover -s tests -v
```

Python 3.10 or newer and the standard library are sufficient. The tests and
the CPU simulator need no server, GPU or downloaded course materials.

Check the V9 launcher using the four small XML fixtures included in Git:

```powershell
python scripts/compare_mcts_v9.py --opponent v6 --maps maps --dry-run
```

For one short installation smoke test:

```powershell
python scripts/compare_mcts_v9.py --opponent v6 --maps maps --workers 1 --rounds 1 --iterations 32 --move-time 0 --max-plies 20 --max-games 1 --checkpoint .local/campaigns/v9-installation-check
```

This is a small untimed setup check, not the development tournament or evidence
of which version is stronger. Its results use a separate checkpoint folder.

## Prepare the four development maps

The default comparisons need these files under `.local/maps/mcts-vs-best-ab/`:

- `testmap2.xml`
- `thetrap.xml`
- `val-medium-1280000.xml`
- `val-large-1290000.xml`

With the course software ZIP on Windows, the existing preparation command
extracts both course maps and deterministically generates the same medium/large
maps. It also prepares a local graphical server, without launching it:

```powershell
python scripts/prepare_watch.py --archive "$env:USERPROFILE\Downloads\Softwares-20261008.zip" --map testmap2
```

Adjust the archive path if needed. Someone with the prepared maps can also
share those four XML files directly with teammates for local placement in that
directory. These map assets, course archives, server binaries and full campaign
data are intentionally outside Git. Other map sets work with `--maps PATH`,
but their scores should be labeled as a different experiment.

## Run the current experiment

```powershell
python scripts/compare_mcts_v9.py --opponent v6 --workers 6
```

That schedules 32 games across the four development maps, with both species
and starting orders balanced. Each agent gets 1.5 seconds thinking within a
two-second allowance; the cap is 200 individual player turns. Use fewer workers
if needed, with a fresh `--checkpoint` folder for changed settings. Keep the
computer awake and avoid concurrent timed campaigns.

Each completed game is saved. Run the same command to resume; unfinished games
restart. Add `--max-games 4` to play at most four more games in a session.

Under `.local/campaigns/mcts-v9-vs-v6/`:

- `report.md/json`: scores by map, timing, faults and timeouts.
- `recruitment.md/json`: planning activations, proposed two-capture sequences,
  planning cost and stop statuses.
- `games/`: individual completed-game checkpoints.

Do not change code or settings inside an existing campaign. A changed experiment
needs a new `--checkpoint` directory. Share the resulting report summaries with
the team; local checkpoint files do not travel with a Git pull.

## Current evidence and next work

- V6 scored **16 wins / 10 draws / 6 losses** against Julian's retained AB2
  width-7 profile in the completed local 32-game run, with zero faults/timeouts.
- V8 scored **11 wins / 2 draws / 19 losses** against V6, also without
  faults/timeouts. It has not replaced V6.
- V9 adds short recruitment sequences, opponent arrival/growth checks and
  counterattack exposure. At the recorded delayed-capture position, it takes
  the available 14 humans immediately for four fixed seeds; fresh V6 probes
  delay the capture for all four. This is a local behavioral fix, not a
  match-strength claim. No completed V9 campaign result is claimed here.

Review the V9-versus-V6 scores **and** activation records before combining
features or testing Julian again. Then confirm promising changes on unseen
map families. The four development maps have already been used for tuning.

See [the V9 guide](MCTS_V9.md) for assumptions, controls, tracing and the criteria
for considering a compact learned guide. A neural network is a later experiment
if traces show persistent evaluation errors that better offline search can fix
but the live budget cannot afford, and diverse training/holdout data exist.
Offline training frameworks are allowed; runtime remains independent of them.
