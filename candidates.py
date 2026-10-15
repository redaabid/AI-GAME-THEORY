"""Bounded, heuristic whole-turn candidates; no AI/graph library required."""

from itertools import combinations
import time

from combat import win_probability
from game import Cell, distance

CANDIDATE_SET = "recruitment_turns_v1"


def check_deadline(deadline):
    if deadline is not None and time.perf_counter() >= deadline:
        raise TimeoutError("Search deadline reached.")


def supported_turn(state, moves):
    """The simulator supports legal turns whose possible stacks fit a byte."""
    try:
        state.validate_moves(moves)
    except ValueError:
        return False
    incoming = {}
    for _, _, count, x, y in moves:
        incoming[(x, y)] = incoming.get((x, y), 0) + count
    return all(count + getattr(state.cells.get(p, Cell()), state.species)
               + state.cells.get(p, Cell()).humans <= 255 for p, count in incoming.items())


def first_supported_move(state):
    """A small legal fallback, established before doing any tree search."""
    for source, count in state.groups():
        for target in state.neighbors(source):
            moves = [(source[0], source[1], count, target[0], target[1])]
            if supported_turn(state, moves):
                return moves
    raise ValueError("No full-group move is supported within the simulator's byte limits.")


def turn_score(state, moves, humans, enemies, *, deadline=None):
    """Order candidates by recruitment, material, travel, and reply exposure."""
    arrivals, score = {}, 0.0
    for x, y, count, tx, ty in moves:
        check_deadline(deadline)
        source, target = (x, y), (tx, ty)
        arrivals[target] = arrivals.get(target, 0) + count
        goals = [(p, n) for p, n in humans if n <= count]
        if goals:
            goal, population = max(goals, key=lambda item: item[1] / (1 + distance(source, item[0])))
            score += 0.7 * min(count, population) * (distance(source, goal) - distance(target, goal))
        elif enemies:
            goal, n = min(enemies, key=lambda item: distance(source, item[0]))
            direction = 1 if 2 * count >= 3 * n else -0.25
            score += direction * (distance(source, goal) - distance(target, goal))
    for target, count in arrivals.items():
        check_deadline(deadline)
        cell = state.cells.get(target, Cell())
        friendly, enemy = getattr(cell, state.species), getattr(cell, state.enemy_species)
        strength = count + friendly
        if cell.humans or enemy:
            defenders = cell.humans or enemy
            p = win_probability(count, defenders, humans=bool(cell.humans), rules_profile=state.rules_profile)
            strength = (count + cell.humans) * p * p
            score += 2 * (strength - count)
            if enemy:
                score += 2 * enemy * (1 - (1 - p) ** 2)
        threat = sum(n for p, n in enemies if p != target and distance(p, target) == 1)
        if threat and strength:
            p = win_probability(threat, strength, rules_profile=state.rules_profile)
            score -= 2.5 * strength * (1 - (1 - p) ** 2)
        if friendly:
            score += 0.15 * min(count, friendly)
    return score


def generate_candidates(position, *, limit=32, fallback=None, deadline=None):
    """Rank a subset of valid turns, including coordinated arrivals and splits.

    The fallback is retained even when pruning. This is deliberately not an
    exhaustive action enumeration; widening in search exposes more of this list.
    """
    if type(limit) is not int or limit < 2:
        raise ValueError("The candidate limit must be an integer of at least two.")
    check_deadline(deadline)
    state = position.to_game_state()
    own = sorted(state.groups())
    humans, enemies = state.groups("humans"), state.groups(state.enemy_species)
    plans = {}

    def add(moves):
        check_deadline(deadline)
        key = tuple(sorted(tuple(move) for move in moves))
        if key not in plans and supported_turn(state, key):
            plans[key] = turn_score(state, key, humans, enemies, deadline=deadline)

    if fallback is not None:
        add(fallback)
    singles = []
    targets = set()
    for source, count in own:
        check_deadline(deadline)
        neighbors = list(state.neighbors(source))
        for target in neighbors:
            move = (source[0], source[1], count, target[0], target[1])
            add([move])
            singles.append(move)
            targets.add(target)
        # Send exactly enough to recruit while reserving troops, and split
        # toward two distinct human objectives (not every possible partition).
        goals = sorted(((p, h) for p, h in humans if h < count),
                       key=lambda item: -item[1] / (1 + distance(source, item[0])))[:4]
        steps = []
        for goal, h in goals:
            target = min(neighbors, key=lambda p: (distance(p, goal), p))
            if distance(target, goal) < distance(source, goal):
                steps.append((target, h))
                add([(source[0], source[1], h, target[0], target[1])])
        for (first, h1), (second, h2) in combinations(steps, 2):
            if first != second and h1 + h2 <= count:
                for second_count in {h2, count - h1}:
                    add([(source[0], source[1], h1, first[0], first[1]),
                         (source[0], source[1], second_count, second[0], second[1])])

    # All adjacent groups can combine at one destination before a battle.
    for target in sorted(targets):
        check_deadline(deadline)
        moves = [(p[0], p[1], n, target[0], target[1]) for p, n in own if distance(p, target) == 1]
        if len(moves) > 1:
            add(moves)

    # Independent groups can also pursue separate goals in the same turn.
    ranked = sorted(singles, key=lambda move: -plans.get((move,), float("-inf")))
    for offset in range(min(3, len(ranked))):
        combined, sources, destinations = [], set(), set()
        for move in ranked[offset:]:
            check_deadline(deadline)
            source, target = move[:2], move[3:]
            if source in sources or source in destinations or target in sources:
                continue
            trial = combined + [move]
            if supported_turn(state, trial):
                combined = trial
                sources.add(source)
                destinations.add(target)
                if len(combined) > 1:
                    add(combined)

    ranked = sorted(plans, key=lambda key: (-plans[key], key))[:limit]
    if fallback is not None:
        key = tuple(sorted(tuple(move) for move in fallback))
        if key not in ranked:
            ranked = ranked[:limit - 1] + [key]
    if not ranked:
        raise ValueError("No supported candidate turns are available.")
    return [list(key) for key in ranked]
