# V5 against Julian AB2 width 7: first completed comparison

Verified on 6 November 2026 from all 32 per-game checkpoints and the saved
manifest in `.local/campaigns/mcts-v5-vs-julian-ab2-width7/`.

V5 finished **13 wins, 11 draws, 8 losses**, a **57.8125% match score**.
V1 previously finished **11 wins, 7 draws, 14 losses**, scoring **45.3125%**
against the identical opponent. The observed difference is **+12.5 percentage
points**. Score means `(wins + 0.5 * draws) / games`, not the proportion of
outright wins.

## Comparable setup and checkpoint verification

- Same AB2 spec: `ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000`.
- Same four maps, seeds, two rounds, species and first-player roles.
- Same 1.5-second thinking budget, 2-second hard allowance, 200-ply cap and two workers.
- Both manifests pin identical core source hashes. V5's four isolated source
  hashes also match the current implementation. Per-game job/result checksums
  and the report's correspondence to the checkpoints passed verification.
- V5 adds the recruitment-feasibility leaf value to V1; it uses no neural network.

Timed iteration counts can still vary with machine load. This is one small
comparison against one opponent profile, not a statistically established ranking.
The retained AB2 profile also has pending WPF-server validation.

## Results by map

W/D/L and scores are from MCTS's perspective; each row contains eight games.

| Map | V1 W/D/L | V1 score | V5 W/D/L | V5 score |
|---|---|---|---|---|
| testmap2 | 0 / 2 / 6 | 12.50% | 1 / 7 / 0 | 56.25% |
| thetrap | 5 / 0 / 3 | 62.50% | 6 / 0 / 2 | 75.00% |
| val-large-1290000 | 4 / 0 / 4 | 50.00% | 3 / 1 / 4 | 43.75% |
| val-medium-1280000 | 2 / 5 / 1 | 56.25% | 3 / 3 / 2 | 56.25% |
| **Total** | **11 / 7 / 14** | **45.31%** | **13 / 11 / 8** | **57.81%** |

The strongest result is on `testmap2`, the map that motivated the change. Its
six V1 losses became zero V5 losses. All eight V5 games reached the 200-ply
cap: seven draws at 16 versus 16 units, and one win at 13 versus 12. Average
MCTS final population rose from 9.875 to 15.625; average final margin rose
from -6 to +0.125. There were no timeouts on this map in either campaign.

This is consistent with the recruitment-value diagnosis. It does not prove
every opening follows the recorded example, or that long-range planning is
solved. V5 still recorded 514 repeated own-turn positions across 800 decisions
on this map, mostly at equal population. Time spent behind fell from 615/798
V1 decisions to 50/800 V5 decisions; repeated positions while behind fell
from 108 to zero. Existing repetition memory acts only while losing, so it
does not resolve these tied endgames.

`thetrap` improved in the aggregate, the medium map's score stayed equal,
and the large map's score decreased. Outside `testmap2`, aggregate score
changed only from 56.25% to 58.33%, before excluding standby-affected games.
Most of the overall improvement therefore comes from the targeted weakness.

## Two games were affected by laptop standby

Both agents have zero recorded faults. The report records two timeouts for
V5 and two for AB2, confined to these two games:

| Saved game | Map | Agent whose turns timed out | Plies | Wall seconds / CPU seconds |
|---|---|---|---|---|
| 15 | thetrap | V5 | 125, 127 | 348.324 / 0.359; 1579.433 / 0.641 |
| 17 | val-large-1290000 | AB2 | 17, 19 | 349.065 / 1.109; 1579.433 / 0.609 |

Windows System events confirm Modern Standby entry at **10:34:31** local time
on 6 November, a transition at **10:40:16**, and exit at **11:06:37** with
reason `Lid`. The two pauses match the recorded wall-time outliers while CPU
time remained below 1.2 seconds. The runner skipped those turns under its
normal timeout policy, so both complete games should be repeated for a clean
comparison. Both currently count as V5 wins; original checkpoints are retained.

Excluding the same two scheduled game indices from both campaigns gives:

| Agent | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| V1 | 30 | 9 | 7 | 14 | 41.67% |
| V5 | 30 | 11 | 11 | 8 | 55.00% |

This sensitivity check still favors V5 in the observed sample. The remaining
schedule has uneven roles on two maps, so it is not a replacement for rerunning
the affected games. Keep the laptop awake during future timed runs.

## Search behavior and next experiment

V5 averaged about **1,590 completed iterations per decision**, versus **1,941**
for V1 (about 18% fewer). Different game trajectories and CPU load contribute,
so this is not a controlled measurement of evaluator overhead. Mean completed
tree depth stayed near 3.3 plies, with a maximum of 7 in both campaigns;
rollouts averaged about 5.76 plies, with the same six-ply limit.

The observed gain came with the existing search horizon. V5 is the next
candidate to validate: repeat the two standby-affected games, then compare V1
and V5 on fresh maps, including asymmetric layouts. Diagnose tied late-game
positions and the large-map losses before bundling further strategy changes.
The direct V5-versus-V1 comparison has not yet been run.

See [the V5 guide](MCTS_V5.md) for commands and the exact evaluation change.

## Behavior supported by the saved records

On `testmap2`, the share of V5 decisions made while behind was **50/800
(6.25%)**, compared with V1's **615/798 (77.07%)**. Its better final population
and zero losses support the recruitment-value adjustment. However, its
**514/800 repeated positions (64.25%)** show that remaining competitive often
leads to a stalemate. None of these V5 repeated positions occurred while
behind. The memory wrapper only applies penalties when `own < enemy`, so it
does not discourage repetitions at equal population or while ahead. Breaking
such ties needs a useful, risk-aware alternative; simply forcing an attack
could sacrifice a draw.

V5 can also finish attacks: four of its six wins on `thetrap` ended by
elimination. One of its other two wins on that map was standby-affected.
All four large-map losses reached the population-scored turn cap rather than
ending by elimination. After removing the large-map game affected by AB's
standby timeouts, its remaining result there is 2 wins, 1 draw, 4 losses.
These records identify a persistent population deficit on that map, but do
not establish whether missed recruitment or combat losses caused it.

One hypothesis is that the conservative feasibility gate undervalues growth
chains beyond the short search horizon. An army of 12 can first recruit four
humans and then recruit a village of 14; the larger village becomes eligible
as soon as that growth actually appears in a simulated leaf. A leaf reached
before the growth will omit it. This is a hypothesis to check in recorded
large-map trajectories, not a confirmed explanation of the four losses.

The campaign saves per-game populations, repetition counts, search aggregates
and exceptional slow-turn snapshots. It does not retain every ordinary move
or every AB decision's completed depth. Exact movement routes and tactical
mistakes therefore require a new recorded diagnostic, rather than inventing
a replay of these timed games.

## Why the opponent spec says depth=1

For the tested `ab2exp` profile, iterative deepening is enabled. In
`agents/ab_variants.py`, the search chooses its depth ceiling as follows:

```python
cap = self.max_depth if context.deadline is not None else self.depth
```

- `depth=1` is the depth cap for an **untimed** search.
- `max_depth=24` is the ceiling for a **timed** search. Our campaign gives both
  agents a deadline 1.5 seconds after their turn starts.
- The engine completes depth 1, then 2, then 3, and so on. If the next depth
  runs out of time, it returns the best move from the last completed depth.
- `agent.info['depth']` / `AB_METRICS depth` is that actual completed depth;
  it is distinct from the `depth=1` configuration parameter.
- One depth unit is a whole turn by one player (one ply), potentially moving
  several groups. Depth 6 covers about three turns for each player.

The earlier four recorded **V1** opening prefixes used the identical AB
configuration and timed budget. They retained 96 AB decisions: **7 at depth
5, 51 at depth 6 and 38 at depth 7**. This demonstrates actual deeper searches
with these settings, but is not a depth distribution for the V5 campaign,
which did not retain those per-decision metrics. A ceiling of 24 does not mean
24 plies were reached, and changing the untimed `depth` parameter would not
raise the timed ceiling.

Two subsequent full-game diagnostics now record all decisions and actual AB
depths. They expose tied zero-valued moves and repeated deferral of guaranteed
recruitment, with zero faults/timeouts. See the
[full investigation and offline replay](MCTS_V5_DIAGNOSTIC.md).
