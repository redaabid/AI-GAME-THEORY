"""Record a new V9 game, including recruitment sequences and MCTS root visits.

    python scripts/trace_mcts_v9.py --dry-run
    python scripts/trace_mcts_v9.py --opponent width7

This is a new timed diagnostic, not a replay of a previous campaign decision.
"""

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from campaign import atomic_json
from scripts.compare_mcts_v9 import OPPONENTS, comparison_plan
from scripts.diagnose_mcts_recruitment import populations, verify_trace
from scripts.diagnose_mcts_v5 import trace_game
from simulator import Position


def record(plan, role, directory, *, stop_after_plies=200):
    job = plan["jobs"][role - 1]
    initial = replace(Position.from_dict(job["map"]), to_play=job["first"])
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    observers = (Path(__file__), ROOT / "scripts/diagnose_mcts_recruitment.py",
                 ROOT / "scripts/diagnose_mcts_v5.py")
    manifest = dict(purpose="new_v9_diagnostic_not_replay", plan=plan, role=role,
                    stop_after_plies=stop_after_plies,
                    observer_sha256={p.relative_to(ROOT).as_posix(): sha256(
                        p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in observers})
    atomic_json(directory / "manifest.json", manifest)
    sources = plan["source_sha256"] | plan["v9_source_sha256"] | manifest["observer_sha256"]
    with zipfile.ZipFile(directory / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for relative, expected in sources.items():
            data = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
            if sha256(data).hexdigest() != expected:
                raise ValueError(f"Source changed while starting diagnostic: {relative}")
            archive.writestr(relative, data)
    specs = {job["a_species"]: job["a"],
             "werewolves" if job["a_species"] == "vampires" else "vampires": job["b"]}
    with (directory / "game.jsonl").open("x", encoding="utf-8") as stream:
        def save(row):
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            if (row["ply"] + 1) % 20 == 0:
                print(f"Recorded {row['ply'] + 1} plies | {row['populations_after']}", flush=True)
        result = trace_game(initial, specs, seed=job["seed"], stop_after_plies=stop_after_plies,
                            on_record=save, **{k: v for k, v in job["settings"].items() if k != "on_timeout"})
    final = verify_trace(result["records"], initial, seed=job["seed"])
    if final.to_dict() != result["final"]:
        raise ValueError("Trace verification ended at another board.")
    decisions = [r for r in result["records"] if r["actor"] == job["a_species"]]
    summary = dict(status=result["status"], outcome=result["outcome"], recorded_plies=len(result["records"]),
                   final_populations=populations(final),
                   guided_decisions=sum(bool((r["agent_info"] or {}).get("recruitment", {}).get("guided")) for r in decisions),
                   recruitment_statuses=dict(Counter((r["agent_info"] or {}).get("recruitment", {}).get("status") for r in decisions)),
                   timeouts=sum(r["timeout"] for r in result["records"]),
                   faults=[r["fault"] for r in result["records"] if r["fault"]],
                   trace_sha256=sha256((directory / "game.jsonl").read_bytes()).hexdigest())
    atomic_json(directory / "summary.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--opponent", choices=OPPONENTS, default="width7")
    parser.add_argument("--agent", default="mcts-v9")
    parser.add_argument("--map", type=Path, default=ROOT / ".local/maps/mcts-vs-best-ab/testmap2.xml")
    parser.add_argument("--role", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--stop-after-plies", type=int, default=200)
    parser.add_argument("--move-time", type=float, default=2.0)
    parser.add_argument("--margin", type=float, default=.5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.stop_after_plies < 1:
        parser.error("stop-after-plies must be positive")
    from simulator import load_map
    try:
        plan = comparison_plan(args.agent, args.opponent, maps=[(args.map.stem, load_map(args.map))],
                               rounds=1, workers=1, iterations=args.iterations, seed=args.seed,
                               max_plies=args.max_plies, move_time=args.move_time, margin=args.margin)
        directory = args.output or ROOT / ".local/diagnostics" / (
            "v9-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        print(f"New diagnostic: {plan['agents']} | role {args.role} | {directory}", flush=True)
        if args.dry_run:
            print("Validated. No game started or files written.")
            return 0
        summary = record(plan, args.role, directory, stop_after_plies=args.stop_after_plies)
        print(json.dumps(summary, indent=2), flush=True)
        print(f"Verified trace: {directory.resolve() / 'game.jsonl'}", flush=True)
        return 0
    except KeyboardInterrupt:
        print("Stopped. Partial JSONL trace is retained; unfinished games are not results.", flush=True)
        return 130
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"V9 diagnostic failed: {error}\nExisting recordings are preserved.\n")


if __name__ == "__main__":
    raise SystemExit(main())




