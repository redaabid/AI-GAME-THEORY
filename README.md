> **Avancement AB2 de Julian — branche du 4 novembre 2026 :** [configurations, code et résultats](README_JULIAN_ALPHA_BETA_2026-11-04.md).

# AI Game Theory: Vampires vs Werewolves

**Team quickstart:** the latest MCTS experiments are on `feat/mcts-memory`.
See [the current handoff](docs/MCTS_TEAM_HANDOFF.md) for checkout, tests, map
setup and the V9-versus-V6 command. V6 remains the reference.

A four-person team project to build an AI for the Vampires vs Werewolves game.
The repository contains a Python benchmark bot, a CPU simulator, and agents behind
one interface: `alphabeta`, `oep`, `portfolio`, `mcts`, `baseline`, and `random`,
plus the experimental `mcts-memory`, `mcts-v1`, `mcts-v2`, and `mcts-v3` variants on `feat/mcts-memory`.
A round-robin tournament compares them, and `tune.py` tunes them offline.

**MCTS v3 = V1 plus coordinated rollouts.** It keeps V1's six-ply rollout
horizon, memory and turn-limit evaluation. Start the 32-game comparison against
V1 on four maps yourself:

```sh
python campaign.py --opponent mcts-v1 --agent mcts-v3
```

It prints progress and saves each completed game. Run the same command to resume.
Reports: `.local/campaigns/mcts-v3-vs-v1/`;
see [the v3 guide](docs/MCTS_V3.md) for settings and commands.

**MCTS V4: experimental contextual parameter tuning.** V1's exploration and
rollout length adapt to distances, group counts and remaining turns. The
[V4 research and run guide](docs/MCTS_V4.md) explains the sources, limits and
separate launcher. The completed 32-game comparison finished **14 wins / 1 draw /
17 losses** for V4 against V1, with zero timeouts or faults for either agent.

**Exploration-only V4 also completed 32 games:** **13 wins / 1 draw / 18 losses**
against V1. Its reproduction/resume command is:

```sh
python scripts/compare_mcts_v4.py --opponent v1 --exploration-only
```

Reports and resumable checkpoints go to
`.local/campaigns/mcts-v4-exploration-vs-v1/`. Add `--dry-run` to preview or
`--max-games 4` to finish at most four additional games this session.

**Latest opponent test: V1 against Julian AB2 width 7.** MCTS finished
**11 wins / 7 draws / 14 losses** across 32 balanced games, with zero timeouts
or faults for either agent. The main weakness was `testmap2`; see the
[analysis and next steps](docs/MCTS_JULIAN_RESULTS.md).

**Recruitment diagnosis:** four recorded openings exposed a retreat/loop near
a guaranteed village capture. The [recorder and findings](docs/MCTS_RECRUITMENT_DIAGNOSTIC.md)
include a portable counterexample and a controlled evaluation probe. Run a new
diagnostic with `python scripts/diagnose_mcts_recruitment.py`.

**MCTS V5 = V1 plus recruitment-feasibility evaluation.** It applies the
diagnostic's village-value adjustment during search. Start the separate
32-game comparison against Julian's retained AB2 width-7 profile yourself:

```sh
python scripts/compare_mcts_v5.py --opponent width7
```

Eight games on each of the same four maps, with 1.5 seconds thinking per turn.
Add `--dry-run` to preview or `--max-games 4` to play four additional games;
rerun to resume. Results: `.local/campaigns/mcts-v5-vs-julian-ab2-width7/`.
The first completed run scored **13 wins / 11 draws / 8 losses** (57.81%),
versus V1's 45.31% against the same opponent. Two games were affected by laptop
standby; see [the verified V5 results](docs/MCTS_V5_RESULTS.md) and
[the V5 guide](docs/MCTS_V5.md) for controls, limits and commands.

Two full V5 game recordings now expose the tied endgame and delayed recruitment
on the large map. See [the investigation and offline replay](docs/MCTS_V5_DIAGNOSTIC.md).

**MCTS V6 = V5 plus clock-aware endgame evaluation.** With no humans left and
fewer than 40 plies remaining, simulated positions are scored increasingly by
their population-at-cap result. This tests whether V5 can take worthwhile
risks instead of waiting for a population loss. See [the V6 guide](docs/MCTS_V6.md)
for the two-position probes, limits and controls. Start its separate 32-game
comparison against V5 yourself:

```sh
python scripts/compare_mcts_v6.py --opponent v5
```

Use `--opponent width7` to face Julian's retained AB2, `--dry-run` to preview,
or `--max-games 4` to play only four additional games. Completed games are
checkpointed; rerun to resume. Completed six-worker V6 runs scored **16 wins /
4 draws / 12 losses against V5** (56.25%) and **16 wins / 10 draws / 6 losses
against Julian's AB2 width 7** (65.63%). All eight AB2 games on `testmap2`
ended 16-16 at the turn cap. Both runs had zero faults and timeouts.

**MCTS V7 = V6 plus persistent objectives after a tied board repeats.** It
compares interception, recruitment and regrouping plans against three simple
reply models, then adds bounded progress guidance to MCTS. See [the V7 guide](docs/MCTS_V7.md)
for the exact activation, local probes, controls and full-game recorder.
Start its separate 32-game comparison against V6 with six workers:

```sh
python scripts/compare_mcts_v7.py --opponent v6 --workers 6
```

Use `--opponent width7` to face Julian's retained AB2. Add `--dry-run` to
preview, or `--max-games 4` to complete only four more games. Rerun to resume.
Record a new detailed game with
`python scripts/trace_mcts_v7.py --opponent width7` to inspect its objectives.

**V7 controlled diagnosis:** the first 32-game comparison finished
**8 wins / 5 draws / 19 losses** against V6 (32.81%). Six games had system-stall
timeouts; excluding those left 32.69%. A later diagnostic won for V7 with zero
objective activations. The [controlled stalemate experiment](docs/MCTS_V7_CONTROLLED.md)
therefore compares goals on/off directly from the recorded 16-16 position,
using paired seeds and fixed MCTS budgets. The completed controlled test ended
in **four draws with objectives on and four draws with objectives off**;
[the results](docs/MCTS_V7_CONTROLLED_RESULTS.md) explain why pursuing the
enemy failed to close the gap. V6 remains the reference version.

**MCTS V8: experimental interception feasibility on V6.** It checks moving
enemy merge escapes and bounded intact-group contact scenarios, then applies
a small root selection preference only when the model verifies contact.
V6 remains the reference; recruitment changes come later. Launch the new
32-game, four-map comparison yourself:

```sh
python scripts/compare_mcts_v8.py --opponent v6 --workers 6
```

Rerun the same command to resume completed-game checkpoints. Add `--dry-run`
to preview or `--max-games 4` to play at most four additional games. See
[the V8 guide](docs/MCTS_V8.md) for limits, diagnostics and the AB2 command.

The completed V8 comparison scored **11 wins / 2 draws / 19 losses** against
V6 (37.5%), with zero faults or timeouts. V6 remains the reference.

**MCTS V9 = V6 plus short recruitment-sequence planning.** It compares capture
timing, future growth, enemy village races and counterattack exposure, with
bounded root guidance. The local recorded-position probe changes V6's delayed
14-human capture to an immediate capture for four fixed seeds; match strength
is not yet established. Launch the separate 32-game comparison yourself:

```sh
python scripts/compare_mcts_v9.py --opponent v6 --workers 6
```

Results and planner activations/cost are saved separately in `report.md` and
`recruitment.md` under `.local/campaigns/mcts-v9-vs-v6/`. Rerun to resume;
add `--dry-run` to preview or `--max-games 4` for four additional games. See
[the V9 guide](docs/MCTS_V9.md) for assumptions, controls and when to consider
a small neural guide. V9 currently has no neural network.

To play V5 against another team's bot on their course server, use the
[remote match guide](docs/PLAY_FRIEND_V5.md) and `scripts/play_mcts_v5.py`.

The completed local V2 comparison scored **9 wins / 1 draw / 22 losses** against
V1. V3 isolates coordination from V2's other rollout changes. See
[the v2 guide](docs/MCTS_V2.md) for that version's implementation.

**Earlier: 32 timed games against AB2 and AB6**, plus resumable per-game
checkpoints: [results and team handoff](docs/MCTS_AB_COMPARISON.md). MCTS scored
7 W / 3 D / 6 L against AB2 and 7 W / 2 D / 7 L against AB6; two MCTS timeouts in
the AB6 batch need investigation. No overall champion is established by this sample.

Earlier engine comparisons: [docs/RESULTS.md](docs/RESULTS.md). Earlier progress notes:
[docs/PROGRESS.md](docs/PROGRESS.md) (15 October 2026).

## What runs during a game?

| Program | Job |
| --- | --- |
| Game server | Shows the map, alternates turns, and resolves battles |
| Bot A | Controls one species |
| Bot B | Controls the other species, initially using the same Python code |

The server chooses which species each bot controls. Start the server first, then
both bots. The first bot can wait while the second connects.

## Get started

Install Git and Python 3.10 or newer, then open a terminal:

```sh
git clone https://github.com/redaabid/AI-GAME-THEORY.git
cd AI-GAME-THEORY
python --version
python -m unittest discover -s tests -v
```

If you already cloned the repository, save your work, then run
`git switch main` and `git pull --ff-only` to update it.

The bot, setup command, and tests use only the Python standard library. You can
run them directly without installing packages. A GPU is for later training work.
On macOS or Linux, use `python3` if that is your interpreter's command name.

## Compare models: the common base

Every model implements one `Agent` interface (`agents/`), and a round-robin
tournament compares them all in the simulator, on fair generated maps:

```sh
python tournament.py --agents baseline portfolio alphabeta oep mcts --random-maps 6 --family large --move-time 0
```

`--move-time 0` gives fast, reproducible untimed games; the default (2 s per move,
as on the server) is realistic but slow. It prints a score matrix (who beats whom), an Elo ranking, decision times,
timeouts, and faults. To add a model, create `agents/<name>.py`; see
[docs/COMMON_BASE.md](docs/COMMON_BASE.md). Any registered agent plays live with
`python main.py --agent <spec> IP PORT`.

Registered engines: `baseline`, `random`, `mcts`, `portfolio` (Portfolio Greedy
Search), `alphabeta` (iterative deepening with chance nodes), and `oep` (online
evolutionary planning). `tune.py` tunes their parameters offline.
This branch also includes `mcts-memory` and Julian's `ab0`–`ab8` variants;
`ab7` requires an explicit weight dictionary. See [the AB2/AB6 guide](docs/WATCH_MATCH.md).

## Experimental MCTS: memory and the turn limit

To try this branch after saving your work:

```sh
git fetch origin
git switch feat/mcts-memory
python -m unittest discover -s tests -q
python demo_mcts_memory.py
```

The demo loads a losing loop from a recorded server match. At a fixed 2,048
iterations, original MCTS repeats the recorded retreat; memory MCTS chooses
another move. It remembers repeated quiet decisions while behind and can ignore
human groups that cannot be reached before the turn limit. No GPU is needed.

This is an experiment, not a new champion: **96 CPU games across six maps showed
no win-rate improvement** against alpha-beta. All four switch combinations scored
7 wins, 2 draws, and 15 losses each. See [the implementation and results](docs/MCTS_MEMORY.md)
for the reproduction commands, diagnostics, and remaining work.

Compare all four variants yourself:

```sh
python benchmark_mcts.py --iterations 128 --max-plies 200
```

With the prepared 40-ply demo server running, the new agent can play live:

```sh
python main.py --agent mcts-memory --max-plies 40 --move-time 0.15 --name Memory 127.0.0.1 5555
```

Start a second bot in another terminal, as described below. For a 200-ply server,
use `--max-plies 200 --move-time 1.5`. The original `mcts` remains the control agent.

## Run CPU games without the graphical server

From the repository folder:

```sh
python simulate.py --games 20 --seed 42
```

This runs the baseline against a random agent on `maps/demo.xml`, rotating species
and the first player in four-game blocks. It needs Python only: no GPU, server,
course ZIP, or extra packages. It prints the results folder under `.local/simulations/`.

Each run exports `manifest.json`, `games.jsonl`, and `transitions.jsonl`. These
baseline/random examples let your colleague build and test a GPU data loader.

To run the new search agent and export root visit targets:

```sh
python simulate.py --agent mcts --opponent baseline --games 4 --iterations 128 --seed 42
```

To compare both agents on all bundled development maps, with balanced species
and first-player roles on every map:

```sh
python evaluate.py --games 8 --iterations 128 --seed 100 --max-plies 60
```

This plays eight games per map and writes a JSON report under `.local/evaluations/`.
See [docs/MCTS.md](docs/MCTS.md) for the algorithm, initial measurements, timing
budgets, and training-label meanings. The candidate generator includes joint
arrivals, independent group movement, and selected recruitment splits.

To watch memory MCTS against Julian's AB2 or AB6 on four comparison maps, follow
[the three-terminal commands](docs/WATCH_MATCH.md). These variants are available
on this branch; the guide also gives a balanced 32-game CPU comparison.
Use `python campaign.py --opponent ab2 --max-games 4` to play four games and save
them, then `python campaign.py --opponent ab2` to resume later. The same commands
with `ab6` run the other 16-game campaign. Prepare the four maps using the guide
first. Completed games are checkpointed individually; unfinished games restart.

Use `--map path/to/map.xml`, `--max-plies 100`, or `--output .local/my-new-run` to
choose the map, turn cap, and a new output folder. Existing runs are preserved.
See [docs/CPU_GPU_HANDOFF.md](docs/CPU_GPU_HANDOFF.md) for the simulator API and data contract.

### Rule profiles

The supplied v3.2.1 model differs from the written brief: an attack against a
defender at least 1.5 times stronger remains random. Its human-conversion and
attacker-victory thresholds agree with the brief. Both the live benchmark and
simulator default to `server-v3.2.1`; every exported state records that profile.
Use `--rules-profile brief` with `main.py` or `simulate.py` to use the written
guaranteed-defender rule. Confirm which server/rules the instructor will grade.

The simulator explicitly rejects turns whose possible resulting population
exceeds 255 on one cell. Byte-overflow behavior is outside the current model.

To repeat the optional Windows reference checks after preparing the course server:

```powershell
.\scripts\check_server_model.ps1
```

This checks the supplied model DLL directly, without launching its GUI, and writes
`.local/server-model-check.json`. The reference checks cover ten movement/rule
cases and four combat distributions with 20,000 samples each. The portable Python
test suite uses the same movement fixtures plus independent probability tests.

## Prepare the Windows server

Get **`Softwares-20261008.zip`** from the course materials or a teammate. Keep the
outer ZIP intact: it contains `Server v3.2.1.zip` and `Map generator.zip`.
Your colleagues need their own copy of this course archive.

From the repository folder in **PowerShell**, run this command if the ZIP is in
your Downloads folder:

```powershell
python scripts/setup_server.py "$env:USERPROFILE\Downloads\Softwares-20261008.zip"
```

If you saved it elsewhere, replace the quoted path with its actual location.
The script creates `.local/server/` with the executable, DLLs, map, and config.
It prepares a two-player demo on **127.0.0.1:5555**, with a two-second move limit
and a 40-ply or 30-second game limit. These generated files are ignored by Git.

Re-running setup with `--force` replaces the generated files and resets the demo
settings. Use `--map testmap2.xml` to select the other supplied map, or
`--port 5556` to change ports. Use that same port in both bot commands below.

The graphical server is a Windows .NET Framework application. The Python bot and
tests also run on macOS and Linux; for a full match, use an accessible Windows
server. Hosting for other computers requires configuring the server's `ServerIP`
for that network and giving both bots the host's address.

## Start a match

Open `.local/server/` in File Explorer and double-click
**`VampiresVSWerewolvesGameServer.exe`**. Leave its window open to watch the board.
Alternatively, from the repository folder in PowerShell:

```powershell
Start-Process -FilePath ".\.local\server\VampiresVSWerewolvesGameServer.exe" -WorkingDirectory ".\.local\server"
```

Open **two separate terminals** in the repository folder. In VS Code, use
**Terminal > New Terminal**, then the terminal panel's **+** button for another.

In terminal A:

```sh
python main.py --name Bot-A 127.0.0.1 5555
```

In terminal B:

```sh
python main.py --name Bot-B 127.0.0.1 5555
```

The bots play automatically. Terminals log the assigned species, moves, and
decision times. `Game ended` and `Server finished the session` indicate a
completed match. The server window shows the board.

Both bots use the `baseline` engine by default. To play the shared alpha-beta engine in
terminal A instead, run:

```sh
python main.py --agent alphabeta --max-plies 40 --move-time 0.15 --name AlphaBeta 127.0.0.1 5555
```

The short budget suits the demo's 30-second game cap, and `--max-plies` must match
the server's `MaxPlays` (40 in the demo, 200 by default): the engines plan the
endgame with it. For real matches, keep the defaults (`--move-time 1.5`,
`--max-plies 200`): `python main.py --agent alphabeta IP PORT`. Any spec works,
for example `--agent oep` or `--agent "mcts:iterations=512"`.

To play again, close and reopen the server, then re-run both bot commands. To
stop early, press **Ctrl+C** in each bot terminal and close the server window.

For longer matches, edit `MaxPlays` and `MaxGameDuration` in
`.local/server/VampiresVSWerewolvesGameServer.exe.config` before starting it.
Keep `MaxPlayDuration` at `00:00:02` to match the brief.

## Code and checks

The benchmark bot moves one whole group per turn. It seeks humans it can convert,
considers friendly merging and enemy targets, and penalizes exposure to immediate
enemy counterattacks. It provides a baseline for later search and learning work.

The client handles TCP messages split across reads, board updates, game resets
(`END`), and session endings (`BYE`). Logs show the selected move and decision time.

| File | Responsibility |
| --- | --- |
| `client.py` | TCP connection and binary protocol |
| `game.py` | Board state, species identification, and movement validation |
| `strategy.py` | Baseline move selection and combat probability calculation |
| `combat.py` | Shared probability rules and integer battle sampling |
| `simulator.py` | Immutable states, complete-turn transitions, outcomes, XML loading |
| `simulate.py` | CPU games and versioned JSONL export |
| `candidates.py` | Bounded whole-turn generation, recruitment splits, coordinated moves |
| `search.py` | Adversarial UCT, sampled battles, deadline, root visit targets |
| `agents/mcts_memory.py` | Experimental repeated-position memory and clock switches |
| `demo_mcts_memory.py` | Replay one recorded losing decision with all four switch combinations |
| `benchmark_mcts.py` | Balanced comparison of original, memory, clock, and both against one opponent |
| `evaluate.py` | Balanced multi-map comparisons and decision timing |
| `main.py` | Command-line entry point and game loop; `--agent` takes any registered agent |
| `agents/` | Shared `Agent` interface, registry, safety net, built-in agents |
| `tournament.py` | Round-robin tournament: score matrix, Elo, timing, faults |
| `mapgen.py` | Fair symmetric random maps with train/val/test splits |
| `macro.py` | Orders per group (macro-actions) turned into legal moves |
| `evaluation.py` | Human-race evaluation with tunable weights |
| `playbook.py` | Scripted group behaviours and deterministic playouts |
| `lookahead.py` | Candidate turns and win/loss branches of uncertain battles |
| `tune.py` | Offline tuning: SPSA, genetic search, Texel |
| `agents/alphabeta.py`, `agents/oep.py`, `agents/portfolio.py` | Search engines built on the shared modules |
| `config.py` | Default server address and port |
| `scripts/setup_server.py` | Prepare the course server and a map locally |
| `tests/` | Protocol, board, simulator, engines, tournament, and mock-server checks |

Run the checks with:

```sh
python -m unittest discover -s tests -v
```

The checks include a local mock server to verify communication and game resets.
The bot has also completed a two-bot compatibility match on the supplied Server
v3.2.1 using `thetrap.xml`, a two-second move limit, and a 40-ply test cap.
The simulator supports splitting and combined arrivals. The benchmark agent still
moves one full group per turn; the search engines also split and coordinate groups.
Teammates' real-server alpha-beta campaigns are on the
`julian-tests-alpha-beta-2026-10-27` branch. The 32-game memory-MCTS comparison
reported here uses the CPU simulator. Validate the final selected variant on
the course server before the tournament. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Configuration and troubleshooting

Running `python main.py` uses `config.py` (127.0.0.1, port 5555). Command-line IP
and port override those defaults. Both bots must use the address and port of the
server you started. Tournament launchers can append them after your options.

| What you see | What to check |
| --- | --- |
| `python` is unavailable | Install Python or select the correct interpreter; on Windows, try `py -3` instead of `python` |
| `can't open file main.py` | Run commands from the cloned `AI-GAME-THEORY` folder |
| Setup cannot find the ZIP | Check the path; supply the outer `Softwares-20261008.zip` archive |
| `Connection refused` / error 10061 | Start the server and match its configured port in both bot commands |
| One bot waits without moving | Start the second bot in a separate terminal |
| Server cannot bind its port | Close the previous server, or prepare a different port and use it in both bot commands |
| Server does not open | Check its Windows .NET Framework runtime and keep both DLLs beside the executable |
| Game ends after a short time | The demo caps play at 40 individual turns or 30 seconds |

## How to collaborate

1. **Pick a task.** Check the [GitHub issues](https://github.com/redaabid/AI-GAME-THEORY/issues) or create one. Comment on the issue to let the team know you are working on it.

2. **Create your branch.** From the project folder, run:

   ```sh
   git switch main
   git pull --ff-only origin main
   git switch -c your-name/task-name
   ```

   Replace `your-name/task-name` with a descriptive name, such as `reda/update-readme`.

3. **Make your changes and push them.** Replace `path/to/changed-file` with the file you changed and use the branch name you chose above:

   ```sh
   git add path/to/changed-file
   git commit -m "Describe your changes"
   git push -u origin your-name/task-name
   ```

4. **Open a pull request.** Go to the [repository](https://github.com/redaabid/AI-GAME-THEORY), click **Compare & pull request**, and choose `main` as the base branch. Explain what you changed, link your issue, and ask a teammate to review it before merging.

For your next task, repeat these steps with a new branch. Use issues and pull request comments to share progress or ask for help.

You need write access to push branches to this repository. Ask the repository owner for an invitation if you need access.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution guidelines.
