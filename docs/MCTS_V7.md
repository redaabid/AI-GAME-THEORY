# MCTS V7: persistent objectives for tied loops

V7 adds a bounded objective planner and positional guidance to V6. The target
problem is a repeated tied board where ordinary search gives quiet moves the
same value. No neural network is included. Its first full comparison regressed
against V6. The subsequent [controlled test](MCTS_V7_CONTROLLED_RESULTS.md)
found that objectives changed movement but did not improve the recorded draw.

## When it activates

V7 initially behaves like V6. Planning starts when both populations are equal
and an exact board has appeared on a previous own turn in the last 32 supplied
history entries. The position key includes dimensions, actor, rules and cells,
but ignores elapsed plies. Immediate adjacent enemy contact defers to V6.

After activation, a valid objective can persist as the board changes. Its
default lifetime is 16 plies (eight own turns); it is reconsidered each turn.
A changed population balance, immediate contact, missing target or changed
group counts ends it. Tracking uses nearby equal-count detachments, not true
server-provided group identities. Ambiguous equal-size groups are a limitation.

This deliberately targets tied repetitions. Ordinary opening play, losing
endgame risk-taking and V6's existing repetition rule retain their control
behavior. It does not add a general tie repetition penalty.

## What it compares

At most three objectives are proposed, with coverage for different kinds:

- **Intercept:** approach a smaller enemy group, including worthwhile uncertain
  battles such as 16 versus 12. The 1.5x guarantee is not a requirement.
- **Recruit:** approach humans that the selected group can certainly convert.
  The planner does not propose charging an oversized village with insufficient
  troops.
- **Regroup:** join an ally, potentially unlocking a larger village or a
  stronger attack. The partner can stay still so the merge is actually legal.

The desired first move must be present in V6's existing MCTS candidate set.
Unsupported or pruned first moves are not assumed available. Legal movement,
blocked sources, stack bounds and counterattack exposure are checked.

Each objective is simulated against three cheap opponent profiles:
recruiting/economic, regrouping, and evasive. They can move multiple groups.
They are simplified reply models, not Julian's actual alpha-beta search and
not an exhaustive adversarial solution.

The default comparison uses three samples per objective/profile and up to 24
plies per continuation. Every actual simulated move uses the stochastic server
combat model. Opponent turns alternate normally. After a nonterminal population
change, the continuation includes the opponent's reply before stopping, unless
the horizon or actual game cap ends the line. Actual terminal rewards are exact.

Rank objectives by the worst profile's sample mean, using common random seeds
across alternatives. Commit a sample only after every objective and profile
completes; incomplete comparison groups are discarded. Negative best values
defer to V6. A valid old objective is retained when within 0.02 of the best
nonnegative score. Tied comparison values use the proposal order, based on
discounted recruitment/expected material gain. None of these scores is a
proven win probability.

## How it guides MCTS

The chosen objective is a preference, not a forced move. V6's adversarial UCT,
candidate generator, tree depth cap and six-ply rollout policy remain intact.
For nonterminal leaves that preserve the root populations and have no adjacent
enemy contact, a bounded distance-progress term is added to V6's value.
Its default maximum magnitude is 0.12. Progress is scaled by the initial
distance, with a denominator clamped between two and eight steps.

If material changes or opposing groups touch, the ordinary V6 value applies.
Elimination and the actual population-at-cap outcome always use exact rewards;
a draw remains zero. This is a heuristic for choosing useful movement on flat
leaves, not a learned evaluator or a guarantee that pursuing an enemy wins.

The planner receives at most 15% of the remaining thinking budget, capped at
0.2 seconds. It shares the same total deadline with MCTS. If no complete initial
comparison fits, V6 continues without a new objective. At a normal 1.5-second
thinking allowance this leaves at least about 1.3 seconds for the main search.
An explicit `time_limit` covers the whole decision, including planning.

With no time limit, objective work is bounded by counts/depth instead, making
fixed-iteration probes reproducible. At defaults its maximum is 648 simulated
plies, before earlier terminations. Separate planner/search RNGs keep
`goals=False` exactly equivalent to V6 at fixed iterations and seed.

## Local checks before matches

The portable [tied-position fixture](../examples/mcts_v7_tied_objectives.json)
contains the earlier V5 board at ply 58 and its real previous own-turn history.
It is not a solved position and does not contain the original turn RNG state.

In four new fixed-seed probes (0-3), each with 512 main MCTS iterations, V7
selected an interception objective and moved inward toward the opposing group.
V6's seed-zero control stayed at the right edge, moving (28,0) to (28,1).
V7's seed-zero move was (28,0) to (27,1), pursuing the enemy 12 at (11,2).
Its initial objective comparisons all scored zero: no winning continuation was
established. The inward choice demonstrates the new progress guidance only.

A new single-position timed check with a 1.5-second thinking deadline completed
three comparison samples in about 0.129 seconds. V7 completed 811 main search
iterations versus V6's 924; both returned in about 1.502 seconds, within the
2-second hard allowance, without faults. V7 again moved inward while V6 stayed
at the edge. This idle-CPU check is not a six-worker throughput or strength
measurement. Its full data is `.local/probes/mcts-v7-timed-position.json`.

Tests also force a capture-then-counterattack sequence and check that its
two-ply loss is scored as a loss, validate objective tracking and reset,
verify terminal values, exercise expired deadlines, and compare disabled
V7 exactly against V6 on four development maps, both species and both clocks.

## Start the 32-game comparison

From the repository directory:

```powershell
python scripts/compare_mcts_v7.py --opponent v6 --workers 6 --dry-run
python scripts/compare_mcts_v7.py --opponent v6 --workers 6
```

Defaults: 32 games on the same four prepared maps, eight per map, balanced
species and first-player roles, 1.5 seconds thinking inside a 2-second allowance,
200-ply cap and a 100,000-iteration ceiling. Six workers are now the default,
matching the user's recent V6 tests. Lower `--workers` if needed on another CPU.

Checkpoint/report directory: `.local/campaigns/mcts-v7-vs-v6/`.
Add `--max-games 4` to finish at most four additional games now. Rerun the exact
command to resume completed-game checkpoints; unfinished games restart.
Keep the computer awake and keep the same worker count when resuming.

Against Julian's same retained AB2 width-7 profile:

```powershell
python scripts/compare_mcts_v7.py --opponent width7 --workers 6
```

This saves separately under `.local/campaigns/mcts-v7-vs-julian-ab2-width7/`.
The opponent is exactly
`ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000`.
Other choices are `v5`, `v1` and the retained AB2 `reference` profile.

The disabled-objective ablation has a separate default directory:

```powershell
python scripts/compare_mcts_v7.py --agent mcts-v7:goals=False --opponent width7 --workers 6
```

The manifest pins core sources plus V5, V6, V7 and the new launcher. Existing
V5/V6 source fingerprints and completed campaigns remain unchanged. For changed
parameters or worker counts, choose a new `--checkpoint` directory.

## Record why the objectives succeed or fail

A separate recorder writes complete boards, executed moves, battle-replay
metadata, root candidates/visits/values, chosen objectives, reply-profile scores,
planning time and activation status:

```powershell
python scripts/trace_mcts_v7.py --opponent width7 --dry-run
python scripts/trace_mcts_v7.py --opponent width7
```

It plays one new `testmap2` diagnostic using role 1 by default, under the same
turn allowance. `--role 1` through `--role 4` select balanced roles, `--map`
accepts another XML, and `--seed` selects another seed. Timed decisions can
vary and this single-worker diagnostic is not a replay of the six-worker run.

Each run creates `.local/diagnostics/v7-TIMESTAMP/` containing:

- `manifest.json`: exact settings, maps and source hashes.
- `source.zip`: the source snapshot needed to inspect the recording.
- `game.jsonl`: full per-turn positions, objective comparisons and root search.
- `summary.json`: result or truncation, objective activations, faults/timeouts
  and trace fingerprint. Saved moves/battle seed are verified against the final
  board before this summary is written.

`--stop-after-plies 80` records only an opening; a nonterminal opening is
labelled truncated, not a draw. Ctrl+C keeps the partial JSONL trace. This new
format does not yet have a dedicated HTML replay viewer. No data collection
command trains a neural model automatically.

The ordinary campaign report contains aggregate MCTS statistics, not individual
objective decisions. Use the recorder to investigate activation, chases and
abandoned targets. Compare total match score, newly won draws and newly lost
draws, per-map outcomes and search throughput. A smaller draw count alone is
not evidence of improvement.

## Verification

```powershell
python -m unittest discover -s tests -p "test_mcts_v7.py" -v
python -m unittest discover -s tests -p "test_compare_mcts_v7.py" -v
```

These checks include source provenance, exact retained opponents, balanced plans,
Windows spawned workers, saved-game resume, incompatible-setting rejection and
a small fully recorded/replayed diagnostic. Tiny integration games test the
pipeline; they do not measure strength. The launchers let the user initiate
new full comparisons without changing the earlier checkpoints.

The complete repository suite passed **318 tests** after the V7 implementation.
