"""Scripted group behaviours (the "portfolio"), and playouts that use them.

A script maps one group to Orders (macro.py). Portfolio Greedy Search chooses a
script per group; OEP can use playouts as its fitness and its opponent model.
Each script falls back to another behaviour when it has nothing to do, so every
group always receives an order.
"""

from game import distance
from macro import Order, groups, orders_to_moves
from simulator import get_outcome, opponent, simulate_turn

DISCOUNT = 0.9


class View:
    """Groups of one side's turn, computed once and shared by all its scripts."""

    def __init__(self, position, species=None):
        self.position = position
        self.species = species or position.to_play
        self.own = groups(position, self.species)
        self.enemy = groups(position, opponent(self.species))
        self.humans = groups(position, "humans")
        self.center = ((position.columns - 1) // 2, (position.rows - 1) // 2)

    def safe_humans(self, cell, n):
        """Humans this group converts before any enemy able to convert them, best first."""
        options = []
        for target, h in self.humans:
            if h > n:
                continue
            ours = distance(cell, target)
            # We move first in our own turn, so a tie is ours.
            if any(m >= h and distance(p, target) < ours for p, m in self.enemy):
                continue
            # Do not convert next to an enemy that could then kill the larger group.
            if any(2 * m >= 3 * (n + h) and distance(p, target) <= ours + 1 for p, m in self.enemy):
                continue
            options.append((h * DISCOUNT ** ours, target, h))
        return sorted(options, key=lambda item: (-item[0], item[1]))

    def killable(self, cell, n):
        options = [(m / (1 + distance(cell, p)), p) for p, m in self.enemy if 2 * n >= 3 * m]
        return max(options)[1] if options else None

    def predator(self, cell, n, radius=2):
        """Nearest enemy within radius that surely kills this group, or None."""
        threats = [(distance(cell, p), p) for p, m in self.enemy
                   if 2 * m >= 3 * n and distance(cell, p) <= radius]
        return min(threats)[1] if threats else None


def eat(view, cell, n):
    options = view.safe_humans(cell, n)
    return [Order(cell, n, options[0][1])] if options else attack(view, cell, n)


def attack(view, cell, n):
    target = view.killable(cell, n)
    return [Order(cell, n, target)] if target else regroup(view, cell, n)


def flee(view, cell, n):
    threat = view.predator(cell, n)
    return [Order(cell, n, threat, away=True)] if threat else eat(view, cell, n)


def merge(view, cell, n):
    allies = [(distance(cell, p), -m, p) for p, m in view.own if p != cell]
    return [Order(cell, n, min(allies)[2])] if allies else eat(view, cell, n)


def split(view, cell, n):
    """Send exactly enough to the best humans and the rest to the next ones (D2)."""
    options = view.safe_humans(cell, n)
    for _, first, h1 in options:
        for _, second, h2 in options:
            if second != first and h1 + h2 <= n:
                return [Order(cell, h1, first), Order(cell, n - h1, second)]
    return eat(view, cell, n)


def regroup(view, cell, n):
    """Nothing to eat or kill: flee danger, join the largest ally, or close in on a weaker enemy."""
    threat = view.predator(cell, n)
    if threat:
        return [Order(cell, n, threat, away=True)]
    allies = [(-m, distance(cell, p), p) for p, m in view.own if p != cell]
    if allies:
        return [Order(cell, n, min(allies)[2])]
    weaker = [(distance(cell, p), p) for p, m in view.enemy if m < n]
    if weaker:
        return [Order(cell, n, min(weaker)[1])]
    return [Order(cell, n, view.center)] if cell != view.center else [Order(cell, n, view.enemy[0][0], away=True)]


SCRIPTS = {"eat": eat, "attack": attack, "flee": flee, "merge": merge, "split": split}


def play_turn(position, assignment, default="eat"):
    """Moves for the side to play, and its assignment carried to the groups' new cells."""
    view = View(position)
    orders, owners = [], []
    for cell, n in view.own:
        script = assignment.get(cell, default)
        new = SCRIPTS[script](view, cell, n)
        orders += new
        owners += [script] * len(new)
    moves, steps = orders_to_moves(position, orders)
    carried = {}
    for order, target, script in zip(orders, steps, owners):
        carried.setdefault(target if target is not None else order.source, script)
    return moves, carried


def playout(position, assignments, *, horizon, default="eat", max_plies=None, deadline_check=None):
    """Play `horizon` plies with scripts for both sides; battles are deterministic."""
    from agents import fallback_moves  # Late import: agents imports the engines.

    assignments = {side: dict(a) for side, a in assignments.items()}
    for _ in range(horizon):
        if deadline_check:
            deadline_check()
        if get_outcome(position, max_plies=max_plies) is not None:
            break
        side = position.to_play
        moves, assignments[side] = play_turn(position, assignments.get(side, {}), default)
        try:
            following = simulate_turn(position, moves, None) if moves else None
        except ValueError:
            following = None
        # Empty or unsupported turn: play the greedy fallback instead.
        position = following or simulate_turn(position, fallback_moves(position), None)
    return position
