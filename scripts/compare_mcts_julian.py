"""Checkpointed MCTS comparison against Julian's published retained AB2 specs.

    python scripts/compare_mcts_julian.py --agent mcts-v3 --opponent width7
    python scripts/compare_mcts_julian.py --agent mcts-v1 --opponent width7

Run these after the existing campaign finishes to avoid competing for CPU time.
This launcher does not modify the engines or the existing campaign runner.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents import make_agent, parse_spec
from campaign import MAP_NAMES, make_plan, run_campaign
from simulator import load_map

PROFILE_FILE = ROOT / "scripts" / "ab2_retained_profiles.json"
OPPONENTS = {"width7": "ab2_width7", "reference": "ab2_reference", "tie-width7": "ab2_tie_width7"}


def comparison_plan(agent, opponent, *, maps=None, rounds=2, workers=2, iterations=100000):
    """Read the published spec verbatim; pin launcher and profile provenance too."""
    name, params = parse_spec(agent)
    if name not in ("mcts", "mcts-memory", "mcts-v1", "mcts-v2", "mcts-v3"):
        raise ValueError("Choose an MCTS agent for this comparison.")
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be a positive integer.")
    if "iterations" not in params:
        agent += f"{',' if ':' in agent else ':'}iterations={iterations}"
    retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    profile = OPPONENTS[opponent]
    names = [agent, retained["profiles"][profile]]
    for spec in names:
        make_agent(spec)
    if maps is None:
        maps = [(map_name, load_map(ROOT / ".local/maps/mcts-vs-best-ab" / f"{map_name}.xml"))
                for map_name in MAP_NAMES]
    plan = make_plan(names, maps, rounds=rounds, workers=workers, seed=20261028,
                     max_plies=200, move_time=2.0, margin=0.5)
    plan["comparison"] = {
        "opponent_profile": profile,
        "published_status": retained["validation_status"][profile],
        "launcher_sha256": sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "retained_profiles_sha256": sha256(PROFILE_FILE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
    }
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", default="mcts-v3", help="MCTS spec; default mcts-v3")
    parser.add_argument("--opponent", choices=OPPONENTS, default="width7")
    parser.add_argument("--rounds", type=int, default=2, help="4 balanced roles per map per round")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--maps", nargs="+", type=Path, help="XML files or folders; default the four prepared maps")
    parser.add_argument("--max-games", type=int, help="Complete at most N additional games this session")
    parser.add_argument("--checkpoint", type=Path, help="Override the separate per-agent/opponent checkpoint folder")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without starting games or writing files")
    args = parser.parse_args(argv)
    if min(args.rounds, args.workers, args.iterations) < 1 or (args.max_games is not None and args.max_games < 1):
        parser.error("rounds, workers, iterations and max-games must be positive")

    def progress(done, total, result):
        if result is None:
            print(f"Saved {done}/{total}. Workers running if games remain...", flush=True)
        else:
            score = {0: "loss", 0.5: "draw", 1: "win"}[result["a_score"]]
            print(f"Saved {done}/{total} | {result['map_name']} | {label} {score} | {result['plies']} plies", flush=True)

    try:
        maps = None
        if args.maps:
            paths = [file for path in args.maps for file in
                     (sorted(path.glob("*.xml")) if path.is_dir() else [path])]
            maps = [(path.stem, load_map(path)) for path in paths]
        plan = comparison_plan(args.agent, args.opponent, rounds=args.rounds,
                               workers=args.workers, iterations=args.iterations, maps=maps)
        label = parse_spec(plan["agents"][0])[0]
        directory = args.checkpoint or ROOT / ".local/campaigns" / f"{label}-vs-julian-ab2-{args.opponent}"
        print(f"Checkpoint: {directory.resolve()}", flush=True)
        print(f"Agents: {plan['agents'][0]} vs {plan['agents'][1]}", flush=True)
        print(f"Published opponent status: {plan['comparison']['published_status']}", flush=True)
        map_count = len({job["map_name"] for job in plan["jobs"]})
        print(f"Planned: {len(plan['jobs'])} games | {map_count} maps | {args.rounds} rounds | {args.workers} workers", flush=True)
        print("Thinking time: 1.5 s each | allowance 2 s | cap 200 plies", flush=True)
        if args.dry_run:
            print("Plan validated. No games started and no checkpoint files written.")
            return 0
        report, interrupted = run_campaign(plan, directory, max_games=args.max_games, progress=progress)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Comparison setup/run failed: {error}\nSaved games are preserved.\n")
    print(f"{report['completed_games']}/{report['total_games']} saved. Report: {directory / 'report.md'}")
    if report["status"] != "complete":
        print("Run the same command later to resume; unfinished games restart.")
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
