"""V5 = V1 search, memory and rollouts + recruitment-feasibility leaf value."""

import logging

from agents import register
from agents.mcts_memory import MemoryMCTSAgent
from scripts.mcts_v5.value import feasible_evaluate
from search import action_key, evaluate, search
from simulator import opponent

LOGGER = logging.getLogger(__name__)


@register("mcts-v5")
class FeasibleMCTSAgent(MemoryMCTSAgent):
    """Isolate one evaluation change; feasibility=False is the V1 control."""

    def __init__(self, feasibility=True, **config):
        if type(feasibility) is not bool:
            raise ValueError("feasibility must be True or False.")
        super().__init__(**config)
        self.feasibility = feasibility

    def leaf_value(self, position, species, *, deadline=None, max_plies=None):
        return feasible_evaluate(position, species, deadline=deadline,
                                 max_plies=max_plies if self.clock else None)

    def choose_moves(self, position, context):
        # Mirror V1's memory wrapper here so existing engines and their saved
        # campaign fingerprints stay intact. Only the leaf callback changes.
        own = sum(getattr(cell, position.to_play) for cell in position.cells.values())
        other = opponent(position.to_play)
        enemy = sum(getattr(cell, other) for cell in position.cells.values())
        penalties, repetitions = {}, 0
        if self.memory and own < enemy:
            penalties, repetitions = self.repetition_penalties(position, context.history)
        leaf = self.leaf_value if self.feasibility else (evaluate if self.clock else None)
        result = search(position, config=self.config, rng=self.rng,
                        max_plies=context.max_plies, deadline=context.deadline,
                        leaf_evaluator=leaf, root_penalties=penalties,
                        collect_diagnostics=True)
        self.info = {"version": "v5", "feasibility": self.feasibility,
                     "leaf_evaluation": "recruitment-feasibility-v1" if self.feasibility else "v1",
                     "iterations": result.iterations, "fallback": result.fallback,
                     "memory": self.memory, "clock": self.clock,
                     "population_margin": own - enemy, "repetitions": repetitions,
                     "penalized_actions": len(penalties),
                     "chosen_repeated": action_key(result.moves) in penalties}
        if result.diagnostics:
            self.info["search"] = result.diagnostics
        if penalties:
            LOGGER.info("Memory: margin=%d, repeats=%d, penalized=%d, chosen_repeated=%s",
                        own - enemy, repetitions, len(penalties), self.info["chosen_repeated"])
        return result.moves
