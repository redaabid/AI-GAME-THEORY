"""Compare CPU agents across development maps, species, and first-player roles."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import platform
import xml.etree.ElementTree as ET

from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from search import SearchConfig
from simulate import AGENTS, ROOT, code_fingerprint, play_game
from simulator import load_map


def timing_summary(samples):
    ordered = sorted(samples)
    return {"moves": len(ordered), "max": max(ordered, default=0),
            "p95": ordered[max(0, ceil(0.95 * len(ordered)) - 1)] if ordered else 0}


def evaluate_maps(map_paths, *, games=4, seed=42, max_plies=80, search_config=None,
                  agent="mcts", opponent_agent="baseline", rules_profile=DEFAULT_RULES_PROFILE):
    if type(games) is not int or games < 4 or games % 4:
        raise ValueError("games must be a positive multiple of four to balance all roles.")
    if not map_paths:
        raise ValueError("Provide at least one map.")
    if agent not in AGENTS or opponent_agent not in AGENTS:
        raise ValueError("Unknown agent.")
    search_config = search_config or SearchConfig(iterations=128)
    rows, all_timings = [], []
    for map_id, path in enumerate(map_paths):
        initial = load_map(path, rules_profile=rules_profile)
        scores, summaries, timings = [], [], []
        for game_id in range(games):
            species = "vampires" if game_id % 2 == 0 else "werewolves"
            first = "vampires" if (game_id // 2) % 2 == 0 else "werewolves"
            summary, _ = play_game(replace(initial, to_play=first), seed=seed + map_id * games + game_id,
                                   game_id=game_id, max_plies=max_plies, baseline_species=species,
                                   agent=agent, opponent_agent=opponent_agent, search_config=search_config,
                                   record_transitions=False, timings=timings)
            scores.append(summary["agent_score"])
            summaries.append(summary)
        row = {"map": Path(path).name, "map_sha256": sha256(Path(path).read_bytes()).hexdigest(),
               "games": games, "mean_score": sum(scores) / games,
               "wins": scores.count(1), "draws": scores.count(0.5), "losses": scores.count(0),
               "timings": {name: timing_summary([t["seconds"] for t in timings if t["agent"] == name])
                           for name in {agent, opponent_agent}}, "matches": summaries}
        rows.append(row)
        all_timings.extend(timings)
    return {"schema_version": 1, "purpose": "development_evaluation", "agent": agent,
            "opponent": opponent_agent, "games_per_map": games, "base_seed": seed,
            "max_plies": max_plies, "rules_profile": rules_profile, "search_config": asdict(search_config),
            "python_version": platform.python_version(), "code_sha256": code_fingerprint(),
            "macro_mean_score": sum(row["mean_score"] for row in rows) / len(rows),
            "timings": {name: timing_summary([t["seconds"] for t in all_timings if t["agent"] == name])
                        for name in {agent, opponent_agent}},
            "search_fallbacks": sum(t["fallback"] for t in all_timings), "maps": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", nargs="+", type=Path, default=sorted((ROOT / "maps").glob("*.xml")))
    parser.add_argument("--games", type=int, default=4, help="Games per map, a multiple of four")
    parser.add_argument("--agent", choices=AGENTS, default="mcts")
    parser.add_argument("--opponent", choices=AGENTS, default="baseline")
    parser.add_argument("--iterations", type=int, default=128)
    parser.add_argument("--move-time", type=float, help="Optional wall-time budget per search")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-plies", type=int, default=80)
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--output", type=Path, help="New report filename")
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output or ROOT / ".local" / "evaluations" / f"{stamp}.json"
    try:
        if output.exists():
            raise FileExistsError(f"Report already exists: {output}")
        report = evaluate_maps(args.maps, games=args.games, seed=args.seed, max_plies=args.max_plies,
                               agent=args.agent, opponent_agent=args.opponent, rules_profile=args.rules_profile,
                               search_config=SearchConfig(iterations=args.iterations, time_limit=args.move_time))
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")
    for row in report["maps"]:
        print(f"{row['map']}: {row['wins']}W {row['draws']}D {row['losses']}L; mean {row['mean_score']:.3f}")
    print(f"Macro mean score ({args.agent} vs {args.opponent}): {report['macro_mean_score']:.3f}")
    print(f"Decision timing (seconds): {report['timings']}")
    print(f"Search fallbacks: {report['search_fallbacks']}; report: {output.resolve()}")
    print("These are development maps. Use separate held-out maps and more seeds before model selection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
