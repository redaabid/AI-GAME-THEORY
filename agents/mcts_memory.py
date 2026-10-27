"""Experimental MCTS: repeated-position memory and optional turn-cap evaluation."""

from collections import Counter
import logging
from math import isfinite

from agents import register
from agents.builtin import MCTSAgent
from search import action_key, evaluate, search
from simulator import opponent

LOGGER = logging.getLogger(__name__)


def position_key(position):
    """Ignore elapsed plies, but keep all board, actor and rule information."""
    return (position.rows, position.columns, position.rules_profile,
            position.to_play, tuple(sorted(position.cells.items())))


def quiet_plan(position, moves):
    """Only discourage repositioning, never a direct recruitment or attack."""
    if not moves:
        return False
    other = opponent(position.to_play)
    for _, _, _, tx, ty in moves:
        cell = position.cells.get((tx, ty))
        if cell is not None and (cell.humans or getattr(cell, other)):
            return False
    return True


@register("mcts-memory")
class MemoryMCTSAgent(MCTSAgent):
    """Keep the baseline intact; memory and clock can be ablated independently.

    Memory uses this game's supplied own-turn history only. When behind, a quiet
    action taken at least repetition_visits times from this exact board gets a
    fixed root selection penalty. This is a search preference, not a ban or a
    learned value. A modest penalty may leave the action preferred by search.
    """

    def __init__(self, memory=True, clock=True, repetition_visits=2,
                 history_window=32, penalty=0.3, **config):
        super().__init__(**config)
        if type(memory) is not bool or type(clock) is not bool:
            raise ValueError("memory and clock must be True or False.")
        if type(repetition_visits) is not int or repetition_visits < 1:
            raise ValueError("repetition_visits must be a positive integer.")
        if type(history_window) is not int or history_window < repetition_visits:
            raise ValueError("history_window must be at least repetition_visits.")
        if type(penalty) not in (float, int) or not isfinite(penalty) or penalty < 0:
            raise ValueError("penalty must be nonnegative and finite.")
        self.memory, self.clock = memory, clock
        self.repetition_visits, self.history_window = repetition_visits, history_window
        self.penalty = penalty
        self.info = None

    def new_game(self, position, species, seed):
        super().new_game(position, species, seed)
        self.info = None

    def repetition_penalties(self, position, history):
        key = position_key(position)
        counts = Counter()
        repetitions = 0
        for previous, moves in history[-self.history_window:]:
            if previous.ply < position.ply and position_key(previous) == key:
                repetitions += 1
                if quiet_plan(position, moves):
                    counts[action_key(moves)] += 1
        penalties = {action: self.penalty for action, count in counts.items()
                     if count >= self.repetition_visits and self.penalty}
        return penalties, repetitions

    def choose_moves(self, position, context):
        own = sum(getattr(cell, position.to_play) for cell in position.cells.values())
        other = opponent(position.to_play)
        enemy = sum(getattr(cell, other) for cell in position.cells.values())
        penalties, repetitions = {}, 0
        if self.memory and own < enemy:
            penalties, repetitions = self.repetition_penalties(position, context.history)
        result = search(position, config=self.config, rng=self.rng,
                        max_plies=context.max_plies, deadline=context.deadline,
                        leaf_evaluator=evaluate if self.clock else None,
                        root_penalties=penalties)
        self.info = {"iterations": result.iterations, "fallback": result.fallback,
                     "memory": self.memory, "clock": self.clock,
                     "population_margin": own - enemy, "repetitions": repetitions,
                     "penalized_actions": len(penalties),
                     "chosen_repeated": action_key(result.moves) in penalties}
        if penalties:
            LOGGER.info("Memory: margin=%d, repeats=%d, penalized=%d, chosen_repeated=%s",
                        own - enemy, repetitions, len(penalties), self.info["chosen_repeated"])
        return result.moves
