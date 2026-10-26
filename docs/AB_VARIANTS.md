# AB0--AB8: implemented, auditable configurations

The original `alphabeta` agent and its shared modules are unchanged. The new
`agents/ab_variants.py` registers `ab0` through `ab8` using one modular engine.
Each move emits `AB_METRICS` JSON with feature flags, completed depth, nodes,
deadline status, bootstrap use, TT hits, re-searches and chance counts.

| Name | Active components |
|---|---|
| ab0 | Fixed-depth deterministic alpha-beta, canonical move order |
| ab1 | Iterative deepening and static move ordering |
| ab2 | ab1 plus transposition bounds and history ordering |
| ab3 | ab2 plus script-based coordinated turns, threshold splits and role/critical-group diversity |
| ab4 | ab3 plus PVS and aspiration, with full-window re-search |
| ab5 | ab3 plus bounded capture/recruitment quiescence (no stand-pat assumption) |
| ab6 | ab3 plus full finite survivor distributions and chance interval cutoffs |
| ab7 | ab3 with explicit training/validation-selected evaluation weights |
| ab8 | ab2 with an MTD(f) driver over integer scores and memory |

The deterministic transition is the existing `simulate_turn(..., None)`
surrogate, not the true random game. Only ab6 enumerates survivor distributions;
it assumes the simulator's independent destination-combat semantics. This does
not by itself independently certify the Windows DLL. Chance outcomes are lazy,
and incomplete searches are discarded on the deadline.

Move generation is bounded in every variant, including ab0. These agents do not
claim to enumerate all legal turns. AB3's critical-group diversity is a heuristic,
not a proven lossless action abstraction. All profiles use the same bounded
integer evaluation; terminal values are +/-1,000,000 and heuristic values lie
strictly between them. TT keys include rules, player, ply, game cap and search
horizon. No quiescence score is silently reused as a normal-depth exact score.

Static generated plans/children are cached within each decision (up to 2048
states), reducing repeated generation during iterative deepening. History only
permutes the already selected action set. TT capacity is bounded. Generation,
distribution construction and search check deadlines; a complete legal bootstrap
is acquired first and reported as such if no iteration completes.

Parameters: `depth` (ab0 fixed depth or untimed cap), `max_depth` (timed cap),
`width`, `extra` (selective profiles), `tt_size`, `qdepth`, `qwidth`, `aspiration`,
and `weights`. Parameters irrelevant to a feature do not magically activate it:
the emitted feature manifest is the authority.

Example (not a tuned recommendation):

```sh
python -B main.py --agent "ab4:width=10,max_depth=8" --move-time 1.5 --max-plies 200 127.0.0.1 5555
```

`ab7` deliberately requires an explicit weight dictionary. It is not called
optimized merely because it exists. `scripts/benchmark_ab_variants.py` screens
three configurations per architecture on two generated training maps and selects
between two finalists on separate generated validation maps, with balanced
species and identical budgets against the existing alphabeta. Seeds, settings,
per-game results and timings are exported. Small-budget screening is only a
bounded search for a useful setting, not global optimization or a significant
claim of strength. Re-selecting default weights is a valid negative result and
must be reported; ab7 may then behave identically to ab3.

```sh
python -B scripts/benchmark_ab_variants.py --output .local/ab-tuning/run-1
```

The course maps are reserved for the WPF campaign, not used for weight selection.
The primary campaign compares each selected architecture to ab3 on both supplied
maps, with both connection orders and 40/200-ply caps (64 games). This is a limited
compatibility/strength sample, not a tournament-wide ranking.

`scripts/run_ab_server.py` starts only owned processes, writes commands/configs,
keeps raw bot logs and server traces, and waits for `ui-evidence.json` after each
game. A separate UI observer must capture the actual WPF result; a simulator
prediction is not a substitute. With no observer, results remain unconfirmed.

Tests include an independently enumerated tiny minimax tree, TT/PVS/MTD equality,
game-cap cache isolation, expired budgets, quiescence execution, probability mass,
unconditional survivor means, extinction mass and joint arrivals. Run:

```sh
python -B -m unittest discover -s tests -v
```
