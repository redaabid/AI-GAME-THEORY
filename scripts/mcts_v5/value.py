"""V1 leaf value with the recorded recruitment-feasibility ablation."""

from dataclasses import replace

from candidates import check_deadline
from search import evaluate
from simulator import get_outcome


def feasible_evaluate(position, species, *, deadline=None, max_plies=None):
    """Exclude oversized villages from potential and its normalization only.

    A village is excluded when its humans exceed BOTH species' current total
    populations. Totals include separate groups, so possible merging is allowed.
    This conservative heuristic ignores future growth that could unlock it.
    Understrength battles remain legal and stochastic on the real search board.
    """
    check_deadline(deadline)
    outcome = get_outcome(position, max_plies=max_plies)
    if outcome is not None:
        return outcome.value_for(species)

    vampires = werewolves = 0
    for cell in position.cells.values():
        check_deadline(deadline)
        vampires += cell.vampires
        werewolves += cell.werewolves
    maximum = max(vampires, werewolves)
    cells = {}
    excluded = False
    for coordinate, cell in position.cells.items():
        check_deadline(deadline)
        if cell.humans > maximum:
            excluded = True
        else:
            cells[coordinate] = cell
    check_deadline(deadline)
    view = replace(position, cells=cells) if excluded else position
    return evaluate(view, species, deadline=deadline, max_plies=max_plies)
