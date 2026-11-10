# V8: bounded interception analysis on V6

V6 remains the reference. V8 is an unvalidated experiment: V6 plus a small root
selection preference for moves that lead to contact in a bounded intact-group
pursuit model. It does not inherit V7's persistent goals or distance reward.
Recruitment evaluation, stochastic battles, MCTS depths and ordinary rollouts
are inherited from V6. No neural network is trained or used.

## Start the comparison yourself

From the repository directory in PowerShell:

```powershell
python scripts/compare_mcts_v8.py --opponent v6 --workers 6
```

This starts **32 games on four prepared maps**, eight games per map, with both
species and starting orders balanced. Each bot has 1.5 seconds thinking within
a two-second allowance; V8's analysis is included in that thinking budget.
The game cap is 200 individual player turns (plies).

The launcher prints its plan immediately and saves progress when games finish;
several minutes without a finished-game line can be normal. Results and completed
game checkpoints go to `.local/campaigns/mcts-v8-vs-v6/`. Run exactly the same
command to resume. Completed games remain saved; an unfinished game restarts.
Keep the computer awake while playing timed games.

Add `--dry-run` to validate the plan without games, or `--max-games 4` to finish
at most four additional games this session. The defaults require the existing
four XML files in `.local/maps/mcts-vs-best-ab/`.

After reviewing that comparison, face Julian's retained AB2 width-7 profile:

```powershell
python scripts/compare_mcts_v8.py --opponent width7 --workers 6
```

That command uses a separate checkpoint folder. Its exact AB2 specification and
published validation status are printed and retained in the manifest. V6 is
still the reference; a new version number is not evidence of higher strength.

## What V8 checks

For at most four stronger-own/weaker-enemy group pairs, first look for a legal
enemy rendezvous outside all our armies' reachable sets. Both enemy groups can
move. In the recorded 16-16 snapshot, the 12 and 4 can merge in six enemy turns,
before any of our armies can contact them. A found witness rules out forcing
contact **before that available merge**, not winning the rest of the match.
Blocked midpoint routes and missing witnesses are inconclusive.

For other selected pairs, check existing whole-group quiet root moves against
all neighboring evader moves plus waiting, within eight future plies. Waiting
overapproximates enemy choices when a sole group must move. Third-party armies
use expanding reachable envelopes: possible intervention is unresolved, not a
frozen-ally assumption. Stepping onto a human village is also unresolved.

This is a bounded **intact-group geometric model**. It does not enumerate enemy
splits, prove full-game wins, or substitute for stochastic battle evaluation.
An enemy can initiate a risky battle; geometric contact is not a guaranteed
capture. `avoid` means no forced contact within this model's horizon, not that
the group can escape forever. `unknown` means no conclusion.

When some root moves yield contact in that model, other quiet moves receive
an additional root UCT selection penalty between zero and 0.08. This preference
is fixed during that decision; it is **not** progressive bias. Empirical backed-up
values, terminal rewards, root candidates, and direct recruitment/attack choices
remain unchanged. No action is banned. If no contact is verified, V6's original
decision method is used after the analysis. There is no multi-turn commitment.

Analysis has a shared 4,000-node limit and, in timed play, at most 30 ms or 5%
of the remaining whole-decision time, whichever is smaller. Partial comparisons
are discarded. Fixed-iteration play has a node limit without a wall-clock
cutoff, so it is reproducible but gives V8 extra analysis computation.

## Diagnostics and control

Record one new detailed game, including analysis statuses and root visits:

```powershell
python scripts/trace_mcts_v8.py --opponent v6
```

The trace defaults to `testmap2`, writes a fresh `.local/diagnostics/v8-*/`
directory, archives its sources, and checks all transitions against the saved
battle seed. It is a new game, not an exact replay of a timed campaign game.
`summary.json` reports actual root-guidance decisions and analysis statuses.
Campaign aggregate scores alone do not establish how often guidance activated.

Disable interception analysis for a V6 control:

```powershell
python scripts/compare_mcts_v8.py --agent mcts-v8:interceptions=False --opponent v6 --workers 6
```

This uses a separate control folder. At fixed iterations and equal seeds,
disabled V8 reproduces V6's moves, root targets and RNG stream. The known merge
snapshot also falls back to the same V6 search when analysis is enabled.

The new tests cover legal merge witnesses, blocked or interfered routes, the
clock, bounded contact versus avoidance, recruitment uncertainty, budget/deadline
fallbacks, species symmetry, control parity, Windows worker spawning, checkpoints
and replayable traces. No full strength campaign was launched during setup.

See [the research note](MCTS_RESEARCH_NEXT_UPGRADES.md) for the rationale and the
subsequent recruitment investigation. Existing V6/V7 algorithm files and old
campaign fingerprints are preserved.
