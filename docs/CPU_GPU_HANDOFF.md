# CPU simulator and GPU handoff

## Work on the CPU now

The simulator, baseline agents, and exports use only the Python standard library.
Run all commands from the repository folder:

```sh
python -m unittest discover -s tests -v
python simulate.py --games 20 --seed 42
```

Search is also ready on the CPU. Export search decisions with:

```sh
python simulate.py --agent mcts --opponent baseline --games 4 --iterations 128 --seed 42
```

Use `--opponent mcts` for search self-play. Read [MCTS.md](MCTS.md) for the
visit-target fields, fallback filtering, search configuration, and measured limits.

The runner prints a fresh `.local/simulations/` directory. A completed run contains:

| File | Purpose |
| --- | --- |
| `manifest.json` | Schema, rule profile, Python version, map/code fingerprints, seeds, settings, and aggregate score |
| `games.jsonl` | One match summary per line, including species, first player, winner, and termination reason |
| `transitions.jsonl` | One state/action/next-state example per line with policy and outcome targets |

The manifest is written last. Treat a run without it as incomplete. Keep these
files together when transferring a run to your colleague. Generated files stay
in `.local/`, which Git ignores; share the code through GitHub and transfer large
datasets separately.

The baseline score is win = 1, draw = 0.5, loss = 0. This smoke-test opponent is
random, so the resulting score measures this pairing, not tournament strength.

## Simulator interface

```python
import random
from simulator import load_map, simulate_turn, get_outcome

initial = load_map("maps/demo.xml", rules_profile="server-v3.2.1")
rng = random.Random(42)
next_position = simulate_turn(initial, [(0, 0, 8, 1, 1)], rng)
result = get_outcome(next_position, max_plies=100)
```

`Position` is immutable: the input board, dictionary, and cells remain unchanged.
`simulate_turn` validates the entire turn, debits sources, combines all arrivals
at each destination before fighting, then switches `to_play` and increments `ply`.
Destinations resolve in sorted `(x, y)` order, making input move-list order
irrelevant for a fixed Python RNG state.

A move is `(source_x, source_y, count, target_x, target_y)`. A turn is a nonempty
list of moves. Partial moves, splitting, and joint arrivals are supported. A
source cannot also be a destination that turn. All outgoing counts are checked
together, and invalid plans are rejected before consuming randomness.

Pass an explicit `random.Random` instance. Reusing one instance gives a stream
of battle outcomes; restoring/copying its state reproduces a branch. The RNG is
mutable even though boards are immutable. Different RNG implementations, including
the .NET server's generator, need statistical comparison rather than identical
draws for the same seed.

`Position.from_game_state(state)` adapts a network board. Set `ply` explicitly
when known: network `state.turn` counts our UPDs, not both players' moves.
`position.to_game_state()` returns an independent view for `strategy.choose_moves`.
Use `position.to_dict()` / `Position.from_dict(data)` for JSON or process handoff.

`get_outcome` returns `None` while the game continues. An `Outcome` has `winner`
(`vampires`, `werewolves`, or `None` for a draw) and a reason (`elimination` or
`ply_limit`). At the ply cap, the species with more creatures wins; humans do not
count toward either side. Wall-clock game duration is outside the pure simulator.

## Explicit rules and supported limits

The default is `server-v3.2.1`, matching the supplied model on the checked cases.
The written `brief` profile additionally guarantees victory to a defender at
least 1.5 times stronger. For example, 10 attacking 15 has probability 0 under
`brief`, and 1/3 under `server-v3.2.1`. Both profiles guarantee human conversion
at equal strength and enemy defeat at a 1.5 attacker advantage.

Choose the profile explicitly for experiments:

```sh
python simulate.py --games 20 --seed 42 --rules-profile brief
```

Both profiles use the documented conditional survivor distributions. A winner
may have zero survivors; an empty battle cell is removed. Combined arrivals fight
as one group. The supplied model accepted splitting one group into multiple moves,
so the shared validator permits up to 255 move records rather than capping them
by the original number of groups.

Coordinates, dimensions, populations, and outbound counts currently follow the
one-byte protocol. If a turn could produce more than 255 creatures in one cell,
the simulator raises `ValueError`; overflow/wrapping behavior is not modeled.
Reference checking covers the supplied DLL with SHA-256
`a8ad22443da5d6456d1a7365e15783afba1d7a73f2c51b395972192c70022929`.
The optional Windows check is `scripts/check_server_model.ps1`; it records the
DLL hash, observed movement outcomes, and sampled combat moments under `.local/`.
Additional server versions and scenarios need their own comparisons.

## Data contract for the GPU colleague

`schema_version` is **1**. Positions contain:

```json
{
  "schema_version": 1,
  "rows": 5,
  "columns": 7,
  "to_play": "vampires",
  "ply": 0,
  "rules_profile": "server-v3.2.1",
  "cells": [[0, 0, 0, 8, 0], [6, 4, 0, 0, 8]]
}
```

Only occupied cells are stored, sorted by `(x, y)`. Each cell is
`[x, y, humans, vampires, werewolves]`. Board sizes vary. Interpret troop channels
relative to `to_play` when building actor-relative features.

Each transition has these fields:

| Field | Meaning |
| --- | --- |
| `game_id`, `seed` | Match identity and reproducibility metadata |
| `teacher` | `baseline`, `random`, or `mcts` |
| `state`, `next_state` | Versioned positions before and after the move |
| `candidate_set` | `single_full_group_v1` for baseline/random; `recruitment_turns_v1` for MCTS |
| `candidate_actions` | List of turn plans; each plan is a list of five-integer moves |
| `action` | The turn plan that was played |
| `policy_target_kind` | `behavior_one_hot`, `mcts_visits`, or `fallback_one_hot` |
| `policy_target` | One-hot behavior/fallback, or normalized MCTS visits, aligned with candidates |
| `value_target` | Final outcome from `state.to_play`'s perspective: -1, 0, or +1 |
| `termination` | How the match ended |
| `search` | MCTS metadata: visits, completed iterations, seed, action values, fallback |

Default runs remain **pipeline examples from baseline/random play**. Search runs
also contain MCTS visit targets. Filter by both `teacher` and `policy_target_kind`:
random decisions and deadline fallbacks are not search targets. The search policy
is limited by its candidate set, horizon, and budget; visits are not a guarantee
of expert strength. No neural network is trained by these commands.

The GPU colleague can implement parsing, variable-size/candidate masking, and
a small policy/value training loop with the search-generated targets. Compare
search budgets and add diverse opponents before large training runs. Keep rule profiles and horizon
settings explicit, and split datasets by whole games/map families so related
states do not leak across training, validation, and final test sets.

The instructor permits AI frameworks for offline training. Export weights and
their schema/profile/code metadata; runtime search and inference remain the
team's implementation and must be measured on the target CPU.
