"""Run the isolated adaptive V4 after the existing V1/V3 campaign finishes.

    python scripts/compare_mcts_v4.py --dry-run
    python scripts/compare_mcts_v4.py --opponent v1
    python scripts/compare_mcts_v4.py --opponent v1 --exploration-only

Uses the existing checkpoint runner and simulator. Importing V4 explicitly at
module scope also registers it in Windows spawn workers. No shared engine or
running campaign source file is modified.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.mcts_v4  # Explicit registration in parent and spawned workers.
import campaign
import tournament
from agents import make_agent, parse_spec
from simulator import load_map

OPPONENTS = {"v1": "mcts-v1", "v3": "mcts-v3",
             "julian-width7": "ab2_width7", "julian-reference": "ab2_reference"}
PROFILE_FILE = ROOT / "scripts/ab2_retained_profiles.json"


def source_hashes():
    paths = [Path(__file__), *sorted((ROOT / "scripts/mcts_v4").glob("*.py"))]
    return {p.relative_to(ROOT).as_posix(): sha256(
        p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in paths}


def comparison_plan(agent="mcts-v4", opponent="v1", *, maps=None, rounds=2,
                    workers=2, iterations=100000, move_time=2.0, margin=0.5,
                    max_plies=200, seed=20261028, exploration_only=False):
    name, params = parse_spec(agent)
    if name != "mcts-v4":
        raise ValueError("This isolated launcher requires the mcts-v4 agent.")
    if type(exploration_only) is not bool:
        raise ValueError("exploration_only must be True or False.")
    if exploration_only:
        if params.get("adaptive", True) is not True:
            raise ValueError("--exploration-only requires adaptive=True.")
        if params.get("tune_rollout", False) is not False:
            raise ValueError("--exploration-only conflicts with tune_rollout=True.")
        if "tune_rollout" not in params:
            agent += f"{',' if ':' in agent else ':'}tune_rollout=False"
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be a positive integer.")
    if "iterations" not in params:
        agent += f"{',' if ':' in agent else ':'}iterations={iterations}"
    other = OPPONENTS[opponent]
    provenance = {}
    if opponent.startswith("julian-"):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        provenance = {"profile": other, "status": retained["validation_status"][other],
                      "retained_profiles_sha256": sha256(
                          PROFILE_FILE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
        other = retained["profiles"][other]
    else:
        other += f":iterations={iterations}"
    for spec in (agent, other):
        make_agent(spec)
    if maps is None:
        maps = [(name, load_map(ROOT / ".local/maps/mcts-vs-best-ab" / f"{name}.xml"))
                for name in campaign.MAP_NAMES]
    plan = campaign.make_plan([agent, other], maps, rounds=rounds, workers=workers,
                              seed=seed, max_plies=max_plies, move_time=move_time, margin=margin)
    plan["v4_source_sha256"] = source_hashes()
    plan["v4_opponent"] = provenance
    return plan


def checkpoint_label(agent):
    """Keep full adaptation, exploration-only and fixed controls separate."""
    _, params = parse_spec(agent)
    if params.get("adaptive") is False:
        return "mcts-v4-fixed"
    return "mcts-v4-exploration" if params.get("tune_rollout") is False else "mcts-v4"


def run_v4_job(job):
    """Attach V4's context/parameter trace using a process-local observer.

    The existing tournament aggregator keeps only common scalar diagnostics.
    This observer preserves that behavior and adds V4 metadata to the result.
    It is restored even on failure and never writes shared source files.
    """
    trace = []
    original = tournament.safe_choose

    def observe(agent, position, context):
        moves, fault = original(agent, position, context)
        if agent.name == "mcts-v4" and agent.info and "adaptive" in agent.info:
            trace.append({"ply": position.ply, "species": position.to_play, "fault": fault,
                          **agent.info["adaptive"]})
        return moves, fault

    tournament.safe_choose = observe
    try:
        result = tournament._run_job(job)
    finally:
        tournament.safe_choose = original
    return result | {"v4_decisions": trace}


def tuning_summary(report):
    contexts, arms = Counter(), Counter()
    decisions = samples = 0
    seconds = 0.0
    for game in report["games"]:
        for decision in game.get("v4_decisions", []):
            decisions += 1
            contexts[decision["context"].get("regime", "fallback")] += 1
            samples += decision["samples"]
            seconds += decision["tuner_cpu_seconds"]
            for arm in decision["arms"]:
                arms[(arm["exploration"], arm["rollout_depth"])] += arm["samples"]
    lines = ["# V4 tuning diagnostics", "",
             f"{report['status'].upper()}: {report['completed_games']}/{report['total_games']} games.", "",
             f"Challenger: `{report['plan']['agents'][0]}`.", "",
             f"V4 decisions: {decisions}; completed tuning observations: {samples}; "
             f"controller CPU: {seconds:.6f} s.", "",
             "Simulation feedback is an internal proxy, not an observed match win rate.", "",
             "| Context | Decisions |", "|---|---|",
             *[f"| {name} | {count} |" for name, count in sorted(contexts.items())], "",
             "| Exploration C | Rollout limit (plies) | Completed simulations |", "|---|---|---|",
             *[f"| {c:g} | {depth} | {count} |" for (c, depth), count in sorted(arms.items())], "",
             "See report.md for actual match scores, throughput, timeouts and faults.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", default="mcts-v4", help="V4 spec; adaptive=False supplies the fixed V1 control")
    parser.add_argument("--exploration-only", action="store_true",
                        help="Tune exploration only; keep V1's rollout limit (default 6 plies)")
    parser.add_argument("--opponent", choices=OPPONENTS, default="v1")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--move-time", type=float, default=2.0, help="Hard allowance; 0 means fixed-iteration screening")
    parser.add_argument("--margin", type=float, default=0.5)
    parser.add_argument("--maps", nargs="+", type=Path, help="XML files or folders; default the four prepared maps")
    parser.add_argument("--max-games", type=int, help="At most N additional games this session")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Validate without starting games or writing files")
    args = parser.parse_args(argv)
    if args.max_games is not None and args.max_games < 1:
        parser.error("max-games must be positive")

    def progress(done, total, result):
        if result is None:
            print(f"Saved {done}/{total}. Workers running if games remain...", flush=True)
        else:
            score = {0: "loss", 0.5: "draw", 1: "win"}[result["a_score"]]
            print(f"Saved {done}/{total} | {result['map_name']} | V4 {score} | {result['plies']} plies", flush=True)

    try:
        maps = None
        if args.maps:
            paths = [file for path in args.maps for file in
                     (sorted(path.glob("*.xml")) if path.is_dir() else [path])]
            maps = [(path.stem, load_map(path)) for path in paths]
        plan = comparison_plan(args.agent, args.opponent, maps=maps, rounds=args.rounds,
                               workers=args.workers, iterations=args.iterations, seed=args.seed,
                               max_plies=args.max_plies, move_time=args.move_time, margin=args.margin,
                               exploration_only=args.exploration_only)
        label = checkpoint_label(plan["agents"][0])
        directory = args.checkpoint or ROOT / ".local/campaigns" / f"{label}-vs-{args.opponent}"
        print(f"Checkpoint: {directory.resolve()}", flush=True)
        print(f"Agents: {plan['agents'][0]} vs {plan['agents'][1]}", flush=True)
        challenger = make_agent(plan["agents"][0])
        tuning = ("exploration + rollout length" if challenger.tune_rollout else "exploration only")
        print(f"Tuning: {tuning if challenger.adaptive else 'disabled'}"
              f" | base rollout limit: {challenger.config.rollout_depth} plies", flush=True)
        print(f"Planned: {len(plan['jobs'])} games | {len({j['map_name'] for j in plan['jobs']})} maps"
              f" | {args.rounds} rounds | {args.workers} workers", flush=True)
        thinking = f"{args.move_time - args.margin:g} s each" if args.move_time else "fixed iteration cap"
        print(f"Thinking time: {thinking} | allowance {args.move_time:g} s | cap {args.max_plies} plies", flush=True)
        if args.dry_run:
            print("Plan validated. No games started and no checkpoint files written.")
            return 0
        original = campaign._run_job
        campaign._run_job = run_v4_job
        try:
            report, interrupted = campaign.run_campaign(plan, directory, max_games=args.max_games, progress=progress)
        finally:
            campaign._run_job = original
        (directory / "tuning.md").write_text(tuning_summary(report), encoding="utf-8")
        print(f"{report['status'].upper()}: {report['completed_games']}/{report['total_games']}. "
              "Rerun the same command to resume.", flush=True)
        print(f"Results: {directory.resolve() / 'report.md'}", flush=True)
        print(f"Tuning diagnostics: {directory.resolve() / 'tuning.md'}", flush=True)
        return 130 if interrupted else 0
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
