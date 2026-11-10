# MCTS V5: recruitment-feasibility evaluation

V5 is **V1 plus one leaf-evaluation adjustment**. Its first 32-game comparison
against Julian AB2 width 7 finished **13 wins / 11 draws / 8 losses** (57.81%
score). Two games were affected by laptop standby; see the
[verified results and limits](MCTS_V5_RESULTS.md). It uses Python's standard
library and runs on the CPU.

## What changed

V1 values future human recruitment using distance, group strength and remaining
turns. The [recorded recruitment diagnosis](MCTS_RECRUITMENT_DIAGNOSTIC.md)
found a position where this gave too much value to approaching a village of
20 humans while each army had only 10 units in total. MCTS retreated from a
nearby village of four humans instead.

At each evaluated leaf, V5 totals vampires and werewolves separately. A village
larger than **both totals** is omitted from V1's recruitment potential and its
normalization. All other terms use V1's existing formula. For example:

| Armies at the leaf | Village | Evaluation treatment |
|---|---|---|
| 10 vampires, 10 werewolves | 20 humans | Omit its recruitment potential |
| 10 vampires, 10 werewolves | 4 humans | Keep V1's distance-based value |
| 10 vampires, 20 werewolves | 20 humans | Keep V1's contested value |
| Two vampire groups of 3, 2 werewolves | 6 humans | Keep it: vampire total is 6 |

This rule is recalculated after simulated growth or losses. Filtering applies
only to the evaluation view. The actual tree and rollouts retain every village,
including legal risky attacks against larger human populations. Battle outcomes
are still sampled using the simulator's normal rules.

V5 keeps V1's candidates, UCT exploration (1.4), tree limit (12 plies), rollout
limit (6 plies), rollout policy, repetition memory and turn-cap handling. It
adds no neural network or offline training. The implementation is isolated in
`scripts/mcts_v5/`; the launcher imports it explicitly, including in Windows
workers. Use this launcher to select V5; ordinary `main.py` does not discover
this isolated package automatically.

For live course-server matches, use the separate entry point
`python scripts/play_mcts_v5.py --move-time 1.5 HOST_IP PORT`.
See [the opponent/Tailscale guide](PLAY_FRIEND_V5.md) for the supplied ticket
launcher, remote benchmark settings and connection steps.

## Start the 32-game AB2 comparison

From the repository folder, preview the plan:

```sh
python scripts/compare_mcts_v5.py --opponent width7 --dry-run
```

Then start it yourself:

```sh
python scripts/compare_mcts_v5.py --opponent width7
```

The default plan matches the existing V1-versus-Julian comparison:

- Four maps: `testmap2`, `thetrap`, `val-large-1290000`, `val-medium-1280000`.
- Eight games per map: two rounds of all four species/first-player roles.
- 32 games total, two CPU workers, seed `20261028`.
- Each agent gets 1.5 seconds thinking time within a 2-second hard allowance.
- 200-ply cap; a timeout skips that turn.
- MCTS's iteration ceiling is 100,000; the time budget normally stops it first.
- Julian's retained profile is read verbatim from `scripts/ab2_retained_profiles.json`:
  `ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000`.

The map XMLs must be in `.local/maps/mcts-vs-best-ab/`, as for the previous
comparisons. New clones can prepare them using [the match guide](WATCH_MATCH.md),
or supply XML files/folders with `--maps`.

Progress prints immediately, after each completed game and approximately every
15 seconds while workers are busy. Results and per-game checkpoints go to:

```text
.local/campaigns/mcts-v5-vs-julian-ab2-width7/
    manifest.json
    games/game-0001.json ...
    report.json
    report.md
```

To play only four additional games now:

```sh
python scripts/compare_mcts_v5.py --opponent width7 --max-games 4
```

Run the same command later to resume. Completed games are retained; an
interrupted game restarts. Stop with Ctrl+C and allow the runner to finish
saving. Keep the computer awake during a timed comparison. The manifest pins
the core code, all four V5/launcher source files, retained profile file, Python
version, maps and settings. Changed experiments require a new `--checkpoint`
directory.

## Controls and interpreting the results

To compare V5 directly against V1 on the same 32-game plan:

```sh
python scripts/compare_mcts_v5.py --opponent v1
```

This saves separately under `.local/campaigns/mcts-v5-vs-v1/`.
To disable the adjustment and reproduce V1's decisions with V5's wrapper:

```sh
python scripts/compare_mcts_v5.py --agent mcts-v5:feasibility=False --opponent width7
```

That control gets its own default directory:
`.local/campaigns/mcts-v5-control-vs-julian-ab2-width7/`.
`--opponent reference` selects Julian's retained width-6 AB2 profile.

Compare overall and per-map wins/draws/losses, score `(wins + 0.5 * draws) / games`,
population margins, iterations, faults and timeouts. V1 previously scored
**11 wins / 7 draws / 14 losses** against this width-7 opponent; on `testmap2`
it scored **0 wins / 2 draws / 6 losses**. Use all four maps to assess whether
an improvement generalizes. Timed searches can vary with CPU load even with
identical seeds, and 32 games remain a small sample.

The heuristic is deliberately conservative: it can undervalue a large village
that becomes recruitable after future growth, or a worthwhile risky attack.
It also does not solve long-distance planning or coordinated recruitment.
Julian's retained profile still has pending WPF-server validation. These CPU
matches will test the hypothesis, rather than establish a tournament champion.

## Verification

```sh
python -m unittest discover -s tests -p "test_mcts_v5.py" -v
python -m unittest discover -s tests -p "test_compare_mcts_v5.py" -v
python -m unittest discover -s tests -q
```

The tests cover the recorded counterexample across four fixed seeds at 512
iterations, exact V1 control parity on four development maps and both species,
total-population thresholds, leaf clocks, terminal rewards, deadlines, memory,
unchanged risky-battle simulation, balanced plans and spawned-worker checkpoint
resume. The recorded-position result is a regression check, not proof that the
alternative move is globally optimal or that V5 wins more complete matches.
