"""Targeted AB2 root tie ordering, preserving the searched actions and scores.

Observed issue: static scoring plus lexicographic ordering discards the existing
generator's strategic ordering on flat endgames. At the root, order by static
score, fewer recently repeated exact after-move boards, then generator rank.
This replaces root TT/history ordering; internal-node ordering stays unchanged.
Alpha-Beta still replaces a move whenever a higher searched value is found.
No evaluation weight, movement rule, combat model or repetition penalty changes.
"""
from collections import Counter
from agents import register
from agents.ab_variants import Variant, position_key, signature
from agents.ab2_experiments import repetition_key
from candidates import generate_candidates
from game import Cell
from simulator import simulate_turn, opponent


@register('ab2tie')
class AB2Tie(Variant):
    profile_name = 'ab2'

    def choose_moves(self, position, context):
        self.root_key = position_key(position)
        self.root_rank = None
        self.recent_after = Counter()
        # Reconstruct only non-combat historical turns: these transitions are
        # deterministic observations, not invented outcomes of past dice rolls.
        for prior, moves in context.history[-8:]:
            if not moves:
                continue
            targets = [prior.cells.get((m[3], m[4]), Cell()) for m in moves]
            if any(c.humans or getattr(c, opponent(prior.to_play)) for c in targets):
                continue
            after = simulate_turn(prior, moves, None)
            self.recent_after[repetition_key(after)] += 1
        moves = super().choose_moves(position, context)
        self.info.update(experiment='root_generator_tie_order', width=self.width,
                         max_depth=self.max_depth, recent_after_boards=len(self.recent_after))
        return moves

    def plans(self, node, principal=None, tactical=False):
        rows = super().plans(node, principal, tactical)
        if not tactical and position_key(node) == self.root_key:
            if self.root_rank is None:
                ordered = generate_candidates(node, limit=max(2, self.width), deadline=self.deadline)
                self.root_rank = {signature(moves): i for i, moves in enumerate(ordered)}
            # Exactly the same set; only static-score ties use generator rank.
            rows.sort(key=lambda row: (-row[0], self.recent_after[repetition_key(row[2])],
                                      self.root_rank.get(row[1], len(self.root_rank)), row[1]))
        return rows

    def search(self, node, depth, alpha, beta, qleft=0):
        if position_key(node) == self.root_key:
            # Previous searches can have stored this future position as an
            # internal node. Its value is useful but its tied principal action
            # did not use the root policy. Re-search the root to apply that policy.
            self.table.pop((self.root_key, depth, qleft, self.max_plies), None)
        return super().search(node, depth, alpha, beta, qleft)
