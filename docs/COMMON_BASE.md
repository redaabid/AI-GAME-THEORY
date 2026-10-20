# Common base: plug in a model, compare them all

Every model (alpha-beta, OEP, Portfolio Greedy Search, MCTS, neural...) uses the
same interface. The same code then plays live on the server, in CPU matches,
and in the round-robin tournament, so results are directly comparable.

| File | Role |
| --- | --- |
| `agents/__init__.py` | `Agent` interface, registry, spec strings, safety net (`safe_choose`) |
| `agents/builtin.py` | `random`, `baseline`, `mcts` adapters |
| `tournament.py` | Round-robin in the simulator: score matrix, Elo, timing, faults |
| `mapgen.py` | Fair (point-symmetric) random maps with train/val/test splits |
| `main.py` | Live client; `--agent` accepts any registered spec |

## Add a model

Create `agents/<your_model>.py`. It is discovered automatically, so there is no
list to edit and no merge conflict with teammates:

```python
from agents import Agent, register


@register("alphabeta")
class AlphaBeta(Agent):
    def __init__(self, depth=4, discount=0.95):  # Parameters = variants.
        self.depth, self.discount = depth, discount

    def new_game(self, position, species, seed):
        """Optional: reset per-game memory (opponent model, opening plan...)."""

    def choose_moves(self, position, context):
        # position: immutable simulator.Position; our species is position.to_play.
        # context.deadline: perf_counter() limit (margin already removed), or None.
        # context.max_plies, context.history: our previous (position, moves) turns.
        # Return a list of (x, y, count, target_x, target_y) moves.
        ...
```

Then use it everywhere by its spec: `alphabeta`, `alphabeta:depth=6`,
`alphabeta:depth=6,discount=0.9`.

Rules for every agent:

- **Respect `context.deadline`.** Check `context.time_left()` and return your best
  turn so far. Deadlines are `None` in untimed runs.
- **Use the simulator** (`simulator.simulate_turn`, `combat.win_probability`) for
  look-ahead. It matches Server v3.2.1, not the PDF.
- **No AI, tree, or graph libraries at runtime** (brief). Offline training may use them.
- **Do not worry about crashes.** `safe_choose` validates every turn and sends a
  greedy legal move if your agent raises or returns an illegal turn. Fallbacks
  are counted as *faults* in the tournament: a fault means a bug to fix.

## Run a tournament

```sh
python tournament.py --agents baseline mcts "mcts:iterations=64" --random-maps 6 --rounds 2
```

Each pair plays each map in rounds of 4 games, covering both species and both
first-player roles. Games with the same map, round, and role share a battle seed
across pairs. Output:

- **Score matrix:** the row agent's mean score against the column agent, ±95% interval.
- **Ranking:** Bradley-Terry Elo (baseline = 0), max/p95 decision time, timeouts, faults.
- `.local/tournaments/<time>.json` (every game) and a `.md` copy of the tables.

Useful options:

| Option | Default | Meaning |
| --- | --- | --- |
| `--move-time` | 2.0 | Seconds per move, as the brief says (the supplied config uses 5); `0` = untimed and reproducible |
| `--on-timeout` | `skip` | A move slower than `--move-time` loses the turn, like on the server |
| `--margin` | 0.3 | Safety margin removed from the agent's deadline |
| `--max-plies` | 200 | Server `MaxPlays`; both players' turns count |
| `--maps` | `maps/` | XML files or folders; combine with `--random-maps N --family small/medium/large` |
| `--workers` | 1 | Parallel games. Keep it ≤ physical cores for timed runs, or timings are wrong |

Timed results depend on the machine. Compare agents on the same machine, and
confirm the final choice with `--move-time 2` on a CTI machine.

## Maps and fair comparisons

```sh
python mapgen.py --count 20 --family medium --split val
```

Generated maps are point-symmetric: the werewolves start on the mirror of the
vampires, and the humans are mirrored too. The `train`, `val`, and `test` splits
use disjoint seeds:

- **train**: tune weights and parameters (Texel, SPSA, genetic search).
- **val**: choose between models and variants.
- **test**: report the final numbers once, in the report.

`tournament.py --random-maps` uses the `val` split by default.

## Next shared pieces

The alpha-beta, OEP, and Portfolio Greedy Search all need the same building
blocks. Write them once, in shared modules, rather than once per model:

- macro-actions per group ("go to target", minimal split): partly in `candidates.py`;
- the human-race evaluation (who reaches each human group first, with enough troops);
- the Portfolio scripts (eat, attack, flee, merge), reused by OEP as its opponent model.
