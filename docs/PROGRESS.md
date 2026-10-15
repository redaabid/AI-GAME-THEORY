# Team progress — 15 October 2026

We have a working CPU search agent and a reproducible evaluation/training-data
pipeline. The next milestone is to improve its weak matchups and train a first
small policy/value network using the exported search decisions.

## Get the latest work

The current work is on **`feat/adversarial-mcts`**, pending integration into
`main`. From an existing clone, save or commit your own work first, then run:

```sh
git fetch origin
git switch feat/adversarial-mcts
git pull --ff-only
python -m unittest discover -s tests -v
```

For a fresh clone, follow [the README setup](../README.md#get-started).
Python 3.10+ is enough for the bot, simulator, search, and tests. They use the
standard library. A GPU can accelerate the planned offline neural training.

## What is implemented

| Part | What works | Where |
| --- | --- | --- |
| Live bot | TCP protocol, board updates, species assignment, game resets, legal moves | `client.py`, `game.py`, `main.py` |
| Baseline | One whole-group move with recruitment and counterattack estimates | `strategy.py` |
| CPU simulator | Immutable boards, complete turns, splitting, joint arrivals, stochastic battles | `simulator.py`, `combat.py` |
| MCTS | Adversarial enemy decisions, sampled battle outcomes, selected recruitment splits, coordinated moves, deadline fallback | `search.py`, `candidates.py` |
| Evaluation | Multiple maps, balanced species/first player, seeds, scores, timing, reproducibility metadata | `evaluate.py` |
| Training exports | State/action/next-state records, MCTS root visits, final-outcome targets, configuration and code/map hashes | `simulate.py` |
| Team setup | Windows server preparation, runnable commands, simulator API and training-data documentation | [README](../README.md), [handoff](CPU_GPU_HANDOFF.md), [MCTS guide](MCTS.md) |

Neural training code, trained weights, and neural-guided runtime search are still
to be implemented. The current MCTS runs entirely on the CPU.

## What we verified

- **72 tests passed**, covering rules, protocol, splitting/merging, chance
  resampling, deadlines, game replay, and reproducible search from saved JSON.
- **14 reference checks passed** against the supplied server model: ten movement
  cases and four combat scenarios with 20,000 samples each.
- A short MCTS-versus-baseline match completed on the supplied Windows server.
- The final MCTS evaluation won **30 of 48 games (62.5%)** against the baseline
  across four development maps, balancing both species and first-player roles.
  It used 128 iterations per move, a 60-ply cap, and base seeds 42 and 100.
- The longest measured decision in those two evaluation runs was approximately
  **0.22 seconds**, with no search fallbacks. Larger budgets need their own timing checks.

| Development map | Combined MCTS wins / games |
| --- | --- |
| `demo.xml` | 8 / 12 |
| `endgame.xml` | 4 / 12 |
| `recruitment.xml` | 7 / 12 |
| `tactics.xml` | 11 / 12 |

These are small development runs. Endgame is the weakest measured matchup, and
we still need unseen maps and stronger opponents before selecting a final agent.
See [MCTS.md](MCTS.md#initial-measurements-and-next-work) for the settings and limits.

## Run it yourself

Export a small MCTS-versus-baseline dataset on the bundled demo map:

```sh
python simulate.py --agent mcts --opponent baseline --games 4 --iterations 128 --seed 42
```

Compare on all four bundled maps; `--games` here means games **per map**:

```sh
python evaluate.py --games 8 --iterations 128 --seed 100 --max-plies 60
```

Exports go to `.local/simulations/`; evaluation reports go to `.local/evaluations/`.
Both are ignored by Git. Each teammate can regenerate sample data using the
commands above. Keep a run's manifest and JSONL files together when sharing it.

For a graphical match, follow [Start a match](../README.md#start-a-match).

## Next tasks for the four teammates

Suggested areas to claim before starting a task branch:

| Area | First deliverable |
| --- | --- |
| CPU search | Investigate losing endgames; compare 128, 256, and 512 iterations on the same seeds/maps. Propose a rollout or leaf-evaluation improvement with a tactical regression test and before/after results. |
| Candidate turns | Improve recruitment and coordination; check whether selected splits help or leave weak groups. Submit a focused candidate-generation change with legal-turn tests and match results. |
| Evaluation | Add unseen map families and opponent comparisons. Keep training, validation, and final-test maps separate; report scores per map and an equal-weight average across maps. |
| GPU training | Build a JSONL loader and a small policy/value training prototype. Use actor-relative features and padding/masks for variable maps and candidate counts; split by whole games and map families. |

The GPU teammate should initially select `teacher == "mcts"` and
`policy_target_kind == "mcts_visits"`. Align policy labels with
`candidate_actions`, and use `value_target` for the outcome head. Baseline/random
behavior and deadline fallbacks have different label kinds. Follow the
[data contract](CPU_GPU_HANDOFF.md#data-contract-for-the-gpu-colleague) and
[search-target explanation](MCTS.md#reading-training-records).

Offline training frameworks are allowed by the instructor. Runtime search and
inference must follow the course library restrictions and fit the target CPU's
two-second turn limit.

The next shared milestone is a reproducible comparison of the improved CPU
agent, the current MCTS, and the baseline on validation maps, plus a first neural
training run with saved configuration and weights. Evaluate neural assistance
against the existing MCTS before adopting it.

## Work together

Until this branch is merged, create related task branches from
`feat/adversarial-mcts` and target it in pull requests:

```sh
git switch feat/adversarial-mcts
git pull --ff-only
git switch -c your-name/task-name
```

Claim an area with the team, keep each PR focused, and include the relevant tests
and evaluation settings. Keep datasets, checkpoints, course ZIPs, and local server
files outside commits. The known rule-profile discrepancy and byte-population
limit are documented in [the simulator handoff](CPU_GPU_HANDOFF.md#explicit-rules-and-supported-limits).
