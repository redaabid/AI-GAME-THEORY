# MCTS memory versus AB2 and AB6: 28 October 2026

The completed CPU campaign contains **32 games across four maps**. Memory MCTS
scored **7 wins / 3 draws / 6 losses against AB2**, then **7 / 2 / 7 against AB6**.
These small samples show competitive results, not a proven ranking or an isolated
benefit from memory. **Two MCTS timeouts occurred in the AB6 series and need
investigation before claiming reliable tournament-budget behavior.**

## Team handoff

- Optional `mcts-memory`: repetition preference while behind and recruitment
  estimates that account for remaining plies. Original `mcts` remains available.
- Independent memory/clock switches, a recorded-decision demo, and the earlier
  [96-game comparison](MCTS_MEMORY.md), which showed no score improvement at
  its smaller fixed-iteration budget against the original alpha-beta engine.
- Julian's unchanged AB0–AB8 module and ten tests, imported from `c1bb526`.
  This campaign uses the selected AB2 and AB6 configurations.
- A separate graphical-server setup for four maps, plus a checkpointed campaign
  runner that saves each completed game and resumes missing ones.
- **157 automated tests passed** before publication. This does not erase the
  two long decision times observed in the AB6 campaign.

This is search implementation and evaluation. No neural network was trained.

## Results from MCTS's perspective

| Map | Against AB2: W / D / L | Against AB6: W / D / L |
| --- | --- | --- |
| `thetrap` | 4 / 0 / 0 | 4 / 0 / 0 |
| `testmap2` | 0 / 1 / 3 | 0 / 0 / 4 |
| Medium: `val-medium-1280000` | 1 / 2 / 1 | 1 / 2 / 1 |
| Large: `val-large-1290000` | 2 / 0 / 2 | 2 / 0 / 2 |
| **Total** | **7 / 3 / 6** | **7 / 2 / 7** |
| **Mean match score** | **0.53125** | **0.50000** |

Score uses win=1, draw=0.5, loss=0; it is not the win percentage. Each opponent
gets four games per map, covering both species and both first-player roles.

`testmap2` is the clear weakness: no wins in eight games across both opponents.
The eight `thetrap` wins also need context: three AB2-series victories ended
with a narrow 9–8 population lead at the cap. Across both series, **25 of 32
games reached the ply limit**, and seven ended by elimination. Population
management and repeated positions remain central issues.

Memory was active on 53 decisions against AB2 and 112 against AB6. The chosen
plan matched a penalized action zero and two times respectively. A penalty is
a preference rather than a ban. These diagnostics do not establish that memory
caused any score gain; there was no original-MCTS control in this campaign.

## Conditions and timing

- Rules: `server-v3.2.1`, sampled battles in the shared CPU simulator.
- MCTS: `mcts-memory:iterations=100000`, default memory and clock enabled.
- Opponent: `ab2` or `ab6`, with
  `width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000`.
  The deadline activates iterative deepening up to depth 8; `depth=1` is the
  untimed setting, not a claim that these timed opponents searched only one ply.
- Decision budget: 1.5 seconds each, from a 2-second allowance minus a 0.5-second
  margin. Two workers; cap 200 plies; seed 20261028.
- Independent policy and battle RNGs. Role/map seeds match across opponents,
  but different actions can consume different draws. Timed decisions vary with
  hardware and load.
- Python 3.12.9. AB2 batch: 1,363.5 seconds; AB6 batch: 1,964.3 seconds.

| Series | MCTS decisions | MCTS faults / timeouts | MCTS max / p95 seconds | Opponent faults / timeouts |
| --- | --- | --- | --- | --- |
| Against AB2 | 1,362 | 0 / 0 | 1.515 / 1.504 | 0 / 0 |
| Against AB6 | 1,324 | 0 / 2 | 13.313 / 1.503 | 0 / 0 |

The two timeouts were on the medium map, with MCTS playing werewolves in both
starting orders (seeds 20561038 and 20561040). The longest decisions were 13.313
and 13.016 seconds. The runner's `on_timeout=skip` policy passed those turns;
both games finished drawn at 23–23 after 200 plies. The summaries do not contain
per-turn traces or system events sufficient to establish the cause. Keep those
results as recorded and rerun/instrument the affected conditions; do not silently
discard them or describe the campaign as timeout-free.

The score difference from the earlier 96-game experiment is not a controlled
before/after improvement: opponents, maps and computation budgets differ.

## Read or reproduce

Archives contain bounded game summaries, without server binaries, per-turn logs,
local training data or checkpoints:

- [AB2: original completed report](experiments/mcts-vs-ab2-2026-10-28.json).
- [AB6: original completed report](experiments/mcts-vs-ab6-2026-10-28.json).
- [Map states, report hashes and verified policy provenance](experiments/mcts-vs-ab2-ab6-2026-10-28-manifest.json).

The reports came from `tournament.py`, which writes only after a whole batch.
Their policy kernel hash matches the current kernel. The additional manifest
supplements that legacy fingerprint with agent/shared-module hashes verified
during archiving; it does not pretend they were captured at match startup.

After saving your own work, get this branch:

```sh
git fetch origin
git switch feat/mcts-memory
git pull --ff-only origin feat/mcts-memory
python -m unittest discover -s tests -q
```

For a visible game or to prepare the four maps, follow [WATCH_MATCH.md](WATCH_MATCH.md).
The course ZIP is required to prepare the two supplied maps locally. Then run:

```sh
python campaign.py --opponent ab2
python campaign.py --opponent ab6
```

For a short session: `python campaign.py --opponent ab2 --max-games 4`. Run the
same opponent command later to resume. Each opponent has a separate folder under
`.local/campaigns/`. Completed games are retained; unfinished ones restart.
These commands create a fresh checkpointed experiment rather than importing
the archived legacy batches. Checkpoints enforce the same code/maps/settings.

Next priorities: investigate the two long decisions, inspect recruitment and
population deficits on `testmap2`, and repeat balanced seeds before selecting
an agent. Keep training, validation and final test maps separate.
