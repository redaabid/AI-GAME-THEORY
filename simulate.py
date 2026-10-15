"""Play CPU-only games and export behavior labels or MCTS visit targets."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import time
import xml.etree.ElementTree as ET

from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from candidates import CANDIDATE_SET
from search import SearchConfig, search
from simulator import SCHEMA_VERSION, full_group_actions, get_outcome, load_map, opponent, simulate_turn
from strategy import choose_moves

ROOT = Path(__file__).resolve().parent
AGENTS = ("baseline", "random", "mcts")


def code_fingerprint():
    fingerprint = sha256()
    for name in ("game.py", "combat.py", "strategy.py", "simulator.py", "simulate.py", "search.py", "candidates.py"):
        fingerprint.update(name.encode() + b"\0" + (ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
    return fingerprint.hexdigest()


def play_game(initial, *, seed, game_id=0, max_plies=100, baseline_species="vampires",
              agent="baseline", opponent_agent="random", search_config=None,
              record_transitions=True, timings=None):
    """Return a summary and labeled records; baseline_species is the focal side.

    The old keyword remains compatible with the first CPU runner. Both players
    can use MCTS, and actual battles use an RNG independent of policy/search.
    """
    opponent(baseline_species)
    if agent not in AGENTS or opponent_agent not in AGENTS:
        raise ValueError("Unknown agent.")
    search_config = search_config or SearchConfig(iterations=128)
    battle_rng = random.Random(seed)
    policy_rng = random.Random(seed ^ 0x5EED)
    position = initial
    records = []
    while (outcome := get_outcome(position, max_plies=max_plies)) is None:
        candidates = full_group_actions(position)
        if not candidates:
            raise ValueError("An ongoing position has no legal full-group move.")
        teacher = agent if position.to_play == baseline_species else opponent_agent
        started = time.perf_counter()
        search_metadata = None
        if teacher == "mcts":
            search_seed = policy_rng.getrandbits(64)
            result = search(position, config=search_config, rng=random.Random(search_seed),
                            max_plies=max_plies)
            candidates, moves = result.candidate_actions, result.moves
            policy = result.policy
            kind = "fallback_one_hot" if result.fallback else "mcts_visits"
            search_metadata = result.training_metadata()
            search_metadata["seed"] = search_seed
        else:
            moves = choose_moves(position.to_game_state()) if teacher == "baseline" else policy_rng.choice(candidates)
            chosen_index = candidates.index(moves)
            policy = [int(i == chosen_index) for i in range(len(candidates))]
            kind = "behavior_one_hot"
        if timings is not None:
            timings.append({"agent": teacher, "seconds": time.perf_counter() - started,
                            "iterations": search_metadata["iterations"] if search_metadata else 0,
                            "fallback": search_metadata["fallback"] if search_metadata else False})
        next_position = simulate_turn(position, moves, battle_rng)
        record = {
            "schema_version": SCHEMA_VERSION, "game_id": game_id, "seed": seed,
            "teacher": teacher, "candidate_set": CANDIDATE_SET if teacher == "mcts" else "single_full_group_v1",
            "state": position.to_dict(), "candidate_actions": candidates,
            "action": moves, "policy_target_kind": kind, "policy_target": policy,
            "next_state": next_position.to_dict(),
        }
        if search_metadata is not None:
            record["search"] = search_metadata
        if record_transitions:
            records.append(record)
        position = next_position
    for record in records:
        record["value_target"] = outcome.value_for(record["state"]["to_play"])
        record["termination"] = outcome.reason
    summary = {
        "schema_version": SCHEMA_VERSION, "game_id": game_id, "seed": seed,
        "agent": agent, "opponent": opponent_agent, "agent_species": baseline_species,
        "first_player": initial.to_play,
        "plies": position.ply, "winner": outcome.winner, "termination": outcome.reason,
        "agent_score": (outcome.value_for(baseline_species) + 1) / 2,
        "final_state": position.to_dict(),
    }
    if agent == "baseline":
        summary["baseline_species"] = baseline_species
        summary["baseline_score"] = summary["agent_score"]
    return summary, records


def export_games(map_path, output, *, games=10, seed=42, max_plies=100,
                 rules_profile=DEFAULT_RULES_PROFILE, agent="baseline", opponent_agent="random",
                 search_config=None):
    if type(games) is not int or games < 1 or type(max_plies) is not int or max_plies < 1:
        raise ValueError("games and max_plies must be positive integers.")
    if agent not in AGENTS or opponent_agent not in AGENTS:
        raise ValueError("Unknown agent.")
    search_config = search_config or SearchConfig(iterations=128)
    uses_search = "mcts" in (agent, opponent_agent)
    initial = load_map(map_path, rules_profile=rules_profile)
    if get_outcome(initial) is not None:
        raise ValueError("The initial map must contain both monster species.")
    output = Path(output)
    # Keep each run in a new directory so previous experiments remain intact.
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "mcts_search_targets" if uses_search else "baseline_pipeline_example",
        "candidate_set": "per_transition" if uses_search else "single_full_group_v1",
        "agent": agent, "opponent": opponent_agent,
        "search_config": asdict(search_config) if uses_search else None,
        "games": games, "base_seed": seed,
        "rules_profile": rules_profile,
        "python_version": platform.python_version(), "rng": "python.random.Random",
        "max_plies": max_plies, "map_name": Path(map_path).name,
        "map_sha256": sha256(Path(map_path).read_bytes()).hexdigest(),
        "code_sha256": code_fingerprint(), "initial_state": initial.to_dict(),
        "agent_mean_score": None, "transitions": 0,
    }
    total_score = 0.0
    # Write the manifest last: its presence marks a completed export.
    with (output / "games.jsonl").open("x", encoding="utf-8") as summaries, \
            (output / "transitions.jsonl").open("x", encoding="utf-8") as transitions:
        for game_id in range(games):
            baseline_species = "vampires" if game_id % 2 == 0 else "werewolves"
            first_player = "vampires" if (game_id // 2) % 2 == 0 else "werewolves"
            summary, records = play_game(replace(initial, to_play=first_player), seed=seed + game_id,
                                         game_id=game_id, max_plies=max_plies,
                                         baseline_species=baseline_species, agent=agent,
                                         opponent_agent=opponent_agent, search_config=search_config)
            summaries.write(json.dumps(summary, sort_keys=True) + "\n")
            for record in records:
                transitions.write(json.dumps(record, sort_keys=True) + "\n")
            total_score += summary["agent_score"]
            manifest["transitions"] += len(records)
    manifest["agent_mean_score"] = total_score / games
    if agent == "baseline":
        manifest["baseline_mean_score"] = manifest["agent_mean_score"]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=ROOT / "maps" / "demo.xml", dest="map_path")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-plies", type=int, default=100)
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--agent", choices=AGENTS, default="baseline")
    parser.add_argument("--opponent", choices=AGENTS, default="random")
    parser.add_argument("--iterations", type=int, default=128, help="MCTS iterations per move")
    parser.add_argument("--move-time", type=float, help="Optional MCTS seconds per move; omit for reproducibility")
    parser.add_argument("--output", type=Path, help="New output directory; existing runs are preserved")
    args = parser.parse_args(argv)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output or ROOT / ".local" / "simulations" / timestamp
    try:
        manifest = export_games(args.map_path, output, games=args.games, seed=args.seed,
                                max_plies=args.max_plies, rules_profile=args.rules_profile,
                                agent=args.agent, opponent_agent=args.opponent,
                                search_config=SearchConfig(iterations=args.iterations, time_limit=args.move_time))
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        parser.exit(1, f"Simulation failed: {error}\n")
    print(f"Completed {manifest['games']} CPU games and {manifest['transitions']} transitions.")
    print(f"{args.agent.upper()} mean match score versus {args.opponent}: {manifest['agent_mean_score']:.3f}")
    print(f"Exported to: {output.resolve()}")
    if "mcts" in (args.agent, args.opponent):
        print("MCTS records contain root visit targets. Filter by policy_target_kind before training.")
    else:
        print("These are baseline/random examples for testing the training pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
