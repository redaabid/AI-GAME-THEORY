"""V6 plus a bounded root preference for geometrically checked interceptions."""

from dataclasses import replace
from math import isfinite
import time

from agents import register
from agents.mcts_memory import quiet_plan
from scripts.mcts_v5 import agent as v5_agent
from scripts.mcts_v6 import EndgameMCTSAgent
from scripts.mcts_v6.value import endgame_weight
from scripts.mcts_v8.interception import analyse
from search import action_key, evaluate
from simulator import opponent


@register("mcts-v8")
class InterceptionMCTSAgent(EndgameMCTSAgent):
    """interceptions=False reproduces V6, including its MCTS RNG stream.

    No persistent chase, distance reward, neural guide or recruitment change.
    The small root preference uses the existing nonnegative penalty hook; it is
    fixed during a search, not progressive bias. Backed-up values stay V6's.
    """

    def __init__(self, interceptions=True, intercept_depth=8, intercept_nodes=4000,
                 intercept_pairs=4, intercept_weight=.08, intercept_time=.03, **config):
        if type(interceptions) is not bool:
            raise ValueError("interceptions must be True or False.")
        for key, value in (("intercept_depth", intercept_depth), ("intercept_nodes", intercept_nodes),
                           ("intercept_pairs", intercept_pairs)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer.")
        if intercept_depth > 16:
            raise ValueError("intercept_depth must not exceed 16 future plies.")
        for key, value, upper in (("intercept_weight", intercept_weight, .25),
                                  ("intercept_time", intercept_time, .2)):
            if type(value) not in (int, float) or not isfinite(value) or not 0 < value <= upper:
                raise ValueError(f"{key} must be finite and in (0, {upper}].")
        super().__init__(**config)
        self.interceptions = interceptions
        self.intercept_depth, self.intercept_nodes, self.intercept_pairs = (
            intercept_depth, intercept_nodes, intercept_pairs)
        self.intercept_weight, self.intercept_time = intercept_weight, intercept_time

    def choose_moves(self, position, context):
        started = time.perf_counter()
        scores, details = {}, {"status": "disabled", "nodes": 0, "pairs": []}
        guided_actions = 0
        if self.interceptions:
            deadline = context.deadline
            if self.config.time_limit is not None:
                limit = started + self.config.time_limit
                deadline = limit if deadline is None else min(deadline, limit)
            if deadline is not None:
                context = replace(context, deadline=deadline)
            analysis_deadline = None if deadline is None else started + min(
                self.intercept_time, max(0, deadline - started) * .05)
            scores, details = analyse(position, depth=self.intercept_depth,
                                      nodes=self.intercept_nodes, pairs=self.intercept_pairs,
                                      deadline=analysis_deadline, max_plies=context.max_plies,
                                      max_candidates=self.config.max_candidates)
        planning = time.perf_counter() - started
        if not scores:
            moves = super().choose_moves(position, context)
        else:
            # Mirror only the V5/V6 wrapper; leave their search and sources intact.
            species, enemy_species = position.to_play, opponent(position.to_play)
            own = sum(getattr(c, species) for c in position.cells.values())
            enemy = sum(getattr(c, enemy_species) for c in position.cells.values())
            penalties, repetitions = {}, 0
            if self.memory and own < enemy:
                penalties, repetitions = self.repetition_penalties(position, context.history)
            memory_penalties = dict(penalties)
            best = max(scores.values())
            # Search copies this mapping. Missing quiet actions get a bounded
            # preference below; direct material-changing actions are untouched.
            from candidates import generate_candidates
            from strategy import choose_moves
            try:
                fallback = choose_moves(position.to_game_state(), deadline=context.deadline)
                actions = generate_candidates(position, limit=self.config.max_candidates,
                                              fallback=fallback, deadline=context.deadline)
                for action in actions:
                    if quiet_plan(position, action):
                        key = action_key(action)
                        preference = self.intercept_weight * (1 - scores.get(key, 0) / best)
                        if preference > 0:
                            penalties[key] = penalties.get(key, 0) + preference
                            guided_actions += 1
            except TimeoutError:
                moves = super().choose_moves(position, context)
                self.info.update(version="v8", interceptions=self.interceptions,
                                 interception={**details, "status": "search_deadline"},
                                 interception_seconds=planning, interception_guided=False)
                return moves
            effective = self.endgame and self.clock and self.feasibility
            weight = 0.0
            try:
                if effective:
                    weight = endgame_weight(position, max_plies=context.max_plies,
                                            endgame_window=self.endgame_window, deadline=context.deadline)
            except TimeoutError:
                pass
            result = v5_agent.search(position, config=self.config, rng=self.rng,
                                     max_plies=context.max_plies, deadline=context.deadline,
                                     leaf_evaluator=self.leaf_value if self.feasibility else (
                                         evaluate if self.clock else None),
                                     root_penalties=penalties, collect_diagnostics=True)
            moves = result.moves
            self.info = dict(iterations=result.iterations, fallback=result.fallback,
                             memory=self.memory, clock=self.clock, feasibility=self.feasibility,
                             population_margin=own - enemy, repetitions=repetitions,
                             penalized_actions=len(memory_penalties),
                             chosen_repeated=action_key(moves) in memory_penalties,
                             interception_penalized_actions=guided_actions,
                             endgame=self.endgame, endgame_window=self.endgame_window,
                             endgame_effective=effective, endgame_root_weight=weight,
                             leaf_evaluation="no-human-clock-calibration-v1" if effective else "v6",
                             search=result.diagnostics)
        self.info.update(version="v8", interceptions=self.interceptions, interception=details,
                         interception_seconds=planning, interception_guided=bool(guided_actions),
                         chosen_interception=action_key(moves) in scores)
        return moves
