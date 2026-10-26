"""Alpha-beta over macro-turns: the ZCSN 2022 approach, upgraded (A2+).

Each ply is one side's whole turn. Turns come from lookahead.candidate_turns
(playbook scripts, splits included), ordered by a one-ply evaluation and by the
transposition table. Uncertain battles are chance nodes (lookahead.outcomes):
their value is the probability-weighted value of the win and loss branches.
Iterative deepening keeps the best turn of the last completed depth, so the
agent always answers before its deadline. Leaves use evaluation.evaluate with
the clock (max_plies), so the endgame counts only what can still be reached.
"""

import time

from agents import Agent, fallback_moves, register
from evaluation import WEIGHTS, WIN, win_value
from lookahead import candidate_turns, key, outcomes
from simulator import get_outcome

EXACT, LOWER, UPPER = 0, 1, 2


@register("alphabeta")
class AlphaBeta(Agent):
    def __init__(self, depth=3, max_depth=12, width=10, extra=0, max_risky=2, weights=None):
        self.depth = depth            # Untimed depth (reproducible tournaments).
        self.max_depth = max_depth    # Cap for iterative deepening with a deadline.
        self.width = width            # Turns searched per node, best first.
        self.extra = extra            # Extra turns from candidates.generate_candidates.
        self.max_risky = max_risky
        self.weights = WEIGHTS | (weights or {})

    def new_game(self, position, species, seed):
        self.table = {}

    def choose_moves(self, position, context):
        deadline, max_plies = context.deadline, context.max_plies
        if not hasattr(self, "table") or len(self.table) > 200_000:
            self.table = {}
        nodes = 0

        def check():
            if deadline is not None and time.perf_counter() >= deadline:
                raise TimeoutError

        def leaf(node):
            return win_value(node, node.to_play, self.weights, max_plies)

        def ordered(node, best=None):
            turns = candidate_turns(node, extra=self.extra)
            scored = []
            for moves in turns:
                check()
                child = outcomes(node, moves, 0)[0][1]
                scored.append((-leaf(child), moves))
            scored.sort(key=lambda item: -item[0])
            turns = [moves for _, moves in scored[:self.width]]
            if best is not None:
                if best in turns:
                    turns.remove(best)
                turns.insert(0, best)
            return turns

        def negamax(node, depth, alpha, beta):
            nonlocal nodes
            nodes += 1
            check()
            outcome = get_outcome(node, max_plies=max_plies)
            if outcome is not None or depth == 0:
                return leaf(node)
            entry = self.table.get(key(node))
            best_turn = None
            if entry is not None:
                stored_depth, value, flag, best_turn = entry
                if stored_depth >= depth and (flag == EXACT or (flag == LOWER and value >= beta)
                                              or (flag == UPPER and value <= alpha)):
                    return value
            original_alpha, best_value = alpha, -float("inf")
            for moves in ordered(node, best_turn):
                value = expected(node, moves, depth, alpha, beta)
                if value > best_value:
                    best_value, best_turn = value, moves
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            if best_turn is None:
                return leaf(node)
            flag = UPPER if best_value <= original_alpha else LOWER if best_value >= beta else EXACT
            self.table[key(node)] = (depth, best_value, flag, best_turn)
            return best_value

        def expected(node, moves, depth, alpha, beta):
            branches = outcomes(node, moves, self.max_risky)
            if len(branches) == 1:
                return -negamax(branches[0][1], depth - 1, -beta, -alpha)
            # Chance node: a full window keeps the weighted average exact.
            return sum(q * -negamax(child, depth - 1, -WIN * 2, WIN * 2) for q, child in branches if q > 0)

        best, completed = None, 0
        target = self.depth if deadline is None else self.max_depth
        try:
            for depth in range(1, target + 1):
                value, choice = -float("inf"), None
                for moves in ordered(position, best):
                    score = expected(position, moves, depth, value, float("inf"))
                    if score > value:
                        value, choice = score, moves
                best, completed = choice, depth
                if abs(value) >= WIN:
                    break  # Forced result found: deeper search cannot change the choice.
        except TimeoutError:
            pass
        self.info = {"depth": completed, "nodes": nodes}
        return best or fallback_moves(position)
