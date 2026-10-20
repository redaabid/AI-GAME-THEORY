# Engine comparison (CPU simulator, server v3.2.1 rules)

Untimed runs (`--move-time 0`) on generated `val` maps, both species and both
first-player roles, common battle seeds. Score = row agent against column agent
(1 = always wins), with a 95% interval. Reproduce with the commands shown.

## Five engines at small budgets

`python tournament.py --agents baseline portfolio "alphabeta:depth=3" oep "mcts:iterations=128" --random-maps 6 --family large --rounds 1 --move-time 0`

|                     | baseline | portfolio | alphabeta:depth=3 | oep | mcts:iterations=128 |
|---------------------|---|---|---|---|---|
| baseline            | — | 0.38±0.18 | 0.31±0.18 | 0.35±0.19 | 0.15±0.14 |
| portfolio           | 0.62±0.18 | — | 0.33±0.19 | 0.35±0.19 | 0.62±0.18 |
| alphabeta:depth=3   | 0.69±0.18 | 0.67±0.19 | — | 0.58±0.20 | 0.50±0.17 |
| oep                 | 0.65±0.19 | 0.65±0.19 | 0.42±0.20 | — | 0.46±0.19 |
| mcts:iterations=128 | 0.85±0.14 | 0.38±0.18 | 0.50±0.17 | 0.54±0.19 | — |

Elo (baseline = 0): alphabeta +180, mcts +157, oep +142, portfolio +110.

## Larger budgets

`python tournament.py --agents "alphabeta:depth=3" "alphabeta:depth=5" "mcts:iterations=512" "oep:generations=30,horizon=12" --random-maps 4 --family large --map-seed 50 --rounds 1 --move-time 0`

|                               | ab depth=3 | ab depth=5 | mcts 512 | oep 30 gen |
|-------------------------------|---|---|---|---|
| alphabeta:depth=3             | — | 0.31±0.23 | 0.62±0.24 | 0.31±0.23 |
| alphabeta:depth=5             | 0.69±0.23 | — | 0.81±0.19 | 0.69±0.23 |
| mcts:iterations=512           | 0.38±0.24 | 0.19±0.19 | — | 0.41±0.23 |
| oep:generations=30,horizon=12 | 0.69±0.23 | 0.31±0.23 | 0.59±0.23 | — |

Alpha-beta gains the most from extra budget. With a 1.7 s deadline it reaches
depth 8-9 on typical large-map positions and depth 4 on a crowded 10-group board.

## Tuning attempts (alpha-beta evaluation weights)

| Method | Result | Check: tuned vs default, depth 3, 64 games per family |
|---|---|---|
| SPSA, 30 iterations at depth 2 | discount 0.9 → 0.66, others ≈ unchanged | medium 0.56, large 0.45: not significant |
| Texel, 40 self-play games | humans 3.4, groups 3.2, discount 0.46 | medium 0.38, large 0.41: worse |

The default `evaluation.WEIGHTS` stay. Texel fits who wins from a position, which
does not reward good play directly; more games and an SPRT check are needed
before trusting any tuned weights.

These numbers come from the simulator with Adam's MacBook timings. Confirm the
final choice with `--move-time 2` on the tournament machines.
