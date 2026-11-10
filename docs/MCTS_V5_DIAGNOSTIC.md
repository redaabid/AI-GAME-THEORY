# V5 full-game investigation: 6 November 2026

Two new timed games investigated the draw and large-map weaknesses. They reuse
the maps, roles, seeds and settings of reference games 1 and 19 from the
completed V5-versus-AB2 campaign. Selection happened before playing; both new
outcomes were retained. They are not exact replays of earlier timed decisions.

Local recording: `.local/diagnostics/v5-full-20261106T135048452489Z/`.
It includes full JSONL traces, summaries, interaction timelines, an offline
`replay.html` viewer and an archive of the exact source code.

| Map | V5 role | New result at 200 plies | Faults | Timeouts |
|---|---|---|---|---|
| testmap2 | Vampires, first | Draw: 16 / 16 | 0 | 0 |
| val-large-1290000 | Vampires, second | Loss: 52 / 56 | 0 | 0 |

All **400 transitions** passed exact replay using saved moves and battle seeds.
The original 32-game campaigns and their source fingerprints remain intact.
These two selected diagnostics do not establish a new win rate.

## testmap2: recruitment works, then the evaluation becomes flat

AB recruited four humans after ply 20; V5 recruited four after ply 23. AB
recruited two more after ply 28, and V5 recruited two after ply 33. Both armies
then had 16 units, with only the central village of 20 humans remaining.

V5's first repeated board occurred before its decision at **ply 58**, matching
ply 54. Its army of 16 was at `(28, 0)`, while AB had groups of 12 at `(11, 2)`
and 4 at `(0, 1)`. V5 moved to `(28, 1)` and continued oscillating near that
corner. There were **71 repeated V5 boards**, all at tied population.

At ply 58, its three root candidates all had mean search value **0.0**, with
328, 328 and 327 visits. Its static V5 value was also zero. The only remaining
village is larger than either total army, so V5 excludes its potential.
Several quiet moves consequently have the same value. Memory applies only
while behind, so no repetition penalty activates at the tie.
The [portable snapshot](../examples/mcts_v5_equal_loop.json) preserves this board.

This identifies the tied-loop behavior, but does not prove a safe winning
continuation exists. Risking a battle to avoid a draw can worsen the result.
An improvement must find worthwhile progress rather than force aggression.

## Large map: recruitment allocation and delayed conversions

Both armies started at 12. Every recorded battle was a guaranteed human
conversion: **there were no monster battles or population losses**. V5
recruited 40 humans and AB recruited 44, producing the 52 / 56 result.
This particular loss is entirely a recruitment problem, rather than combat
casualties. V5 collected one of the six one-human villages; AB collected five.
Those four extra small conversions account for the final population difference.

| After ply | V5 | AB | What changed |
|---|---|---|---|
| 10 | 17 | 13 | V5 collected four humans |
| 11 | 17 | 21 | AB collected eight |
| 15 | 17 | 34 | AB collected thirteen |
| 17 | 17 | 38 | AB collected four |
| 24 | 25 | 38 | V5 collected eight |
| 28 | 38 | 39 | V5 collected thirteen |
| 41 | 38 | 42 | AB finished collecting the small villages |
| 122 | 52 | 42 | V5 collected fourteen |
| 157 | 52 | 56 | AB collected the other fourteen |

At the decision at **ply 79**, V5 had 14 units at `(5, 0)` and 15 at `(5, 1)`,
beside 14 humans at `(4, 0)`. Capturing with either capable group, or both,
was legal and guaranteed. Enemy groups were at least 11 steps from that
village, preventing an immediate counterattack.

| Root plan | Visits | Mean search value |
|---|---|---|
| Send both groups into the fourteen-human village | 20 | 0.10584 |
| Send the fourteen-unit group into the village | 20 | 0.10893 |
| Merge both groups at `(6, 0)`, away from the village — chosen | 21 | 0.13783 |

These heuristic values are not win probabilities. The small visit difference
also shows weak separation between the choices at this finite search budget.

Guaranteed fourteen-human captures were present in the root candidate set at
**plies 79, 83, 87, 91, 95, 99, 103, 107, 111 and 115**, all declined. V5 finally
selected the capture at ply 121, changing its population after ply 122: a
delay of 42 plies from the first such opportunity. The
[counterexample](../examples/mcts_v5_delayed_capture.json) preserves ply 79.

This rules out a missing legal capture at those decisions. V1 and V5 static
values were identical at ply 79: the feasibility gate retained both villages
because the armies were already large enough. Search/evaluation/rollout
interaction still ranked waiting above immediate conversion. This is
consistent with crediting recruitment that a future policy is expected to
perform while actual play keeps postponing it. Controlled ablations are
needed to isolate the precise cause.

Taking the village earlier is not proven to win the complete game: AB could
still recruit its village or exploit other differences. The established
finding is repeated delay and poor prioritization of available progress.

## Why no monster attacks occurred in these two games

Combat is enabled: V5 won eight of its original 32 campaign games by
elimination. The absence of combat in these two diagnostics has different
causes in different positions.

On `testmap2`, opposing groups never came within one move of each other;
their minimum recorded separation was eight grid steps. There was no direct
monster attack available from any recorded board.

On the large map, V5 had an adjacent enemy on only two of its 100 turns.
Attacks were in its root candidate list on both occasions:

- **Ply 25:** nine V5 units could certainly kill one enemy at `(14, 11)`,
  but an enemy group of 19 at `(13, 12)` could then certainly destroy those
  nine on the next turn. Declining that full-group attack avoids a visible
  counterattack trap. Monster kills do not convert the enemy into new troops.
- **Ply 167:** V5's group of 52 could attack AB's group of 46. V5 had 52 units
  in total while AB had 56, including two other groups totaling ten. Its
  battle-winning probability was **63.04%**, not a guaranteed victory.
  The attack received 241 visits with mean value -0.00096; the chosen quiet
  move received 279 visits with mean value +0.01803. Those are search values,
  not match-winning probabilities. AB subsequently kept moving away and
  retained its population lead through the turn cap.

AB had an adjacent enemy on 15 turns in the large-map recording and also
declined combat. Late in the game its 46-unit main group faced V5's 52, giving
AB about a 44.23% chance to win an attack. Its retreat preserved a winning
population score. Reaching 1.5 times the defender's group guarantees a
monster victory; that threshold is not a rule forbidding smaller attacks.

The late V5 decision is a useful risk/clock diagnostic: continuing without
fighting eventually lost, while its search slightly preferred quiet play.
It does not prove the rejected battle would have won the complete game.
One plausible contributor is the simple baseline policy used for both sides
inside rollouts, which does not reproduce AB's actual evasive strategy.
Testing that hypothesis and losing-endgame risk valuation would be more
informative than assuming every available attack should be taken.

## AB's actual depth

| Map | AB decisions | Minimum / maximum completed search level | Mean |
|---|---|---|---|
| testmap2 | 100 | 5 / 24 | 13.78 |
| Large | 100 | 4 / 24 | 8.14 |

`depth=1` did not restrict timed play to one ply. AB used iterative deepening
toward `max_depth=24` with a 1.5-second deadline. Level 24 occurred only late:
plies 185–199 on `testmap2`, and 192–198 on the large map. The 200-ply game
cap terminates branches sooner than that requested depth, so completion at
level 24 there does not mean every branch physically simulated 24 additional
turns. These levels should not be compared directly with average MCTS depth.

## Reproduce and inspect

```powershell
python scripts/diagnose_mcts_v5.py --dry-run
python scripts/diagnose_mcts_v5.py
```

Defaults choose the first clean `testmap2` draw and first clean large-map loss
in the reference campaign. Use `--games 1 19` to specify those reference
indices explicitly, or `--campaign PATH` for another saved V5 campaign. Each
run creates a fresh directory, preserves the original clock, and records the
complete games. It requires core/V5 source matching the reference campaign.

To verify this recording and regenerate its viewer:

```powershell
python scripts/diagnose_mcts_v5.py --analyse .local/diagnostics/v5-full-20261106T135048452489Z
python scripts/render_mcts_trace.py .local/diagnostics/v5-full-20261106T135048452489Z
```

Open `replay.html` in that directory. Select a map, play or step through the
board, drag the turn slider, or click the population timeline. V5 turns show
root candidates, visits, values and the selected move; AB turns show actual
completed depth. Everything runs offline with embedded data.

Verification: 16 recorder tests passed, followed by the added replay-data
round-trip check and JavaScript syntax check. Tests cover unchanged seeded
play, stochastic replay, partial-game labels, root capture, observer
restoration, reference selection, repetitions, Windows workers, tampering
rejection and preservation of recordings. No search-policy upgrade was applied.
