"""Auditable AB0--AB8 experiments; the existing alphabeta agent is unchanged.

All deterministic variants share an integer-valued evaluator and transition.
AB6 instead integrates the complete finite survivor distribution, lazily, and
uses chance intervals. Deadline interruption returns the last completed search.
"""
from dataclasses import asdict, dataclass, replace
from itertools import product
import json
import logging
from math import comb, fsum, isfinite
import time

from agents import Agent, fallback_moves, register
from candidates import generate_candidates
from combat import win_probability
from evaluation import WEIGHTS, win_value
from game import Cell, distance
from lookahead import candidate_turns
from simulator import Position, get_outcome, opponent, simulate_turn

LOGGER = logging.getLogger(__name__)
SCORE = 1_000_000
EXACT, LOWER, UPPER = 0, 1, 2


@dataclass(frozen=True)
class Features:
    iterative: bool = False
    ordering: bool = False
    tt: bool = False
    history: bool = False
    selective: bool = False
    pvs: bool = False
    aspiration: bool = False
    quiescence: bool = False
    chance: bool = False
    tuned: bool = False
    mtd: bool = False


BASE = Features()
ID = replace(BASE, iterative=True, ordering=True)
MEMORY = replace(ID, tt=True, history=True)
SELECTIVE = replace(MEMORY, selective=True)
PROFILES = {
    "ab0": BASE,
    "ab1": ID,
    "ab2": MEMORY,
    "ab3": SELECTIVE,
    "ab4": replace(SELECTIVE, pvs=True, aspiration=True),
    "ab5": replace(SELECTIVE, quiescence=True),
    "ab6": replace(SELECTIVE, chance=True),
    "ab7": replace(SELECTIVE, tuned=True),
    "ab8": replace(MEMORY, mtd=True),
}


def position_key(node):
    return (node.rows, node.columns, node.to_play, node.ply, node.rules_profile,
            tuple(sorted((p, c.humans, c.vampires, c.werewolves)
                         for p, c in node.cells.items())))


def signature(moves):
    return tuple(sorted(tuple(m) for m in moves))


def battle_distribution(attackers, defenders, humans, actor, profile, check=lambda: None):
    """Complete unconditional distribution; coalesce the all-dead outcome."""
    p = win_probability(attackers, defenders, humans=humans, rules_profile=profile)
    if p == 1:
        return [(1.0, Cell(**{actor: attackers + (defenders if humans else 0)}))]
    defender = "humans" if humans else opponent(actor)
    if p == 0:
        return [(1.0, Cell(**{defender: defenders}))]
    masses = {}
    for branch, n, survival, species in (
        (p, attackers + (defenders if humans else 0), p, actor),
        (1 - p, defenders, 1 - p, defender),
    ):
        for k in range(n + 1):
            check()
            probability = branch * comb(n, k) * survival**k * (1 - survival)**(n - k)
            cell = Cell(**{species: k})
            masses[cell] = masses.get(cell, 0.0) + probability
    total = fsum(masses.values())
    return sorted(((q / total, cell) for cell, q in masses.items() if q > 0),
                  key=lambda item: -item[0])


def exact_successors(node, moves, check=lambda: None):
    """Lazy product of independent destination combats in simulator semantics."""
    check()
    following = simulate_turn(node, moves, None)
    arrivals = {}
    for _, _, n, x, y in moves:
        arrivals[(x, y)] = arrivals.get((x, y), 0) + n
    destinations, distributions = [], []
    for target, n in sorted(arrivals.items()):
        check()
        old = node.cells.get(target, Cell())
        defending = old.humans or getattr(old, opponent(node.to_play))
        if defending:
            destinations.append(target)
            distributions.append(battle_distribution(
                n, defending, bool(old.humans), node.to_play, node.rules_profile, check))
    if not distributions:
        yield 1.0, following
        return
    for choices in product(*distributions):
        check()
        probability = 1.0
        cells = dict(following.cells)
        for target, (q, cell) in zip(destinations, choices):
            probability *= q
            if cell == Cell():
                cells.pop(target, None)
            else:
                cells[target] = cell
        if probability:
            yield probability, replace(following, cells=cells)


class Variant(Agent):
    profile_name = "ab0"

    def __init__(self, depth=3, max_depth=10, width=12, extra=8, tt_size=50000,
                 qdepth=2, qwidth=4, aspiration=50000, weights=None):
        for key, value in dict(depth=depth, max_depth=max_depth, width=width,
                               tt_size=tt_size, qwidth=qwidth, aspiration=aspiration).items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if type(extra) is not int or extra < 0 or type(qdepth) is not int or qdepth < 0:
            raise ValueError("extra and qdepth must be nonnegative integers")
        if max(depth, max_depth, qdepth) > 64:
            raise ValueError("depth caps must be at most 64")
        self.features = PROFILES[self.profile_name]
        if self.features.tuned and weights is None:
            raise ValueError("ab7 requires explicit weights selected on training/validation data")
        if weights is not None and (not isinstance(weights, dict) or set(weights) - WEIGHTS.keys()
                                   or any(not isinstance(v, (int, float)) or not isfinite(v)
                                          for v in weights.values())):
            raise ValueError("weights must contain finite, known evaluation weights")
        self.weights = WEIGHTS | (weights or {})
        if not 0 < self.weights["discount"] <= 1:
            raise ValueError("discount must be in (0, 1]")
        self.depth, self.max_depth, self.width, self.extra = depth, max_depth, width, extra
        self.tt_size, self.qdepth, self.qwidth = tt_size, qdepth, qwidth
        self.aspiration = aspiration
        self.table, self.history = {}, {}

    def new_game(self, position, species, seed):
        self.table, self.history = {}, {}

    def choose_moves(self, position, context):
        self.deadline, self.max_plies = context.deadline, context.max_plies
        self.stats = dict(nodes=0, cutoffs=0, tt_hits=0, researches=0, passes=0,
                          chance_outcomes=0, chance_cutoffs=0, qnodes=0, generated=0,
                          plan_cache_hits=0)
        self.plan_cache = {}
        # Acquired before the first deadline check; never a partial MOV.
        best = signature(fallback_moves(position))
        completed, value, expired = 0, None, False
        cap = self.max_depth if context.deadline is not None else self.depth
        depths = range(1, cap + 1) if self.features.iterative else [self.depth]
        started = time.perf_counter()
        try:
            for depth in depths:
                self.check()
                if self.features.mtd:
                    score, choice = self.mtd(position, depth, value or 0)
                else:
                    alpha, beta = -SCORE - 1, SCORE + 1
                    if self.features.aspiration and value is not None:
                        alpha, beta = value - self.aspiration, value + self.aspiration
                    score, choice = self.search(position, depth, alpha, beta,
                                                self.qdepth if self.features.quiescence else 0)
                    if score <= alpha or score >= beta:
                        self.stats["researches"] += 1
                        score, choice = self.search(position, depth, -SCORE - 1, SCORE + 1,
                                                    self.qdepth if self.features.quiescence else 0)
                if choice is not None:
                    best, completed, value = choice, depth, score
        except TimeoutError:
            expired = True
        self.info = dict(profile=self.profile_name, features=asdict(self.features),
                         depth=completed, value=value, bootstrap=completed == 0,
                         deadline_reached=expired, seconds=time.perf_counter() - started,
                         **self.stats)
        LOGGER.info("AB_METRICS %s", json.dumps(self.info, sort_keys=True))
        return list(best)

    def check(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise TimeoutError("variant deadline")

    def leaf(self, node):
        outcome = get_outcome(node, max_plies=self.max_plies)
        if outcome is not None:
            return outcome.value_for(node.to_play) * SCORE
        raw = win_value(node, node.to_play, self.weights, self.max_plies)
        return max(-SCORE + 1, min(SCORE - 1, round(raw * 100)))

    def _plans(self, node):
        self.check()
        # Selection is independent of history/TT ordering: AB0/1/2/8 see the
        # same candidate set at a given state and parameter configuration.
        count = max(2, self.width + (self.extra if self.features.selective else 0))
        candidates = generate_candidates(node, limit=count, deadline=self.deadline)
        if self.features.selective:
            # Script-based whole-turn coordination plus threshold splits already
            # supplied by the common generator. Fine one-group alternatives are
            # retained for groups close to enemies; no hard two-group restriction.
            scripts = candidate_turns(node, extra=0)
            candidates += scripts
        unique = sorted({signature(m) for m in candidates})
        scored = []
        for moves in unique:
            self.check()
            child = simulate_turn(node, moves, None)
            score = -self.leaf(child)
            scored.append((score, moves, child))
        self.stats["generated"] += len(scored)
        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = scored[:self.width]
        if self.features.selective and selected:
            # Explicit diversity, not just k versions of the same capture.
            categories = {}
            enemies = [p for p, c in node.cells.items() if getattr(c, opponent(node.to_play))]
            critical = {p for p, c in node.cells.items() if getattr(c, node.to_play)
                        and any(distance(p, q) <= 2 for q in enemies)}
            for row in scored:
                moves = row[1]
                split = len({m[:2] for m in moves}) < len(moves)
                attack = any(getattr(node.cells.get(m[3:], Cell()), opponent(node.to_play))
                             for m in moves)
                role = (attack, split, len({m[:2] for m in moves}) > 1,
                        any(m[:2] in critical for m in moves))
                categories.setdefault(role, row)
            diverse = list(categories.values())[:max(1, self.width // 2)]
            selected = diverse + [r for r in scored if r not in diverse]
            selected = selected[:self.width]
        return selected

    def plans(self, node, principal=None, tactical=False):
        self.check()
        cache_key = position_key(node)
        if cache_key in self.plan_cache:
            self.stats["plan_cache_hits"] += 1
            selected = list(self.plan_cache[cache_key])
        else:
            selected = self._plans(node)
            if len(self.plan_cache) < 2048:
                self.plan_cache[cache_key] = tuple(selected)
        if tactical:
            selected = [r for r in selected if any(
                node.cells.get(m[3:], Cell()).humans or
                getattr(node.cells.get(m[3:], Cell()), opponent(node.to_play))
                for m in r[1])][:self.qwidth]
        if self.features.ordering:
            selected.sort(key=lambda r: (r[1] != principal,
                                         -self.history.get(r[1], 0) if self.features.history else 0,
                                         -r[0], r[1]))
        else:
            selected.sort(key=lambda r: r[1])
        return selected

    def action_value(self, node, moves, child, depth, alpha, beta, qleft):
        if not self.features.chance:
            return -self.search(child, depth - 1, -beta, -alpha, qleft)[0]
        accumulated, mass = 0.0, 0.0
        for probability, successor in exact_successors(node, moves, self.check):
            self.stats["chance_outcomes"] += 1
            # Full windows give exact child values before averaging. Star-style
            # interval cutoffs concern only the remaining probability mass.
            score = -self.search(successor, depth - 1, -SCORE - 1, SCORE + 1, qleft)[0]
            accumulated += probability * score
            mass += probability
            remaining = max(0.0, 1.0 - mass)
            lower = accumulated - remaining * SCORE - 1e-6
            upper = accumulated + remaining * SCORE + 1e-6
            if upper <= alpha:
                self.stats["chance_cutoffs"] += 1
                return upper
            if lower >= beta:
                self.stats["chance_cutoffs"] += 1
                return lower
        return accumulated

    def search(self, node, depth, alpha, beta, qleft=0):
        self.check()
        self.stats["nodes"] += 1
        if get_outcome(node, max_plies=self.max_plies) is not None:
            return self.leaf(node), None
        quiet = depth <= 0
        if quiet and qleft <= 0:
            return self.leaf(node), None
        if quiet:
            self.stats["qnodes"] += 1
        # Include horizon, q-regime and game cap; deeper heuristic scores are
        # not exact substitutes for a shallower fixed-depth minimax test.
        cache_key = (position_key(node), depth, qleft, self.max_plies)
        entry = self.table.get(cache_key) if self.features.tt else None
        principal = entry[3] if entry else None
        if entry:
            value, low, high, _ = entry
            if low == high or low >= beta or high <= alpha:
                self.stats["tt_hits"] += 1
                return value, principal
        original_alpha, original_beta = alpha, beta
        rows = self.plans(node, principal, tactical=quiet)
        if not rows:
            return self.leaf(node), None
        best_value, best_move = -float("inf"), None
        next_depth = depth if not quiet else 1
        next_q = qleft if not quiet else qleft - 1
        for index, (_, moves, child) in enumerate(rows):
            self.check()
            if self.features.pvs and index:
                value = self.action_value(node, moves, child, next_depth, alpha, alpha + 1, next_q)
                if alpha < value < beta:
                    self.stats["researches"] += 1
                    value = self.action_value(node, moves, child, next_depth, alpha, beta, next_q)
            else:
                value = self.action_value(node, moves, child, next_depth, alpha, beta, next_q)
            if value > best_value:
                best_value, best_move = value, moves
            alpha = max(alpha, value)
            if alpha >= beta:
                self.stats["cutoffs"] += 1
                if self.features.history:
                    self.history[moves] = self.history.get(moves, 0) + max(1, depth)**2
                break
        if self.features.tt:
            low = best_value if best_value > original_alpha else -float("inf")
            high = best_value if best_value < original_beta else float("inf")
            if entry:
                low, high = max(low, entry[1]), min(high, entry[2])
            if len(self.table) >= self.tt_size:
                self.table.clear()
            self.table[cache_key] = (best_value, low, high, best_move)
        return best_value, best_move

    def mtd(self, node, depth, guess):
        lower, upper = -SCORE - 1, SCORE + 1
        value, witness = int(guess), None
        while lower < upper:
            self.check()
            self.stats["passes"] += 1
            beta = value + 1 if value == lower else value
            value, move = self.search(node, depth, beta - 1, beta)
            if value < beta:
                upper = value
            else:
                lower = value
                if move is not None:
                    witness = move
        return value, witness


for _name in PROFILES:
    register(_name)(type(_name.upper(), (Variant,), {"profile_name": _name}))
