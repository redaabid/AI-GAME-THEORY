"""MCTS v2: coordinated longer rollouts; v1 is the current memory/clock control."""

from agents import register
from agents.mcts_memory import MemoryMCTSAgent
from rollouts import CoordinatedRollout


@register("mcts-v1")
class MCTSV1Agent(MemoryMCTSAgent):
    """Same decisions as mcts-memory at a fixed seed/budget, with diagnostics."""

    def search_options(self):
        return {"collect_diagnostics": True}


@register("mcts-v2")
class MCTSV2Agent(MCTSV1Agent):
    def __init__(self, extension_depth=4, coordinated=True, variation=0.1,
                 rollout_width=3, detect_loops=True, **config):
        config.setdefault("rollout_depth", 12)
        super().__init__(**config)
        self.rollout_policy = CoordinatedRollout(
            extension_depth, coordinated, variation, rollout_width, detect_loops)

    def search_options(self):
        return super().search_options() | {"rollout_policy": self.rollout_policy}
