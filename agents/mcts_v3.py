"""V3 isolates the coordinated rollout policy at V1's original search settings."""

from agents import register
from agents.mcts_v2 import MCTSV1Agent
from rollouts import CoordinatedRollout


@register("mcts-v3")
class MCTSV3Agent(MCTSV1Agent):
    """V1 plus coordinated rollouts for both sides; no other V2 rollout options."""

    def __init__(self, **config):
        super().__init__(**config)
        self.rollout_policy = CoordinatedRollout(
            extension_depth=0, coordinated=True, variation=0, detect_loops=False)

    def search_options(self):
        return super().search_options() | {"rollout_policy": self.rollout_policy}
