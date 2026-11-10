"""V6 = V5 plus a clock-aware value for no-human endgames."""

from agents import register
from scripts.mcts_v5.agent import FeasibleMCTSAgent
from scripts.mcts_v6.value import endgame_evaluate, endgame_weight, validate_window


@register("mcts-v6")
class EndgameMCTSAgent(FeasibleMCTSAgent):
    """Keep V5's search, rollouts and memory; endgame=False is the V5 control."""

    def __init__(self, endgame=True, endgame_window=40, **config):
        if type(endgame) is not bool:
            raise ValueError("endgame must be True or False.")
        validate_window(endgame_window)
        super().__init__(**config)
        self.endgame = endgame
        self.endgame_window = endgame_window

    def leaf_value(self, position, species, *, deadline=None, max_plies=None):
        if not self.endgame or not self.clock:
            return super().leaf_value(position, species, deadline=deadline, max_plies=max_plies)
        return endgame_evaluate(position, species, deadline=deadline, max_plies=max_plies,
                                endgame_window=self.endgame_window)

    def choose_moves(self, position, context):
        # Compute reporting fields before search, with its deadline. An expired
        # deadline must still reach V5's legal-fallback handling.
        effective = self.endgame and self.clock and self.feasibility
        weight = 0.0
        if effective:
            try:
                weight = endgame_weight(position, max_plies=context.max_plies,
                                        endgame_window=self.endgame_window, deadline=context.deadline)
            except TimeoutError:
                pass
        moves = super().choose_moves(position, context)
        self.info.update(version="v6", endgame=self.endgame, endgame_window=self.endgame_window,
                         endgame_effective=effective, endgame_root_weight=weight)
        if effective:
            self.info["leaf_evaluation"] = "no-human-clock-calibration-v1"
        return moves
