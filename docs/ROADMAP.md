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

## Next: implement and validate the simulator

Build an in-process model that accepts a board and a legal turn, resolves its
outcomes, and returns a new board. Search and training will use this model.

Completion criteria:

- Apply empty-cell moves, friendly merges, human conversion, and enemy battles.
- Resolve a whole turn consistently, including groups arriving together.
- Model battle winners and conditional survivor counts, with seedable randomness.
- Preserve the input state so competing search branches remain independent.
- Test deterministic thresholds and survivor distributions against the brief.
- Compare deterministic scenarios and repeated random-battle outcomes with the
  supplied Server v3.2.1. A shared random seed does not imply identical random
  draws across different server implementations.
- Investigate the brief's splitting ambiguity: its rules allow splitting, while
  the protocol text caps move count by group count. Verify accepted behavior
  before broadening `GameState.validate_moves` or generating split turns.

Suggested parallel work for the four teammates:

| Area | First deliverable |
| --- | --- |
| Board transitions | Movement, merging, immutable search-state transitions |
| Combat | Seeded battle resolution and probability/distribution checks |
| Server validation | Small scenario maps and comparisons with the supplied server |
| Evaluation | Match-record format, map families, and baseline result collection |

Agree on the simulator interface together before splitting these tasks into
separate branches and pull requests.

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
