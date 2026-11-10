# MCTS research and next experiments - 8 November 2026

**Decision: keep V6 as the reference.** This note proposes isolated experiments;
it does not implement a new agent or establish a stronger configuration.
Priority: interception feasibility, then earlier recruitment opportunities.

The papers below support mechanisms in their own experimental domains. Our
Twilight adaptations and their ordering are engineering hypotheses informed by
our traces, not published results for this game.

## Evidence that determines the priority

The [controlled V7 experiment](MCTS_V7_CONTROLLED_RESULTS.md) started from the
recorded 16-16 position at ply 58, with real histories, 256 completed main MCTS
iterations per decision and the original 200-ply cap. Goals on and off each
produced four draws. Within each arm the four seeds produced identical moves.
The chase lasted eight own decisions; its pre-decision gap stayed at 17. All
observed worst-profile objective values were zero. Movement and fewer repeated
boards did not produce a battle or material advantage.

V6 already has adversarial UCT, sampled combat outcomes, progressive widening
of decision actions, split/joint candidate moves, repetition handling and its
clock-aware endgame value. Those mechanisms are not new recommendations here.
Its search currently starts a fresh tree on each call. Its standard rollout
still uses a cheap single-group policy; earlier broad coordination/depth
experiments did not establish an improvement under our time budget.

## A stronger merge reply checked locally

Using `examples/mcts_v7_controlled_snapshot.json` and the current legal turn
simulator, I checked this quiet continuation. Coordinates are `(x,y)`.
Our 16 moves left along row zero on every own turn. Both enemy groups approach
one another; the 12 holds on the last enemy turn while the 4 joins it.

| Enemy turns completed | Ply | Our 16 | Enemy 12 | Enemy 4 |
| ---: | ---: | --- | --- | --- |
| 0 | 58 | (28,0) | (11,2) | (0,1) |
| 1 | 60 | (27,0) | (10,1) | (1,1) |
| 2 | 62 | (26,0) | (9,1) | (2,1) |
| 3 | 64 | (25,0) | (8,1) | (3,1) |
| 4 | 66 | (24,0) | (7,1) | (4,1) |
| 5 | 68 | (23,0) | (6,1) | (5,1) |
| 6 | 70 | (22,0) | merged 16 at (6,1) | merged |

All twelve alternating turns passed `simulate_turn`; there were no battles.
This is a hand-specified legal reply, not a new MCTS match result.

The enemy groups initially have Chebyshev separation 11. With both moving,
their geometric earliest rendezvous is `ceil(11/2) = 6` enemy turns, attained
by this route. Our initial distance from the nearer enemy is 17. During six
turns each, even cooperative movement toward each other could close at most
12 cells. Thus our army, including any detachments split from its starting
cell, cannot contact either enemy before this six-turn merge. The remaining
20-human village is also beyond our six-turn reach.

This rules out forcing an interception before this available merge from this
snapshot. It does **not** prove the full position is a draw, solve subsequent
equal-army stochastic combat, or rule out wins against an opponent that delays
or chooses another route. Increasing a pursuit lifetime cannot remove this
particular geometric obstacle.

## 1. Interception feasibility before a pursuit objective

A recent pursuit-evasion paper explicitly separates task proposal from
interception feasibility validation and replans when feasibility changes.
Its continuous differential-game geometry and LLM planner do not transfer
directly to our alternating grid game. The useful design principle is to
validate the proposed task before committing to it. Only its publisher
abstract/highlights were accessible in this review. [Li et al., 2026](https://www.sciencedirect.com/science/article/pii/S0016003226005685)

Proposed first experiment, built separately on V6:

- Compute earliest arrival plies, not just distance to the target's current
  square. Account for the current player, board bounds and remaining clock.
  Empty-board Chebyshev distance is a geometric lower bound; occupied routes
  and battles still require legal simulation.
- Consider moving rendezvous points for pairs of enemy groups. Do not assume
  that the target's ally stays still. Track how a merge or recruitment changes
  the battle odds and the meaning of the original target.
- Compare our possible interception cells and times with escape/recruit/merge
  replies. A favorable race to one predicted cell does not prove that the
  enemy must pass through it. First run cheap reachability bounds, then bounded
  adversarial reply checks for the few promising cases.
- Report three distinct results: ruled out under a stated bound, promising
  under tested replies, or unresolved. A sampled reply portfolio cannot
  certify an interception against every legal response.
- Initially use this information only for pursuit proposals or a small root
  selection preference. Preserve the base V6 actions and terminal match
  utility; uncertainty must not become a blanket ban on risky legal attacks.
- Recheck after observed enemy moves, recruitment or merges. Stop committing
  computation to a plan whose justification has disappeared.

One integration option is progressive bias: a bounded heuristic preference in
selection that decreases as an action accumulates visits. This is an established
method, not a new 2026 invention. Our contribution would be the interception
features and their validation. Keep the preference separate from backed-up
match outcomes; a shorter distance is not itself a win. [Chaslot, thesis
chapter 5, 2010, describing the 2007/2008 work](https://project.dke.maastrichtuniversity.nl/games/files/phd/Chaslot_thesis.pdf)

Success at the known snapshot means recognizing the six-turn merge escape
without wasting a long chase. A changed route or reduced repetition alone
does not count as improved playing strength.

## 2. Earlier recruitment races and useful splits

Once interception analysis is isolated, investigate where the material
advantage could have been created before the 16-16 stalemate. Inspect opening
decisions and the [delayed-capture example](../examples/mcts_v5_delayed_capture.json).
The old V1 oversized-village evaluation issue was already addressed by V5;
do not describe that old diagnosis as a newly observed V6 failure.

For a candidate village, estimate who can arrive first with enough troops,
the strength left elsewhere after splitting, the immediate enemy reply, and
which next village becomes affordable after conversion. Compare recruitment
sequences, including an enemy stealing or contesting a village, rather than
giving both players optimistic credit for eventually collecting it.

An extra four humans relative to a 16-unit route can bring an army to 20 and
make certain recruitment of a 20-human village possible. This is an example
of a threshold that distance-only evaluation misses, not evidence that this
extra village can actually be secured on our symmetric map.

For positions with several groups, combinatorial bandit research provides an
approach to sampling joint actions by combining choices for individual units.
It was evaluated in RTS games with large action spaces. Here it could inform
bounded group-to-village assignments, subject to joint-move legality and
counterattacks; troops cannot be assigned to two tasks at once. Defer this
larger action-generation experiment until a trace identifies a missing useful
assignment. [Ontanon, JAIR 2017](https://arxiv.org/abs/1710.04805)

## 3. Tactical verification at critical events

An attractive recruitment or attack can be bad after the opponent's immediate
reply. A small tactical search around contact, conversion or merge events is
a better targeted hypothesis than increasing every rollout's length.

Implicit minimax backups maintain a separate heuristic minimax estimate to
guide MCTS alongside its sampled estimates. The original experiments concern
deterministic games. For our battles, any tactical adaptation must retain
probability-weighted chance outcomes or correctly weighted sampling.
[Lanctot et al., 2014](https://mlanctot.info/files/papers/cig14-immcts.pdf)

Monte Carlo *-Minimax is a closer stochastic-game reference: it combines sparse
sampling with adversarial expectimax search in perfect-information, two-player,
zero-sum games. A small root tactical verifier inspired by this work could
check the strongest immediate replies while leaving the main V6 search intact.
That proposed hybrid is our adaptation, not the algorithm tested in the paper.
[Lanctot et al., IJCAI 2013](https://www.ijcai.org/Proceedings/13/Papers/093.pdf)

Use exact probabilities when a small event can be enumerated cheaply; otherwise
sample under a strict budget. Do not treat our `rng=None` survivor surrogate
as a real battle distribution. Report whether the verifier found a refutation
or only failed to find one.

## 4. Root allocation: Anytime Sequential Halving

This is a concrete recent alternative to our current root UCT allocation and
most-visited final choice. It repeatedly samples all root actions, concentrates
on the better half, then restarts consideration of all actions in a new pass.
It can stop without a predetermined iteration count; no neural network is
required. Internal nodes can retain UCT. [Sagers, Winands and Soemers,
2024 preprint / 2025 publication](https://arxiv.org/html/2411.07171v1)

The paper's results are mixed: competitive with UCT overall, possibly slightly
worse at small budgets and better at some larger budgets. It is not evidence
of automatic superiority at our roughly thousand-iteration timed budget.

Test this separately with the same root candidate set and normal deadline.
Keep a legal fallback throughout incomplete passes. Root progressive widening
and halving must be reconciled explicitly: silently giving halving a different
action set would confound the comparison. Better allocation cannot discover
a material advantage if every sampled continuation and evaluation stays zero.

## 5. Reuse computation safely

Tree reuse can carry useful previous search work into the next decision.
The real-time game-playing literature also discusses decaying retained
statistics in nondeterministic games. This reference was originally published
in **2016**, despite its 2024 arXiv upload. Its published aggregate results
combine several enhancements and are not a tree-reuse-only gain for Twilight.
[Soemers et al., 2016](https://dennissoemers.github.io/assets/publications/CIG2016_GVGAI.pdf)

Start with bounded caches for pure candidate computations or static values,
then consider retaining a tree only when the actual board after both players'
moves matches a stored outcome. Include board dimensions, troops, player to
move, remaining clock/cap, battle rules and evaluator configuration in relevant
keys. History-dependent penalties need their own context handling. Recalculate
or discard data that depends on a changed horizon or history.

Never cache a randomly sampled battle as the sole outcome of an action. Do
not collapse chance outcomes by troop count averages. Measure actual cache
hits, completed iterations, memory and timed playing strength; lookup overhead
can outweigh reuse. Extra zero-valued simulations still do not solve the
strategic evaluation problem.

## 6. Semantic novelty and a small learned guide, later

The 2025 novelty paper combines value with novelty during selection and tests
four measures, including feature pseudocounts, across six board games. This
supports an exploration experiment, not rewarding arbitrary movement.
[Baier and Kaisers, 2025](https://ir.cwi.nl/pub/35890)

Possible game-specific features include first access to a contested village,
a newly affordable recruitment threshold, a threatened merge, or a change in
interception feasibility. That feature design is our hypothesis. Apply any
bonus to search exploration and measure outcomes; fewer loops alone did not
help V7. Novelty remains lower priority than feasibility and recruitment.

The [existing small-network proposal](MCTS_DRAW_AND_NEURAL_PLAN.md) remains a
later option. Arrival-time differences, merge escape opportunities, recruitment
thresholds and counterattack exposure are useful candidate inputs. Start with
a root move prior; measure CPU feature/inference overhead before adding a
value call at every leaf. Offline training on the colleague's GPU is allowed;
there is currently no trained neural guide in V6 or V7.

Training requires diverse completed games and strategic alternatives, including
better opening recruitment and defended or failed interceptions. Four identical
draw continuations cannot teach a winning alternative. Keep draws as draws
and split training/evaluation by whole games and map families.

## Experiment order and acceptance

1. Preserve V6 and record a fresh experimental variant's sources/configuration.
2. Implement only interception feasibility and its diagnostics first. Test
   the six-turn merge case, a genuinely catchable target, an escaping target,
   a blocked route, a merge with both groups moving, and an ambiguous case.
   A heuristic result must not be mislabeled as a proof.
3. Investigate and isolate recruitment changes on opening counterexamples.
4. Test tactical verification, root halving and reuse in separate ablations;
   combine only changes that survive their individual tests.
5. Use fixed-iteration probes to explain decisions, then equal total 1.5-second
   decision budgets for strength. Include extra planning/cache/NN work in that
   deadline. Keep six workers and both player/starting roles consistent.
6. Run the familiar four-map campaign against V6 and Julian's retained AB2
   configuration for development. Report per-map wins/draws/losses, score
   `(wins + 0.5 * draws) / games`, faults, timeouts and search work. Keep each
   paired seed/role together when comparing uncertainty; timed matches need
   not replay identical moves under different CPU load.
7. Confirm promising changes on new map families and seeds, including
   asymmetric maps. Our repeatedly tuned four maps are development maps.
   Thirty-two games are a screen, not a precise general win-rate estimate.

Adaptive effort should depend on the situation: reachable recruitment,
number of groups/candidate plans, imminent contact or merge, and time left.
Map area alone does not describe the difficulty of a decision.

Increasing search depth is not a general strength guarantee. Recent research
demonstrates lookahead pathology for UCT in synthetic adversarial games. It
does not diagnose our earlier regressions by itself, but supports measuring
each depth/budget change rather than assuming improvement. [Nguyen and
Ramanujan, ICAPS 2024](https://ojs.aaai.org/index.php/ICAPS/article/view/31501)

No V6/V7 algorithm sources were edited and no new full campaign was started
for this review. The new local computation was the twelve-turn legal merge
continuation above, not training or a strength comparison.
