"""Isolated AB2 experiments; historical AB0--AB8 remain unchanged.

Repetition uses observed whole boards with the same actor, never visited cells.
Its cost is a fixed function during one decision (not search-path dependent).
History/goal-dependent caches are cleared between decisions. No new draw rule,
teleportation, opponent skip, or multi-turn macro transition is introduced.
"""
from collections import Counter
from dataclasses import replace
import json
import logging
from math import isfinite

from agents import register
from agents.ab_variants import SCORE, Variant, position_key
from game import distance
from simulator import get_outcome, opponent


def repetition_key(node):
    key = position_key(node)
    return key[:3] + key[4:]  # Ignore absolute ply, retain actor/rules/full board.


@register('ab2exp')
class AB2Experiment(Variant):
    profile_name = 'ab2'

    def __init__(self, *, depth=1, max_depth=8, width=6, tactical=False,
                 repeat_penalty=0, repeat_after=2, progress_weight=0, **kwargs):
        super().__init__(depth=depth, max_depth=max_depth, width=width, **kwargs)
        if type(tactical) is not bool:
            raise ValueError('tactical must be a boolean')
        for name, value in [('repeat_penalty', repeat_penalty),
                            ('progress_weight', progress_weight)]:
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        if type(repeat_after) is not int or repeat_after < 2:
            raise ValueError('repeat_after must be an integer >= 2')
        self.features = replace(self.features, quiescence=tactical)
        self.repeat_penalty = repeat_penalty
        self.repeat_after = repeat_after
        self.progress_weight = progress_weight
        self.observed = Counter()
        self.goal = None
        self.root_species = None

    def choose_moves(self, position, context):
        self.root_species = position.to_play
        self.observed = Counter(repetition_key(p) for p, _ in context.history)
        self.observed[repetition_key(position)] += 1
        self.goal = self.select_goal(position) if self.progress_weight else None
        if self.repeat_penalty or self.progress_weight:
            # A previous decision used another observed-history snapshot/goal.
            self.table.clear()
            self.history.clear()
        moves = super().choose_moves(position, context)
        self.info.update(experiment='ab2exp', width=self.width,
                         max_depth=self.max_depth, repeat_penalty=self.repeat_penalty,
                         repeat_after=self.repeat_after, progress_weight=self.progress_weight,
                         goal=self.goal)
        logging.getLogger(__name__).info('AB2_EXPERIMENT_METRICS %s',
                                        json.dumps(self.info, sort_keys=True))
        return moves

    def select_goal(self, node):
        own = [(p, getattr(c, self.root_species)) for p, c in node.cells.items()
               if getattr(c, self.root_species)]
        goals = []
        for target, cell in sorted(node.cells.items()):
            enemy = getattr(cell, opponent(self.root_species))
            required = cell.humans or ((3 * enemy + 1) // 2 if enemy else 0)
            capable = [distance(p, target) for p, n in own if n >= required]
            if required and capable:
                travel = min(capable)
                benefit = cell.humans or enemy
                goals.append((benefit / (1 + travel), target, required, travel))
        if not goals:
            return None  # Do not reward an under-strength army for suicidal pursuit.
        _, target, required, travel = max(goals)
        return target, required, travel

    def leaf(self, node):
        base = super().leaf(node)
        if self.root_species is None or get_outcome(node, max_plies=self.max_plies) is not None:
            return base  # No heuristic can outweigh or change a terminal verdict.
        utility = 0
        if self.repeat_penalty:
            occurrences = self.observed[repetition_key(node)] + 1
            repeats = min(3, max(0, occurrences - self.repeat_after + 1))
            utility -= self.repeat_penalty * repeats
        if self.goal is not None:
            target, required, initial_distance = self.goal
            distances = [distance(p, target) for p, c in node.cells.items()
                         if getattr(c, self.root_species) >= required]
            remaining = min(distances, default=max(node.rows, node.columns))
            utility += self.progress_weight * (initial_distance - remaining)
        utility = max(-SCORE // 10, min(SCORE // 10, utility))
        score = base + (utility if node.to_play == self.root_species else -utility)
        return max(-SCORE + 1, min(SCORE - 1, round(score)))
