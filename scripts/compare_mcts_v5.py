"""Checkpointed V5 comparison against Julian's retained AB2 or the V1 control.

    python scripts/compare_mcts_v5.py --opponent width7 --dry-run
    python scripts/compare_mcts_v5.py --opponent width7
    python scripts/compare_mcts_v5.py --opponent v1

Default: 32 games on four maps, balanced species and first player, 1.5 s thinking
per turn. Run the same command to resume completed-game checkpoints.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.mcts_v5  # Register in the parent AND Windows spawn workers.
from agents import make_agent, parse_spec
from campaign import MAP_NAMES, make_plan, run_campaign
from simulator import load_map

PROFILE_FILE = ROOT / "scripts/ab2_retained_profiles.json"
OPPONENTS = {"width7": "ab2_width7", "reference": "ab2_reference", "v1": "mcts-v1"}


def source_hashes():
    paths = [Path(__file__), *sorted((ROOT / "scripts/mcts_v5").glob("*.py"))]
    return {path.relative_to(ROOT).as_posix(): sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for path in paths}


def comparison_plan(agent="mcts-v5", opponent="width7", *, maps=None, rounds=2,
                    workers=2, iterations=100000, move_time=2.0, margin=0.5,
                    max_plies=200, seed=20261028):
    name, params = parse_spec(agent)
    if name != "mcts-v5":
        raise ValueError("This isolated launcher requires the mcts-v5 agent.")
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be a positive integer.")
    if "iterations" not in params:
        agent += f"{',' if ':' in agent else ':'}iterations={iterations}"
    other = OPPONENTS[opponent]
    provenance = {}
    if opponent == "v1":
        other += f":iterations={iterations}"
    else:
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        provenance = {"profile": other, "published_status": retained["validation_status"][other],
                      "retained_profiles_sha256": sha256(
                          PROFILE_FILE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
        other = retained["profiles"][other]
    for spec in (agent, other):
        make_agent(spec)
    if maps is None:
        maps = [(name, load_map(ROOT / ".local/maps/mcts-vs-best-ab" / f"{name}.xml"))
                for name in MAP_NAMES]
    plan = make_plan([agent, other], maps, rounds=rounds, workers=workers, seed=seed,
                     max_plies=max_plies, move_time=move_time, margin=margin)
    plan["v5_source_sha256"] = source_hashes()
    plan["v5_opponent"] = provenance
    return plan


def checkpoint_directory(agent, opponent):
    """The disabled-feature control has its own default result folder."""
    _, params = parse_spec(agent)
    label = "mcts-v5-control" if params.get("feasibility") is False else "mcts-v5"
    suffix = "v1" if opponent == "v1" else f"julian-ab2-{opponent}"
    return ROOT / ".local/campaigns" / f"{label}-vs-{suffix}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", default="mcts-v5", help="V5 spec; feasibility=False gives the V1 control")
    parser.add_argument("--opponent", choices=OPPONENTS, default="width7")
    parser.add_argument("--rounds", type=int, default=2, help="Four balanced roles per map per round")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--move-time", type=float, default=2.0, help="Hard allowance; 0 for fixed-iteration screening")
    parser.add_argument("--margin", type=float, default=0.5)
    parser.add_argument("--maps", nargs="+", type=Path, help="XML files or folders; default the four prepared maps")
    parser.add_argument("--max-games", type=int, help="Finish at most N additional games this session")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Validate without starting games or writing checkpoints")
    args = parser.parse_args(argv)
    if args.max_games is not None and args.max_games < 1:
        parser.error("max-games must be positive")

    def progress(done, total, result):
        if result is None:
            print(f"Saved {done}/{total}. Workers running if games remain...", flush=True)
        else:
            score = {0: "loss", 0.5: "draw", 1: "win"}[result["a_score"]]
            print(f"Saved {done}/{total} | {result['map_name']} | V5 {score} | {result['plies']} plies", flush=True)

    try:
        maps = None
        if args.maps:
            paths = [file for path in args.maps for file in
                     (sorted(path.glob("*.xml")) if path.is_dir() else [path])]
            maps = [(path.stem, load_map(path)) for path in paths]
        plan = comparison_plan(args.agent, args.opponent, maps=maps, rounds=args.rounds,
                               workers=args.workers, iterations=args.iterations, seed=args.seed,
                               max_plies=args.max_plies, move_time=args.move_time, margin=args.margin)
        directory = args.checkpoint or checkpoint_directory(plan["agents"][0], args.opponent)
        print(f"Checkpoint: {directory.resolve()}", flush=True)
        print(f"Agents: {plan['agents'][0]} vs {plan['agents'][1]}", flush=True)
        if plan["v5_opponent"]:
            print(f"Published opponent status: {plan['v5_opponent']['published_status']}", flush=True)
        challenger = make_agent(plan["agents"][0])
        print(f"Recruitment-feasibility evaluation: {'enabled' if challenger.feasibility else 'disabled (V1 control)'}",
              flush=True)
        print(f"Planned: {len(plan['jobs'])} games | {len({job['map_name'] for job in plan['jobs']})} maps"
              f" | {args.rounds} rounds | {args.workers} workers", flush=True)
        thinking = f"{args.move_time - args.margin:g} s each" if args.move_time else "fixed iteration cap"
        print(f"Thinking time: {thinking} | allowance {args.move_time:g} s | cap {args.max_plies} plies", flush=True)
        if args.dry_run:
            print("Plan validated. No games started and no checkpoint files written.")
            return 0
        report, interrupted = run_campaign(plan, directory, max_games=args.max_games, progress=progress)
        print(f"{report['status'].upper()}: {report['completed_games']}/{report['total_games']} saved.", flush=True)
        print(f"Results: {directory.resolve() / 'report.md'}", flush=True)
        if report["status"] != "complete":
            print("Run the same command later to resume; unfinished games restart.", flush=True)
        return 130 if interrupted else 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Comparison setup/run failed: {error}\nSaved games are preserved.\n")


if __name__ == "__main__":
    raise SystemExit(main())
