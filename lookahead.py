"""Look-ahead helpers shared by alpha-beta and OEP: candidate turns and risky battles.

candidate_turns gives a small, diverse set of legal turns built from the
playbook scripts. outcomes splits a turn's uncertain battles into a win branch
and a loss branch, each with its mean survivors, so a search weighs a 55% fight
as a 55% fight instead of a sure win.
"""

from dataclasses import replace

from candidates import generate_candidates
from combat import win_probability
from game import Cell
from macro import groups
from playbook import SCRIPTS, play_turn
from simulator import opponent, simulate_turn


def key(position):
    """Hashable identity of a position (Position itself is not hashable)."""
    cells = tuple(sorted((p, c.humans, c.vampires, c.werewolves) for p, c in position.cells.items()))
    return cells, position.to_play, position.ply


def candidate_turns(position, *, extra=0, default="eat"):
    """Distinct legal turns: each script for every group, then one group switched from default.

    extra > 0 adds the best turns of candidates.generate_candidates (single steps,
    coordinated arrivals), for engines that want a wider action set.
    """
    turns, seen = [], set()

    def add(moves):
        moves = [tuple(m) for m in moves]
        signature = tuple(sorted(moves))
        if moves and signature not in seen:
            seen.add(signature)
            turns.append(moves)

    for script in SCRIPTS:
        add(play_turn(position, {}, script)[0])
    for cell, _ in groups(position, position.to_play):
        for script in SCRIPTS:
            if script != default:
                add(play_turn(position, {cell: script}, default)[0])
    if extra:
        for moves in generate_candidates(position, limit=max(2, extra)):
            add(moves)
    return turns


def outcomes(position, moves, max_risky=2):
    """[(probability, next position)] for a turn.

    Each uncertain battle (0 < p < 1) becomes two branches, as in the server:
    the attacker wins with mean survivors population * p, or the defender keeps
    defenders * (1 - p). Beyond max_risky battles, the rest stay deterministic.
    """
    following = simulate_turn(position, moves, None)
    actor = position.to_play
    incoming = {}
    for _, _, count, tx, ty in moves:
        incoming[(tx, ty)] = incoming.get((tx, ty), 0) + count
    risky = []
    for target, count in sorted(incoming.items()):
        cell = position.cells.get(target)
        if cell is None:
            continue
        kind = "humans" if cell.humans else opponent(actor)
        defenders = getattr(cell, kind)
        if not defenders:
            continue
        humans = kind == "humans"
        p = win_probability(count, defenders, humans=humans, rules_profile=position.rules_profile)
        if 0 < p < 1:
            population = count + (defenders if humans else 0)
            risky.append((target, p, Cell(**{actor: round(population * p)}),
                          Cell(**{kind: round(defenders * (1 - p))})))
    if not risky:
        return [(1.0, following)]
    branches = [(1.0, {})]
    for target, p, win, loss in risky[:max_risky]:
        branches = [(q * r, change | {target: cell}) for q, change in branches
                    for r, cell in ((p, win), (1 - p, loss))]
    results = []
    for q, change in branches:
        cells = dict(following.cells)
        for target, cell in change.items():
            if cell == Cell():
                cells.pop(target, None)
            else:
                cells[target] = cell
        results.append((q, replace(following, cells=cells)))
    return results
