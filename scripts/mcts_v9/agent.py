"""V6 plus a bounded root preference from short recruitment sequences."""

from collections import Counter
from dataclasses import replace
from math import isfinite
import time

from agents import register
from scripts.mcts_v5 import agent as v5_agent
from scripts.mcts_v6 import EndgameMCTSAgent
from scripts.mcts_v6.value import endgame_weight
from scripts.mcts_v9.planning import analyse
from search import action_key, evaluate
from simulator import opponent


@register("mcts-v9")
class RecruitmentMCTSAgent(EndgameMCTSAgent):
    """recruitment=False is the exact fixed-iteration V6 control.

    Root preferences do not change candidate legality, the leaf evaluator,
    stochastic simulation, true terminal utility or the MCTS RNG stream.
    """

    def __init__(self, recruitment=True, recruit_horizon=8, recruit_work=20000,
                 recruit_goals=4, recruit_weight=.12, recruit_time=.025, **config):
        if type(recruitment) is not bool:
            raise ValueError("recruitment must be True or False.")
        for key, value, high in (("recruit_horizon", recruit_horizon, 16),
                                 ("recruit_work", recruit_work, 1000000), ("recruit_goals", recruit_goals, 16)):
            if type(value) is not int or not 1 <= value <= high:
                raise ValueError(f"{key} must be an integer in [1, {high}].")
        for key, value, high in (("recruit_weight", recruit_weight, .25), ("recruit_time", recruit_time, .2)):
            if type(value) not in (int, float) or not isfinite(value) or not 0 < value <= high:
                raise ValueError(f"{key} must be finite and in (0, {high}].")
        super().__init__(**config)
        self.recruitment = recruitment
        self.recruit_horizon, self.recruit_work, self.recruit_goals = recruit_horizon, recruit_work, recruit_goals
        self.recruit_weight, self.recruit_time = recruit_weight, recruit_time
        self._reset_counters()

    def _reset_counters(self):
        self.recruitment_totals = dict(decisions=0, guided_decisions=0, chosen_preferred=0,
                                       planning_seconds=0.0, work=0, two_capture_decisions=0, statuses={})

    def new_game(self, position, species, seed):
        super().new_game(position, species, seed)
        self._reset_counters()

    def choose_moves(self, position, context):
        started = time.perf_counter()
        scores, details = {}, dict(status="disabled", work=0, plans=[], rejected={})
        if self.recruitment:
            deadline = context.deadline
            if self.config.time_limit is not None:
                limit = started + self.config.time_limit
                deadline = limit if deadline is None else min(deadline, limit)
            if deadline is not None:
                context = replace(context, deadline=deadline)
            planning_deadline = None if deadline is None else started + min(
                self.recruit_time, max(0, deadline - started) * .03)
            scores, details = analyse(position, horizon=self.recruit_horizon, work=self.recruit_work,
                                      goals=self.recruit_goals, deadline=planning_deadline,
                                      max_plies=context.max_plies, max_candidates=self.config.max_candidates)
        planning_seconds = time.perf_counter() - started
        best = max(scores.values(), default=0)
        preferences = {key: self.recruit_weight * min(1, max(0, 1 - score / best))
                       for key, score in scores.items() if best > 0 and score < best - 1e-9}
        if not preferences:
            moves = super().choose_moves(position, context)
        else:
            # Mirror V6's wrapper to use the existing root selection hook;
            # the reference classes and shared search remain unedited.
            own = sum(getattr(c, position.to_play) for c in position.cells.values())
            enemy = sum(getattr(c, opponent(position.to_play)) for c in position.cells.values())
            memory_penalties, repetitions = {}, 0
            if self.memory and own < enemy:
                memory_penalties, repetitions = self.repetition_penalties(position, context.history)
            penalties = dict(memory_penalties)
            for key, value in preferences.items():
                penalties[key] = penalties.get(key, 0) + value
            effective = self.endgame and self.clock and self.feasibility
            weight = 0.0
            if effective:
                try:
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
                             endgame=self.endgame, endgame_window=self.endgame_window,
                             endgame_effective=effective, endgame_root_weight=weight,
                             leaf_evaluation="no-human-clock-calibration-v1" if effective else "v6",
                             search=result.diagnostics)
        chosen_score = scores.get(action_key(moves))
        chosen_preferred = chosen_score is not None and best > 0 and abs(chosen_score - best) < 1e-9
        details.update(guided=bool(preferences), planning_seconds=planning_seconds,
                       preferred_score=best if scores else None, chosen_score=chosen_score,
                       chosen_preferred=chosen_preferred, biased_actions=len(preferences))
        self.info.update(version="v9", recruitment_enabled=self.recruitment, recruitment=details)
        totals = self.recruitment_totals
        totals["decisions"] += 1
        totals["guided_decisions"] += bool(preferences)
        totals["chosen_preferred"] += bool(preferences) and chosen_preferred
        totals["planning_seconds"] += planning_seconds
        totals["work"] += details["work"]
        totals["two_capture_decisions"] += any(len(row["captures"]) >= 2 for row in details["plans"])
        statuses = Counter(totals["statuses"])
        statuses[details["status"]] += 1
        totals["statuses"] = dict(statuses)
        return moves
