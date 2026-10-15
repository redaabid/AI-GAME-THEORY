# Project scope and next milestone

We are a four-person team with an approximately two-month project window. The
goal is to develop an opponent-aware AI, compare approaches on diverse maps,
and select a strong tournament agent using reproducible results.

## Current milestone: working baseline

- TCP client and automatic command-line launch with server IP and port.
- Board updates, species identification, and movement validation.
- One-group benchmark strategy with immediate counterattack estimates.
- Protocol and strategy tests, including a local mock server.
- A completed two-bot compatibility match on the supplied Windows server.
- Shared setup instructions and a local server-preparation command.

The current strategy provides a benchmark. Its score estimates do not constitute
a complete stochastic simulator or a deeper adversarial search.

## Implemented: CPU simulator and first data export

`simulator.py` accepts a board, a legal turn, and an explicit RNG, then returns
a new immutable board. `simulate.py` runs baseline/random games and exports
versioned JSONL records for the GPU colleague's pipeline.

Completion criteria:

- [x] Apply empty-cell moves, friendly merges, human conversion, and enemy battles.
- [x] Resolve combined arrivals before battle and preserve independent branches.
- [x] Model battle winners and conditional survivors with seedable randomness.
- [x] Test thresholds, empty outcomes, conservation, replay, and distributions.
- [x] Compare movement cases and four sampled combat scenarios with the supplied DLL.
- [x] Verify that the supplied model accepts splitting one group into multiple moves.
- [x] Document the stronger-defender discrepancy and separate the two rule profiles.
- [x] Export labeled, reproducible pipeline examples with map and code fingerprints.
- [ ] Expand reference coverage and investigate populations beyond one-byte limits.

See [CPU_GPU_HANDOFF.md](CPU_GPU_HANDOFF.md) for the API, dataset schema, exact
reference DLL, and supported limits. The current exporter uses baseline/random
agents; search-generated learning targets are the next stage.

## Next: recruitment-aware adversarial MCTS

- Generate a useful, validated set of whole-turn plans, including coordinated
  movement and selected splits, and expand candidates as the budget permits.
- Model enemy decisions adversarially and battle outcomes probabilistically.
- Use a bounded search budget with a validated fallback before the two-second deadline.
- Compare against existing agents on held-out maps, both species and first-player roles.
- Export search-policy targets before starting competitive neural training.

Suggested parallel work for the four teammates:

| Area | First deliverable |
| --- | --- |
| Search core | Adversarial MCTS over the immutable simulator with a deadline and fallback |
| Candidate turns | Recruitment races, coordinated moves, and useful split sizes |
| Evaluation | Additional reference scenarios, map families, and repeated match comparisons |
| GPU pipeline | Parse exported records and prepare policy/value training batches |

Use the simulator interface and schema in the handoff document when splitting
these tasks into separate branches and pull requests.

## Later milestones

1. **Evaluation harness:** repeated matches on multiple map families, both sides,
   fixed seeds where supported, timing, invalid-move counts, and outcome tables.
2. **Search:** compare expectiminimax and MCTS under the two-second turn budget.
   Explore opponent recruitment races and useful splitting decisions.
3. **Offline learning:** train small policy/value networks using search-generated
   examples and diverse opponents; export weights for our runtime implementation.
4. **Population training:** add counter-agents and prioritize training maps where
   another agent exposes a learnable weakness.
5. **Selection and delivery:** choose using average validation match score across
   maps, opponents, and starting sides; inspect weak matchups, then evaluate once
   on held-out test maps. Finish the report and five-minute presentation.

Use win = 1, draw = 0.5, loss = 0 for internal match-score comparisons unless the
instructor specifies different scoring. Keep training, validation, and final
test maps separate. Record enough repeated games to show uncertainty in results.
