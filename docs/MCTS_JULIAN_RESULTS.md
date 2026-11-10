# MCTS V1 versus Julian AB2 width 7: analysis

Completed 6 November 2026. Campaign:
`.local/campaigns/mcts-v1-vs-julian-ab2-width7/`.

MCTS finished **11 wins, 7 draws and 14 losses**. Its match score was
**45.3125%**, versus **54.6875%** for AB2. A draw counts as half a point.
Julian finished ahead in this sample; 32 games do not establish a decisive
overall strength difference or a ranking on unseen maps.

## Conditions and validation

- MCTS: `mcts-v1:iterations=100000`.
- Opponent: `ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000`.
- Four maps, two rounds, all four species/first-player roles per map per round.
- Each agent: 1.5 seconds thinking from a 2-second allowance; 200-ply match cap.
- Two workers; seed schedule starts at 20261028; server-v3.2.1 combat rules.
- Both agents: **zero timeouts and zero faults**. Maximum decision times were
  approximately 1.51 seconds for MCTS and 1.53 seconds for AB2.
- All 32 game/job checksums, report contents, shared source fingerprints,
  and retained-profile/launcher hashes were verified against the manifest.

AB2's depth 24 is a configured ceiling. Actual AB2 depths are not retained in
these campaign records, so this run cannot establish its average search depth.
MCTS iteration counts measure search work, not the number of played matches.

## Per-map results

All counts below are from MCTS's perspective.

| Map | Wins | Draws | Losses | Score | Games reaching the 200-ply cap |
|---|---:|---:|---:|---:|---:|
| testmap2 | 0 | 2 | 6 | 12.5% | 7 |
| thetrap | 5 | 0 | 3 | 62.5% | 1 |
| val-large-1290000 | 4 | 0 | 4 | 50.0% | 6 |
| val-medium-1280000 | 2 | 5 | 1 | 56.25% | 5 |
| Total | 11 | 7 | 14 | 45.3125% | 19 |

On the other three maps combined, MCTS scored 56.25%: 11 wins, 5 draws and
8 losses in 24 games. This post-hoc breakdown identifies a weakness; the full
four-map result remains the comparison score. Eight games per map are an
initial diagnostic sample.

## Main weakness: long-distance recruitment on testmap2

Observed facts:

- The map is 29 columns by 15 rows. Both starting armies have 10 units.
- For either starting side, the closest village that can certainly be recruited
  by the initial group is 10 movement steps away.
- V1 caps tree traversal at 12 plies and rollouts at 6. Their combined maximum
  is 18 alternating player turns, allowing the root player only 9 moves.
- Consequently, from the untouched starting position the search cannot
  explicitly simulate its own first guaranteed recruitment. It relies on the
  leaf evaluation to judge those routes. In this campaign the observed maximum
  tree depth on this map was only 6 plies, with a 6-ply rollout maximum.
- MCTS was behind in population on 615 of its 798 decisions on this map.
  AB2 was behind on zero of its 798 decision points.
- Five losses were decided by a population deficit at the match cap; one was
  an elimination. Two games drew at the cap. For example, game 1 finished
  with MCTS at 14 units and AB2 at 18 after 200 plies.

The most useful hypothesis is that recruitment-route choices establish a
population deficit that MCTS then fails to reverse. This is supported by the
horizon and material statistics, but the exact cause of each lost game is not
recoverable from summary records alone.

**Follow-up evidence, 6 November:** [four recorded opening diagnostics](MCTS_RECRUITMENT_DIAGNOSTIC.md)
found a concrete retreat/loop with a generated, guaranteed recruitment route
available. A controlled leaf-value ablation points to overoptimistic credit
for a 20-human village that neither army can currently recruit with certainty.
This refines the horizon hypothesis into a specific evaluation issue; it does
not prove that the same move caused every loss in the original campaign.

The current leaf evaluator already uses distances and contested human
potential. The next candidate improvement should investigate **sequences of
recruitments and arrival-time competition**, rather than simply add distance
to an evaluation that already contains it. A cheap route estimate could value
a village partly by which next village becomes reachable/affordable afterward.
It should use general board features, not hardcoded coordinates for this map.

## Second issue: repeated equal-population positions

All five medium-map draws finished at **23 versus 23** after 200 plies.
Across those five games, 406 of MCTS's 500 decision positions had appeared
earlier in the same game; AB2 had 405 repeated positions in 500 decisions.
Neither agent was behind when those repetitions were counted.

V1's repetition memory activates only while behind in population. It applied
no penalties in these five draws. Thus it does not address repetition at equal
population. This is an opening for a later search-diversification experiment,
including a carefully bounded novelty preference. It is not evidence that a
winning alternative existed, and forcing activity could turn a valid draw into
a loss. Long-distance recruitment on testmap2 is the clearer first priority.

## Timing, search and role sensitivity

MCTS completed 4,277,095 iterations across 2,204 decisions: approximately
1,941 iterations per move. Mean tree depth was 3.37 plies and mean rollout
depth was 5.75 plies; their respective maxima were 7 and 6.
About 66.8% of MCTS search CPU was spent in rollouts. With zero faults and
timeouts, this batch's score deficit is not explained by execution failures.

MCTS scored 59.375% when playing vampires and 31.25% when playing werewolves.
Going first versus second made a smaller difference: 46.875% versus 43.75%.
The schedule is balanced, so neither side received extra games.

A small fixed-iteration diagnostic swapped only species labels and populations,
keeping geometry unchanged. On all four starting boards, the original search
produced identical moves, candidates and visit/value statistics under this swap
(64 iterations, tree cap 4, rollout cap 6, seed 42). This found no basic
species-label inconsistency in those positions. It does not rule out
coordinate-order effects, later-position bugs, spawn geometry or chance.
Species-label swapping is different from rotating or mirroring the board.

## Recommended next work

1. Keep V1 as the reference and retain these 32 results unchanged.
2. Add optional per-turn recording for a small testmap2 diagnostic run:
   boards, chosen moves, populations, remaining human villages, seeds and
   actual search counts. Include both species and starting roles.
3. Identify the first lasting recruitment/population deficit. Check whether
   the useful move was absent from the candidate set or was present but
   undervalued. This separates candidate coverage from evaluation/search issues.
4. Make one small recruitment-planning change addressing that evidence.
   Preserve the reference and use a separate agent/checkpoint.
5. Screen it against V1 and the same AB2 opponent, then confirm promising
   results with additional seeds and unseen maps. Track match score alongside
   early population margins, repetition, timing and faults.

The ordinary campaign report stores final populations and aggregate statistics,
not every actual move. Seeds alone do not recreate identical decisions for a
wall-time-limited search because completed iteration counts vary with machine
throughput. Any new diagnostic replay must be labeled as a new run.

This analysis changed documentation only; it did not change either algorithm
or start another campaign. No neural network was trained.
