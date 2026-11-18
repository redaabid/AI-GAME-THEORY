COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                               | ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------|
| ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                               —                               |         0.44±0.21         |
| mcts-v6:iterations=100000                                     |                           0.56±0.21                           |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | mcts-v6:iterations=100000 | +21 | 0.562 | 8 | 1.51 | 1.50 | 0 | 0 |
| 2 | ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | -21 | 0.438 | 8 | 1.50 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.44 / 7 | 5.77 / 6 | 0 | 0 | 0 | 964.52 / 960.98 |

Results for ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| holdout-medium-20261113 | 4 | 1 | 1 | 2 | 0.375 |
| testmap2 | 4 | 0 | 4 | 0 | 0.500 |
