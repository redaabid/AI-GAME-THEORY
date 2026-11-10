"""Small stochastic objective comparisons with intervening opponent turns."""

from statistics import mean
import random

from candidates import check_deadline
from scripts.mcts_v7.objectives import policy_moves, populations, progress, track
from simulator import get_outcome, simulate_turn

PROFILES = ("economic", "regroup", "evasive")


def objective_value(position, root, objective, species, evaluator, weight, *, deadline=None, max_plies=None):
    check_deadline(deadline)
    outcome = get_outcome(position, max_plies=max_plies)
    if outcome is not None:
        return outcome.value_for(species)
    value = evaluator(position, species, deadline=deadline, max_plies=max_plies)
    sign = 1 if species == root.to_play else -1
    bonus = sign * weight * progress(position, root, objective, root.to_play, deadline=deadline)
    return max(-.999, min(.999, value + bonus)) if bonus else value


def continuation(position, objective, profile, rng, *, depth, evaluator, weight,
                 deadline=None, max_plies=None):
    root, goal = position, objective
    species, plies = position.to_play, 0
    # Never cut directly after our capture: leave the opponent a reply unless
    # the game itself is over. A deadline discards the whole incomplete trial.
    while plies < depth:
        check_deadline(deadline)
        if get_outcome(position, max_plies=max_plies) is not None:
            break
        goal = track(position, goal, species, deadline=deadline) if goal is not None else None
        moves = policy_moves(position, objective=goal if position.to_play == species else None,
                             profile="economic" if position.to_play == species else profile,
                             deadline=deadline)
        position = simulate_turn(position, moves, rng)
        plies += 1
        if plies % 2 == 0 and (populations(position) != populations(root) or
                              get_outcome(position, max_plies=max_plies) is not None):
            break
    check_deadline(deadline)
    value = objective_value(position, root, objective, species, evaluator, weight,
                            deadline=deadline, max_plies=max_plies)
    return value, plies


def compare_objectives(position, objectives, *, rng, depth, samples, evaluator,
                       weight, deadline=None, max_plies=None):
    """Choose the best worst-profile mean; trial groups complete atomically.

    Common random seeds reduce arbitrary comparison noise. Each sample covers
    every objective and every reply model; a partial sample is never ranked.
    """
    scores = [[[] for _ in PROFILES] for _ in objectives]
    rows = [dict(objective=g.to_dict(), profile_means={}, robust_value=None, trials=0,
                 simulated_plies=0) for g in objectives]
    completed = 0
    for _ in range(samples):
        seed = rng.getrandbits(64)
        batch = []
        try:
            for i, goal in enumerate(objectives):
                for j, profile in enumerate(PROFILES):
                    check_deadline(deadline)
                    value, plies = continuation(position, goal, profile, random.Random(seed), depth=depth,
                                                 evaluator=evaluator, weight=weight,
                                                 deadline=deadline, max_plies=max_plies)
                    batch.append((i, j, value, plies))
        except TimeoutError:
            break
        for i, j, value, plies in batch:
            scores[i][j].append(value)
            rows[i]["trials"] += 1
            rows[i]["simulated_plies"] += plies
        completed += 1
    for i, row in enumerate(rows):
        if completed:
            row["profile_means"] = {profile: mean(scores[i][j]) for j, profile in enumerate(PROFILES)}
            row["robust_value"] = min(row["profile_means"].values())
    best = max(range(len(rows)), key=lambda i: rows[i]["robust_value"]) if completed and rows else None
    return best, rows, completed
