COMPLETE: 4/4 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                           | ab2tie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|-----------------------------------------------------------|-----------------------------------------------------------|---------------------------|
| ab2tie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                             —                             |         0.50±0.49         |
| mcts-v6:iterations=100000                                 |                         0.50±0.49                         |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | ab2tie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | +0 | 0.500 | 4 | 1.50 | 1.50 | 0 | 0 |
| 2 | mcts-v6:iterations=100000 | +0 | 0.500 | 4 | 1.50 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.34 / 7 | 5.41 / 6 | 0 | 0 | 0 | 120.00 / 119.47 |

Results for ab2tie:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| thetrap | 4 | 2 | 0 | 2 | 0.500 |
