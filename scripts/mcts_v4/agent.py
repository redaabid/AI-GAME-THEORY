"""Register the isolated V4 explicitly, without changing agents/ during a run."""

from math import isfinite
import random

from agents import register
from agents.mcts_memory import MemoryMCTSAgent
from search import action_key, evaluate
from simulator import opponent
from scripts.mcts_v4.engine import adaptive_search


@register("mcts-v4")
class AdaptiveMCTSAgent(MemoryMCTSAgent):
    def __init__(self, adaptive=True, tuner_exploration=0.35, tuning_batch=8,
                 tune_rollout=True, **config):
        super().__init__(**config)
        if type(adaptive) is not bool:
            raise ValueError("adaptive must be True or False.")
        if type(tune_rollout) is not bool:
            raise ValueError("tune_rollout must be True or False.")
        if type(tuning_batch) is not int or tuning_batch < 1:
            raise ValueError("tuning_batch must be a positive integer.")
        if (type(tuner_exploration) not in (float, int) or not isfinite(tuner_exploration)
                or tuner_exploration < 0):
            raise ValueError("tuner_exploration must be finite and nonnegative.")
        self.adaptive, self.tuner_exploration, self.tuning_batch = adaptive, tuner_exploration, tuning_batch
        self.tune_rollout = tune_rollout
        self.parameter_rng = random.Random(0)

    def new_game(self, position, species, seed):
        super().new_game(position, species, seed)
        self.parameter_rng = random.Random(seed ^ 0x5634)

    def choose_moves(self, position, context):
        self.info = None
        own = sum(getattr(cell, position.to_play) for cell in position.cells.values())
        other = opponent(position.to_play)
        enemy = sum(getattr(cell, other) for cell in position.cells.values())
        penalties, repetitions = {}, 0
        if self.memory and own < enemy:
            penalties, repetitions = self.repetition_penalties(position, context.history)
        result = adaptive_search(
            position, config=self.config, rng=self.rng, max_plies=context.max_plies,
            deadline=context.deadline, leaf_evaluator=evaluate if self.clock else None,
            root_penalties=penalties, adaptive=self.adaptive, parameter_rng=self.parameter_rng,
            tuner_exploration=self.tuner_exploration, tuning_batch=self.tuning_batch,
            tune_rollout=self.tune_rollout)
        self.info = {"iterations": result.iterations, "fallback": result.fallback,
                     "memory": self.memory, "clock": self.clock, "population_margin": own - enemy,
                     "repetitions": repetitions, "penalized_actions": len(penalties),
                     "chosen_repeated": action_key(result.moves) in penalties,
                     "search": result.diagnostics, "adaptive": result.diagnostics["adaptive"]}
        return result.moves
