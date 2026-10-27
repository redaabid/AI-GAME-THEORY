"""Round-robin tournament between any registered agents, in the CPU simulator.

Every pair plays every map in rounds of four games: each agent plays both
species and both first-player roles, as on tournament day. Games with the same
map, round, and role use the same battle seed whatever the pair (common random
numbers), so differences between agents are less blurred by dice luck.

    python tournament.py --agents baseline mcts "mcts:iterations=64" --random-maps 6 --rounds 2

Output: a score matrix (row agent's mean score against the column agent;
win = 1, draw = 0.5, loss = 0), a Bradley-Terry Elo ranking, and per-agent
timing, timeouts, and faults. A JSON report and a Markdown copy of the tables
go to .local/tournaments/.
"""

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from itertools import combinations
import json
from math import ceil, log10, sqrt
import multiprocessing
from pathlib import Path
import platform
import random
import sys
import time
import xml.etree.ElementTree as ET

from agents import TurnContext, available_agents, fallback_moves, make_agent, safe_choose
from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from mapgen import FAMILIES, SPLIT_OFFSETS, generate_maps
from simulate import code_fingerprint
from simulator import SPECIES, Position, get_outcome, load_map, opponent, simulate_turn

ROOT = Path(__file__).resolve().parent
ROLES = [(species, first) for first in SPECIES for species in SPECIES]  # 4 games per round


def play_match(initial, specs, *, seed, max_plies=200, move_time=2.0, margin=0.3, on_timeout="skip"):
    """Play one game; specs maps each species to an agent spec. Returns a summary dict.

    With move_time > 0 an agent sees a deadline move_time - margin after its turn
    starts. A decision slower than move_time is a timeout: with on_timeout="skip"
    the turn passes, like the server calling the other player.
    """
    agents = {species: make_agent(spec) for species, spec in specs.items()}
    for index, species in enumerate(SPECIES):
        agents[species].new_game(initial, species, seed * 2 + index)
    battle_rng = random.Random(seed)
    position, history = initial, {s: [] for s in SPECIES}
    stats = {s: {"moves": 0, "seconds": [], "timeouts": 0, "faults": [],
                 "repeated_positions": 0, "behind_moves": 0, "repeated_while_behind": 0,
                 "memory_interventions": 0, "repeated_chosen_after_penalty": 0} for s in SPECIES}
    seen = {s: Counter() for s in SPECIES}
    while (outcome := get_outcome(position, max_plies=max_plies)) is None:
        actor = position.to_play
        started = time.perf_counter()
        deadline = started + move_time - margin if move_time else None
        moves, fault = safe_choose(agents[actor], position, TurnContext(deadline, max_plies, history[actor]))
        elapsed = time.perf_counter() - started
        record = stats[actor]
        record["moves"] += 1
        record["seconds"].append(elapsed)
        # Dimensions/rules are constant within this match. Ignore ply so a
        # returning board counts as a repetition, including both armies/humans.
        key = tuple(sorted(position.cells.items()))
        repeated = seen[actor][key] > 0
        seen[actor][key] += 1
        behind = (sum(getattr(c, actor) for c in position.cells.values())
                  < sum(getattr(c, opponent(actor)) for c in position.cells.values()))
        record["repeated_positions"] += repeated
        record["behind_moves"] += behind
        record["repeated_while_behind"] += repeated and behind
        info = agents[actor].info or {}
        if info.get("penalized_actions", 0):
            record["memory_interventions"] += 1
            record["repeated_chosen_after_penalty"] += bool(info.get("chosen_repeated"))
        if fault:
            record["faults"].append(f"ply {position.ply}: {fault}"[:200])
        if move_time and elapsed > move_time:
            record["timeouts"] += 1
            if on_timeout == "skip":
                history[actor].append((position, []))
                position = replace(position, to_play=opponent(actor), ply=position.ply + 1)
                continue
        try:
            next_position = simulate_turn(position, moves, battle_rng)
        except ValueError as error:
            record["faults"].append(f"ply {position.ply}: simulator rejected {moves}: {error}"[:200])
            moves = fallback_moves(position)
            next_position = simulate_turn(position, moves, battle_rng)
        history[actor].append((position, moves))
        position = next_position
    totals = {s: sum(getattr(c, s) for c in position.cells.values()) for s in SPECIES}
    return {"winner": outcome.winner, "termination": outcome.reason, "plies": position.ply,
            "final_populations": totals, "stats": stats}


def _run_job(job):
    initial = Position.from_dict(job["map"])
    initial = replace(initial, to_play=job["first"])
    a_species = job["a_species"]
    specs = {a_species: job["a"], opponent(a_species): job["b"]}
    result = play_match(initial, specs, seed=job["seed"], **job["settings"])
    score = 0.5 if result["winner"] is None else float(result["winner"] == a_species)
    return {key: job[key] for key in ("i", "j", "map_name", "round", "a_species", "first", "seed")} | {
        "a_score": score, "a_margin": (result["final_populations"][a_species]
                                       - result["final_populations"][opponent(a_species)]),
        **{k: result[k] for k in ("winner", "termination", "plies", "final_populations")},
        "a_stats": result["stats"][a_species], "b_stats": result["stats"][opponent(a_species)]}


def bradley_terry_elo(names, score, games, anchor=None):
    """Elo from pairwise scores (MM algorithm); half a draw per pair as a prior."""
    n = len(names)
    w = [[score[i][j] + (0.25 if i != j else 0) for j in range(n)] for i in range(n)]
    g = [[games[i][j] + (0.5 if i != j else 0) for j in range(n)] for i in range(n)]
    strength = [1.0] * n
    for _ in range(500):
        strength = [sum(w[i]) / sum(g[i][j] / (strength[i] + strength[j]) for j in range(n) if j != i)
                    for i in range(n)]
        mean = sum(log10(s) for s in strength) / n
        strength = [s / 10 ** mean for s in strength]
    elo = [400 * log10(s) for s in strength]
    offset = elo[names.index(anchor)] if anchor in names else 0.0
    return [e - offset for e in elo]


def _percentile(values, q):
    ordered = sorted(values)
    return ordered[max(0, ceil(q * len(ordered)) - 1)] if ordered else 0.0


def summarize(names, results):
    n = len(names)
    score = [[0.0] * n for _ in range(n)]
    games = [[0] * n for _ in range(n)]
    squares = [[0.0] * n for _ in range(n)]
    margin = [[0.0] * n for _ in range(n)]
    eliminations = [[0] * n for _ in range(n)]
    per_agent = [{"seconds": [], "timeouts": 0, "faults": [], "moves": 0} for _ in range(n)]
    for r in results:
        for me, other, s, m, st in ((r["i"], r["j"], r["a_score"], r["a_margin"], r["a_stats"]),
                                    (r["j"], r["i"], 1 - r["a_score"], -r["a_margin"], r["b_stats"])):
            score[me][other] += s
            squares[me][other] += s * s
            games[me][other] += 1
            margin[me][other] += m
            eliminations[me][other] += r["termination"] == "elimination" and s == 1
            agent = per_agent[me]
            agent["seconds"] += st["seconds"]
            agent["timeouts"] += st["timeouts"]
            agent["moves"] += st["moves"]
            agent["faults"] += st["faults"]
    anchor = "baseline" if "baseline" in names else None
    elo = bradley_terry_elo(names, score, games, anchor)
    matrix = {}
    for i, j in ((i, j) for i in range(n) for j in range(n) if i != j and games[i][j]):
        mean = score[i][j] / games[i][j]
        variance = max(0.0, squares[i][j] / games[i][j] - mean * mean)
        matrix[f"{names[i]} vs {names[j]}"] = {
            "games": games[i][j], "mean_score": mean,
            "ci95": 1.96 * sqrt(variance / games[i][j]),
            "mean_final_margin": margin[i][j] / games[i][j],
            "wins_by_elimination": eliminations[i][j]}
    ranking = []
    for i, name in enumerate(names):
        played = sum(games[i])
        seconds = per_agent[i]["seconds"]
        ranking.append({"agent": name, "elo": elo[i], "games": played,
                        "mean_score": sum(score[i]) / played if played else None,
                        "moves": per_agent[i]["moves"], "timeouts": per_agent[i]["timeouts"],
                        "faults": len(per_agent[i]["faults"]),
                        "fault_examples": per_agent[i]["faults"][:5],
                        "max_seconds": max(seconds, default=0.0), "p95_seconds": _percentile(seconds, 0.95)})
    ranking.sort(key=lambda row: -row["elo"])
    return matrix, ranking


def markdown_tables(names, matrix, ranking):
    width = max(len(name) for name in names)
    widths = [max(len(name), 9) for name in names]
    lines = ["Score of the ROW agent against the COLUMN agent (1 = always wins):", "",
             "| " + " " * width + " | " + " | ".join(n.center(w) for n, w in zip(names, widths)) + " |",
             "|" + "-" * (width + 2) + "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    for row in names:
        cells = []
        for column, column_width in zip(names, widths):
            cell = matrix.get(f"{row} vs {column}")
            text = "—" if cell is None else f"{cell['mean_score']:.2f}±{cell['ci95']:.2f}"
            cells.append(text.center(column_width))
        lines.append(f"| {row.ljust(width)} | " + " | ".join(cells) + " |")
    lines += ["", "| Rank | Agent | Elo | Score | Games | Max s | p95 s | Timeouts | Faults |",
              "|---|---|---|---|---|---|---|---|---|"]
    for rank, row in enumerate(ranking, 1):
        lines.append(f"| {rank} | {row['agent']} | {row['elo']:+.0f} | {row['mean_score']:.3f} | {row['games']} "
                     f"| {row['max_seconds']:.2f} | {row['p95_seconds']:.2f} | {row['timeouts']} | {row['faults']} |")
    return "\n".join(lines)


def collect_maps(args, rules_profile):
    maps = []
    for path in args.maps or []:
        files = sorted(path.glob("*.xml")) if path.is_dir() else [path]
        maps += [(file.stem, load_map(file, rules_profile=rules_profile)) for file in files]
    if args.random_maps:
        generated = generate_maps(args.random_maps, family=args.family, split=args.split, seed=args.map_seed)
        maps += [(name, replace(position, rules_profile=rules_profile)) for name, position in generated]
    if not maps:
        maps = [(file.stem, load_map(file, rules_profile=rules_profile))
                for file in sorted((ROOT / "maps").glob("*.xml"))]
    for name, position in maps:
        if get_outcome(position) is not None:
            raise ValueError(f"Map {name} must contain both monster species.")
    return maps


def run_tournament(names, maps, *, rounds=1, seed=0, workers=1, progress=None, **settings):
    jobs = []
    for map_index, (map_name, position) in enumerate(maps):
        for round_index in range(rounds):
            for role_index, (a_species, first) in enumerate(ROLES):
                game_seed = seed + 100_003 * map_index + 4 * round_index + role_index
                for i, j in combinations(range(len(names)), 2):
                    jobs.append({"i": i, "j": j, "a": names[i], "b": names[j], "map_name": map_name,
                                 "map": position.to_dict(), "round": round_index, "a_species": a_species,
                                 "first": first, "seed": game_seed, "settings": settings})
    results = []
    if workers > 1:
        with multiprocessing.get_context("spawn").Pool(workers) as pool:
            for result in pool.imap_unordered(_run_job, jobs):
                results.append(result)
                if progress:
                    progress(len(results), len(jobs))
    else:
        for job in jobs:
            results.append(_run_job(job))
            if progress:
                progress(len(results), len(jobs))
    results.sort(key=lambda r: (r["map_name"], r["round"], r["a_species"], r["first"], r["i"], r["j"]))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agents", nargs="+", required=True,
                        help=f"Agent specs such as mcts:iterations=64. Available: {', '.join(available_agents())}")
    parser.add_argument("--maps", nargs="+", type=Path, help="XML map files or folders (default: maps/)")
    parser.add_argument("--random-maps", type=int, default=0, help="Add N symmetric generated maps")
    parser.add_argument("--family", choices=FAMILIES, default="medium")
    parser.add_argument("--split", choices=SPLIT_OFFSETS, default="val")
    parser.add_argument("--map-seed", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=1, help="Rounds of 4 games per pair and map")
    parser.add_argument("--max-plies", type=int, default=200, help="Server MaxPlays (default 200)")
    parser.add_argument("--move-time", type=float, default=2.0, help="Seconds per move; 0 = untimed")
    parser.add_argument("--margin", type=float, default=0.3, help="Safety margin taken off agent deadlines")
    parser.add_argument("--on-timeout", choices=("skip", "ignore"), default="skip")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel games; timings are only realistic if cores are not oversubscribed")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--output", type=Path, help="JSON report path")
    args = parser.parse_args(argv)
    if len(args.agents) < 2 or len(set(args.agents)) != len(args.agents):
        parser.error("give at least two distinct agent specs")
    if args.rounds < 1 or args.workers < 1 or args.max_plies < 1 or args.move_time < 0:
        parser.error("rounds, workers, and max-plies must be positive; move-time nonnegative")
    if args.move_time and not 0 <= args.margin < args.move_time:
        parser.error("margin must be nonnegative and smaller than move-time")
    try:
        for spec in args.agents:
            make_agent(spec)
        maps = collect_maps(args, args.rules_profile)
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        parser.exit(1, f"Tournament setup failed: {error}\n")

    def progress(done, total):
        if sys.stdout.isatty():
            print(f"\r{done}/{total} games", end="" if done < total else "\n", flush=True)
        elif done == total or done % max(1, total // 10) == 0:
            print(f"{done}/{total} games", flush=True)

    started = time.perf_counter()
    results = run_tournament(args.agents, maps, rounds=args.rounds, seed=args.seed, workers=args.workers,
                             progress=progress, max_plies=args.max_plies, move_time=args.move_time,
                             margin=args.margin, on_timeout=args.on_timeout)
    matrix, ranking = summarize(args.agents, results)
    for result in results:  # Keep the report small: per-move timings are summarized above.
        for key in ("a_stats", "b_stats"):
            result[key]["max_seconds"] = max(result[key].pop("seconds"), default=0.0)
    tables = markdown_tables(args.agents, matrix, ranking)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or ROOT / ".local" / "tournaments" / f"{stamp}.json"
    report = {"schema_version": 1, "agents": args.agents, "maps": [name for name, _ in maps],
              "rounds": args.rounds, "seed": args.seed, "max_plies": args.max_plies,
              "move_time": args.move_time, "margin": args.margin, "on_timeout": args.on_timeout,
              "rules_profile": args.rules_profile, "workers": args.workers,
              "python_version": platform.python_version(), "code_sha256": code_fingerprint(),
              "wall_seconds": time.perf_counter() - started,
              "ranking": ranking, "matrix": matrix, "games": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(tables + "\n", encoding="utf-8")
    print(tables)
    print(f"\n{len(results)} games on {len(maps)} maps in {report['wall_seconds']:.0f} s. Report: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
