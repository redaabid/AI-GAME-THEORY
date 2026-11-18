COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                           | ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|-----------------------------------------------------------|-----------------------------------------------------------|---------------------------|
| ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                             —                             |         0.44±0.32         |
| mcts-v6:iterations=100000                                 |                         0.56±0.32                         |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | mcts-v6:iterations=100000 | +21 | 0.562 | 8 | 1.51 | 1.51 | 0 | 0 |
| 2 | ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | -21 | 0.438 | 8 | 0.25 | 0.24 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 2.13 / 6 | 1.06 / 5 | 0 | 0 | 0 | 28.50 / 28.44 |

Results for ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| late-dominance-15v10 | 4 | 1 | 1 | 2 | 0.375 |
| late-risk-13v10 | 4 | 2 | 0 | 2 | 0.500 |
