"""Macro-actions shared by the search agents: orders per group, turned into legal moves.

An Order says "send `count` creatures from `source` toward `goal`". The goal may
be far away; orders_to_moves takes one step toward it (Chebyshev distance) while
respecting the turn rules, so engines reason in objectives, not in cells.
"""

from dataclasses import dataclass
from math import ceil

from game import Cell, distance
from simulator import opponent


@dataclass(frozen=True)
class Order:
    source: tuple
    count: int
    goal: tuple
    away: bool = False  # Step away from goal instead (fleeing).


def groups(position, kind):
    """Sorted [(cell, count)] for 'humans', 'vampires', or 'werewolves'."""
    return sorted((p, getattr(c, kind)) for p, c in position.cells.items() if getattr(c, kind))


def neighbors(cell, rows, columns):
    x, y = cell
    return [(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if (dx or dy) and 0 <= x + dx < columns and 0 <= y + dy < rows]


def needed(position, target, species):
    """Smallest group that surely wins at target: humans h, enemies ceil(1.5 m), else 1."""
    cell = position.cells.get(target, Cell())
    if cell.humans:
        return cell.humans
    enemy = getattr(cell, opponent(species))
    return ceil(1.5 * enemy) if enemy else 1


def step(order, rows, columns, blocked=()):
    """Best neighbour toward (or away from) the goal, avoiding blocked cells; None if stuck."""
    gx, gy = order.goal
    options = [n for n in neighbors(order.source, rows, columns) if n not in blocked]
    if not options:
        return None
    sign = -1 if order.away else 1
    # Chebyshev first, then squared Euclidean to keep paths straight, then coordinates.
    return min(options, key=lambda n: (sign * distance(n, order.goal),
                                       sign * ((n[0] - gx) ** 2 + (n[1] - gy) ** 2), n))


def orders_to_moves(position, orders, species=None):
    """Legal turn from orders, plus the step taken by each order (None if dropped).

    Rule 5 (a cell cannot be source and target) is enforced by never stepping
    onto a cell that sends creatures this turn. Orders asking for more creatures
    than remain at their source are trimmed. Returns ([], steps) if nothing moves.
    """
    species = species or position.to_play
    available = {p: n for p, n in groups(position, species)}
    sources = {o.source for o in orders if o.count > 0 and available.get(o.source)}
    merged, steps = {}, []
    for order in orders:
        count = min(order.count, available.get(order.source, 0))
        target = step(order, position.rows, position.columns, sources) if count > 0 else None
        if target is None or target == order.source:
            steps.append(None)
            continue
        available[order.source] -= count
        merged[(order.source, target)] = merged.get((order.source, target), 0) + count
        steps.append(target)
    # Blocking every requested source is conservative: dropped orders never make a turn illegal.
    return [(s[0], s[1], n, t[0], t[1]) for (s, t), n in sorted(merged.items())], steps
