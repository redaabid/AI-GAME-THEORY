# AI Game Theory: Vampires vs Werewolves

A four-person team project to build an AI for the Vampires vs Werewolves game.
The current milestone includes a working Python benchmark bot, a CPU simulator,
and a portable data export for the team's training pipeline. Next we will add
adversarial search and train neural agents offline.

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

If you already cloned the repository, commit your work and run `git switch main`
followed by `git pull --ff-only origin main` to update it.

The bot, setup command, and tests use only the Python standard library. You can
run them directly without installing packages. A GPU is for later training work.
On macOS or Linux, use `python3` if that is your interpreter's command name.

## Run CPU games without the graphical server

From the repository folder:

```sh
python simulate.py --games 20 --seed 42
```

This runs the baseline against a random agent on `maps/demo.xml`, rotating species
and the first player in four-game blocks. It needs Python only: no GPU, server,
course ZIP, or extra packages. It prints the results folder under `.local/simulations/`.

Each run exports `manifest.json`, `games.jsonl`, and `transitions.jsonl`. These
baseline/random examples let your colleague build and test a GPU data loader;
search-generated training targets will come after MCTS is implemented.

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
| `main.py` | Command-line entry point and game loop |
| `config.py` | Default server address and port |
| `scripts/setup_server.py` | Prepare the course server and a map locally |
| `tests/` | Protocol, board, strategy, setup, and mock-server checks |

Run the checks with:

```sh
python -m unittest discover -s tests -v
```

The checks include a local mock server to verify communication and game resets.
The bot has also completed a two-bot compatibility match on the supplied Server
v3.2.1 using `thetrap.xml`, a two-second move limit, and a 40-ply test cap.
The simulator supports splitting and combined arrivals. The benchmark agent still
moves one full group per turn. Deeper search and neural training are the next
milestones. See [docs/ROADMAP.md](docs/ROADMAP.md) for the next tasks.

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
