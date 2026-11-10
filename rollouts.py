"""Coordinated, stochastic MCTS continuations with bounded tactical extensions.

These are neutral tactical policies for BOTH players, not strategic personalities.
Unlike playbook.playout, every simulated battle uses the search RNG. Repeated
boards stop with a heuristic evaluation, never with an invented draw reward.
"""

from dataclasses import dataclass
from math import isfinite

from candidates import check_deadline, first_supported_move, supported_turn, turn_score
from game import distance
from macro import Order, orders_to_moves
from playbook import View, play_turn, regroup
from search import RolloutResult, action_key, evaluate
from simulator import get_outcome, opponent, simulate_turn
from strategy import choose_moves


def recruitment_plan(position, *, deadline=None):
    """Assign distinct affordable villages before issuing simultaneous orders.

    Independent scripts may send multiple sufficient groups to the same village.
    Reserve each target once, favoring population gained per travel distance.
    Joint recruitment of larger villages is proposed separately below.
    """
    view = View(position, deadline=deadline)
    options = []
    for source, count in view.checked(view.own):
        for _, target, humans in view.checked(view.safe_humans(source, count)):
            travel = distance(source, target)
            options.append((-humans / (1 + travel), travel, source, target, count))
    assigned, claimed, orders = set(), set(), []
    for _, _, source, target, count in sorted(options):
        check_deadline(deadline)
        if source not in assigned and target not in claimed:
            assigned.add(source)
            claimed.add(target)
            orders.append(Order(source, count, target))
    for source, count in view.checked(view.own):
        if source not in assigned:
            orders.extend(regroup(view, source, count))
    return orders_to_moves(position, orders, deadline=deadline)[0]


def coordinated_moves(position, rng, *, deadline=None, variation=0.1, width=3):
    """Rank a small set of legal full-turn plans; sometimes try a close alternative.

    Whole-side scripts offer recruitment, splitting and retreat. Adjacent groups
    may also jointly recruit or attack while other groups keep their orders.
    Every proposed plan is validated, including the 255-creature stack bound.
    """
    check_deadline(deadline)
    state = position.to_game_state()
    humans = state.groups("humans")
    enemies = state.groups(state.enemy_species)
    own = sorted(state.groups())
    plans = {}

    def add(moves):
        check_deadline(deadline)
        key = action_key(moves)
        if key not in plans and supported_turn(state, key):
            plans[key] = turn_score(state, key, humans, enemies, deadline=deadline)

    add(recruitment_plan(position, deadline=deadline))
    default_moves = []
    for script in ("eat", "split", "flee"):
        moves, _ = play_turn(position, {}, script, deadline=deadline)
        if script == "eat":
            default_moves = moves
        add(moves)

    # Scripts that assess groups individually can miss a jointly winning battle.
    targets = set()
    for source, _ in own:
        check_deadline(deadline)
        for target in state.neighbors(source):
            cell = state.cells.get(target)
            if cell is not None and (cell.humans or getattr(cell, state.enemy_species)):
                targets.add(target)
    for target in sorted(targets):
        check_deadline(deadline)
        attackers = []
        for source, count in own:
            check_deadline(deadline)
            if distance(source, target) == 1:
                attackers.append((*source, count, *target))
        if len(attackers) < 2:
            continue
        cell = state.cells[target]
        strength = sum(move[2] for move in attackers)
        if (cell.humans and strength < cell.humans) or (
                not cell.humans and 2 * strength < 3 * getattr(cell, state.enemy_species)):
            continue
        sources = {move[:2] for move in attackers}
        add(attackers)
        add(attackers + [move for move in default_moves if move[:2] not in sources])

    if not plans:
        moves = choose_moves(state, deadline=deadline)
        return moves if supported_turn(state, moves) else first_supported_move(state)
    ranked = sorted(plans, key=lambda key: (-plans[key], key))
    best = ranked[0]
    # Diversity affects choices, not battle probabilities or the reward function.
    tolerance = max(1.0, 0.1 * sum(n for _, n in own))
    alternatives = [key for key in ranked[1:width] if plans[key] >= plans[best] - tolerance]
    if variation and alternatives and rng.random() < variation:
        best = rng.choice(alternatives)
    return list(best)


def tactical_contact(position, *, deadline=None):
    """Opposing groups are adjacent: the position may need a tactical extension."""
    own, enemy = [], []
    for point, cell in position.cells.items():
        check_deadline(deadline)
        if getattr(cell, position.to_play):
            own.append(point)
        elif getattr(cell, opponent(position.to_play)):
            enemy.append(point)
    for source in own:
        for target in enemy:
            check_deadline(deadline)
            if distance(source, target) == 1:
                return True
    return False


@dataclass(frozen=True)
class CoordinatedRollout:
    extension_depth: int = 4
    coordinated: bool = True
    variation: float = 0.1
    width: int = 3
    detect_loops: bool = True

    def __post_init__(self):
        if type(self.extension_depth) is not int or self.extension_depth < 0:
            raise ValueError("extension_depth must be a nonnegative integer.")
        if type(self.width) is not int or self.width < 1:
            raise ValueError("rollout_width must be a positive integer.")
        if type(self.variation) not in (int, float) or not isfinite(self.variation) or not 0 <= self.variation <= 1:
            raise ValueError("variation must be finite and between 0 and 1.")
        if type(self.coordinated) is not bool or type(self.detect_loops) is not bool:
            raise ValueError("coordinated and detect_loops must be True or False.")

    def __call__(self, position, species, rng, config, deadline, max_plies, leaf_evaluator=None):
        plies = coordinated_turns = loop_cutoffs = 0
        seen = set()
        while True:
            check_deadline(deadline)
            outcome = get_outcome(position, max_plies=max_plies)
            if outcome is not None:
                value = outcome.value_for(species)
                break
            if self.detect_loops:
                key = (position.to_play, tuple(sorted(position.cells.items())))
                if key in seen:
                    loop_cutoffs = 1
                    break
                seen.add(key)
            if plies >= config.rollout_depth:
                if plies >= config.rollout_depth + self.extension_depth or not tactical_contact(
                        position, deadline=deadline):
                    break
            if self.coordinated:
                moves = coordinated_moves(position, rng, deadline=deadline,
                                          variation=self.variation, width=self.width)
            else:
                state = position.to_game_state()
                moves = choose_moves(state, deadline=deadline)
                if not supported_turn(state, moves):
                    moves = first_supported_move(state)
            check_deadline(deadline)
            position = simulate_turn(position, moves, rng)
            plies += 1
            coordinated_turns += len({move[:2] for move in moves}) > 1
        # A cap or elimination is exact. A loop or a depth cutoff is heuristic.
        outcome = get_outcome(position, max_plies=max_plies)
        if outcome is not None:
            value = outcome.value_for(species)
        elif leaf_evaluator is not None:
            value = leaf_evaluator(position, species, deadline=deadline, max_plies=max_plies)
        else:
            value = evaluate(position, species, deadline=deadline)
        return RolloutResult(value, plies, max(0, plies - config.rollout_depth),
                             coordinated_turns, loop_cutoffs)
