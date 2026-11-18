COMPLETE: 4/4 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                               | ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------|
| ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                               —                               |         1.00±0.00         |
| mcts-v6:iterations=100000                                     |                           0.00±0.00                           |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | +246 | 1.000 | 4 | 1.52 | 1.50 | 0 | 0 |
| 2 | mcts-v6:iterations=100000 | -246 | 0.000 | 4 | 1.50 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.82 / 7 | 5.14 / 6 | 0 | 0 | 0 | 380.99 / 379.50 |

Results for ab2risktie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| thetrap | 4 | 4 | 0 | 0 | 1.000 |
