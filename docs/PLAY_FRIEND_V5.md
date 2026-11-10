# Play V5 against an opponent over Tailscale

The reviewed `friend_kit.zip` contains a README and `friend_run.py`. The
opponent hosts the real course game server and a benchmark scheduler. V5 runs
on your computer and sends its name and game moves through the TCP protocol.
The reviewed launcher contains no source-code or model-upload step.

## Connection and match format

- `HOST_IP` is the opponent's Tailscale address or hostname, supplied separately.
- TCP port **7000** is the game endpoint, according to this kit.
- TCP port **7001** is the ticket service. The launcher requests a ticket there
  before starting each bot on port 7000. Pass **7000**, not 7001, to `friend_run.py`.
- The README describes **30 games**: five maps, both species, three rounds.
  Two maps are symmetric and three asymmetric, ranging from 7x15 to 29x35.
- The stated limits are **2 seconds per move, 200 plies and 5 minutes per game**.
  These are the opponent's supplied settings; confirm them with the host.
- The opponent saves the results and move times. Ask for the detailed results
  after the run; the client launcher does not produce an authoritative score.

This is a different experiment from the local 32-game V5-versus-AB2 campaign.
Network delay and the different computers also affect the comparison.

## Join the opponent's network

1. Install Tailscale using its [official Windows instructions](https://tailscale.com/docs/install/windows).
2. Open the private invitation your opponent sent and complete sign-in yourself.
   Connect your Tailscale client to the invited network; see
   [the official quickstart](https://tailscale.com/docs/how-to/quickstart).
3. Agree a start time and confirm the host address and the two ports.
4. Open a new PowerShell terminal and check connectivity:

```powershell
tailscale status
tailscale ping HOST_IP
```

Replace `HOST_IP` with the real address. If `tailscale` is not found after
installation, reopen PowerShell or use:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" ping HOST_IP
```

Use Tailscale ping for this check. Leave ports 7000 and 7001 to the launcher:
connecting to the ticket port can consume a game ticket, and connecting to the
game port can occupy a game connection. If Tailscale works but the launcher
cannot start games, the host should check the scheduler, game service, access
permissions and firewall for both TCP ports.

## Run from the repository folder

The supplied kit was copied unchanged into ignored `.local/friend-kit/`;
`source.json` records its archive and file hashes. It is local material and
is not added to Git. No invitation token is saved in the repository.

The dedicated live entry point `scripts/play_mcts_v5.py` registers V5, uses the
existing protocol client and exits on `BYE`. It defaults to 100,000 iterations
bounded by a 1.5-second thinking deadline. Ordinary `main.py` is unchanged.

When your opponent confirms that the benchmark is ready:

```powershell
python .local/friend-kit/friend_run.py HOST_IP 7000 --parallel 1 -- python scripts/play_mcts_v5.py --name Reda-V5 --iterations 100000 --move-time 1.5 --max-plies 200 --rules-profile server-v3.2.1
```

This automatically requests subsequent games until the scheduler stops handing
out tickets. `--parallel 1` means one V5 process at a time, not one game total.
It avoids competing searches on this computer during the initial benchmark.
Agree with the host before increasing parallelism; the kit's example of eight
simultaneous games assumes enough free CPU cores on both machines.

For an append-only local copy of the terminal output, use this variant instead:

```powershell
python .local/friend-kit/friend_run.py HOST_IP 7000 --parallel 1 -- python scripts/play_mcts_v5.py --name Reda-V5 --iterations 100000 --move-time 1.5 --max-plies 200 --rules-profile server-v3.2.1 2>&1 | Tee-Object -FilePath .local/friend-kit/v5-live.log -Append
```

The launcher appends the IP and game port to the bot command. Expected output
includes `Connected to`, `Agent: mcts-v5:iterations=100000`, search iterations,
turns, and `Server finished the session`. Each `BYE` ends that bot process; the
launcher then requests another ticket. `END` clears the game state while
waiting for the server's next command, as required by the course protocol.

Keep the computer awake and plugged in. Network delay counts toward the
host's two-second allowance; 1.5 seconds leaves a nominal half-second for
transport and overhead. Reduce `--move-time` if the measured connection is
slow. Stop other local CPU campaigns during timed remote games.

The supplied launcher's final `no more games` message also appears if it cannot
contact the host after retries; it does not prove 30 games completed. Confirm
the number of completed games and the result with the host.

For a single direct connection, only if the host explicitly provides a normal
game endpoint outside its ticket workflow:

```powershell
python scripts/play_mcts_v5.py --name Reda-V5 --iterations 100000 --move-time 1.5 --max-plies 200 HOST_IP GAME_PORT
```

## Verification

```powershell
python -m unittest discover -s tests -p "test_play_mcts_v5.py" -v
```

The local tests exercise iteration settings, invalid parameters, ticket flow,
real loopback TCP moves, both species, reset on `END`, and exit on `BYE`.
They do not join a Tailscale network or start a remote match.
