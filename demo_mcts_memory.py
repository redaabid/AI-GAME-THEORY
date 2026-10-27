"""Replay one recorded losing decision, with independent memory/clock switches.

    python demo_mcts_memory.py
    python demo_mcts_memory.py --move-time 1.5 --iterations 100000

This diagnoses a decision; choosing another move does not establish a win.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import time

from agents import TurnContext, make_agent, safe_choose
from agents.mcts_memory import position_key, quiet_plan
from benchmark_mcts import source_hashes, variants
from search import action_key
from simulator import Position

ROOT = Path(__file__).resolve().parent


def run_demo(fixture, *, iterations=2048, seed=0, move_time=0.0):
    position = Position.from_dict(fixture["state"])
    history = [(Position.from_dict(turn["state"]), turn["action"]) for turn in fixture["history"]]
    counts = Counter(action_key(moves) for previous, moves in history
                     if position_key(previous) == position_key(position) and quiet_plan(position, moves))
    repeated_actions = {action for action, count in counts.items() if count >= 2}
    records = {}
    for label, spec in variants(iterations).items():
        agent = make_agent(spec)
        agent.new_game(position, position.to_play, seed)
        started = time.perf_counter()
        context = TurnContext(started + move_time if move_time else None, fixture["max_plies"], history)
        moves, fault = safe_choose(agent, position, context)
        records[label] = {"spec": spec, "action": moves, "fault": fault,
                          "seconds": time.perf_counter() - started, "info": agent.info,
                          "historical_repeat": action_key(moves) in repeated_actions}
    return {"seed": seed, "iterations": iterations, "move_time": move_time,
            "scope": "One recorded decision, not a match result or proof of improved win rate.",
            "fixture": fixture, "source_sha256": source_hashes(), "decisions": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixture", type=Path, default=ROOT / "examples" / "mcts_losing_loop.json")
    parser.add_argument("--iterations", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--move-time", type=float, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.iterations < 1 or not isfinite(args.move_time) or args.move_time < 0:
        parser.error("iterations must be positive; move-time finite and nonnegative")
    output = args.output or ROOT / ".local" / "mcts-memory" / (
        "demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    if output.exists():
        parser.error(f"output already exists: {output}")
    raw = args.fixture.read_bytes()
    report = run_demo(json.loads(raw), iterations=args.iterations, seed=args.seed, move_time=args.move_time)
    report["fixture_sha256"] = sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    cells = report["fixture"]["state"]["cells"]
    print(f"Recorded position: vampires {sum(c[3] for c in cells)}, "
          f"werewolves {sum(c[4] for c in cells)}.")
    for label, row in report["decisions"].items():
        print(f"{label:13} repeat={row['historical_repeat']!s:5} "
              f"iterations={row['info'].get('iterations', 0) if row['info'] else 0:5} "
              f"move={row['action']} fault={row['fault']}")
    print(report["scope"])
    print(f"Report: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
