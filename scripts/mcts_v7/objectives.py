"""Bounded objective proposals and legal moves for alternating-turn lookahead."""

from dataclasses import asdict, dataclass, replace

from candidates import check_deadline, supported_turn, turn_score
from combat import win_probability
from game import Cell, distance
from macro import Order, groups, orders_to_moves
from simulator import opponent


@dataclass(frozen=True)
class Objective:
    kind: str
    source: tuple
    count: int
    target: tuple
    target_count: int
    created_ply: int
    seen_ply: int

    def to_dict(self):
        return asdict(self)


def populations(position):
    return tuple(sum(getattr(c, s) for c in position.cells.values())
                 for s in ("vampires", "werewolves"))


def contact(position, *, deadline=None):
    own = groups(position, position.to_play, deadline=deadline)
    enemy = groups(position, opponent(position.to_play), deadline=deadline)
    return any(distance(a, b) == 1 for a, _ in own for b, _ in enemy)


def track(position, objective, species, *, deadline=None):
    """Conservative tracking: unchanged counts, nearby cells, no inferred IDs.

    A merge, split, capture or disappearance invalidates a tracked detachment.
    Equal-size nearby groups can be ambiguous; nearest position is a heuristic.
    """
    check_deadline(deadline)
    own_steps = (position.ply - objective.seen_ply + 1) // 2
    radius = max(0, own_steps)
    own = groups(position, species, deadline=deadline)
    sources = [(distance(p, objective.source), p) for p, n in own
               if n == objective.count and distance(p, objective.source) <= radius]
    if not sources:
        return None
    source = min(sources)[1]
    if objective.kind == "recruit":
        cell = position.cells.get(objective.target, Cell())
        if cell.humans != objective.target_count:
            return None
        target = objective.target
    else:
        kind = opponent(species) if objective.kind == "intercept" else species
        targets = [(distance(p, objective.target), p) for p, n in groups(position, kind, deadline=deadline)
                   if n == objective.target_count and p != source
                   and distance(p, objective.target) <= radius]
        if not targets:
            return None
        target = min(targets)[1]
    return replace(objective, source=source, target=target, seen_ply=position.ply)


def priority(position, objective):
    """Proposal ordering only; this is not a win probability."""
    n, m = objective.count, objective.target_count
    if objective.kind == "recruit":
        gain = m
    elif objective.kind == "intercept":
        p = win_probability(n, m, rules_profile=position.rules_profile)
        gain = n * p * p - n + m * (1 - (1 - p) ** 2)
    else:
        unlocked = [c.humans for c in position.cells.values() if max(n, m) < c.humans <= n + m]
        gain = max(unlocked, default=.25 * min(n, m))
    return gain / (1 + distance(objective.source, objective.target))


def propose(position, *, limit=3, previous=None, deadline=None):
    own = groups(position, position.to_play, deadline=deadline)
    enemy = groups(position, opponent(position.to_play), deadline=deadline)
    humans = groups(position, "humans", deadline=deadline)
    proposals = []
    for source, n in own:
        check_deadline(deadline)
        for target, h in humans:
            check_deadline(deadline)
            if h <= n:
                proposals.append(Objective("recruit", source, n, target, h, position.ply, position.ply))
        for target, m in enemy:
            check_deadline(deadline)
            if n > m:  # Positive battle-winning advantage; not a guarantee.
                proposals.append(Objective("intercept", source, n, target, m, position.ply, position.ply))
        if len(own) > 1:
            target, m = max((item for item in own if item[0] != source), key=lambda item: (item[1], item[0]))
            if n + m <= 255:
                proposals.append(Objective("regroup", source, n, target, m, position.ply, position.ply))
    ranked = sorted(proposals, key=lambda g: (-priority(position, g), g.kind, g.source, g.target))
    # Represent different objectives before spending the remaining slots on a
    # second target of the same kind. Retain a valid persistent plan for testing.
    selected = [previous] if previous is not None else []
    kinds = {g.kind for g in selected}
    for goal in ranked:
        if goal.kind not in kinds and len(selected) < limit:
            selected.append(goal)
            kinds.add(goal.kind)
    for goal in ranked:
        if len(selected) == limit:
            break
        if not any((g.kind, g.source, g.target) == (goal.kind, goal.source, goal.target) for g in selected):
            selected.append(goal)
    return selected


def _step(position, source, count, target, blocked, *, deadline=None):
    state = position.to_game_state()
    enemy = state.groups(state.enemy_species)
    humans = state.groups("humans")
    options = []
    for step in state.neighbors(source):
        check_deadline(deadline)
        if step in blocked:
            continue
        cell = position.cells.get(step, Cell())
        defenders = getattr(cell, state.enemy_species)
        # Objectives never require a speculative understrength village battle.
        if cell.humans > count or (defenders and defenders >= count):
            continue
        strength = count + cell.humans + getattr(cell, state.species)
        certain_capture = not defenders or 2 * count >= 3 * defenders
        threat = sum(n for p, n in enemy if p != step and distance(p, step) == 1)
        if certain_capture and threat and 2 * threat >= 3 * strength:
            continue
        move = (*source, count, *step)
        progress = distance(source, target) - distance(step, target)
        score = turn_score(state, [move], humans, enemy, deadline=deadline) + .4 * count * progress
        options.append((-score, step))
    return min(options)[1] if options else None


def policy_moves(position, *, objective=None, profile="economic", deadline=None):
    """A cheap full-turn reply model; all moves are validated before simulation.

    economic: pursue recruitment; regroup: consolidate; evasive: move away from
    stronger enemies. These proxies do not reproduce Julian's alpha-beta agent.
    """
    check_deadline(deadline)
    species = position.to_play
    own = groups(position, species, deadline=deadline)
    enemy = groups(position, opponent(species), deadline=deadline)
    humans = groups(position, "humans", deadline=deadline)
    goals = {}
    held = set()
    if objective is not None:
        goals[objective.source] = objective.target
        if objective.kind == "regroup":
            held.add(objective.target)
    for source, n in own:
        check_deadline(deadline)
        if source in goals or source in held:
            continue
        threats = [(distance(source, p), p) for p, m in enemy if m > n]
        affordable = [(h / (1 + distance(source, p)), p) for p, h in humans if h <= n]
        allies = [(distance(source, p), -m, p) for p, m in own if p != source]
        if threats and (profile == "evasive" or min(threats)[0] <= 2):
            # A virtual coordinate outside the board supplies a direction only.
            p = min(threats)[1]
            goals[source] = (2 * source[0] - p[0], 2 * source[1] - p[1])
        elif profile == "regroup" and allies:
            target = min(allies)[2]
            goals[source] = target
        elif affordable:
            goals[source] = max(affordable)[1]
        elif allies:
            goals[source] = min(allies)[2]
        elif enemy:
            goals[source] = min(enemy, key=lambda item: distance(source, item[0]))[0]
    # Leave one partner stationary when consolidating, permitting a real merge.
    if objective is None and profile == "regroup" and len(own) > 1:
        anchor = max(own, key=lambda item: (item[1], item[0]))[0]
        goals.pop(anchor, None)
        for source in goals:
            goals[source] = anchor
    moving = set(goals)
    orders = []
    for source, n in own:
        if source not in goals:
            continue
        step = _step(position, source, n, goals[source], moving, deadline=deadline)
        if step is not None:
            orders.append(Order(source, n, step))
    moves = orders_to_moves(position, orders, deadline=deadline)[0]
    if moves and supported_turn(position.to_game_state(), moves):
        return moves
    from strategy import choose_moves
    from candidates import first_supported_move
    moves = choose_moves(position.to_game_state(), deadline=deadline)
    return moves if supported_turn(position.to_game_state(), moves) else first_supported_move(position.to_game_state())


def progress(position, root, objective, species, *, deadline=None):
    """Bounded positional guidance only while material is unchanged and tied."""
    check_deadline(deadline)
    if populations(position) != populations(root) or contact(position, deadline=deadline):
        return 0.0
    current = track(position, objective, species, deadline=deadline)
    if current is None:
        if objective.kind == "regroup" and any(
                n >= objective.count + objective.target_count for _, n in groups(position, species, deadline=deadline)):
            return 1.0
        return 0.0
    before = distance(objective.source, objective.target)
    after = distance(current.source, current.target)
    return max(-1.0, min(1.0, (before - after) / max(2, min(8, before))))
