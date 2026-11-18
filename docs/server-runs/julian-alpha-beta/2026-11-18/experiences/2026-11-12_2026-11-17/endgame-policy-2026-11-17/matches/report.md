COMPLETE: 8/8 games.

Score of the ROW agent against the COLUMN agent (1 = always wins):

|                                                               | ab2endgame:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | mcts-v6:iterations=100000 |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------|
| ab2endgame:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 |                               —                               |         0.38±0.29         |
| mcts-v6:iterations=100000                                     |                           0.62±0.29                           |             —             |

| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |
|---|---|---|---|---|---|---|---|---|
| 1 | mcts-v6:iterations=100000 | +42 | 0.625 | 8 | 1.51 | 1.50 | 0 | 0 |
| 2 | ab2endgame:depth=1,max_depth=24,width=7,extra=0,tt_size=50000 | -42 | 0.375 | 8 | 1.51 | 1.50 | 0 | 0 |

Depths below count individual player turns (plies). Means use completed iterations/rollouts.

| Agent | Mean / max tree depth | Mean / max rollout depth | Extra tactical plies | Multi-group turns | Loop cutoffs | Search wall / CPU s |
|---|---|---|---|---|---|---|
| mcts-v6:iterations=100000 | 3.53 / 6 | 5.80 / 6 | 0 | 0 | 0 | 463.52 / 461.89 |

Results for ab2endgame:depth=1,max_depth=24,width=7,extra=0,tt_size=50000:

| Map | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| holdout-medium-20261113 | 4 | 2 | 0 | 2 | 0.500 |
| unseen-medium-20261117 | 4 | 0 | 2 | 2 | 0.250 |
