"""Bounded geometric contact analysis, not a battle or match-win solver.

Only fully checked pair models may guide a root move. Recruitment, a possible
third-party intervention, and incomplete computation are unresolved. A legal,
uninterferable rendezvous is an escape witness before merging, not a draw proof.
"""

from dataclasses import dataclass, replace
from math import ceil
import random

from candidates import check_deadline, generate_candidates
from game import distance
from search import action_key
from simulator import opponent, simulate_turn
from strategy import choose_moves


class AnalysisLimit(Exception):
    pass


@dataclass
class Budget:
    deadline: float | None
    limit: int
    nodes: int = 0

    def tick(self):
        check_deadline(self.deadline)
        if self.nodes >= self.limit:
            raise AnalysisLimit
        self.nodes += 1


def groups(position, species):
    return sorted((p, getattr(c, species)) for p, c in position.cells.items()
                  if getattr(c, species))


def neighbors(position, point):
    x, y = point
    return [(a, b) for a in range(max(0, x - 1), min(position.columns, x + 2))
            for b in range(max(0, y - 1), min(position.rows, y + 2)) if (a, b) != point]


def merge_escape(position, target, *, budget, max_turns=8, max_plies=None):
    """Find one quiet legal enemy rendezvous outside every own reachable set.

    Each own army can travel at most j cells before enemy reply j. Checking
    both enemy pre/post positions against that set makes this witness immune
    to our intervening moves. A blocked midpoint is simply inconclusive.
    """
    species = position.to_play
    enemy = opponent(species)
    own = groups(position, species)
    targets = dict(groups(position, enemy))
    for ally, count in sorted(targets.items()):
        budget.tick()
        if ally == target or count + targets[target] > 255:
            continue
        lower = ceil(distance(target, ally) / 2)
        if lower > max_turns or (max_plies is not None and position.ply + 2 * lower > max_plies):
            continue
        midpoints = sorted({(x, y)
                            for x in ((target[0] + ally[0]) // 2, (target[0] + ally[0] + 1) // 2)
                            for y in ((target[1] + ally[1]) // 2, (target[1] + ally[1] + 1) // 2)})
        for meeting in midpoints:
            current, points, path = position, (target, ally), []
            counts = (targets[target], count)
            for turn in range(1, lower + 1):
                budget.tick()
                if any(distance(a, p) <= turn for a, _ in own for p in points):
                    break
                steps = tuple((p[0] + (meeting[0] > p[0]) - (meeting[0] < p[0]),
                               p[1] + (meeting[1] > p[1]) - (meeting[1] < p[1])) for p in points)
                if any(distance(a, p) <= turn for a, _ in own for p in steps):
                    break
                # A witness must not cross a human village or another army.
                if any(p in current.cells and p not in points for p in steps):
                    break
                moves = [(*p, n, *q) for p, q, n in zip(points, steps, counts) if p != q]
                if not moves:
                    break
                try:
                    current = simulate_turn(replace(current, to_play=enemy,
                                                   ply=position.ply + 2 * turn - 1),
                                            moves, random.Random(0))
                except ValueError:
                    break
                path.append(moves)
                points = steps
                if points[0] == points[1]:
                    return dict(status="merge_escape_witness", target=target, ally=ally,
                                meeting=meeting, enemy_turns=turn,
                                merged_count=sum(counts), enemy_moves=path)
    return None


class PairContact:
    """Finite-horizon alternating pursuit with all evader neighbors plus wait.

    Wait overapproximates the evader's legal choices when it has no other army.
    Other armies' reachable envelopes are unresolved hazards, not frozen units.
    CONTACT means unavoidable geometric contact in this bounded model, never
    guaranteed battle victory. AVOID only means not forced within this horizon.
    This model assumes the target stays intact; enemy splits are not enumerated.
    """

    def __init__(self, position, source, target, *, budget, depth):
        self.position, self.budget, self.depth = position, budget, depth
        species = position.to_play
        self.humans = {p for p, c in position.cells.items() if c.humans}
        self.others = [(p, actor) for actor, name in enumerate((species, opponent(species)))
                       for p, _ in groups(position, name)
                       if p != (source if actor == 0 else target)]
        self.cache = {}

    def solve(self, pursuer, evader, elapsed=0):
        key = pursuer, evader, elapsed
        if key in self.cache:
            return self.cache[key]
        self.budget.tick()
        own_turns, enemy_turns = 1 + elapsed // 2, (elapsed + 1) // 2
        if (pursuer in self.humans or evader in self.humans or
                any(min(distance(p, pursuer), distance(p, evader)) <=
                    (own_turns if actor == 0 else enemy_turns) for p, actor in self.others)):
            result = "unknown", 0
        elif pursuer == evader:
            result = "contact", 0
        elif elapsed >= self.depth or distance(pursuer, evader) > self.depth - elapsed:
            result = "avoid", 0
        else:
            chasing = bool(elapsed % 2)  # First future ply belongs to the enemy.
            point = pursuer if chasing else evader
            choices = neighbors(self.position, point)
            if not chasing:
                choices.append(point)
            choices.sort(key=lambda p: (distance(p, evader) if chasing else -distance(p, pursuer), p))
            results = []
            for step in choices:
                child = self.solve(step if chasing else pursuer, evader if chasing else step, elapsed + 1)
                results.append(child)
                if (chasing and child[0] == "contact") or (not chasing and child[0] == "avoid"):
                    break
            if chasing:
                contacts = [d for s, d in results if s == "contact"]
                result = (("contact", 1 + min(contacts)) if contacts else
                          ("unknown", 0) if any(s == "unknown" for s, _ in results) else ("avoid", 0))
            else:
                result = (("avoid", 0) if any(s == "avoid" for s, _ in results) else
                          ("unknown", 0) if any(s == "unknown" for s, _ in results) else
                          ("contact", 1 + max(d for _, d in results)))
        self.cache[key] = result
        return result


def analyse(position, *, depth=8, nodes=4000, pairs=4, deadline=None, max_plies=None,
            max_candidates=32):
    """Return positive contact preferences or no guidance, never prune actions.

    If any selected comparison exceeds the global bound, discard all preferences
    from the partial comparison. Unselected pairs are not claimed to be solved.
    """
    budget = Budget(deadline, nodes)
    rows, scores = [], {}
    species = position.to_play
    own, enemy = groups(position, species), groups(position, opponent(species))
    candidates = [(distance(a, b), a, n, b, m) for a, n in own for b, m in enemy if n > m]
    info = dict(status="no_weaker_targets", nodes=0, pairs=[], selected_pairs=0)
    if not candidates:
        return scores, info
    if any(distance(a, b) <= 1 for a, _ in own for b, _ in enemy):
        info["status"] = "tactical_contact"
        return scores, info
    try:
        check_deadline(deadline)
        fallback = choose_moves(position.to_game_state(), deadline=deadline)
        actions = generate_candidates(position, limit=max_candidates, fallback=fallback, deadline=deadline)
        if max_plies is not None:
            depth = min(depth, max(0, max_plies - position.ply - 1))
        selected = sorted(candidates)[:pairs]
        info["selected_pairs"] = len(selected)
        for _, source, count, target, target_count in selected:
            budget.tick()
            row = dict(source=source, count=count, target=target, target_count=target_count)
            witness = merge_escape(position, target, budget=budget, max_plies=max_plies)
            if witness:
                row.update(status="merge_escape_witness", witness=witness)
                rows.append(row)
                continue
            solver = PairContact(position, source, target, budget=budget, depth=depth)
            checked = []
            for moves in actions:
                check_deadline(deadline)
                if len(moves) != 1 or tuple(moves[0][:2]) != source or moves[0][2] != count:
                    continue
                step = tuple(moves[0][3:])
                if step in position.cells:  # Direct battles/recruitment/merges stay with V6.
                    continue
                status, delay = solver.solve(step, target)
                checked.append(dict(moves=moves, status=status, future_plies=delay))
                if status == "contact":
                    scores[action_key(moves)] = max(scores.get(action_key(moves), 0), 1 / (1 + delay))
            row.update(status="pair_model_checked", actions=checked)
            rows.append(row)
        info["status"] = "guided" if scores else "no_verified_contact"
    except (AnalysisLimit, TimeoutError) as error:
        scores = {}
        info["status"] = "node_limit" if isinstance(error, AnalysisLimit) else "analysis_deadline"
    info.update(nodes=budget.nodes, pairs=rows)
    return scores, info
