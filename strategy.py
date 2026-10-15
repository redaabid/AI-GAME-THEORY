"""A small benchmark strategy with an immediate enemy-counterattack estimate.

Move one whole group per turn. This deliberately leaves splitting and deeper
search for later, while providing a replaceable baseline for experiments.
"""

from game import Cell, distance
from combat import DEFAULT_RULES_PROFILE, win_probability


def choose_moves(state):
    """Return one legal full-group move, balancing growth, travel, and threats.

    Scores are heuristics, not a full game simulation. Counterattack estimates
    combine enemy groups able to reach the destination on their next turn.
    """
    own = state.groups()
    enemies = state.groups(state.enemy_species)
    humans = state.groups("humans")
    rules_profile = getattr(state, "rules_profile", DEFAULT_RULES_PROFILE)
    best_move, best_score = None, float("-inf")
    for source, count in own:
        affordable = [(p, h) for p, h in humans if h <= count]
        if affordable:
            goal = max(affordable, key=lambda item: item[1] / (1 + distance(source, item[0])))[0]
        elif len(own) > 1:
            goal = min((p for p, _ in own if p != source), key=lambda p: distance(source, p))
        elif enemies:
            goal = min(enemies, key=lambda item: distance(source, item[0]))[0]
        else:
            goal = source

        for target in state.neighbors(source):
            cell = state.cells.get(target, Cell())
            enemy_count = getattr(cell, state.enemy_species)
            friendly_count = getattr(cell, state.species)
            strength, enemy_removed = float(count + friendly_count), 0.0
            if cell.humans or enemy_count:
                defenders = cell.humans or enemy_count
                probability = win_probability(count, defenders, humans=bool(cell.humans),
                                              rules_profile=rules_profile)
                # Win probability times the conditional expected number alive.
                strength = (count + cell.humans) * probability ** 2
                if enemy_count:
                    enemy_removed = enemy_count * (1 - (1 - probability) ** 2)

            threat = sum(n for p, n in enemies if p != target and distance(p, target) == 1)
            reply_loss = 0.0
            if threat and strength:
                probability = win_probability(threat, strength, rules_profile=rules_profile)
                reply_loss = strength * (1 - (1 - probability) ** 2)

            gain = strength - count - friendly_count
            progress = distance(source, goal) - distance(target, goal)
            score = 2 * gain + 2 * enemy_removed - 3 * reply_loss + progress
            if score > best_score:
                best_score = score
                best_move = (source[0], source[1], count, target[0], target[1])

    if best_move is None:
        raise ValueError("No legal movement is available for our species.")
    moves = [best_move]
    state.validate_moves(moves)
    return moves
