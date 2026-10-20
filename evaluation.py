"""Human-race evaluation (G3), in creature units from one species' point of view.

For each human group, who gets there first with enough creatures to convert it?
That predicts the opening far beyond what a search can simulate. The score adds
current material, the humans each side is expected to win (discounted by travel
time), and immediate threats for the side to move. WEIGHTS are meant to be
tuned offline (Texel); pass a modified copy to experiment.
"""

from game import distance
from macro import groups
from simulator import opponent

WEIGHTS = {
    "material": 1.0,   # Own minus enemy creatures.
    "humans": 0.8,     # Humans we win the race to, minus theirs.
    "discount": 0.9,   # Per turn of travel to a human group.
    "threat": 0.7,     # Creatures the side to move can kill right now.
    "groups": 0.1,     # Penalty per extra group (scattered armies are fragile).
}
WIN = 10_000


def arrival(army, target, population):
    """Turns for the nearest group large enough to convert `population`; None if none can."""
    times = [distance(p, target) for p, n in army if n >= population]
    return min(times) if times else None


def turns_left(position, species, max_plies):
    """Turns `species` still plays before the ply limit (None: no limit)."""
    if max_plies is None:
        return None
    remaining = max(0, max_plies - position.ply)
    return (remaining + 1) // 2 if position.to_play == species else remaining // 2


def race_owners(position, species, max_plies=None):
    """{human cell: (winner or None, turns)}: the side that converts each group first."""
    own, enemy = groups(position, species), groups(position, opponent(species))
    we_move_first = position.to_play == species
    ours_left = turns_left(position, species, max_plies)
    theirs_left = turns_left(position, opponent(species), max_plies)
    owners = {}
    for cell, h in groups(position, "humans"):
        ours, theirs = arrival(own, cell, h), arrival(enemy, cell, h)
        if ours is not None and ours_left is not None and ours > ours_left:
            ours = None
        if theirs is not None and theirs_left is not None and theirs > theirs_left:
            theirs = None
        if ours is None and theirs is None:
            owners[cell] = (None, None)
        elif theirs is None or (ours is not None and (ours < theirs or (ours == theirs and we_move_first))):
            owners[cell] = (species, ours)
        else:
            owners[cell] = (opponent(species), theirs)
    return owners


def evaluate(position, species, weights=WEIGHTS, max_plies=None):
    other = opponent(species)
    own, enemy = groups(position, species), groups(position, other)
    own_total, enemy_total = sum(n for _, n in own), sum(n for _, n in enemy)
    if not own_total or not enemy_total:
        if own_total == enemy_total:
            return 0.0
        return WIN + own_total if own_total else -WIN - enemy_total
    if max_plies is not None and position.ply >= max_plies:
        margin = own_total - enemy_total
        return 0.0 if not margin else (WIN if margin > 0 else -WIN) + margin

    humans = {cell: h for cell, h in groups(position, "humans")}
    race = 0.0
    for cell, (winner, turns) in race_owners(position, species, max_plies).items():
        if winner is not None:
            race += (1 if winner == species else -1) * humans[cell] * weights["discount"] ** turns

    # The side to move can kill an adjacent group it outnumbers 1.5 to 1.
    mover, victims = (own, enemy) if position.to_play == species else (enemy, own)
    threat = 0.0
    for p, m in victims:
        attackers = sum(n for q, n in mover if distance(p, q) == 1)
        if 2 * attackers >= 3 * m:
            threat += m
    threat *= 1 if position.to_play == species else -1

    return (weights["material"] * (own_total - enemy_total) + weights["humans"] * race
            + weights["threat"] * threat - weights["groups"] * (len(own) - len(enemy)))
