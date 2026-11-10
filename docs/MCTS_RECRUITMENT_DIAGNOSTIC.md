# Recording MCTS recruitment decisions

## First recorded investigation: 6 November 2026

Four 48-ply openings were recorded at the normal timed budget, covering both
species and both starting roles. All 192 transitions passed exact move/battle
replay, with zero faults and zero timeouts. The raw run is saved locally in
`.local/diagnostics/recruitment-20261106T082837953912Z/`.

These prefixes are truncated, so the table does not report wins or losses.

| MCTS species | First player | Population after 48 plies: MCTS / AB | MCTS first growth after ply | AB first growth after ply |
|---|---|---|---|---|
| vampires | vampires | 10 / 16 | None within prefix | 20 |
| werewolves | vampires | 14 / 16 | 22 | 19 |
| vampires | werewolves | 10 / 16 | None within prefix | 19 |
| werewolves | werewolves | 14 / 16 | 35 | 20 |

The vampire openings both approached a guaranteed four-human village, then
turned away with only two moves left to reach it. In the first opening, the
position at ply 16 had ten vampires at `(20, 11)` and four humans at `(18, 11)`.
The enemy groups were at `(8, 4)` with eight units and `(4, 8)` with two units,
well away from that immediate recruitment. V1 chose `(21, 10)`, increasing
the distance to the village from two to three. It then repeatedly shuttled
near `(21, 10)` and `(21, 11)` and had recruited nobody by the recording limit.

Candidate coverage was not the obstacle at that decision. The direct forward
move to `(19, 11)` was in the root list, with 40 visits and mean simulation
value approximately 0.087. The selected retreat received 165 visits and mean
value approximately 0.385. A partial four-unit advance was also present.
These are search estimates, not win probabilities or proof of optimal play.

The leaf evaluator assigns the central 20-human village roughly **+17.48 units
of potential** at this position even though both armies total ten and neither
can recruit it with certainty yet. Its soft shortage cost is based on
individual groups: splitting the opponent's ten into eight plus two also affects
this estimate. The evaluator already considers distance; credit for uncertain
future growth is a more specific issue than simply omitting travel distances.

A controlled single-position ablation used 512 iterations and seeds 0, 1, 2,
and 3. It suppressed leaf credit for human stacks larger than **both species'
current total populations**, while retaining all actual transition rules,
candidates and risky battles. The original evaluator retreated in all four
searches; the ablation advanced four units toward the four-human village in
all four. Results are saved in the raw run's `evaluation-probe.json`.

This isolates a promising evaluation change, not a validated stronger agent.
Immediate evaluation of the forward move was already higher than immediate
evaluation of the retreat. The bad preference emerges during search and
rollout continuation, so the interaction between the leaf estimate and rollout
policy matters. Ignoring future large-village growth entirely might also hurt
other positions; full-map tests are required before retaining such a change.

AB2 actually completed depths 5 through 7 in these opening decisions, despite
its configured ceiling of 24. This evidence does not support attributing its
recruitment advantage simply to searching 24 plies.

The portable [recorded counterexample](../examples/mcts_recruitment_stall.json)
contains the full board, candidate visits/values, source fingerprints and
counterfactual probe choices. It can seed the next regression test without
needing the local course-map assets or raw traces. The proposed next agent
would retain V1 and change only recruitment feasibility in the leaf value;
its match strength still needs measurement.

## Run the recorder

`scripts/diagnose_mcts_recruitment.py` records **new opening runs** against
Julian's retained AB2 width-7 configuration. Its purpose is to identify where
the population gap opens on `testmap2` before changing V1's strategy.

From the repository directory:

```powershell
python scripts/diagnose_mcts_recruitment.py --dry-run
python scripts/diagnose_mcts_recruitment.py
```

Default conditions are four species/first-player roles, seed 20261028,
1.5 seconds thinking from a 2-second allowance, and two workers. The exact
retained AB2 specification is read from `scripts/ab2_retained_profiles.json`.
Expect about two to three minutes for the four openings on a machine that can
run both workers concurrently.

The recorder stops after **48 individual player turns (plies)** while the
agents retain the normal **200-ply game clock**. Reducing the game clock to
48 would change their endgame evaluation and undermine an opening diagnosis.
Truncated prefixes have no match winner and are not labeled draws or included
in campaign rankings. A game that naturally ends before the recording limit
does retain its actual outcome.

## What is saved

A fresh directory is created under `.local/diagnostics/recruitment-TIMESTAMP/`.
Use `--output PATH` to choose another fresh directory. Existing directories are
refused to preserve earlier recordings. This short diagnostic does not resume
unfinished openings.

- `manifest.json`: agents, complete initial map, roles, seeds, clocks, shared
  runtime hashes, and diagnostic/profile file fingerprints.
- `game-NN.jsonl`: one flushed record per played or skipped turn, including
  boards before/after, suggested/executed moves, population totals, remaining
  human villages, timing, faults/timeouts, and agent diagnostics.
- V1 records also retain all root candidates, visits, empirical values and the
  selected plan. An observer stores the existing search result by reference;
  extra analysis and serialization occur after the thinking timer.
- AB2 records include its actual completed iterative-deepening depth, rather
  than just the configured ceiling.
- `game-NN.summary.json`: completed prefix information and a raw-trace checksum.
- `analysis.json` and `analysis.md`: population-changing events, first growth
  times, completed-depth counts and per-role final prefix populations.

Village distances are **single-group lower bounds** for certain recruitment.
They do not model blocking, enemy interception, risky battles or joint arrivals.
The actual board and moves are also saved so these approximations can be checked.

The recorder mirrors the existing match runner's agent/battle seeding,
own-turn history and skipped-turn timeout rules. Its observer is restored even
on failure. It changes no shared agent or search source file. Recording work
can still affect machine scheduling, so these are new diagnostic runs, not
identical reconstructions of earlier timed games.

## Replay and analysis

```powershell
python scripts/diagnose_mcts_recruitment.py --analyse .local/diagnostics/RECRUITMENT-RUN
```

This validates trace checksums and reproduces every recorded board transition
from the executed moves and battle seed. It also regenerates the analysis.
It does **not** rerun the AI to reconstruct identical wall-time-limited choices.
An interrupted run preserves flushed lines and completed prefix summaries;
the analysis command verifies and aggregates completed prefixes.

For a quick fixed-iteration functional check on the bundled map:

```powershell
python scripts/diagnose_mcts_recruitment.py --map maps/demo.xml --agent "mcts-v1:iterations=32" --opponent baseline --move-time 0 --stop-after-plies 4 --roles 2
```

That changes opponent and search budgets and must not be presented as a
comparison with Julian's retained timed configuration.

## How to use the evidence

Find the first population-changing events and inspect the preceding boards,
V1's candidate list and visits. If a useful plan was not generated, investigate
candidate coverage. If it was present and received little search or a low
value, investigate ordering, exploration and long-range evaluation. Prefix
populations alone cannot prove which alternative was strategically best.

Recorded battle outcomes permit exact transition replay; evaluating a different
move would be a counterfactual experiment. Keep it separate from observations.
Confirm a proposed change in full games on all four maps and then unseen maps.

## Verification

```powershell
python -m unittest tests.test_diagnose_mcts_recruitment -v
```

The nine tests cover normal game-clock preservation, untimed parity with the
original match runner, root-result capture, stochastic transition replay,
timeout skips, legal fallbacks after faults, tamper detection, dry-run behavior,
Windows worker spawning and preservation of existing outputs.
