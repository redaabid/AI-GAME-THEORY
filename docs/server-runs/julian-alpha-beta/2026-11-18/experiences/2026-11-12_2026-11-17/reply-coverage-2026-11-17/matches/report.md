COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                               | ab2replies:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------|
| ab2replies:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                               —                               |         0.69±0.30         |
| mcts-v6:iterations=100000                                     |                           0.31±0.30                           |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | ab2replies:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | +64 | 0.688 | 8 | 1.52 | 1.50 | 0 | 0 |
| 2 | mcts-v6:iterations=100000 | -64 | 0.312 | 8 | 1.53 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.43 / 6 | 5.57 / 6 | 0 | 0 | 0 | 762.03 / 759.45 |

Results for ab2replies:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| holdout-medium-20261113 | 4 | 1 | 1 | 2 | 0.375 |
| unseen-medium-20261117 | 4 | 4 | 0 | 0 | 1.000 |
