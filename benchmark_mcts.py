"""Compare original MCTS, clock, memory and both against one fixed opponent.

    python benchmark_mcts.py --iterations 128 --max-plies 200

Uses the shared match runner, with independent battle/search RNGs and all four
species/first-player roles per map. Reports include full initial maps, settings,
runtime source hashes, per-map scores, repetitions, timing and faults. No neural
training or history-dependent training labels are generated.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import platform
import time

from agents import make_agent
from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from mapgen import generate_maps
from simulator import load_map
from tournament import _percentile, run_tournament

ROOT = Path(__file__).resolve().parent


def source_hashes():
    paths = sorted([*ROOT.glob("*.py"), *(ROOT / "agents").glob("*.py")])
    return {path.relative_to(ROOT).as_posix(): sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for path in paths}


def variants(iterations):
    return {"original": f"mcts:iterations={iterations}",
            "clock": f"mcts-memory:iterations={iterations},memory=False,clock=True",
            "memory": f"mcts-memory:iterations={iterations},memory=True,clock=False",
            "memory-clock": f"mcts-memory:iterations={iterations},memory=True,clock=True"}


def summarize_games(games):
    scores = [game["a_score"] for game in games]
    stats = [game["a_stats"] for game in games]
    seconds = [s for record in stats for s in record["seconds"]]
    counts = {key: sum(record[key] for record in stats) for key in
              ("moves", "timeouts", "repeated_positions", "behind_moves", "repeated_while_behind",
               "memory_interventions", "repeated_chosen_after_penalty")}
    per_map = {}
    for name in sorted({game["map_name"] for game in games}):
        values = [game["a_score"] for game in games if game["map_name"] == name]
        per_map[name] = {"games": len(values), "wins": values.count(1), "draws": values.count(0.5),
                         "losses": values.count(0), "mean_score": sum(values) / len(values)}
    return {"games": len(games), "wins": scores.count(1), "draws": scores.count(0.5),
            "losses": scores.count(0), "macro_mean_score": sum(
                row["mean_score"] for row in per_map.values()) / len(per_map),
            "per_map": per_map, **counts,
            "repeat_rate": counts["repeated_positions"] / max(1, counts["moves"]),
            "behind_repeat_rate": counts["repeated_while_behind"] / max(1, counts["behind_moves"]),
            "faults": sum(len(record["faults"]) for record in stats),
            "opponent_faults": sum(len(game["b_stats"]["faults"]) for game in games),
            "opponent_timeouts": sum(game["b_stats"]["timeouts"] for game in games),
            "ply_limit_games": sum(game["termination"] == "ply_limit" for game in games),
            "p95_seconds": _percentile(seconds, 0.95), "max_seconds": max(seconds, default=0)}


def run_benchmark(maps, *, iterations=128, rounds=1, seed=20261027,
                  max_plies=200, opponent="alphabeta", move_time=0.0, margin=0.3, progress=None):
    specs = variants(iterations)
    make_agent(opponent)
    summaries, results = {}, {}
    for label, spec in specs.items():
        games = run_tournament([spec, opponent], maps, rounds=rounds, seed=seed,
                               max_plies=max_plies, move_time=move_time, margin=margin,
                               progress=(lambda done, total: progress(label, done, total)) if progress else None)
        summaries[label] = summarize_games(games)
        for game in games:
            for key in ("a_stats", "b_stats"):
                seconds = game[key].pop("seconds")
                game[key]["max_seconds"] = max(seconds, default=0)
                game[key]["p95_seconds"] = _percentile(seconds, 0.95)
        results[label] = games
    return {"schema_version": 1, "purpose": "mcts_memory_clock_ablation",
            "variants": specs, "opponent": opponent, "iterations": iterations,
            "rounds": rounds, "seed": seed, "max_plies": max_plies,
            "move_time": move_time, "margin": margin,
            "maps": [{"name": name, "state": position.to_dict()} for name, position in maps],
            "source_sha256": source_hashes(), "python_version": platform.python_version(),
            "summaries": summaries, "games": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--maps", nargs="+", type=Path, help="XML files; default: four bundled maps")
    parser.add_argument("--random-maps", type=int, default=2, help="Additional medium validation maps")
    parser.add_argument("--map-seed", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=128)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--opponent", default="alphabeta")
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--move-time", type=float, default=0, help="0 = reproducible fixed-iteration screening")
    parser.add_argument("--margin", type=float, default=0.3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if min(args.iterations, args.rounds, args.max_plies) < 1 or args.random_maps < 0:
        parser.error("iterations, rounds, max-plies must be positive; random-maps nonnegative")
    if not isfinite(args.move_time) or args.move_time < 0 or not isfinite(args.margin) or args.margin < 0:
        parser.error("move-time and margin must be finite and nonnegative")
    if args.move_time and args.margin >= args.move_time:
        parser.error("margin must be smaller than move-time")
    output = args.output or ROOT / ".local" / "mcts-memory" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    if output.exists():
        parser.error(f"output already exists: {output}")
    maps = [(path.stem, load_map(path, rules_profile=args.rules_profile)) for path in
            (args.maps or sorted((ROOT / "maps").glob("*.xml")))]
    maps += [(name, type(position).from_dict(position.to_dict() | {"rules_profile": args.rules_profile}))
             for name, position in generate_maps(args.random_maps, family="medium", split="val", seed=args.map_seed)]
    if len({name for name, _ in maps}) != len(maps):
        parser.error("map names must be unique")

    def progress(label, done, total):
        if done == total or done % max(1, total // 4) == 0:
            print(f"{label}: {done}/{total} games", flush=True)

    started = time.perf_counter()
    report = run_benchmark(maps, iterations=args.iterations, rounds=args.rounds, seed=args.seed,
                           max_plies=args.max_plies, opponent=args.opponent, move_time=args.move_time,
                           margin=args.margin, progress=progress)
    report["wall_seconds"] = time.perf_counter() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("\nvariant          W/D/L     score  repeats  memory turns  faults")
    for label, row in report["summaries"].items():
        print(f"{label:16} {row['wins']}/{row['draws']}/{row['losses']:<5} "
              f"{row['macro_mean_score']:.3f}  {row['repeat_rate']:.1%}    "
              f"{row['memory_interventions']:>5}         {row['faults']}")
    print(f"Report: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
