# MCTS v3: V1 plus coordinated rollouts

V3 isolates the coordinated rollout policy from V2. The completed local V2 run
scored 9 wins, 1 draw and 22 losses against V1. V2 also changed rollout length,
tactical extensions, alternative-plan sampling and loop handling, so that run
did not isolate coordination's contribution.

`mcts-v3` inherits directly from `mcts-v1`. Every search configuration default,
memory setting, turn-limit evaluation, tree candidate generator, combat rule,
and terminal reward stays the same. The only replacement is the rollout policy
for both simulated players: V3 uses the coordinated planner already introduced
in V2. This includes distinct village assignments, joint recruitment/attacks,
and the existing recruit/split/retreat proposals.

| Setting | V1 | V3 |
|---|---|---|
| Rollout policy | Single-group baseline | Coordinated turn plans |
| Normal rollout horizon | 6 plies | 6 plies |
| Extra tactical plies | 0 | 0 |
| Alternative-plan sampling | None | None |
| Loop cutoff inside rollouts | None | None |
| Tree depth cap | 12 plies | 12 plies |
| Repetition memory and turn-limit evaluation | Enabled | Enabled |

A ply is one player's turn. V1 already considers joint moves and selected splits
inside its search tree; V3 changes the quick continuations after reaching a tree
leaf. Combat remains stochastic, using the supplied RNG. No network is trained.

## Start the comparison yourself

From the repository folder:

```sh
python campaign.py --opponent mcts-v1 --agent mcts-v3
```

This schedules **32 games on four maps**, two rounds of all four species and
first-player roles on each map. Both agents receive a **1.5-second thinking
budget**, a 2-second turn allowance, and a 100,000-iteration cap. Games stop at
200 plies or elimination. Two worker processes run concurrently.

The four maps and seed schedule match the V2 campaign: `testmap2`, `thetrap`,
`val-large-1290000`, and `val-medium-1280000`, under
`.local/maps/mcts-vs-best-ab/`. See [WATCH_MATCH.md](WATCH_MATCH.md) if these maps
need preparation on a colleague's computer.

For a plan preview that starts no games and writes no checkpoints:

```sh
python campaign.py --opponent mcts-v1 --agent mcts-v3 --dry-run
```

For at most four additional completed games this session:

```sh
python campaign.py --opponent mcts-v1 --agent mcts-v3 --max-games 4
```

Run the full command again to resume. Completed games are saved individually;
unfinished games restart. Progress appears every 15 seconds with parallel
workers. Keep the computer awake: Windows Modern Standby interrupted the V2
experiment and caused recorded turn timeouts. The full timed campaign may take
over an hour.

The V3 comparison has its own output directory:

```text
.local/campaigns/mcts-v3-vs-v1/report.md
.local/campaigns/mcts-v3-vs-v1/report.json
.local/campaigns/mcts-v3-vs-v1/games/
```

The old V2 reports remain in `.local/campaigns/mcts-v2-vs-v1/`. Defaults still
select V2 when `--agent` is omitted. A custom `--checkpoint` overrides the
directory; changed code/maps/settings require a fresh checkpoint. For MCTS
challengers, `--iterations` is applied when the agent spec does not already set
an explicit cap.

## What to measure

Compare match score and per-map wins/draws/losses, then iterations per decision,
actual tree/rollout depths, multi-group rollout turns, faults and timeouts. V3's
rollout maximum must stay at or below 6, with zero tactical extensions and loop
cutoffs. Coordination still has a computation cost; the experiment will show
whether it earns that cost at the same wall-time budget.

Implementation tests cover equal V1/V3 settings, coordination for both simulated
players, the unchanged horizon, preservation of memory, seeded reproducibility,
deadline fallback, CLI iteration caps and the independent campaign directory:

```sh
python -m unittest discover -s tests -q
```

V3's campaign has not been started automatically. Strategic profiles remain a
later step.
