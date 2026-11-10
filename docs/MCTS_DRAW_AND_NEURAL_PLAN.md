# Turning the testmap2 draws into wins: investigation and proposed experiments

Analysis date: 7 November 2026. This document proposes experiments; no new
production search algorithm or trained neural network was installed.

## What the evidence actually says

The completed V6-versus-Julian-AB2-width7 campaign finished 16 wins, 10 draws
and 6 losses across 32 balanced games. All eight `testmap2` games reached the
200-ply limit at 16 versus 16. Both agents had zero faults and timeouts.
Campaign summaries contain final populations and aggregated search statistics,
not full per-turn positions or neural training targets.

The detailed evidence about the loop comes from the earlier full V5 recording,
not an exact replay of those eight V6 games. Its portable position is
`examples/mcts_v5_equal_loop.json`: at ply 58, our 16 are at (28,0), opposing
12 at (11,2) and 4 at (0,1), with 20 humans at (14,7). V5 first revisits a board
at ply 58 and records 71 repeated own-turn boards during that full game.

V6 reproduces the flat behavior on this recorded position in a new controlled
probe: seed 0, 512 iterations, SearchConfig defaults, max_plies 200, no supplied
history. The three root moves have values [0,0,0], visits [171,171,170], and the
chosen move is (28,0,16,28,1). This is one search on an older board, not proof
that every new draw follows precisely the same trajectory.

Giving that repeated action the existing 0.3 root penalty changes visits to
[44,234,234] and chooses (28,0,16,27,0), moving toward the interior. All three
values remain zero. This isolates a limitation: repetition pressure changes
movement, but does not identify a winning continuation.

Local probe artifacts:

- `.local/analysis/testmap2-20261107/tie-probe.json`
- `.local/analysis/testmap2-20261107/nn-inference-cost.json`
- `.local/analysis/testmap2-20261107/context.json`

## Four interacting causes

1. **Population ties erase the remaining positional differences in the leaf
   value.** V5 filters the central 20-human village because both totals are 16.
   Its remaining material term is zero. V6 retains this value: its calibration
   requires no humans anywhere on the actual simulated board. Moving the same
   tied board closer to the cap would still not activate that adjustment.
2. **Tie repetition is not penalized.** V6 inherits V5's `own < enemy` guard
   before applying root memory. Exact tied loops consequently receive no
   repetition pressure. A modest tie-specific mechanism is worth testing,
   but the controlled probe does not demonstrate a win from that change.
3. **Candidate ordering is conservative about uncertain monster attacks.**
   `turn_score` prefers approaching an enemy only at the 1.5x guaranteed-win
   threshold. Against the nearest 12, our 16 fall short of 18; the inward
   moves score -0.25 while the selected sideways move scores 0. All three
   legal neighboring full-group moves are available here, so this particular
   case is not a missing-candidate problem. On larger multi-group boards,
   generation and pruning still require coverage checks.
4. **Search cannot cheaply see the distant consequence.** In this position
   the nearest enemy is 17 grid steps away. The recent timed campaign averaged
   about 922 completed MCTS iterations per decision. Six-ply rollouts give a
   limited continuation and use the simple one-group baseline for both sides.
   The actual search tree already supports joint moves and some splits;
   moving one group is specifically a rollout limitation. The existing
   `macro.py`, `playbook.py` and coordinated-rollout implementation provide
   reusable pieces, but long, expensive rollouts previously failed to improve
   V2/V4 under the same thinking budget.

## What a winning plan would need to accomplish

The initial map has 10 creatures per side, two 4-human villages, two 2-human
villages and a central village of 20. Collecting one nearby 4 and one 2 gives
each side 16. Reaching 20 for a guaranteed central capture requires another
four creatures, which the ordinary symmetric collection plan does not supply.
Monster kills remove opponents; they do not convert them into our population.

The initial Chebyshev races also matter: each 4-human village is 10 steps from
its nearer army and 18 from the other; each corner 2-human village is 14 versus
28 steps away. Simply ordering a rush toward the opponent's village is not a
credible winning plan against timely defense. It needs an actual diversion,
interception or a demonstrated opponent mistake.

There are three useful classes of opportunity to investigate:

- **Opening allocation:** collect efficiently while pressuring or intercepting
  an exposed opposing detachment before the enemy completes its own collection.
- **Attack a fragmented enemy:** 16 versus 4 is a certain battle victory;
  16 versus 12 wins that battle with probability 5/6. Accessibility, enemy
  merging, evasion and counterattacks determine whether either is a good plan.
- **Improve the approach geometry:** keep a multi-turn interception objective
  and reconsider it after each actual opponent reply. Empty territory itself
  scores no points; distance or novelty alone is not a winning objective.

Blindly attacking the central village is a poor default. With 16 attacking 20
humans, the server profile gives p=0.4. Conditional on winning, survivors follow
Binomial(36,0.4), with mean 14.4. The unconditional probability of immediately
exceeding the untouched opponent's 16 is approximately 9.44%. If both sides'
populations were then frozen until the cap, its expected match score would be
about 11.73%, versus 50% for a preserved draw. That is an illustrative frozen
continuation, not the actual full-game win probability. Subsequent attacks
can change the result. Any proposed risky capture needs those continuations.

No forced win from the recorded 16-16 board has been established. Against
optimal replies, some states may be drawable. The engineering target is to
exploit real winning opportunities without converting safe draws into losses.

## First search experiment: objective-directed progress

Freeze V6 as a control and keep the same wall-clock budget. Build a diagnostic
that can record V6 and counterfactual continuations from selected boards. The
existing V5 full-game recorder explicitly restricts its reference challenger
to V5, so it needs an isolated adapter for V6; ordinary campaign summaries are
insufficient. Record root visits, candidate coverage, RNG state, exact battle
seeds, phase activation, target choice and completed depths.

Preselect opening positions, first repeated tied positions, and positions with
enemy groups about to merge. Compare a small set of persistent objectives:
recruit, intercept a vulnerable group, regroup safely, and preserve a lead.
Use the existing legal one-turn movement compiler. Each simulated macro step
must allow the opponent its intervening turn; a plan is not a teleport or an
assumption that the enemy stands still. Replan after threats or material changes.

Test modest tie repetition separately. Do not replace draw=0 with a negative
terminal reward: the game's scoring still values a draw above a loss. Initially
use novelty only as bounded search guidance or tie-breaking, not claimed win
value. Predictable attacks must retain explicit reply checks.

Avoid extending every rollout. Put bounded deeper effort into a few objective
comparisons, preferably until a meaningful event (capture, merge, contact) or
a hard depth/time limit. Compare both fixed iterations and fixed wall time.

## A small NN is feasible, with a defined job

The proposed first model has two small components, rather than a full raw-grid
vision network:

| Component | Illustrative architecture | Parameters | Purpose |
| --- | --- | ---: | --- |
| State value | 48 -> 32 -> 16 -> 3 | 2,147 | Win/draw/loss probabilities |
| Candidate scorer | 72 -> 32 -> 16 -> 1 | 2,881 | Score each generated legal turn from state/action features |

These dimensions are a concrete starting design, not tuned hyperparameters.
The candidate model could concatenate 48 state and 24 action features. It
does not assume a fixed number of moves, map dimensions, groups or villages.
This first model uses engineered relational features and is not a lossless map
encoder. If these aggregates prove limiting, a small pooled entity encoder
following Deep Sets is a logical subsequent experiment.

Inputs should include actual and normalized travel distances, village arrival
races, population and local combat ratios, regrouping costs, exposed small
groups, reachable recruitment before the cap, post-capture reply exposure,
map dimensions, actor-relative troop ownership, rules profile, remaining time
and repetition context. Read the real board, including oversized villages:
V5's temporary filtered evaluation view would hide exactly the central-village
unlocking problem we want to learn. Include absolute distances as well as normalized ones:
a normalized distance alone loses the number of turns needed to arrive.
Use geometry and populations, not map names.

The three outcome probabilities distinguish a likely draw from a volatile
position with chances of both winning and losing. The expected signed value
is P(win)-P(loss); equivalent match score is P(win)+0.5*P(draw). The current
root/actor perspective convention must be preserved at opponent nodes.

A five-repeat idle-CPU microbenchmark on this machine, using random weights,
standard-library Python loops and no feature extraction, measured about
0.204 ms per value call and 0.258 ms per candidate call. These are cost probes,
not trained-model evaluations. At 900 value calls, bare inference would cost
about 0.18 seconds; 32 root policy calls about 8 milliseconds. Features, caching,
additional workers and changing clocks can materially alter those costs.

Therefore first test a **root-only neural prior**, with a uniform exploration
floor and the existing candidate/fallback coverage. Search must be able to
override the prediction. Next test learned leaf values independently, using
the heuristic as a validation-tuned fallback/blend. Cache only with a key
that includes board, actor, clock/cap, rules and relevant history, plus model
version; repetition detection's ply-free key is not a valid NN cache key.

Train offline on the colleague's GPU using the already-authorized framework.
Export versioned weights and feature definitions; CPU inference can remain
our own standard-library implementation under the runtime restrictions.
Benchmark actual timed playing strength and legal-deadline behavior, not just
prediction accuracy or raw iteration counts.

## Training data that can teach progress

The 32-game reports alone cannot train this model. `simulate.py` exports
state/candidates/search visits/final outcomes, but currently supports only
`baseline`, `random` and the original `mcts`, not V6 or Julian's agent specs.
It requires an isolated agent-aware export adapter. Exclude deadline fallbacks
from expert policy targets, retain provenance and keep outcome perspective exact.

Generate a pilot of hundreds of finished games using mixed fixed search budgets
and a smaller number of stronger reanalyses, then scale only when validation
shows useful learning. Use V6, retained AB profiles and selected previous agents
as a league; include exploratory openings and counterfactual goal choices.
Do not train solely on successful games or on the repeated 16-16 trajectory.
Sampling should prevent long repeated episodes dominating the replay buffer.

Save (state, candidate plans, search distribution, realized final outcome),
rule/horizon/model metadata and group/game identity. Supplement the main targets
with final population margin or near-term safe recruitment as auxiliary targets,
but measure whether these help; population by itself is not always win value.
Stochastic battles require repeated independent continuations to estimate
expected outcomes rather than treating one lucky battle as proof of strength.

The current random-map generator is point-symmetric. Add asymmetric examples,
sparse wide maps, oversized central villages and split-army situations before
claiming generalization to the opponent's asymmetric maps. Split by whole map
families and complete games. Rotations, reflections and related trajectories
from the same source map must stay within one split. These four repeatedly used
benchmark maps are development/regression cases, not an unseen final test set.

A GPU helps training; it does not automatically accelerate our Python simulator
or search. For scale, copying this campaign's average game length and 1.5-second
per-ply budget to 500 games would take about 31.5 hours of cumulative thinking,
or an idealized 5.3 hours at six workers before overhead/contention. A cheaper
fixed-iteration pilot is sensible before collecting a large timed dataset.

## Decide which addition earns promotion

Test changes separately: V6 control; tie-memory only; objective planning only;
root policy prior only; learned value only; then the selected combination.
Keep workers, opponents, maps, role balance, cap and timing identical within
each comparison. Fixed-iteration tests diagnose decisions; the 1.5-second CPU
benchmark determines whether inference or planning costs outweigh their benefit.

Track full score and per-map W/D/L, newly won draws, newly lost draws, unsafe
attacks, repeated-position count, opportunities collected, endgame-rule use,
neural-call time, search throughput, faults and timeouts. A reduction in draws
is not by itself an improvement. Evaluate new map families and a league, not
only Julian's one profile. Use held-out outcome calibration and policy quality
alongside match scores. Reserve a final set that is not repeatedly used for
selection, and use enough independently seeded games to quantify uncertainty.

The strongest project contribution would be the game-specific combination of
recruitment-race reasoning, objective-based search and a measured CPU-sized
neural guide. Adding a standard neural network alone is not a novelty claim.

## Research grounding

- [AlphaZero, DeepMind, 2018](https://deepmind.google/blog/alphazero-shedding-new-light-on-chess-shogi-and-go/):
  learned guidance and MCTS are complementary. This supports the design pattern,
  not an expectation of AlphaZero-scale results in this game.
- [KataGo: Accelerating Self-Play Learning in Go](https://arxiv.org/html/1902.10565v5):
  useful game-specific features and auxiliary targets can improve learning
  efficiency. Recruitment and future population are our proposed adaptations.
- [Deep Sets, NeurIPS 2017](https://proceedings.neurips.cc/paper/2017/hash/f22e4747da1aa27e363d86d40ff442fe-Abstract.html):
  a basis for handling unordered, variable-size entity collections if the first
  fixed feature model becomes a bottleneck.
- [Novelty in Monte Carlo Tree Search, Baier and Kaisers, 2025](https://ir.cwi.nl/pub/35890):
  studies novelty-assisted selection in six board games. It motivates a bounded
  exploration experiment; it does not establish an advantage in our game.
- [Policy Improvement by Planning with Gumbel, ICLR 2022](https://openreview.net/pdf?id=bERaNdoegnO):
  a possible later approach to allocating a small root search budget once we
  have useful priors and reliable action-value estimates. It is not the first
  change needed to repair today's flat evaluation.
