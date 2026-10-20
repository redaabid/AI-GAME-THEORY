"""Offline tuning of agent parameters and evaluation weights (H3 Texel, H4 SPSA, genetic search).

All three methods play in the CPU simulator on the `train` map split, and print
a spec string to paste into tournament.py or main.py. Confirm any result on
`val` maps with tournament.py before adopting it (H7: enough games, or SPRT).

    # SPSA: two perturbed copies play each other; parameters move toward the winner.
    python tune.py spsa --agent portfolio --params humans=0.8,threat=0.7,horizon=10 --iterations 40

    # Genetic search: a population plays a fixed reference opponent.
    python tune.py ga --agent alphabeta:depth=2 --params humans=0.8,discount=0.9 --generations 8

    # Texel: fit evaluation WEIGHTS to the results of self-play games (no game per trial).
    python tune.py texel --agent portfolio --games 40

A parameter named like an evaluation weight (see evaluation.WEIGHTS) goes into
the agent's `weights`; any other name is an agent keyword (e.g. horizon, depth).
Integer starting values stay integers.
"""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from math import exp
import multiprocessing
from pathlib import Path
import random
import sys

from agents import TurnContext, make_agent, parse_spec, safe_choose
from evaluation import WEIGHTS, evaluate
from mapgen import generate_maps
from simulator import SPECIES, Position, get_outcome, opponent, simulate_turn
from tournament import ROLES, play_match

ROOT = Path(__file__).resolve().parent


def parse_params(raw):
    """'humans=0.8,horizon=10' -> {'humans': 0.8, 'horizon': 10}."""
    _, params = parse_spec(f"x:{raw}")
    if not params or any(type(v) not in (int, float) for v in params.values()):
        raise ValueError("--params needs numeric name=value pairs.")
    return params


def build_spec(base, params, start):
    """Spec string for `base` with params; integers stay integers, weights go to `weights`."""
    name, fixed = parse_spec(base)
    kwargs, weights = dict(fixed), dict(fixed.get("weights", {}))
    for key, value in params.items():
        value = max(1, round(value)) if type(start[key]) is int else round(value, 4)
        if key in WEIGHTS:
            weights[key] = value
        else:
            kwargs[key] = value
    if weights:
        kwargs["weights"] = weights
    return f"{name}:" + ",".join(f"{k}={v!r}" for k, v in kwargs.items()) if kwargs else name


def _game(job):
    position, a, b, a_species, first, seed = job
    initial = replace(Position.from_dict(position), to_play=first)
    result = play_match(initial, {a_species: a, opponent(a_species): b}, seed=seed, move_time=0)
    return 0.5 if result["winner"] is None else float(result["winner"] == a_species)


def match_score(a, b, maps, seed, pool):
    """Mean score of spec a against spec b, both roles on every map (common seeds)."""
    jobs = [(position.to_dict(), a, b, species, first, seed + 4 * index + role)
            for index, (_, position) in enumerate(maps) for role, (species, first) in enumerate(ROLES)]
    scores = pool.map(_game, jobs) if pool else list(map(_game, jobs))
    return sum(scores) / len(scores)


def spsa(args, start, pool, log):
    """Simultaneous perturbation: theta+ plays theta-; theta moves toward the winner."""
    scale = {k: args.scale * abs(v) or args.scale for k, v in start.items()}
    theta = dict(start)
    rng = random.Random(args.seed)
    big_a = max(1, args.iterations // 10)
    for k in range(args.iterations):
        a_k = args.lr / (k + 1 + big_a) ** 0.602
        c_k = 1.0 / (k + 1) ** 0.101
        delta = {key: rng.choice((-1, 1)) for key in theta}
        plus = {key: theta[key] + c_k * scale[key] * delta[key] for key in theta}
        minus = {key: theta[key] - c_k * scale[key] * delta[key] for key in theta}
        maps = generate_maps(args.maps, family=args.family, split="train", seed=args.seed + 1000 * k)
        score = match_score(build_spec(args.agent, plus, start), build_spec(args.agent, minus, start),
                            maps, args.seed + 7919 * k, pool)
        # score - 0.5 in [-0.5, 0.5]: positive means the + side was better.
        for key in theta:
            theta[key] += a_k * scale[key] * (score - 0.5) * 2 * delta[key] / c_k
        log.append({"iteration": k, "score_plus": score, "theta": dict(theta)})
        print(f"[{k + 1}/{args.iterations}] plus scored {score:.2f} -> {build_spec(args.agent, theta, start)}",
              flush=True)
    return theta


def genetic(args, start, pool, log):
    """Elitist genetic search; fitness = score against the reference (default: starting params)."""
    rng = random.Random(args.seed)
    scale = {k: args.scale * abs(v) or args.scale for k, v in start.items()}
    reference = args.opponent or build_spec(args.agent, start, start)
    population = [dict(start)] + [{k: v + rng.gauss(0, scale[k]) for k, v in start.items()}
                                  for _ in range(args.population - 1)]
    best = (None, dict(start))
    for generation in range(args.generations):
        # Same maps for the whole generation, new maps each generation: fair and not overfitted.
        maps = generate_maps(args.maps, family=args.family, split="train", seed=args.seed + 1000 * generation)
        scored = sorted(((match_score(build_spec(args.agent, theta, start), reference, maps,
                                      args.seed + 7919 * generation, pool), theta) for theta in population),
                        key=lambda item: -item[0])
        best = scored[0]
        log.append({"generation": generation, "scores": [s for s, _ in scored], "best": dict(best[1])})
        print(f"[gen {generation + 1}/{args.generations}] best {best[0]:.2f} "
              f"-> {build_spec(args.agent, best[1], start)}", flush=True)
        elite = [theta for _, theta in scored[:max(1, args.population // 4)]]
        sigma = 1.0 / (1 + generation)
        children = [dict(theta) for theta in elite]
        while len(children) < args.population:
            a, b = (rng.choice(scored[:max(2, args.population // 2)])[1] for _ in range(2))
            child = {k: rng.choice((a[k], b[k])) + rng.gauss(0, sigma * scale[k]) for k in start}
            children.append(child)
        population = children
    return best[1]


def texel_positions(args):
    """(position, result for the side to move) from self-play games with real dice."""
    samples = []
    maps = generate_maps(args.games, family=args.family, split="train", seed=args.seed)
    for index, (_, initial) in enumerate(maps):
        agents = {s: make_agent(args.agent) for s in SPECIES}
        for number, species in enumerate(SPECIES):
            agents[species].new_game(initial, species, index * 2 + number)
        rng, position, seen = random.Random(args.seed + index), initial, []
        while (outcome := get_outcome(position, max_plies=200)) is None:
            if position.ply >= 4:
                seen.append(position)
            moves, _ = safe_choose(agents[position.to_play], position, TurnContext(None, 200))
            position = simulate_turn(position, moves, rng)
        for p in seen:
            samples.append((p, 0.5 if outcome.winner is None else float(outcome.winner == p.to_play)))
        print(f"[{index + 1}/{args.games}] {len(samples)} positions", flush=True)
    return samples


def texel(args, start, log):
    """Classic Texel local search on evaluation WEIGHTS: minimise (result - sigmoid(eval))^2."""
    samples = texel_positions(args)
    if args.sample and len(samples) > args.sample:
        samples = random.Random(args.seed).sample(samples, args.sample)
    weights = WEIGHTS | {k: v for k, v in start.items() if k in WEIGHTS}

    def error(w, k):
        total = 0.0
        for position, result in samples:
            value = max(-50.0, min(50.0, k * evaluate(position, position.to_play, w, 200)))
            total += (result - 1 / (1 + exp(-value))) ** 2
        return total / len(samples)

    k = min((0.01 * i for i in range(1, 60)), key=lambda c: error(weights, c))  # Scale first.
    best = error(weights, k)
    print(f"K = {k:.2f}, initial error {best:.5f}", flush=True)
    step = args.scale
    for iteration in range(args.iterations):
        improved = False
        for key in sorted(weights):
            for sign in (1, -1):
                trial = weights | {key: round(weights[key] * (1 + sign * step) if weights[key] else sign * step, 4)}
                if key == "discount" and not 0 < trial[key] <= 1:
                    continue
                value = error(trial, k)
                if value < best:
                    weights, best, improved = trial, value, True
                    break
        log.append({"iteration": iteration, "error": best, "weights": dict(weights)})
        print(f"[{iteration + 1}] error {best:.5f} {weights}", flush=True)
        if not improved:
            step /= 2
            if step < 0.01:
                break
    return weights


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("method", choices=("spsa", "ga", "texel"))
    parser.add_argument("--agent", default="portfolio", help="Base spec; tuned params are added to it")
    parser.add_argument("--params", default="", help="name=value starting point (weights or agent kwargs)")
    parser.add_argument("--opponent", help="ga: reference spec (default: the agent at its starting params)")
    parser.add_argument("--iterations", type=int, default=30, help="spsa iterations / texel passes")
    parser.add_argument("--generations", type=int, default=8)
    parser.add_argument("--population", type=int, default=8)
    parser.add_argument("--maps", type=int, default=2, help="New train maps per iteration (x4 games)")
    parser.add_argument("--games", type=int, default=30, help="texel: self-play games to collect")
    parser.add_argument("--sample", type=int, default=6000, help="texel: positions kept (0 = all)")
    parser.add_argument("--family", default="medium", choices=("small", "medium", "large"))
    parser.add_argument("--scale", type=float, default=0.2, help="Relative perturbation / mutation size")
    parser.add_argument("--lr", type=float, default=1.0, help="spsa step size")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    make_agent(args.agent)  # Fail fast on a bad spec.
    start = parse_params(args.params) if args.params else (
        dict(WEIGHTS) if args.method == "texel" else None)
    if start is None:
        parser.error("--params is required for spsa and ga.")
    log = []
    if args.method == "texel":
        result = texel(args, start, log)
        spec = build_spec(args.agent, result, result)
    else:
        context = multiprocessing.get_context("spawn")
        with context.Pool(args.workers) if args.workers > 1 else _NoPool() as pool:
            result = (spsa if args.method == "spsa" else genetic)(args, start, pool, log)
        spec = build_spec(args.agent, result, start)
    print(f"\nTuned spec: {spec}")
    output = args.output or ROOT / ".local" / "tuning" / (
        f"{args.method}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"method": args.method, "args": {k: str(v) for k, v in vars(args).items()},
                                  "start": start, "result": result, "spec": spec, "log": log}, indent=1))
    print(f"Log: {output}")


class _NoPool:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


if __name__ == "__main__":
    sys.exit(main())
