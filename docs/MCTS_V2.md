# MCTS v2: coordinated and longer simulated continuations

V2 upgrades the shared search before adding strategic personalities. It uses the
CPU and Python standard library. No neural network is trained. The completed
local 32-game comparison on 28 October 2026 scored **9 wins, 1 draw and 22 losses**
against V1. Its report remains in `.local/campaigns/mcts-v2-vs-v1/`. The next
experiment, [V3](MCTS_V3.md), isolates coordination at V1's original horizon.

## What v1 and v2 mean

`mcts-v1` is the current `mcts-memory` agent with diagnostics enabled. It retains
repeated-position preferences while behind, turn-limit-aware evaluation, the
same candidate turns, and adversarial UCT with sampled combat. Fixed-seed tests
check that its decisions match `mcts-memory`. The older original `mcts` is also
still available; it is not the default v1 opponent in this comparison.

`mcts-v2` retains that base and changes the continuations after the tree reaches
a leaf:

| Feature | v1 | v2 default |
|---|---|---|
| Rollout policy for both sides | One group per turn | Validated coordinated plans |
| Normal rollout horizon | 6 plies | 12 plies |
| Tactical extension | None | Up to 4 extra plies while opposing groups are adjacent |
| Alternative continuations | Fixed baseline policy | 10% chance of a close alternative, from at most 3 ranked plans |
| Repeated boards inside a rollout | Continue to horizon | Stop and use the ordinary heuristic |
| Tree depth cap | 12 plies | 12 plies |
| Combat and final rewards | Sampled combat, exact terminal reward | Same |

A ply is one player's turn. Horizons are caps, not promises: elimination, the
game's turn cap, a loop, or the thinking deadline may shorten a continuation.
Read the measured depths in the report instead of assuming every search reaches
the maximum. The tree already supported joint moves and selected splits in v1;
the new coordination is inside the rollouts.

The rollout planner proposes distinct village assignments, whole-side
recruit/split/retreat scripts, and adjacent joint attacks or recruitment. It
ranks a bounded selection of these plans with the existing tactical heuristic;
this is not exhaustive enumeration of all legal turns. Other groups can keep
moving during a joint operation. Unsupported or overflowing plans are rejected.
Both players use the same rollout policy, and battles always use the supplied
search RNG, rather than `playbook.playout`'s deterministic approximation.

For example, two groups of 4 can jointly recruit 6 humans, becoming 14. A
tactical extension can also expose an enemy's immediate response after our 8
recruits 5 humans: a neighboring enemy group of 20 can destroy the resulting 13.
Extensions remain bounded and do not prove every tactic safe.

## Start the comparison yourself

From the repository folder:

```sh
python campaign.py --opponent mcts-v1
```

Defaults: **32 games on the four previously prepared maps**, with two rounds of
all four species/first-player combinations per map. Both engines have a
100,000-iteration cap and a **1.5-second thinking budget**, from a 2-second turn
allowance minus a 0.5-second reserve. The game cap remains 200 plies. Two worker
processes run concurrently. A full timed campaign can take over an hour.

The maps are `testmap2`, `thetrap`, `val-large-1290000`, and
`val-medium-1280000` in `.local/maps/mcts-vs-best-ab/`. If they have not been
prepared on a colleague's computer, follow [WATCH_MATCH.md](WATCH_MATCH.md).
Explicit XML paths or a directory can be supplied with `--maps`.

To inspect the plan without starting games or writing checkpoint files:

```sh
python campaign.py --opponent mcts-v1 --dry-run
```

To finish at most four additional games in this session:

```sh
python campaign.py --opponent mcts-v1 --max-games 4
```

Run the original command again to continue. Each completed game is saved before
it is announced. Ctrl+C keeps saved games; unfinished games restart. A heartbeat
appears every 15 seconds with parallel workers while games are running.

Reports and per-game checkpoints are in:

```text
.local/campaigns/mcts-v2-vs-v1/report.md
.local/campaigns/mcts-v2-vs-v1/report.json
.local/campaigns/mcts-v2-vs-v1/games/
```

The manifest records policies, source hashes, full initial maps, seeds, Python
version and settings. Changes to code, maps, workers or settings require a new
`--checkpoint` directory, so incompatible runs cannot be mixed. Existing AB2/AB6
campaign files are preserved; those commands retain their previous defaults.

## Interpret the report

The report includes per-map wins/draws/losses from v2's perspective, mean match
score (win=1, draw=0.5, loss=0), population margins, eliminations, faults and
timeouts. Scores at the ply limit use surviving population, as in earlier runs.

Search diagnostics for both versions include completed iterations, actual tree
and rollout depths, tactical extension plies, completed multi-group rollout
turns, loop cutoffs, candidate-generation time, and rollout/search wall and CPU
time. Means are calculated from totals, not averages of averages. Rollout depth
counts completed rollouts; phase timings also include work interrupted by the
deadline. Overall decision times include search cleanup and move validation.

Up to eight decisions per player per game that exceed the thinking budget by
more than 0.05 seconds retain wall/CPU timings, the board, search RNG state
before the decision, and up to 32 prior own turns. These traces help investigate
the earlier long decisions. Cooperative checks do not provide an OS-level hard
timeout, and the cause of the two old AB6-series timeouts remains unconfirmed.

Longer and more expensive rollouts can reduce the number of alternatives the
tree examines in the same time. V2 is experimental until measured results show
whether the tradeoff helps. The same seeds and fixed iteration budgets are
reproducible; timed searches vary with machine speed and load. These four maps
are validation cases already used during development, not an unseen final test.

## Isolate the changes later

For coordinated rollouts at the original horizon, without tactical extensions
or alternative-plan sampling:

```sh
python campaign.py --opponent mcts-v1 --agent "mcts-v2:iterations=100000,rollout_depth=6,extension_depth=0,variation=0,detect_loops=False" --checkpoint .local/campaigns/mcts-coordination-only
```

Other independent controls are `coordinated=False`, `rollout_depth=N`,
`extension_depth=N`, `variation=0`, `rollout_width=N`, and `detect_loops=False`.
Memory/clock switches remain available. Disabling coordination, extensions,
variation and loop detection at depth 6 reproduces v1's rollout behavior in
fixed-seed tests. Strategic profiles such as Hunter and Conqueror remain a
later step.

Run implementation checks with:

```sh
python -m unittest discover -s tests -q
```

Live play uses the existing client, for example
`python main.py --agent mcts-v2 --max-plies 200 --move-time 1.5 IP PORT`.
