"""Adapters exposing the existing strategies through the shared Agent interface."""

import random

from agents import Agent, register
from candidates import supported_turn
from search import SearchConfig, search
from simulator import full_group_actions
from strategy import choose_moves


@register("random")
class RandomAgent(Agent):
    """Uniform whole-group move: the weakest reference opponent."""

    def __init__(self):
        self.rng = random.Random()

    def new_game(self, position, species, seed):
        self.rng = random.Random(seed)

    def choose_moves(self, position, context):
        view = position.to_game_state()
        return self.rng.choice([m for m in full_group_actions(position) if supported_turn(view, m)])


@register("baseline")
class BaselineAgent(Agent):
    """The one-group benchmark from strategy.py."""

    def choose_moves(self, position, context):
        return choose_moves(position.to_game_state(), deadline=context.deadline)


@register("mcts")
class MCTSAgent(Agent):
    """Adversarial UCT from search.py; parameters are SearchConfig fields."""

    def __init__(self, **config):
        self.config = SearchConfig(**config)
        self.rng = random.Random()

    def new_game(self, position, species, seed):
        self.rng = random.Random(seed)

    def choose_moves(self, position, context):
        result = search(position, config=self.config, rng=self.rng,
                        max_plies=context.max_plies, deadline=context.deadline)
        self.info = {"iterations": result.iterations, "fallback": result.fallback}
        return result.moves
