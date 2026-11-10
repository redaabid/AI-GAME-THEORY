# V7 controlled stalemate results — 8 November 2026

The controlled experiment completed all eight continuations. Four preselected
future seeds paired V7 objectives on/off against the same V6 opponent, starting
at the recorded 16-16 board at ply 58 with real history for both sides.
Each main decision completed exactly 256 MCTS iterations, without deadlines,
and the original cap remained ply 200. See the [experiment design and commands](MCTS_V7_CONTROLLED.md).

Local evidence: `.local/experiments/v7-stalemate-20261108-paired256/`.
All **1,136 new transitions** replayed exactly from their saved moves and future
battle seeds. The historical 58-ply prefix was also independently checked.
No faults occurred; timeout performance is not measured in an untimed test.
The production V7 and core sources still match the previous campaign hashes.

## Outcome

| Goals | Wins | Draws | Losses | Match score | Objective decisions |
| --- | ---: | ---: | ---: | ---: | ---: |
| On | 0 | 4 | 0 | 50% | 32 (8 per continuation) |
| Off | 0 | 4 | 0 | 50% | 0 |

Every continuation ended at **16 versus 16**, with the central 20 humans
untouched. There were no actual battles or population changes. All four pairs
had identical match scores and final population margins. Within each arm, all
four seeds produced the same move sequence. These seeds therefore demonstrate
reproducibility of one behavior; they are not four distinct strategic situations.

## What the trace explains

At ply 58 our army of 16 starts at (28,0). The opposing groups are 12 at (11,2)
and 4 at (0,1). Objectives on chooses to pursue the 12; objectives off remains
along the right edge. Every observed worst-profile objective estimate in the
enabled continuation is zero, including both initial interception candidates.
No simulated objective establishes a positive win value. V7 nevertheless uses
proposal ordering and its bounded distance preference to choose movement.

| Before our decision | Our enabled position | Enemy 12 | Goal status | Gap |
| --- | --- | --- | --- | ---: |
| Ply 58 | (28,0) | (11,2) | Selected | 17 |
| Ply 60 | (27,0) | (10,1) | Retained | 17 |
| Ply 64 | (25,0) | (8,0) | Retained | 17 |
| Ply 72 | (21,0) | (4,0) | Retained | 17 |
| Ply 74 | (20,0) | (3,0) | No tied repetition | 17 |

After our step the distance temporarily drops to 16, but the enemy restores
17 on its reply. The pursuit has zero closing rate. The objective's 16-ply
lifetime expires at ply 74, after eight own turns. Since the moved board has
not yet repeated, V7 stops using an objective and moves back toward the edge.

After ply 80 the enemy has merged into one group of 16 at (0,1). Once positions
repeat again, V7 reports `no_objectives`: the enemy is no longer smaller,
our single army has no ally to regroup with, and the remaining village is too
large for certain recruitment. No direct attack ever becomes available.

This distinguishes chasing current coordinates from intercepting a future
route. Both sides move at the same speed and the prey has a shorter route to
its ally. For the observed leftward escape, our initial horizontal separation
of 17 cannot shrink while both move left one cell per own turn. Increasing the
objective lifetime alone would not establish an interception before that merge.
This is an explanation of the observed route, not a solution of every legal
continuation or a proof that the board has no winning strategy.

## Cost and limits

Enabled continuations recorded 54 repeated focal boards each, versus 59 with
goals off. Less repetition did not create material or score progress.
Average focal-process CPU use was about 54.75 seconds with goals on versus
52.65 off, approximately 4% extra in this run. Planner wall time averaged about
2.00 seconds per enabled continuation. These measurements came from this
six-worker run and do not substitute for the 1.5-second-per-decision benchmark.

This test isolates the effect at equal main search iterations. V7 does extra
planning work; total computation is not equal. It is one known development
snapshot and a modest search budget. No general win rate or neural-network
advantage follows from the four pairs.

## Decision

Keep V6 as the deployment/reference choice. On this snapshot, V7's current
distance guidance changes movement without improving outcome.

The next planning change should assess **whether a target can be reached before
it escapes or merges**. Useful inputs include closing rate, predicted merge
destination, enemy merge arrival time, and our arrival time at potential
interception cells. Avoid extending a zero-closing-rate chase on the assumption
that moving inward is sufficient progress.

To create a material advantage, investigate earlier contested recruitment and
split-army opportunities as well. The late 16-16 position need not contain a
safe forced win. A future neural guide needs diverse examples of those races
and their consequences; these identical draws alone cannot teach a winning
alternative. No algorithm or reward was tuned after seeing these outcomes.

## Recheck

```powershell
python scripts/probe_mcts_v7.py --analyse .local/experiments/v7-stalemate-20261108-paired256
```

The experiment retains source/snapshot archives, per-arm checkpoints, complete
root visits and objective records, battle probabilities and replay verification.
