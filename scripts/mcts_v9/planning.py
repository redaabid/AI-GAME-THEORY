"""Short recruitment itineraries with clocks, competing growth and reply risk.

These are heuristic root preferences, not guaranteed wins. Travel avoids current
occupied cells; enemy arrival bounds ignore obstacles and include up to two
prior conversions. Enemy splits, longer growth chains and moving blockers are
not solved. The ordinary stochastic MCTS remains responsible for the decision.
"""

from collections import deque
from dataclasses import dataclass

from candidates import check_deadline, first_supported_move, generate_candidates, supported_turn
from combat import win_probability
from game import distance
from macro import neighbors
from search import action_key
from simulator import opponent, simulate_turn
from strategy import choose_moves


class PlanningLimit(Exception):
    pass


@dataclass
class Budget:
    limit: int
    deadline: float | None = None
    work: int = 0

    def tick(self):
        check_deadline(self.deadline)
        if self.work >= self.limit:
            raise PlanningLimit
        self.work += 1


def groups(position, kind, budget):
    result = []
    for p, cell in sorted(position.cells.items()):
        budget.tick()
        if getattr(cell, kind):
            result.append((p, getattr(cell, kind)))
    return result


def reply_damage(own, attackers, rules_profile):
    """Adverse expected change in monster material differential, capped at 0.

    Use both winner probability and conditional survivor means. This is not
    expected_battle's likeliest-outcome surrogate and not a full-game value.
    """
    if not attackers:
        return 0.0
    p = win_probability(attackers, own, rules_profile=rules_profile)
    delta = own * (1 - p) ** 2 - attackers * p ** 2 - (own - attackers)
    return min(0.0, delta)


class Races:
    """Optimistic enemy trajectories; each route consumes a village only once."""

    def __init__(self, position, enemy, humans, horizon, budget):
        self.budget, self.routes = budget, []
        self.arrival_cache, self.threat_cache = {}, {}
        for source, count in enemy:
            states = [(source, count, 0, ())]
            self.routes.append((source, count, 0, (), source))
            for _ in range(2):
                following = []
                for current, strength, turns, used in states:
                    for goal, h in humans:
                        budget.tick()
                        if goal in {p for p, _ in used} or h > strength or strength + h > 255:
                            continue
                        arrival = turns + distance(current, goal)
                        if arrival <= horizon:
                            route = goal, strength + h, arrival, (*used, (goal, 2 * arrival))
                            following.append(route)
                            self.routes.append((*route, source))
                states = following

    @staticmethod
    def available(used, reservations):
        # Relative plies: our kth move is 2*k-1; enemy kth is 2*k.
        return all(p not in reservations or ply < reservations[p] for p, ply in used)

    def arrival(self, goal, humans, reservations):
        key = goal, humans, tuple(sorted(reservations.items()))
        if key not in self.arrival_cache:
            earliest = None
            for current, strength, turns, used, _ in self.routes:
                self.budget.tick()
                if strength < humans or strength + humans > 255:
                    continue
                if any(p == goal for p, _ in used) or not self.available(used, reservations):
                    continue
                ply = 2 * (turns + distance(current, goal))
                earliest = ply if earliest is None else min(earliest, ply)
            self.arrival_cache[key] = earliest
        return self.arrival_cache[key]

    def threat(self, goal, turns, reservations):
        key = goal, turns, tuple(sorted(reservations.items()))
        if key not in self.threat_cache:
            per_source = {}
            for current, strength, elapsed, used, source in self.routes:
                self.budget.tick()
                if elapsed + distance(current, goal) <= turns and self.available(used, reservations):
                    per_source[source] = max(strength, per_source.get(source, 0))
            # Multiple armies can arrive together. This may overestimate their
            # combined strength by sharing a hypothetical growth village.
            self.threat_cache[key] = min(255, sum(per_source.values()))
        return self.threat_cache[key]


class Planner:
    def __init__(self, position, budget, horizon, max_plies, races):
        self.position, self.budget, self.horizon = position, budget, horizon
        self.max_plies = max_plies
        self.root_ply = position.ply - 1  # Position is after the actual root move.
        self.humans = groups(position, "humans", budget)
        self.races = races
        self.paths = {}

    def path(self, source, goal, consumed, origin):
        """A quiet route; try a shortest monotone path before bounded BFS."""
        key = source, goal, tuple(sorted(consumed)), origin
        if key in self.paths:
            return self.paths[key]
        blocked = {p for p, c in self.position.cells.items()
                   if p not in (source, goal, origin) and not (c.humans and p in consumed)}
        point, direct = source, []
        while point != goal and len(direct) < self.horizon:
            self.budget.tick()
            options = [p for p in neighbors(point, self.position.rows, self.position.columns)
                       if p not in blocked and distance(p, goal) < distance(point, goal)]
            if not options:
                break
            point = min(options, key=lambda p: (distance(p, goal),
                                                (p[0] - goal[0]) ** 2 + (p[1] - goal[1]) ** 2, p))
            direct.append(point)
        if point == goal:
            self.paths[key] = direct
            return direct
        previous, queue = {source: None}, deque([(source, 0)])
        found = None
        while queue:
            self.budget.tick()
            point, depth = queue.popleft()
            if point == goal:
                found = point
                break
            if depth >= self.horizon:
                continue
            for step in sorted(neighbors(point, self.position.rows, self.position.columns),
                               key=lambda p: (distance(p, goal), p)):
                if step not in blocked and step not in previous:
                    previous[step] = point
                    queue.append((step, depth + 1))
        if found is None:
            route = None
        else:
            route = []
            while found is not None:
                route.append(found)
                found = previous[found]
            route.reverse()
            route = route[1:]
        self.paths[key] = route
        return route

    def leg(self, source, strength, goal, humans, elapsed, reservations, origin):
        self.budget.tick()
        if humans > strength or strength + humans > 255:
            return None, "insufficient_strength"
        earliest = elapsed + distance(source, goal)
        if earliest > self.horizon or (self.max_plies is not None and
                                       self.root_ply + 2 * earliest - 1 > self.max_plies):
            return None, "clock_or_horizon"
        enemy_ply = self.races.arrival(goal, humans, reservations)
        if enemy_ply is not None and enemy_ply <= 2 * earliest - 1:
            return None, "enemy_arrives_first"
        if self.races.threat(goal, earliest - 1, reservations):
            return None, "possible_interception"
        route = self.path(source, goal, reservations, origin)
        if not route:
            return None, "blocked_route"
        turn = elapsed + len(route)
        arrival_ply = 2 * turn - 1
        if turn > self.horizon or (self.max_plies is not None and
                                  self.root_ply + arrival_ply > self.max_plies):
            return None, "clock_or_horizon"
        if enemy_ply is not None and enemy_ply <= arrival_ply:
            return None, "enemy_arrives_first"
        for i, point in enumerate(route, elapsed + 1):
            self.budget.tick()
            if self.races.threat(point, i - 1, reservations):
                return None, "possible_interception"
            if point != goal and self.races.threat(point, i, reservations):
                return None, "possible_interception"
        after = strength + humans
        taken = {**reservations, goal: arrival_ply}
        reply = self.races.threat(goal, turn, taken)
        damage = reply_damage(after, reply, self.position.rules_profile)
        # Credit completed recruitment and adverse reply material, discounted
        # by when it occurs. Travel alone receives no positive reward.
        score = (humans + damage) / (1 + .2 * (turn - 1))
        return dict(target=goal, humans=humans, strength_before=strength,
                    strength_after=after, own_arrival_ply=arrival_ply,
                    enemy_arrival_ply=enemy_ply, own_turn=turn, path=route,
                    reply_attackers=reply, reply_material_damage=damage,
                    score=score, reservations=taken), None


def analyse(position, *, horizon=8, work=20000, deadline=None, max_plies=None,
            max_candidates=32, goals=4):
    """Compare existing whole-group root actions and at most two conversions.

    Drop every preference if a selected comparison is interrupted, so action
    ordering cannot select a winner from an incomplete comparison.
    """
    budget = Budget(work, deadline)
    details = dict(status="no_humans", work=0, plans=[], rejected={})
    scores = {}
    if not any(c.humans for c in position.cells.values()):
        return scores, details
    try:
        humans = groups(position, "humans", budget)
        enemy = groups(position, opponent(position.to_play), budget)
        races = Races(position, enemy, humans, horizon, budget)
        view = position.to_game_state()
        fallback = choose_moves(view, deadline=deadline)
        if not supported_turn(view, fallback):
            fallback = first_supported_move(view)
        actions = generate_candidates(position, limit=max_candidates, fallback=fallback, deadline=deadline)
        plans = []
        rejected = details["rejected"]
        for moves in actions:
            budget.tick()
            arrivals = {}
            for _, _, n, tx, ty in moves:
                arrivals[(tx, ty)] = arrivals.get((tx, ty), 0) + n
            if any(getattr(position.cells.get(p), opponent(position.to_play), 0) or
                   getattr(position.cells.get(p), "humans", 0) > n for p, n in arrivals.items()):
                continue  # Actual monster/risky-human fights stay entirely with V6.
            # Only deterministic quiet moves, merges and certain conversions.
            after = simulate_turn(position, moves, None)
            planner = Planner(after, budget, horizon, max_plies, races)
            immediate = [(p, c.humans) for p, c in position.cells.items()
                         if p in arrivals and c.humans]
            reservations = {p: 1 for p, _ in immediate}
            root_score, root_captures, threatened = 0.0, [], set()
            for point in arrivals:
                strength = getattr(after.cells[point], position.to_play)
                threat = races.threat(point, 1, reservations)
                if threat:
                    threatened.add(point)
                damage = reply_damage(strength, threat, position.rules_profile)
                h = dict(immediate).get(point, 0)
                root_score += h + damage
                if h:
                    root_captures.append(dict(target=point, humans=h, strength_after=strength,
                                              own_arrival_ply=1, own_turn=1, path=[point],
                                              reply_attackers=threat, reply_material_damage=damage))
            best = dict(moves=moves, score=root_score, captures=root_captures)
            own_groups = groups(after, position.to_play, budget)
            own_groups.sort(key=lambda group: min((distance(group[0], p)
                                                   for p, h in planner.humans if h <= group[1]), default=999))
            for source, count in own_groups[:3] if len(root_captures) < 2 else []:
                if source in threatened:
                    continue
                first_goals = sorted(((p, h) for p, h in planner.humans
                                      if h <= count and h + count <= 255),
                                     key=lambda v: (-v[1] / (1 + distance(source, v[0])), v[0]))[:goals]
                for target, h in first_goals:
                    first, reason = planner.leg(source, count, target, h, 1, reservations, source)
                    if first is None:
                        rejected[reason] = rejected.get(reason, 0) + 1
                        continue
                    sequence, score = [*root_captures, first], root_score + first["score"]
                    if len(sequence) < 2 and not first["reply_attackers"]:
                        second_goals = sorted(((p, n) for p, n in planner.humans
                                               if p != target and n <= first["strength_after"]
                                               and n + first["strength_after"] <= 255),
                                              key=lambda v: (-v[1] / (1 + distance(target, v[0])), v[0]))[:goals]
                        for next_target, next_h in second_goals:
                            second, reason = planner.leg(target, first["strength_after"], next_target,
                                                         next_h, first["own_turn"], first["reservations"], source)
                            if second is None:
                                rejected[reason] = rejected.get(reason, 0) + 1
                            elif root_score + first["score"] + second["score"] > score:
                                sequence = [*root_captures, first, second]
                                score = root_score + first["score"] + second["score"]
                    if score > best["score"]:
                        best = dict(moves=moves, score=score,
                                    captures=[{k: v for k, v in leg.items() if k != "reservations"}
                                              for leg in sequence])
            plans.append(best)
            scores[action_key(moves)] = best["score"]
        details["plans"] = plans
        # Absolute itinerary values are only relative preferences, not values
        # to add to V6's leaf estimate or to label training outcomes.
        if not scores or max(scores.values()) <= 0:
            scores = {}
            details["status"] = "no_positive_plan"
        else:
            details["status"] = "complete"
    except (PlanningLimit, TimeoutError) as error:
        scores = {}
        details["status"] = "work_limit" if isinstance(error, PlanningLimit) else "planning_deadline"
    details["work"] = budget.work
    return scores, details
