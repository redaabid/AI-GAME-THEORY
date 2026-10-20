# Common base: plug in a model, compare them all

Every model (alpha-beta, OEP, Portfolio Greedy Search, MCTS, neural...) uses the
same interface. The same code then plays live on the server, in CPU matches,
and in the round-robin tournament, so results are directly comparable.

| File | Role |
| --- | --- |
| `agents/__init__.py` | `Agent` interface, registry, spec strings, safety net (`safe_choose`) |
| `agents/builtin.py` | `random`, `baseline`, `mcts` adapters |
| `agents/portfolio.py` | Portfolio Greedy Search (`portfolio`) |
| `agents/alphabeta.py` | Alpha-beta over macro-turns with chance nodes (`alphabeta`) |
| `agents/oep.py` | Online Evolutionary Planning (`oep`) |
| `macro.py`, `evaluation.py`, `playbook.py`, `lookahead.py` | Shared building blocks (see below) |
| `tune.py` | Offline tuning: SPSA, genetic search, Texel |
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

## Shared building blocks for the search engines

The alpha-beta, OEP, and Portfolio Greedy Search reuse the same pieces. Use
them instead of rewriting your own, so the engines differ only by their search:

| Module | What it gives | Typical use |
| --- | --- | --- |
| `macro.py` | `Order(source, count, goal)` and `orders_to_moves`: one legal step per order, rules 3 and 5 enforced; `needed()` = humans h or ceil(1.5 × enemy) | Action space: "this group sends N toward that target" |
| `evaluation.py` | `evaluate(position, species)`: material + human race (who converts each group first) + immediate threats; `WEIGHTS` for Texel | Leaf evaluation for alpha-beta, OEP fitness, PGS |
| `playbook.py` | Scripts `eat`, `attack`, `flee`, `merge`, `split`; `play_turn`, `playout` | PGS portfolio, OEP opponent model and population seeds |
| `simulate_turn(position, moves, None)` | Deterministic battles (likely winner keeps its mean survivors) | Noise-free look-ahead; pass an RNG for real games |
| `lookahead.py` | `candidate_turns` (scripts for all groups, then one group switched); `outcomes` (win and loss branches of uncertain battles, with probabilities) | Alpha-beta children and chance nodes, OEP fitness |

`evaluate(position, species, weights, max_plies)` knows the clock: humans a side
cannot reach before the last ply are ignored, and the last ply is scored like
the server (larger population wins). Always pass `context.max_plies`.

Example: an OEP genome can be a list of `Order`s. Turn it into moves with
`orders_to_moves`, play the opponent with `playout`, and score with `evaluate`.

`portfolio` (agents/portfolio.py) is built only from these modules: start there
to see how they fit together. Its parameters are `horizon` (plies simulated),
`passes`, `default` script, `scripts`, and `weights`.

## The engines

| Spec | Search | Main parameters |
| --- | --- | --- |
| `portfolio` | One script per group, improved greedily for each side (Churchill & Buro 2013) | `horizon=10`, `passes=3` |
| `alphabeta` | Negamax, iterative deepening, transposition table, uncertain battles as chance nodes | `depth=3` (untimed), `max_depth=12`, `width=10`, `extra=0` |
| `oep` | Evolves one option per group; fitness = playout, worst case over opponent scripts | `population=16`, `generations=12`, `horizon=8`, `opponents=('eat','attack')` |
| `mcts` | Reda's adversarial UCT (search.py) | `iterations=256`, `rollout_depth=6`, ... |

With a deadline, `alphabeta` deepens and `oep` evolves until the deadline;
`depth` and `generations` only apply to untimed runs.

## Tune parameters offline

```sh
# SPSA: two perturbed copies play each other on new train maps; theta moves toward the winner.
python tune.py spsa --agent alphabeta:depth=2 --params humans=0.8,threat=0.7,discount=0.9 --iterations 40 --workers 4
# Genetic search: a population plays a fixed reference (default: the starting point).
python tune.py ga --agent oep:generations=6 --params horizon=8,mutation=0.3 --generations 8 --workers 4
# Texel: fit evaluation weights to self-play results, no game per trial.
python tune.py texel --agent portfolio --games 40
```

A parameter named like an evaluation weight goes into `weights`; any other
name is an agent keyword. Each run prints a spec such as
`alphabeta:depth=2,weights={'humans': 0.93, 'threat': 0.61}` and saves a log in
`.local/tuning/`. Check the result on `val` maps with `tournament.py` before
adopting it: one tuning run is noisy.
