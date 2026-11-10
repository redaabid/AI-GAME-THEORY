# MCTS V4: contextual parameter adaptation

V4 is an experimental **V1 + adaptive exploration and rollout length**. It is
implemented separately under `scripts/mcts_v4/` so work on it does not change
the source fingerprint or worker imports of the ongoing V3-versus-V1 campaign.
The default experiment adapts both parameters. The new `--exploration-only`
option holds the rollout limit at V1's six plies. No neural network is involved.

## Completed result and next experiment

The original V4-versus-V1 campaign finished on 5 November 2026: **14 wins,
1 draw and 17 losses** for V4 across 32 balanced games on four maps.
Its match score was 45.3%, versus V1's 54.7%. Both agents had zero timeouts
and faults. V4 averaged 1,947 iterations per decision versus V1's 1,573,
but used shorter rollouts: 3.93 versus 5.77 plies. Controller overhead was
about 0.72% of V4 search CPU. This sample does not establish a strength increase.
The original reports remain under `.local/campaigns/mcts-v4-vs-v1/`.

The next experiment isolates exploration tuning:

| Setting | V1 | Original V4 | Exploration-only V4 |
|---|---|---|---|
| Exploration for our simulated role | 1.4 | Adaptive | Adaptive |
| Rollout limit | 6 | Adaptive | 6 |
| Exploration for the opponent | 1.4 | 1.4 | 1.4 |
| Rollout move policy | Original heuristic | Original heuristic | Original heuristic |

Run it yourself from the repository directory:

```powershell
python scripts/compare_mcts_v4.py --opponent v1 --exploration-only
```

Add `--dry-run` to preview, or `--max-games 4` to finish at most four additional
games this session. Repeating the command resumes. It uses the same four maps,
seed schedule, 32 balanced games and 1.5-second thinking budget described below.
Its separate output directory is:

```text
.local/campaigns/mcts-v4-exploration-vs-v1/
```

This option sets the agent parameter `tune_rollout=False`. The configured
rollout limit stays at six on all maps and at every match-clock value. Actual
rollouts still stop at terminal states, the match cap or a search deadline,
exactly as V1 does. Explicit `rollout_depth` overrides are respected, so keep
the default agent spec for the six-ply comparison. Context is still logged;
only `C` is tuned, over the same three values and eight-simulation blocks.
The training metadata identifies this variant as `exploration_sa_uct_v4`.

The original implementation's five pinned source files and manifest were saved
locally before this change in
`.local/backups/mcts-v4-vs-v1-source-20261105T201553450710Z.zip`.
Completed results were preserved. Since source hashes changed, the updated
code cannot resume the original campaign's checkpoint; a new full-adaptation
run requires a fresh `--checkpoint` folder. The new mode chooses its own
directory automatically. Conflicting `adaptive=False` or `tune_rollout=True`
specs are rejected when `--exploration-only` is supplied.

## Research and choice

Research checked on 5 November 2026. There is no published configuration that
can be called the best for our Twilight rules, candidate generator and CPU
budget. The following are useful research directions, not a ranking for our game.

| Research | Contribution | Decision for this experiment |
|---|---|---|
| [Self-Adaptive MCTS, Sironi et al., 2020 journal version](https://cris.maastrichtuniversity.nl/en/publications/self-adaptive-monte-carlo-tree-search-in-general-game-playing/) | Online parameter selection inside a shared search; experiments include a 1-second clock and favor tuning a small parameter set. | Most directly relevant to our 1.5-second CPU search. Adapt two parameters. |
| [NTBEA, Lucas et al., 2018](https://arxiv.org/abs/1802.05991) | A statistical n-tuple model for noisy, expensive discrete optimization. | Borrow parameter-wise and pair-wise reward/count tables. Enumerate our tiny grid rather than implement evolutionary neighborhood search. |
| [Elastic MCTS, Xu et al., 2023](https://www.tnt.uni-hannover.de/papers/data/1675/_2023__IEEE_TOG__Elastic_Monte_Carlo_Tree_Search.pdf) | Dynamic state abstraction shares search information in strategy games. | Promising for large action spaces, but a larger change than parameter tuning. Deferred. |
| [Novelty in MCTS, Baier and Kaisers, 2025](https://ir.cwi.nl/pub/35890) | Adds novelty estimates to selection; evaluated in six board games with heuristic and neural guidance. | A plausible future experiment for exploration and repetitive play. Not included in V4. |
| [Gumbel AlphaZero/MuZero, Danihelka et al., ICLR 2022](https://davidstarsilver.wordpress.com/wp-content/uploads/2025/04/gumbel-alphazero.pdf) | Policy improvement with sampling without replacement and sequential halving. | A later path for policy/value networks; the full algorithm is not a parameter preset for our current UCT. |

The official [DeepMind implementation](https://github.com/google-deepmind/mctx/blob/main/mctx/_src/policies.py)
takes policy logits, values and a recurrent evaluation function. We do not
import that library. V4 uses our own standard-library implementation.

Our adaptation is **research-inspired, not a reproduction of SA-MCTS or full
NTBEA**. The [SA-MCTS paper](https://dke.maastrichtuniversity.nl/m.winands/documents/New-AdaptiveMCTSforGGP.pdf)
retains tuners across a game and describes role-specific adaptation. V4 resets
its model at every decision, chooses settings in blocks of eight completed
simulations, and adapts exploration for our simulated role only.
The paper's successful tuned parameters are not evidence that our chosen
exploration/depth pair or numerical ranges are optimal.

## Why area alone is insufficient

A 20-by-20 map with an enemy one square away is a tactical contact position.
The same dimensions with armies at opposite corners can be a travel position.
Many independently moving groups also change the search cost.

Once per decision, V4 measures dimensions, group counts, nearest enemy distance,
nearest village one of our groups can certainly recruit alone, and remaining
plies. Distances use the game's eight-direction movement. These are cheap
context features, not an exact travel planner or a learned map classifier.
Joint recruitment opportunities can be missed by this simple distance feature;
the normal tree candidate generator still considers joint plans.

Rules are tested in the following order:

| Context | Initial classification | Rollout lengths offered by default |
|---|---|---|
| Late | At most 12 plies remain | 0, 2, 6 |
| Contact | Enemy within 2 squares of an own group | 2, 4, 6 |
| Busy | At least 6 monster groups across both sides | 0, 2, 6 |
| Travel | Nearest enemy/affordable village is at least `max(4, ceil(max(rows, columns)/3))` away | 2, 6, 10 |
| Balanced | Other positions | 2, 4, 6 |

These thresholds are engineering starting points. For example, contact takes
precedence over busy, and busy over travel. They must be validated on new maps.
Lengths are clipped by the remaining match clock and duplicate choices removed.
A ply is one player's turn; these numbers are limits after reaching a tree leaf,
not promises of that many useful moves or of a longer search tree.

## What the tuner does

V1 normally fixes exploration at `C=1.4` and rollout length at 6. V4 tests
`C in {0.7, 1.4, 2.1}` with the contextual lengths above: at most nine pairs.
If base parameters are explicitly overridden, the grid is derived from them.
The V1 pair remains available, except when the match clock clips its length.
This does not guarantee that V4 will perform as well as V1.

1. Begin with the V1 pair for eight completed simulations.
2. Cover the remaining pairs in seeded shuffled order, eight simulations each.
3. Prefer combinations with promising feedback or insufficient observations,
   using the average UCB score of the exploration, depth and complete-pair tables.
4. Update all three tables after every completed simulation, then select again
   at the next block boundary. All simulations contribute to the same MCTS tree.
5. Return the most-visited root action, as V1 does.

The opponent retains V1's exploration coefficient and still minimizes our
reward. This limits a configuration's ability to look good by weakening the
simulated opponent through its exploration setting. Both roles still use the
original rollout move policy and sampled combat.

The tuner normalizes root-perspective simulation values from `[-1, 1]` to
`[0, 1]`. Its own exploration coefficient defaults to 0.35. Separate seeded RNGs
control parameter selection and search/battle sampling. An interrupted
simulation contributes neither visits nor a tuner observation.

This is an online statistical model, **not neural-network training**. Nothing
is learned across games or saved as trained weights. Context restricts the grid;
there is no learned mapping from map features to parameter values yet.

There is a significant limitation: a high simulation return is an internal
proxy, not proof of a good configuration. Short rollouts can overvalue a position,
including truncating an important opponent reply. Later samples see a more
developed shared tree. Those biases, plus tuning overhead and rollout
cost, mean actual equal-time match results must decide whether we retain V4.

## Relationship to existing versions

| Component | V1 | V3 | V4 |
|---|---|---|---|
| Rollout move policy | Original one-group heuristic | Coordinated plans | Original one-group heuristic |
| Rollout horizon | 6 | 6 | Contextual/tuned |
| UCT exploration | 1.4 | 1.4 | Tuned |
| Tree depth cap | 12 | 12 | 12 |
| Candidate limit | 32 | 32 | 32 |
| Repetition memory and clock evaluation | Enabled | Enabled | Enabled |
| Stochastic combat, opponent minimization, terminal rewards | Shared | Shared | Shared |

The completed V2 run lost 9 wins / 1 draw / 22 losses to V1 while spending much
more CPU per rollout. That motivates controlling search cost. V3 subsequently
finished 11 wins / 1 draw / 20 losses against V1 in its separate campaign.
V4 begins from V1 so
its adaptation can be assessed independently of V3's rollout change.

## Run after the current campaign finishes

From the repository directory, preview the plan without writing files or starting games:

```powershell
python scripts/compare_mcts_v4.py --opponent v1 --dry-run
```

Start the comparison yourself:

```powershell
python scripts/compare_mcts_v4.py --opponent v1
```

Defaults: **32 games, four maps, two rounds of all four species/first-player
roles per map**, 1.5 seconds thinking per move, 2-second hard allowance,
200-ply cap, 100,000-iteration ceiling, two workers, seed 20261028.
Prepared maps are `testmap2`, `thetrap`, `val-large-1290000`, and
`val-medium-1280000` in `.local/maps/mcts-vs-best-ab/`.
See [WATCH_MATCH.md](WATCH_MATCH.md) if course assets need preparation.

For four additional games now and the rest later:

```powershell
python scripts/compare_mcts_v4.py --opponent v1 --max-games 4
python scripts/compare_mcts_v4.py --opponent v1
```

Completed games are checkpointed separately. An unfinished game restarts.
Progress heartbeats appear approximately every 15 seconds with parallel workers.
Keep the machine awake and run timed campaigns sequentially to avoid CPU contention.

Outputs:

```text
.local/campaigns/mcts-v4-vs-v1/report.md
.local/campaigns/mcts-v4-vs-v1/report.json
.local/campaigns/mcts-v4-vs-v1/tuning.md
.local/campaigns/mcts-v4-vs-v1/games/game-*.json
```

Each raw game includes `v4_decisions`: contexts, parameter-pair observations,
mean simulation returns and controller CPU/wall time. `tuning.md` aggregates
context counts and completed simulations per pair. The ordinary report retains
actual match scores, tree/rollout depths, iterations, faults and timeouts.
The extra Markdown summary is regenerated when a launcher session ends; raw
game checkpoints are saved immediately after each finished game.

Source hashes include both shared runtime files and all isolated V4 Python
files plus its launcher. Resuming refuses mixed code, maps, Python or settings;
use a fresh `--checkpoint` directory after changes.

Later comparisons are available with `--opponent v3`, `--opponent julian-width7`,
or `--opponent julian-reference`. Julian's specs/status are read verbatim from
`scripts/ab2_retained_profiles.json`; no claim that width7 is universally best.
Each opponent has a separate checkpoint directory.

The fixed-control ablation uses a separate default directory:

```powershell
python scripts/compare_mcts_v4.py --agent "mcts-v4:adaptive=False" --opponent v1
```

V4 is explicitly registered by this launcher, including in Windows worker
processes. It is not yet auto-discovered by `main.py` or `tournament.py`.
Integrate it into `agents/` only after existing campaigns finish and we decide
to retain it; this preserves the current campaign's source provenance.

## Acceptance and verification

Compare the exploration-only variant against V1 under the same wall-time budget. Examine macro map
score and individual maps alongside iterations per decision, rollout cost,
controller overhead, faults and timeouts. Thirty-two games are an initial screen,
not a statistically conclusive ranking. Confirm promising changes on independent
seeds and unseen maps; do not tune thresholds on the eventual test set.
Only then compare with V3 and retained Julian alpha-beta candidates.

Targeted checks:

```powershell
python -m unittest tests.test_mcts_v4 tests.test_compare_mcts_v4 -v
```

They cover exact fixed-configuration parity with V1 on all four development
maps and both species, contextual domains, shared tuner statistics, deterministic
seeding, interrupted simulations, stochastic battles, guaranteed joint kills,
clock rewards, memory, deadline fallback, source pinning, dry-run behavior,
fixed-horizon exploration tuning, and Windows spawn/checkpoint-resume fixtures.
The fixtures are functional tests, not strength comparisons. No exploration-only
campaign has been started automatically.
