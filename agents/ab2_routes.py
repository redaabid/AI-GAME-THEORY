"""AB2 with bounded scripted travel lookahead at quiet leaves.

This is an approximate rollout evaluator, NOT exact temporal Alpha-Beta or
teleportation. Each rollout step is a legal turn and actors alternate. Stop
before nearby enemy contact and return to normal evaluation. The real move is
still the root action chosen by Alpha-Beta; no route is executed open-loop.
"""
from agents import register
from agents.ab_variants import Variant
from candidates import generate_candidates, supported_turn
from game import distance
from simulator import get_outcome, opponent, simulate_turn


@register('ab2route')
class AB2Route(Variant):
    profile_name = 'ab2'

    def __init__(self, *, route_plies=8, **kwargs):
        super().__init__(**kwargs)
        if type(route_plies) is not int or not 0 <= route_plies <= 16:
            raise ValueError('route_plies must be an integer between 0 and 16')
        self.route_plies = route_plies
        self.route_steps = self.route_calls = self.route_max = 0

    def choose_moves(self, position, context):
        self.route_steps = self.route_calls = self.route_max = 0
        moves = super().choose_moves(position, context)
        self.info.update(experiment='scripted_travel_rollout', route_plies=self.route_plies,
                         route_steps=self.route_steps, route_calls=self.route_calls,
                         route_max_steps=self.route_max)
        return moves

    @staticmethod
    def near_enemy(node):
        own = [p for p, c in node.cells.items() if getattr(c, node.to_play)]
        other = [p for p, c in node.cells.items() if getattr(c, opponent(node.to_play))]
        return any(distance(p, q) <= 2 for p in own for q in other)

    def route_move(self, node):
        """One deterministic legal policy for either actor, not a minimax reply."""
        self.check()
        own = [(p, getattr(c, node.to_play)) for p, c in node.cells.items()
               if getattr(c, node.to_play)]
        goals = []
        for target, cell in sorted(node.cells.items()):
            enemy = getattr(cell, opponent(node.to_play))
            required = cell.humans or ((3 * enemy + 1) // 2 if enemy else 0)
            for source, count in own:
                if required and count >= required:
                    benefit = cell.humans or enemy
                    goals.append((benefit / (1 + distance(source, target)), target, source, count))
        if goals:
            _, target, source, count = max(goals)
            state = node.to_game_state()
            for destination in sorted(state.neighbors(source), key=lambda p: (distance(p, target), p)):
                self.check()
                moves = [(source[0], source[1], count, *destination)]
                if supported_turn(state, moves):
                    return moves
        # If this side has no safe target, use the existing heuristic policy;
        # never skip its turn just to let the other side advance.
        choices = generate_candidates(node, limit=2, deadline=self.deadline)
        return choices[0] if choices else None

    def travel(self, node):
        self.route_calls += 1
        following, steps = node, 0
        for _ in range(self.route_plies):
            self.check()
            if get_outcome(following, max_plies=self.max_plies) is not None or self.near_enemy(following):
                break
            moves = self.route_move(following)
            if moves is None:
                break
            following = simulate_turn(following, moves, None)
            steps += 1
            self.route_steps += 1
        self.route_max = max(self.route_max, steps)
        return following

    def leaf(self, node):
        # _plans also calls leaf for prescoring: leave that unchanged. Only
        # extend actual depth-zero search leaves, avoiding hidden generator changes.
        return super().leaf(node)

    def search(self, node, depth, alpha, beta, qleft=0):
        if depth <= 0 and self.route_plies and get_outcome(node, max_plies=self.max_plies) is None:
            self.check()
            self.stats['nodes'] += 1
            following = self.travel(node)
            value = super().leaf(following)
            return (value if following.to_play == node.to_play else -value), None
        return super().search(node, depth, alpha, beta, qleft)
