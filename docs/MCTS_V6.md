# MCTS V6: make the turn limit matter in endgames

V6 is V5 plus one experimental leaf-value adjustment. When no humans remain
and the game is close to its turn limit, a small population deficit should
look more like the loss it would become if neither side fights. This can make
a worthwhile risky battle preferable to waiting, and help the leading side
preserve its advantage. Search still decides which move to play.

## Exact rule

The adjustment applies to **nonterminal simulated leaves**, with a known
`max_plies`, zero humans anywhere on the real board, and fewer than
`endgame_window=40` plies remaining. A ply means one player's turn.

The weight increases linearly: zero at 40 remaining, one half at 20, and
approaching one near the cap. The value blends V5's evaluation with the result
if the current populations were kept until the cap: +1 for a lead, -1 for a
deficit, 0 for a tie. Actual terminal results remain exactly +1, -1 or 0.

For example, in the recorded position at ply 167/200, V5 has 52 vampires
against 56 werewolves and there are no humans. V5's static value is about
**-0.059**. V6 uses a 17.5% clock weight and scores the same board about
**-0.223**. Losing those four units of population advantage at the cap is now
more consequential. With 20 plies remaining, the unchanged board would score
about -0.529. These are heuristic scores, not predicted win probabilities.

This rule treats both species symmetrically. It does not award a separate
attack bonus. Battles still use the simulator's sampled stochastic outcomes;
the search, six-ply rollouts, candidates, memory and default budgets remain
V5's. It adds no neural network or training stage.

The window of 40 plies is an initial parameter, not a researched optimum or
a learned setting. Positions with any remaining humans retain V5's value,
including positions with oversized villages. Delayed village collection and
the tied `testmap2` loop remain separate problems. The existing rollout policy
also remains a limited model of Julian's play.

## Local evidence before full matches

The portable [two-position fixture](../examples/mcts_v6_endgame.json) comes
from the previously recorded large-map game. The original per-turn RNG state
was not saved, so these searches are counterfactual probes, not exact replays
of the timed decision.

With **1,024 iterations per search**, default V5 search settings, and fixed
seeds 0 through 11 on the late position:

| Decision | V5 | V6 |
| --- | ---: | ---: |
| Attack the adjacent enemy army | 9/12 | 12/12 |
| Choose a quiet move | 3/12 | 0/12 |

Seeds 0-3 were checked first, then 4-11 with the same settings. The attack is
52 against 46, with an approximately **63.04% chance of winning that battle**.
This is not the probability of winning the match: survivors and subsequent
opponent replies still matter. V5 already chooses the battle in many probes;
the observed timed refusal was not its only possible behavior.

On the early position at ply 25, both versions avoided the tempting certain
9-versus-1 kill in all four seeds 0-3 at 1,024 iterations. Enemy 19 is adjacent
to that destination and can certainly kill the surviving nine immediately.
Both versions instead moved the other army toward recruitment. This confirms
the new rule does not simply force monster attacks in this counterexample.

These repeated searches concern only two boards. They do not establish a
higher match win rate or an optimal policy.

## Start the comparison yourself

From the repository directory, preview the default plan:

```sh
python scripts/compare_mcts_v6.py --opponent v5 --dry-run
```

Start **32 games against V5**, eight per map on `testmap2`, `thetrap`,
`val-large-1290000` and `val-medium-1280000`:

```sh
python scripts/compare_mcts_v6.py --opponent v5
```

Each map has two rounds of the four balanced species/first-player roles.
Each agent gets 1.5 seconds of thinking within a 2-second allowance, with a
100,000-iteration ceiling and a 200-ply game cap. Two workers run by default.
The launcher uses the existing four prepared XMLs under
`.local/maps/mcts-vs-best-ab/`; `--maps` accepts other XML files or folders.

To test against Julian's same retained AB2 width-7 profile:

```sh
python scripts/compare_mcts_v6.py --opponent width7
```

The exact opponent remains
`ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000`.
It uses timed iterative deepening; `depth=1` does not restrict the timed
search to one ply. Its WPF-server validation is still pending.

Results are saved separately in `.local/campaigns/mcts-v6-vs-v5/` or
`.local/campaigns/mcts-v6-vs-julian-ab2-width7/`. Each completed game is saved;
rerun the same command to resume. Add `--max-games 4` to play only four more
games now. An interrupted unfinished game restarts. Keep the computer awake
during timed matches. The launcher prints progress and reports faults,
timeouts, match scores and per-map results.

Compare V6's score against V5 and its per-map results against the previous V5
AB2 run. Check timeouts and search throughput as well as wins/draws/losses.
Thirty-two games are an initial comparison; they cannot establish a champion.

## Ablation and source preservation

`mcts-v6:endgame=False` reproduces V5 at fixed iterations and seed. It gets
a separate default checkpoint directory:

```sh
python scripts/compare_mcts_v6.py --agent mcts-v6:endgame=False --opponent width7
```

`clock=False` also disables the calibration. The inherited
`feasibility=False` option bypasses V5's custom leaf callback and therefore
disables this addition as well. The actual game cap is enforced in all cases.

To try another window, use an explicit new checkpoint folder:

```sh
python scripts/compare_mcts_v6.py --agent mcts-v6:endgame_window=60 --opponent v5 --checkpoint .local/campaigns/mcts-v6-window60-vs-v5
```

The manifest pins core sources, the V5 parent package, V6 package and launcher,
maps, settings and retained AB profile where used. Changed experiments cannot
resume into the same folder. V6 uses a separate package and entry point;
the previous V5/core sources and their campaign fingerprints remain intact.

## Verification

```sh
python -m unittest discover -s tests -p "test_mcts_v6.py" -v
python -m unittest discover -s tests -p "test_compare_mcts_v6.py" -v
```

The checks cover weight boundaries, terminal outcomes, species symmetry,
ties, humans and unknown clocks, exact V5 parity when disabled, the recorded
battle and counterattack, stochastic simulation, deadlines, legal fallbacks,
balanced plans, exact AB profiles and Windows-worker checkpoint resume.
