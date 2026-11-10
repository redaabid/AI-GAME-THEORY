# Controlled V7 stalemate experiment

The experiment starts directly from the recorded 16-versus-16 board at ply 58,
with its real previous history for **both** species. V7's objective trigger
must activate on the first enabled decision. This avoids spending another
whole opening on a game that never exercises the feature.

The original V7-versus-V6 campaign scored 8 wins, 5 draws and 19 losses for V7
(32.81%). Six games experienced suspension-like stalls; excluding them left
8 wins, 1 draw and 17 losses (32.69%). A subsequent new diagnostic won 10-0
for V7, but its objective planner never activated. Neither result isolates
the objective mechanism. This experiment addresses that specific uncertainty.

## Design fixed before running

- Snapshot: `examples/mcts_v7_controlled_snapshot.json`, from the earlier V5
  full recording. Its complete 58-ply historical prefix replays to the selected
  board. The historical policies are not continued or called experts here.
- Four paired future seeds: 20261108 through 20261111.
- Treatment: `mcts-v7:goals=True,iterations=256`.
- Control: `mcts-v7:goals=False,iterations=256`, which reproduces V6's search.
- Both face `mcts-v6:iterations=256` from identical boards and supplied histories.
- Main MCTS RNG seeds and future battle seeds are matched within each pair.
- No deadlines or time-based early stopping. All main decisions must complete
  exactly 256 MCTS iterations; objective comparisons use V7's unchanged defaults.
- Original absolute cap: ply 200, leaving at most **142** new plies. The cap
  is not restarted at 200 additional moves.
- Six worker processes. Worker scheduling does not control the search budget.

Agents start with fresh search/planner RNGs and no persistent V7 objective;
the historical states/actions are supplied through TurnContext. The recorded
position originally comes from V5 versus AB2, whereas both counterfactual
branches now face V6. These are new continuations, not replays of an old result.

V7 does additional objective-planning work, so this isolates behavior at equal
main search iterations, **not equal total computation**. CPU/wall/planning costs
are recorded. A subsequent timed comparison is needed for deployment strength.
Matched battle seeds also do not force identical battles once actions diverge.

## Run or resume

Preview:

```powershell
python scripts/probe_mcts_v7.py --dry-run
```

Run four pairs (eight continuations):

```powershell
python scripts/probe_mcts_v7.py --pairs 4 --iterations 256 --workers 6 --output .local/experiments/v7-stalemate-20261108-paired256
```

Repeat the exact command to resume completed continuations. Each completed arm
has an independently verified checkpoint. Interrupted attempts remain on disk;
an unfinished arm restarts in a new attempt directory. `--max-continuations 2`
finishes at most two additional arms this session and does not change the plan.
Changed parameters or source require another `--output` folder.

To record only an opening, add `--stop-after-plies 20` and use a separate output
folder. A nonterminal truncation receives **no match score**, not a draw.

Verify saved traces and regenerate the analysis without playing:

```powershell
python scripts/probe_mcts_v7.py --analyse .local/experiments/v7-stalemate-20261108-paired256
```

## Evidence retained

- `manifest.json`: frozen snapshot, both real histories, agent specs, seeds,
  budgets and all relevant source hashes.
- `source.zip`: source archive and a standalone snapshot JSON.
- `pair-0001-on/result.json` and the corresponding `off` result: terminal or
  truncated status, exact outcome, activation count, population events,
  contacts, repetitions and computation cost.
- `pair-0001-on/attempt-0001/trace.jsonl`: every before/after board, executed
  move, root candidates/visits/values, objective before/after each decision,
  reply-profile estimates, goal status, distance and battle probability.
- `analysis.json` and `analysis.md`: both-arm W/D/L and seed-by-seed changes.

All saved moves replay through the stochastic simulator to their final board.
The enabled arm must show an objective on the first decision, and the disabled
arm must never show one. Faults or incomplete MCTS budgets invalidate an arm
instead of becoming fallback-contaminated strength evidence.

Use the traces to distinguish fewer repeated boards from actual winning
progress. Examine target merging, objective expiry, first tactical contact,
population changes, and whether any newly attempted fight helps or hurts.
This small experiment concerns one known development position. It cannot
establish overall superiority or map generalization, and it trains no NN.

The completed eight-continuation run produced **four draws with objectives on
and four draws with objectives off**. See [the verified results and chase diagnosis](MCTS_V7_CONTROLLED_RESULTS.md).

## Verification

```powershell
python -m unittest discover -s tests -p "test_probe_mcts_v7.py" -v
```

Tests cover both real histories, historical replay, deterministic fixed-budget
decisions, on/off activation, the absolute game cap, truncation, Windows-spawn
workers, checkpoint resume, incompatible settings and tampering rejection.
