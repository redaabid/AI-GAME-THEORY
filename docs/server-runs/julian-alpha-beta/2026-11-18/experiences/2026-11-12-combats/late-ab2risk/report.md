COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                            | ab2risk:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|------------------------------------------------------------|------------------------------------------------------------|---------------------------|
| ab2risk:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                             —                              |         0.50±0.35         |
| mcts-v6:iterations=100000                                  |                         0.50±0.35                          |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | ab2risk:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | +0 | 0.500 | 8 | 0.88 | 0.63 | 0 | 0 |
| 2 | mcts-v6:iterations=100000 | +0 | 0.500 | 8 | 1.50 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 2.34 / 6 | 1.03 / 5 | 0 | 0 | 0 | 28.50 / 28.47 |

Results for ab2risk:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| late-dominance-15v10 | 4 | 2 | 0 | 2 | 0.500 |
| late-risk-13v10 | 4 | 2 | 0 | 2 | 0.500 |
