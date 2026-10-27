# MCTS memory and clock experiment: 27 October 2026

This branch adds an optional `mcts-memory` agent, a recorded-decision demo, and a
controlled benchmark. It uses Python's standard library and runs on a CPU.
**The memory changes a recorded looping decision; the first match experiment
shows no improvement in match score. Keep alpha-beta as the current candidate.**

## What changed

Memory reads `TurnContext.history`, which already contains this agent's previous
boards and moves in the current game. A repeated position means the same complete
board, species to move, dimensions, and rule profile. The key ignores elapsed
plies so it can recognize a return to the same position.

When our population is smaller than the enemy's, memory looks at the last 32
own turns. If we took the same quiet plan from this exact board at least twice,
that plan receives a 0.3 penalty in **root UCT selection**. A quiet plan only
repositions or merges friendly units. Recruitment and attacks receive no penalty.
The penalty is a preference, not a prohibition: search can still choose the plan.
Leading and tied players receive no memory penalty. History resets with each game.

The clock option changes MCTS's bounded leaf heuristic. It calculates each side's
remaining moves using `max_plies`, the current ply, and whose turn comes next.
Human groups that neither army can reach before the cap contribute no recruitment
potential or normalization weight. Reachability uses optimistic direct distances;
it does not prove a safe route or successful recruitment. Exact terminal outcomes
remain -1/0/+1.

Original `mcts` keeps its previous heuristic and selection behavior. We compared
its actions, candidates, visit counts and action values with untouched `main`
revision `352ebf4` in 16 seeded searches: four bundled maps, both species, seeds
0 and 42, 64 iterations, cap 40. All matched exactly; a regression check preserves
that reference. Chance outcomes are still sampled afresh on every traversal,
and interrupted iterations add no visits.

| Agent spec | Memory | Clock |
| --- | --- | --- |
| `mcts:iterations=128` | Off | Original evaluation |
| `mcts-memory:iterations=128,memory=False,clock=True` | Off | On |
| `mcts-memory:iterations=128,memory=True,clock=False` | On | Original evaluation |
| `mcts-memory:iterations=128` | On | On |

All `SearchConfig` fields are accepted. The shared live client applies
`--iterations` to both MCTS agents; default live cap is 10,000 iterations with
a 1.5-second cooperative deadline. Fixed-iteration comparisons are reproducible;
timed searches vary with hardware and scheduling.

## Show the recorded decision

```sh
python demo_mcts_memory.py
```

The portable [fixture](../examples/mcts_losing_loop.json) comes from the first
22 October server campaign, `p200_testmap2_MCTS-then-AlphaBeta`, before MCTS's own
turn 41. Source revision and both log paths are embedded in the fixture. Replaying
the first 80 logged plies required no random battle reconstruction: all preceding
battles were guaranteed. The fixture includes the last four own-turn observations.

Vampires have 14 units and werewolves have 16; the cap is 200 plies. MCTS has
already repeated the quiet move from `(11,10)` to `(10,10)` twice at the same
complete board. With seed 0 and 2,048 iterations:

| Variant | Chosen destination of the 14 vampires | Historical retreat repeated? |
| --- | --- | --- |
| Original | `(10,10)` | Yes |
| Clock only | `(10,10)` | Yes |
| Memory only | `(11,11)` | No |
| Memory + clock | `(11,11)` | No |

This isolates the effect of memory on **one decision**. Moving somewhere else
does not establish that a loop is permanently broken or the game can be won.
At 128 iterations, original MCTS already selects another move on this fixture;
the behavior depends on the search budget. The full match history also advances
the agent's RNG, so this seeded decision replay is not a complete live rerun.

To inspect a live-sized decision budget:

```sh
python demo_mcts_memory.py --move-time 1.5 --iterations 100000
```

Reports include the fixture, action, iterations, diagnostics, source hashes and
timings, under `.local/mcts-memory/`. This command does not start the server.

## Controlled match experiment

Run from the repository folder:

```sh
python benchmark_mcts.py --iterations 128 --max-plies 200 --seed 20261027
```

The opponent is `alphabeta` from shared revision `352ebf4`, using its untimed
depth-3 default. Each variant plays four games on each of six maps: `demo`,
`endgame`, `recruitment`, `tactics`, and medium validation seeds 1000000/1000001.
Both species and first-player roles are balanced independently on every map.
The same role/map gets the same battle seed for every variant; battle and agent
RNGs are separate. Different play can consume different random draws, so a shared
seed does not force identical battle outcomes after the policies diverge.

That is **24 games per variant, 96 games total**, using the `server-v3.2.1` rules,
128 iterations per MCTS decision and a 200-ply cap. These are CPU simulator games,
not 96 new graphical-server games. Score is win=1, draw=0.5, loss=0. Raw results
and timing summaries are in [the archived experiment](experiments/mcts-memory-2026-10-27.json).

| Variant | W / D / L | Mean score | Repeated boards / decisions | Losing repetitions / losing decisions | Memory-active decisions |
| --- | --- | --- | --- | --- | --- |
| Original | 7 / 2 / 15 | 0.333 | 211 / 537 (39.3%) | 39 / 286 (13.6%) | 0 |
| Clock only | 7 / 2 / 15 | 0.333 | 211 / 537 (39.3%) | 39 / 286 (13.6%) | 0 |
| Memory only | 7 / 2 / 15 | 0.333 | 216 / 566 (38.2%) | 44 / 315 (14.0%) | 8 |
| Memory + clock | 7 / 2 / 15 | 0.333 | 216 / 566 (38.2%) | 44 / 315 (14.0%) | 8 |

**There is no measured competitive gain here.** Every individual game's winner
was unchanged across variants. The lower overall repetition percentage comes
with more turns and more absolute repeated boards; losing repetition counts and
rates increased slightly. Memory activated only in one game per memory-enabled
variant (`demo`, playing werewolves second). All eight active decisions avoided
the penalized action, but that game still lost. Clock alone changed none of the
aggregate metrics. It needs more targeted endgame positions to assess its value.

No agent faults were recorded for either side. The slowest MCTS decision was
0.329 seconds in this untimed screening run; no turn deadlines were imposed,
so its zero timeout counters are **not** evidence of full-budget server safety.
Timing comparisons are exploratory: the variants ran sequentially, and these
budgets do not equate MCTS and alpha-beta computation. The suite also includes
TCP checks of joint turns and game resets for both MCTS agents and both species.

The JSON records map states, specs, seeds, rules, runtime source hashes, per-map
scores, all game summaries, fault/timeout counts, and decision timing summaries.
Existing files are not overwritten. Add `--rounds 2`, `--random-maps 6`,
`--map-seed 1`, or `--opponent portfolio` for a broader validation campaign.
Reserve the `test` map split for final reporting; the default benchmark uses `val`.

## What this means for our next work

We now have a testable history-aware policy and a way to separate two changes
instead of judging them together. The repetition penalty remains an uncalibrated
heuristic. Exact-board matching misses cycles with changing opponent positions;
it also cannot help if the candidate set omits a useful plan. Changing a retreat
does not fix the baseline rollout's preference for continued avoidance.

The next search experiment should improve tactical candidate coverage and compare
rollouts that recruit, attack, merge, and flee, then repeat the same controlled
match experiment. Calibrate any repetition penalty on training maps and select
on separate validation seeds. Validate promising variants with equal wall-time
budgets and full real-server games before changing our tournament choice.

This work is **search engineering and evaluation, not neural training**. The
existing `simulate.py` MCTS exporter is unchanged. It does not export the new
history-dependent agent: training it later requires history and clock features,
plus explicit teacher/version labels. The GPU teammate can keep developing the
original policy/value data pipeline independently.
