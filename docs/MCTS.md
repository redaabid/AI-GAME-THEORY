# CPU search: adversarial MCTS

This is the first search agent, implemented using the Python standard library.
It is a measurable starting point for the team; map coverage and finite search
budgets still limit its strength. No neural model is required.

## Try it

From the repository folder, generate search examples against the baseline:

```sh
python simulate.py --agent mcts --opponent baseline --games 4 --iterations 128 --seed 42
```

Compare across all four bundled development maps:

```sh
python evaluate.py --games 8 --iterations 128 --seed 100 --max-plies 60
```

`--games` is the number **per map** in evaluation, and the total on the selected
map in simulation. Evaluation requires a multiple of four and balances species
and first player independently on every map. Reports under `.local/evaluations/`
include per-map wins/draws/losses, seeds, code/map hashes, rule profile, and timing.
The macro score weights each map equally. An invalid turn aborts the run.

Choose other maps with `--maps first.xml second.xml` in evaluation, or
`--map first.xml` in simulation. Add `--rules-profile brief` for the written
defender rule. Add `--opponent mcts` to simulation for search self-play.

For a graphical match, start the supplied server and use two terminals:

```sh
python main.py --agent mcts --move-time 0.15 --iterations 128 --name Search 127.0.0.1 5555
python main.py --agent baseline --name Baseline 127.0.0.1 5555
```

The short budget suits the 30-second demo match. For longer tournament matches,
increase `--move-time` to its default of 1.5 seconds and the iteration cap to its
default of 10,000. Live budgets are capped at 1.8 seconds to reserve some of the
two-second allowance for communication. The deadline includes board adaptation,
candidate generation, tree search, and rollout work. Checks are cooperative;
Python and OS scheduling provide no hard real-time guarantee. Measure on the
actual tournament machine. An expired deadline returns a validated fallback or
the best action from completed search iterations.

Offline simulation/evaluation use a fixed iteration count by default. Omit
`--move-time` there for reproducibility; timed runs depend on machine throughput.
`python main.py` continues to select the original baseline for comparison.

## What the search does

1. Establish a legal fallback before building the tree.
2. Rank a bounded set of whole-turn plans: full moves, exact recruitment moves,
   selected two-way recruitment splits, joint arrivals, and compatible movements
   from independent groups. Validate counts, source/destination constraints, and
   the simulator's one-byte population limit.
3. Select decision actions using UCT. Values are stored from the root player's
   perspective; enemy nodes reverse the exploitation sign to seek enemy rewards.
   Progressively expose up to `ceil(2 * sqrt(node_visits + 1))` ranked candidates,
   bounded by the configured candidate cap (default 32).
4. Sample a fresh battle outcome every time an edge is traversed. Each action
   can lead to several child boards. Chance outcomes are never selected by UCB,
   maximized, or fixed after the first lucky draw.
5. At a new leaf, play up to six baseline rollout plies. At the horizon, use a
   bounded estimate of material and human recruitment races. Actual terminal
   results use -1/0/+1. The tree depth is capped at 12 decision plies by default.
6. Back up completed iterations and play the most visited root action, breaking
   visit ties by its mean value. The live bot logs iterations and decision time.

This adapts [Kocsis and Szepesvari's UCT method (2006)](https://web.engr.oregonstate.edu/~afern/classes/cs533/notes/uct.pdf)
to alternating players and the supplied simulator. The recruitment heuristics,
candidate pruning, finite horizons, and most-visited recommendation are our
implementation choices. This implementation does not inherit a blanket optimality
guarantee from that paper. Candidate pruning can omit a winning turn; short
rollouts and limited enemy exploration can miss tactical refutations.

## Reading training records

The position schema remains version 1. Every transition identifies its candidate
set and target kind. For MCTS training, select:

```python
if record["teacher"] == "mcts" and record["policy_target_kind"] == "mcts_visits":
    visits = record["search"]["visits"]
    policy = record["policy_target"]  # visits[i] / sum(visits)
    outcome = record["value_target"]  # final game result for state.to_play
```

`search` also records completed iterations, the per-search seed, fallback status,
and per-action mean values. Those means include heuristic horizon estimates;
they are not calibrated win probabilities. Interrupted iterations add no visits.
Fallback examples use `fallback_one_hot`, and baseline/random examples use
`behavior_one_hot`. Filter these separately. The manifest records the search
configuration and says `candidate_set: per_transition` for runs using search.

`candidate_actions[i]`, `search.visits[i]`, and `policy_target[i]` align. Each
action is an entire list of moves. Pad and mask the variable number of actions
when forming GPU batches. All listed plans are legal; zero visits means
unexplored, and omitted plans may still be legal. Value targets use the final
elimination or recorded ply-cap outcome, never the heuristic search value.

Battle randomness is separate from policy/search randomness, so actual game
transitions replay with `random.Random(game_seed)` without rerunning search.
Wall-clock measurements are kept in evaluation reports, outside reproducible
training records. See [CPU_GPU_HANDOFF.md](CPU_GPU_HANDOFF.md) for state features.

## Initial measurements and next work

Both runs below used Python 3.12.9, `server-v3.2.1`, 128 iterations, a 60-ply
game cap, and all four bundled development maps. Roles were balanced on each map.
Score is win = 1, draw = 0.5, loss = 0. Local JSON reports retain full game details.

| Base seed | Games per map | MCTS vs baseline | Macro score |
| --- | --- | --- | --- |
| 42 | 4 | 10 wins, 0 draws, 6 losses | 0.6250 |
| 100 | 8 | 20 wins, 0 draws, 12 losses | 0.6250 |
| Combined | 12 | 30 wins, 0 draws, 18 losses | 0.6250 |

The 72-test suite covers seeded chance sampling, legal joint/split turns,
adversarial tactics, deadline fallbacks, interrupted iteration labels, game replay,
JSON/order-independent search replay, and TCP games with both species. A short MCTS-vs-baseline compatibility match
also completed on the supplied Windows server with its two-second turn limit.

Across these final runs the longest measured MCTS decision was 0.219 seconds,
with no search fallbacks. This measures 128-iteration searches on this machine,
not the timing of the larger live iteration cap.

Map-level results vary: in the eight-game-per-map run, MCTS won 2/8 on endgame
and 8/8 on tactics. Collect more seeds and inspect each map. These
maps are development fixtures, not a held-out test set or evidence of tournament
dominance. Evaluation records are separate from training exports.

Next: compare larger search budgets, add unseen map families and opponent agents,
inspect weak recruitment/endgame matchups, and improve candidate coverage and
rollout/evaluation quality. The GPU teammate can test policy/value training with
the exported visits now; retain a final untouched map set before model selection.
