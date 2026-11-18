COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                             | ab2goals:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|-------------------------------------------------------------|-------------------------------------------------------------|---------------------------|
| ab2goals:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                              —                              |         0.56±0.21         |
| mcts-v6:iterations=100000                                   |                          0.44±0.21                          |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | ab2goals:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | +21 | 0.562 | 8 | 1.52 | 1.50 | 0 | 0 |
| 2 | mcts-v6:iterations=100000 | -21 | 0.438 | 8 | 1.70 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.45 / 6 | 5.74 / 6 | 0 | 0 | 0 | 1195.73 / 1187.20 |

Results for ab2goals:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| holdout-medium-20261113 | 4 | 2 | 1 | 1 | 0.625 |
| testmap2 | 4 | 0 | 4 | 0 | 0.500 |
