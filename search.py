"""Adversarial UCT with sampled chance outcomes and a CPU deadline."""

from dataclasses import dataclass, field
from math import ceil, isfinite, log, sqrt, tanh
import random
import time

from candidates import (CANDIDATE_SET, check_deadline, first_supported_move,
                        generate_candidates, supported_turn)
from game import distance
from simulator import get_outcome, opponent, simulate_turn
from strategy import choose_moves


@dataclass(frozen=True)
class SearchConfig:
    iterations: int = 256
    time_limit: float | None = None
    tree_depth: int = 12
    rollout_depth: int = 6
    max_candidates: int = 32
    exploration: float = 1.4

    def __post_init__(self):
        for name in ("iterations", "tree_depth", "max_candidates"):
            if type(getattr(self, name)) is not int or getattr(self, name) < (2 if name == "max_candidates" else 1):
                raise ValueError(f"{name} must be a positive integer (candidates: at least 2).")
        if type(self.rollout_depth) is not int or self.rollout_depth < 0:
            raise ValueError("rollout_depth must be a nonnegative integer.")
        for name in ("time_limit", "exploration"):
            value = getattr(self, name)
            if value is None and name == "time_limit":
                continue
            if not isinstance(value, (float, int)) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")


@dataclass(frozen=True)
class SearchResult:
    moves: list
    candidate_actions: list
    visits: list[int]
    action_values: list[float | None]
    iterations: int
    elapsed_seconds: float
    fallback: bool

    @property
    def policy(self):
        total = sum(self.visits)
        if total:
            return [n / total for n in self.visits]
        return [float(action == self.moves) for action in self.candidate_actions]

    def training_metadata(self):
        # Wall time is deliberately excluded from reproducible training records.
        return {"algorithm": "adversarial_uct_v1", "iterations": self.iterations,
                "candidate_set": CANDIDATE_SET, "visits": self.visits,
                "action_values": self.action_values, "fallback": self.fallback}


@dataclass
class _Edge:
    moves: list
    visits: int = 0
    total_value: float = 0.0
    outcomes: dict = field(default_factory=dict)


@dataclass
class _Node:
    position: object
    edges: list = field(default_factory=list)
    visits: int = 0


def evaluate(position, species, *, deadline=None, max_plies=None):
    """Bounded leaf value; an optional clock excludes unreachable humans.

    Omitting max_plies preserves the original MCTS heuristic. Distances with a
    clock are an optimistic reachability test, not a promise of recruitment.
    """
    if max_plies is not None:
        outcome = get_outcome(position, max_plies=max_plies)
        if outcome is not None:
            return outcome.value_for(species)
    other = opponent(species)
    own, enemy, humans = [], [], []
    for p, cell in sorted(position.cells.items()):
        check_deadline(deadline)
        if getattr(cell, species):
            own.append((p, getattr(cell, species)))
        elif getattr(cell, other):
            enemy.append((p, getattr(cell, other)))
        elif cell.humans:
            humans.append((p, cell.humans))
    own_total, enemy_total = sum(n for _, n in own), sum(n for _, n in enemy)
    if not own_total or not enemy_total:
        return 0.0 if own_total == enemy_total else (1.0 if own_total else -1.0)

    remaining = None if max_plies is None else max(0, max_plies - position.ply)

    def recruitment_cost(groups, target, population, actor):
        turns = None if remaining is None else (remaining + int(position.to_play == actor)) // 2
        costs = [distance(p, target) + 4 * max(0, population - n) / n
                 for p, n in groups if turns is None or distance(p, target) <= turns]
        return min(costs) if costs else None

    potential = 0.0
    reachable_humans = 0
    tempo = 0.25 if position.to_play == species else -0.25
    for p, n in humans:
        check_deadline(deadline)
        own_cost = recruitment_cost(own, p, n, species)
        enemy_cost = recruitment_cost(enemy, p, n, other)
        if own_cost is None and enemy_cost is None:
            continue
        reachable_humans += n
        if enemy_cost is None:
            potential += n
        elif own_cost is None:
            potential -= n
        else:
            potential += n * tanh(0.6 * (enemy_cost - own_cost + tempo))
    scale = max(1, 0.6 * (own_total + enemy_total) + 0.25 * reachable_humans)
    return 0.95 * tanh((own_total - enemy_total + 0.65 * potential) / scale)


def _key(position):
    return tuple(sorted(position.cells.items()))


def action_key(moves):
    """Canonical key for a complete turn, independent of move ordering."""
    return tuple(sorted(tuple(move) for move in moves))


def _select(node, root_species, exploration, penalties=None):
    # Widen DECISION actions only. Chance outcomes are always sampled afresh.
    width = min(len(node.edges), max(2, ceil(2 * sqrt(node.visits + 1))))
    active = node.edges[:width]
    for edge in active:
        if edge.visits == 0:
            return edge
    sign = 1 if node.position.to_play == root_species else -1
    return max(active, key=lambda edge: sign * edge.total_value / edge.visits
               + exploration * sqrt(log(node.visits + 1) / edge.visits)
               - (penalties.get(action_key(edge.moves), 0.0) if penalties else 0.0))


def _rollout(position, species, rng, config, deadline, max_plies, leaf_evaluator=None):
    for _ in range(config.rollout_depth):
        check_deadline(deadline)
        outcome = get_outcome(position, max_plies=max_plies)
        if outcome is not None:
            return outcome.value_for(species)
        view = position.to_game_state()
        moves = choose_moves(view, deadline=deadline)
        if not supported_turn(view, moves):
            moves = first_supported_move(view)
        position = simulate_turn(position, moves, rng)
    check_deadline(deadline)
    outcome = get_outcome(position, max_plies=max_plies)
    if outcome is not None:
        return outcome.value_for(species)
    if leaf_evaluator is not None:
        return leaf_evaluator(position, species, deadline=deadline, max_plies=max_plies)
    return evaluate(position, species, deadline=deadline)


def search(position, *, config=None, rng=None, max_plies=None, deadline=None,
           leaf_evaluator=None, root_penalties=None):
    """Return a legal plan and root visit targets without mutating the input.

    Opponent nodes maximize the opponent's reward. Every selected edge samples a
    fresh battle outcome, so an early lucky battle is never frozen into the tree.
    Completed iterations alone contribute visits. A fixed iteration budget and
    RNG seed are reproducible; a wall-time budget depends on machine throughput.

    Optional root penalties bias UCT selection only: backed-up rewards and visit
    targets stay empirical. The optional evaluator affects nonterminal rollout
    leaves only. Neither hook changes chance sampling or exact terminal rewards.
    """
    started = time.perf_counter()
    config = config or SearchConfig()
    rng = rng if rng is not None else random.Random()
    root_penalties = dict(root_penalties or {})
    if any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0
           for value in root_penalties.values()):
        raise ValueError("Root penalties must be nonnegative and finite.")
    if config.time_limit is not None:
        limit = started + config.time_limit
        deadline = limit if deadline is None else min(deadline, limit)
    if get_outcome(position, max_plies=max_plies) is not None:
        raise ValueError("Cannot search a terminal position.")
    view = position.to_game_state()
    fallback = first_supported_move(view)
    root = _Node(position, [_Edge(fallback)])
    try:
        benchmark = choose_moves(view, deadline=deadline)
        if supported_turn(view, benchmark):
            fallback = benchmark
        root.edges = [_Edge(fallback)]
        actions = generate_candidates(position, limit=config.max_candidates,
                                      fallback=fallback, deadline=deadline)
        root.edges = [_Edge(moves) for moves in actions]
    except TimeoutError:
        pass

    for _ in range(config.iterations):
        node, path, nodes = root, [], [root]
        try:
            for _ in range(config.tree_depth):
                check_deadline(deadline)
                outcome = get_outcome(node.position, max_plies=max_plies)
                if outcome is not None:
                    value = outcome.value_for(position.to_play)
                    break
                if not node.edges:
                    actions = generate_candidates(node.position, limit=config.max_candidates, deadline=deadline)
                    node.edges = [_Edge(moves) for moves in actions]
                edge = _select(node, position.to_play, config.exploration,
                               root_penalties if node is root else None)
                next_position = simulate_turn(node.position, edge.moves, rng)
                path.append(edge)
                key = _key(next_position)
                child = edge.outcomes.get(key)
                if child is None:
                    child = _Node(next_position)
                    edge.outcomes[key] = child
                    nodes.append(child)
                    value = _rollout(next_position, position.to_play, rng, config, deadline,
                                     max_plies, leaf_evaluator)
                    break
                node = child
                nodes.append(node)
            else:
                value = _rollout(node.position, position.to_play, rng, config, deadline,
                                 max_plies, leaf_evaluator)
        except TimeoutError:
            break
        for visited in nodes:
            visited.visits += 1
        for edge in path:
            edge.visits += 1
            edge.total_value += value

    if root.visits:
        best = max(root.edges, key=lambda edge: (edge.visits,
                   edge.total_value / edge.visits if edge.visits else -float("inf")))
        moves = best.moves
    else:
        moves = fallback
    view.validate_moves(moves)
    return SearchResult(moves, [edge.moves for edge in root.edges],
                        [edge.visits for edge in root.edges],
                        [edge.total_value / edge.visits if edge.visits else None for edge in root.edges],
                        root.visits, time.perf_counter() - started, root.visits == 0)
