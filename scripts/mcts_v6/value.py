"""Experimental turn-limit calibration on top of V5's leaf evaluation."""

from candidates import check_deadline
from scripts.mcts_v5.value import feasible_evaluate
from simulator import get_outcome, opponent


def validate_window(endgame_window):
    if type(endgame_window) is not int or endgame_window < 1:
        raise ValueError("endgame_window must be a positive integer (in plies).")


def endgame_weight(position, *, max_plies=None, endgame_window=40, deadline=None):
    """Report the clock weight; a ply is one player's turn, not a full round."""
    check_deadline(deadline)
    validate_window(endgame_window)
    if max_plies is None or max_plies - position.ply >= endgame_window:
        return 0.0
    for cell in position.cells.values():
        check_deadline(deadline)
        if cell.humans:
            return 0.0
    return min(1.0, 1 - (max_plies - position.ply) / endgame_window)


def endgame_evaluate(position, species, *, deadline=None, max_plies=None,
                     endgame_window=40):
    """Blend no-human endgame leaves toward their population-at-cap result.

    This is a heuristic, not a solved win probability: further battles can
    change the population lead. The weight rises linearly from zero at the
    window boundary to one at the cap. Actual terminal outcomes stay exact.
    Both species use the same rule; attacks receive no separate bonus.
    """
    check_deadline(deadline)
    validate_window(endgame_window)
    value = feasible_evaluate(position, species, deadline=deadline, max_plies=max_plies)
    weight = endgame_weight(position, max_plies=max_plies,
                            endgame_window=endgame_window, deadline=deadline)
    if not weight:
        return value
    outcome = get_outcome(position, max_plies=max_plies)
    if outcome is not None:
        return outcome.value_for(species)
    own = enemy = 0
    other = opponent(species)
    for cell in position.cells.values():
        check_deadline(deadline)
        own += getattr(cell, species)
        enemy += getattr(cell, other)
    cap_value = (own > enemy) - (own < enemy)
    return (1 - weight) * value + weight * cap_value
