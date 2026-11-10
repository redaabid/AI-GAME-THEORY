# MCTS against Julian's retained AB2 configurations

**Completed 6 November 2026:** V1 finished **11 wins / 7 draws / 14 losses**
against width 7 across 32 games, with zero timeouts or faults for either agent.
See [the result analysis](MCTS_JULIAN_RESULTS.md) for the map breakdown and
long-distance recruitment diagnosis. V1 remains our reference after the V2,
V3 and both V4 experiments failed to demonstrate an improvement against it.

Run the following campaigns one at a time so they do not compete for CPU
during timed decisions. The launcher reuses
the checkpoint machinery without changing the existing MCTS or campaign code.

Julian's width-7 configuration is a useful primary opponent; width-6 reference
is a second control. His published evidence does not establish a universal
winner. TIE remains experimental. Exact opponent specifications and statuses
come from [ab2_retained_profiles.json](../scripts/ab2_retained_profiles.json).

The V1 comparison command is:

```powershell
python scripts/compare_mcts_julian.py --agent mcts-v1 --opponent width7
```

V3 can also be compared against the same opponent. Its own loss to V1 does
not determine its matchup against alpha-beta:

```powershell
python scripts/compare_mcts_julian.py --agent mcts-v3 --opponent width7
```

Each command schedules **32 games**: the same four prepared maps, two rounds,
and both species/first-player roles on each map. Both agents receive **1.5 s**
of thinking time from a 2 s allowance, with 200 plies per game and two workers.
Each MCTS has a 100,000-iteration cap. AB2 uses iterative deepening up to depth
24; this cap is not an assurance that every search reaches that depth.

Each completed game is checkpointed. Run the same command to resume. Add
`--max-games 4` to finish at most four additional games in a session, or
`--dry-run` to inspect the plan without starting games or writing checkpoints.
Keep the computer awake during a run.

Reports and individual games are stored separately:

```text
.local/campaigns/mcts-v3-vs-julian-ab2-width7/
.local/campaigns/mcts-v1-vs-julian-ab2-width7/
```

Read `report.md` for per-map wins/draws/losses, scores, timing and search depths;
`report.json` contains the raw summaries and provenance. The plan pins both the
runtime sources and this launcher's source/profile files. Changed settings or
code require a new checkpoint directory.

Use `--opponent reference` for width 6 or `--opponent tie-width7` for the
experimental TIE version. Those choices get independent checkpoint folders.
These comparisons use the CPU simulator. Final selection still needs unseen
maps and validation on the course server.
