# V9: recruitment sequences on V6

V6 remains the reference. V9 is an isolated experimental variant built directly
on V6, with a bounded root preference for short recruitment itineraries. It
does not inherit V7 objectives or V8 interception guidance. It has no neural
network and does not train one.

## Run the comparison yourself

From the repository directory:

```powershell
python scripts/compare_mcts_v9.py --opponent v6 --workers 6
```

This schedules **32 games on the same four prepared maps**, eight per map,
balanced across species and starting player. Both bots have 1.5 seconds thinking
within a two-second allowance and a 200-ply cap. Planning is included in V9's
thinking budget. The first progress lines print immediately; game results
print when games finish. Keep the computer awake for timed play.

Results: `.local/campaigns/mcts-v9-vs-v6/report.md`.
Activation/cost diagnostics: `.local/campaigns/mcts-v9-vs-v6/recruitment.md`.
The matching JSON files retain authoritative scores and counters.

Run exactly the same command to resume completed-game checkpoints. An unfinished
game restarts. Add `--dry-run` to validate without playing, or `--max-games 4`
to complete at most four more games in this session.

After reviewing the V6 comparison, a separate comparison against Julian's
retained AB2 width-7 profile is available:

```powershell
python scripts/compare_mcts_v9.py --opponent width7 --workers 6
```

The opponent specification and its published validation status are printed
and saved. No new full strength campaign was launched during implementation.

## What changed

V6 already scores travel and recruitment potential. V9 additionally compares
**capture sequences and their timing** at the root, rather than merely crediting
nearby humans. For example, ten units can convert four humans, reach fourteen,
then convert twelve to reach twenty-six.

The planner uses the unchanged root candidate list. It applies quiet moves,
merges, splits and certain human conversions to a temporary board, then compares
up to two conversions, including those completed in the proposed root move.
Actual immediate turns that convert more villages retain all their conversions;
the planner does not discard real gains to enforce its itinerary limit.
It follows at most three resulting own groups and four shortlisted villages
at each stage, within eight own turns including the root move. This is a separate
planning horizon: V6's MCTS tree/rollout settings remain unchanged.

Routes avoid currently occupied cells and check:

- Troops sufficient for certain conversion and the 255-unit stack limit.
- Arrival before the actual game cap; our kth move is relative ply `2*k-1`,
  the enemy's kth move is relative ply `2*k`.
- Competing enemy arrivals, including up to two prior certain conversions that
  can grow the enemy. Villages already secured earlier in our itinerary cannot
  also supply their hypothetical growth.
- Possible enemy interference along travel, and an adverse immediate
  counterattack after conversion. Expected monster material uses the actual
  battle probability and conditional survivor means, not the likeliest-outcome
  `expected_battle` surrogate.
- A possible battle stops further assumed growth along that army's sequence;
  the next leg cannot rely on its original unchanged troop count.

The ranking is discounted recruited humans plus adverse expected reply material
at each conversion. Delay receives less credit; walking alone receives none.
Other quiet root moves receive a selection penalty between zero and 0.12 when
their itinerary score is lower. This is a heuristic preference, fixed during a
decision. MCTS keeps every original candidate, the V6 leaf evaluator, stochastic
battles, empirical backed-up values and exact terminal utility. Actual monster
attacks and risky human attacks remain entirely with the original search.

Planning has a 20,000-work-unit limit and, in timed play, at most 25 ms or 3%
of the remaining whole-decision time, whichever is smaller. Interrupted
comparisons contribute **no** root preferences. Without humans, positive plans
or distinct preferences, V6's original decision method is used. Untimed probes
use the work bound without a wall-clock cutoff, for reproducibility.

This is not a solved recruitment race. Enemy arrival bounds ignore obstacles;
travel treats other current groups as blockers; a sequence follows one future
own army at a time. Enemy splits, moving blockers, risky enemy recruitment and
growth chains beyond two prior captures are not exhaustively modeled. Summed
enemy threat can overestimate compatible simultaneous growth, capped at 255.
These limitations can suppress useful plans or misrank them, so full timed and
unseen-map comparisons are needed before replacing V6.

## What the local probes establish

Two positions were checked at **256 completed main MCTS iterations**, seeds
0, 1, 2 and 3, with V6 and V9:

| Position | V6 immediate capture | V9 immediate capture |
| --- | --- | --- |
| Synthetic 10 -> 14 -> 26 chain | 4 humans in 4/4 searches | 4 humans in 4/4 searches |
| Recorded delayed-capture position, ply 79 | No immediate village capture in 4/4 | 14 humans in 4/4 |

In the second case, the new preference changes the observed V6 delay to an
immediate conversion. The historical snapshot originally came from V5, but
these fresh probes explicitly compare **V6 and V9**. The chain's legal alternating
turns were also replayed to verify an actual army of 26 at ply 5.

Local data: `.local/probes/v9-recruitment-20261109.json`, with boards, seeds,
source hashes, chosen moves and root targets. This is two development positions,
not completed matches, a win rate or general strength evidence. V9 does extra
planning work in the untimed probe; total computation is not equal.

Initial planning-only timed checks on the four prepared maps and both species
completed in roughly 1.6-20.3 ms on this machine after early reachability checks.
These are initial-position measurements, not a per-turn performance guarantee
under six-worker load; incomplete planning is counted in the actual campaign.

## Diagnosis, controls and preserved references

Every V9 game checkpoint retains planner decisions, activations, preferred
itinerary choices, two-capture proposals, work, planning time and stop statuses.
`recruitment.md/json` aggregate those counters after each saved game and resume.
Activation does not mean the preference caused the move; a proposed itinerary
is not evidence that its later captures occurred.

Record one full game with boards, root targets and the actual planning records:

```powershell
python scripts/trace_mcts_v9.py --opponent v6
```

This writes a fresh `.local/diagnostics/v9-*/` directory, archives sources and
verifies the saved transitions. Timed search decisions are new measurements,
not exact replays of another timed campaign.

Disable the feature for the V6 control:

```powershell
python scripts/compare_mcts_v9.py --agent mcts-v9:recruitment=False --opponent v6 --workers 6
```

At fixed iterations and equal seeds, disabled V9 reproduces V6's moves, root
targets and MCTS RNG stream. Control games use a separate checkpoint folder.
The new code stays under `scripts/mcts_v9/` and separate launchers; shared
engine and V6/V7/V8 source fingerprints are preserved. The per-game metrics
observer operates inside the comparison worker and restores its factory hooks.

## When to consider a neural network

**A neural network is not established as necessary by this change.** The current
problem admits a small, testable rules-based planning addition. A failed V9
campaign would not by itself establish a need for learning.

At subsequent result reviews, flag a small learned guide when evidence shows:

1. Valid candidates and reliable simulation still produce repeated strategic
   misvaluations across diverse maps, visible in complete decision traces.
2. More accurate offline search fixes those decisions but is too expensive
   within the live 1.5-second thinking budget after ordinary optimizations.
3. We have diverse completed games and policy/value targets, with separate
   map-family holdouts, to train and assess the guide without memorizing the
   repeatedly tuned four maps.

Then test a compact root policy/value guide as its own ablation, including
feature and inference costs in the same deadline. Continue using V6 as the
control. The [neural planning note](MCTS_DRAW_AND_NEURAL_PLAN.md) describes the
offline-GPU/CPU-inference route. This note is a decision checklist for future
reviews; it does not schedule background monitoring or automatically train NN
weights.
