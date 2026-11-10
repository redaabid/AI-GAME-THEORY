"""V6 plus persistent objective guidance after a tied board repeats."""

from dataclasses import replace
from math import isfinite
import random
import time

from agents import register
from agents.mcts_memory import position_key
from candidates import check_deadline, generate_candidates
from scripts.mcts_v6 import EndgameMCTSAgent
from scripts.mcts_v7.objectives import contact, populations, policy_moves, propose, track
from scripts.mcts_v7.planning import compare_objectives, objective_value
from search import action_key


@register("mcts-v7")
class GoalMCTSAgent(EndgameMCTSAgent):
    """goals=False reproduces V6, including the MCTS RNG stream."""

    def __init__(self, goals=True, goal_depth=24, goal_samples=3, goal_candidates=3,
                 goal_weight=.12, goal_fraction=.15, goal_time=.2, goal_ttl=16,
                 **config):
        if type(goals) is not bool:
            raise ValueError("goals must be True or False.")
        for key, value in (("goal_samples", goal_samples), ("goal_candidates", goal_candidates),
                           ("goal_ttl", goal_ttl)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer.")
        if type(goal_depth) is not int or goal_depth < 2 or goal_depth % 2:
            raise ValueError("goal_depth must be an even integer of at least two plies.")
        for key, value, upper in (("goal_weight", goal_weight, .25),
                                  ("goal_fraction", goal_fraction, .5), ("goal_time", goal_time, 10)):
            if type(value) not in (int, float) or not isfinite(value) or not 0 < value <= upper:
                raise ValueError(f"{key} must be finite and in (0, {upper}].")
        super().__init__(**config)
        self.goals = goals
        self.goal_depth, self.goal_samples, self.goal_candidates = goal_depth, goal_samples, goal_candidates
        self.goal_weight, self.goal_fraction, self.goal_time, self.goal_ttl = (
            goal_weight, goal_fraction, goal_time, goal_ttl)
        self._goal = self._active = None
        self._planner_rng = random.Random(0)

    def new_game(self, position, species, seed):
        super().new_game(position, species, seed)
        self._planner_rng = random.Random(seed ^ 0x7007)
        self._goal = self._active = None

    def leaf_value(self, position, species, *, deadline=None, max_plies=None):
        base = super().leaf_value
        if self._active is None:
            return base(position, species, deadline=deadline, max_plies=max_plies)
        root, goal = self._active
        return objective_value(position, root, goal, species, base, self.goal_weight,
                               deadline=deadline, max_plies=max_plies)

    def _plan(self, position, context, deadline):
        check_deadline(deadline)
        if not self.feasibility:
            return None, "leaf_disabled", [], 0
        a, b = populations(position)
        if not a or a != b:
            return None, "population_not_tied", [], 0
        if contact(position, deadline=deadline):
            return None, "tactical_contact", [], 0
        previous = None
        if self._goal is not None and position.ply - self._goal.created_ply < self.goal_ttl:
            previous = track(position, self._goal, position.to_play, deadline=deadline)
        repeated = any(old.ply < position.ply and position_key(old) == position_key(position)
                       for old, _ in context.history[-self.history_window:])
        if previous is None and not repeated:
            return None, "no_tied_repetition", [], 0
        proposed = propose(position, limit=self.goal_candidates, previous=previous, deadline=deadline)
        if not proposed:
            return None, "no_objectives", [], 0
        # Guidance must refer to a first move our unchanged MCTS can consider.
        from strategy import choose_moves
        fallback = choose_moves(position.to_game_state(), deadline=deadline)
        covered = {action_key(a) for a in generate_candidates(
            position, limit=self.config.max_candidates, fallback=fallback, deadline=deadline)}
        goals, first_moves = [], []
        for goal in proposed:
            moves = policy_moves(position, objective=goal, deadline=deadline)
            if action_key(moves) in covered:
                goals.append(goal)
                first_moves.append(moves)
        if not goals:
            return None, "first_moves_pruned", [], 0
        if previous not in goals:
            previous = None
        best, rows, samples = compare_objectives(
            position, goals, rng=self._planner_rng, depth=self.goal_depth, samples=self.goal_samples,
            evaluator=super().leaf_value, weight=self.goal_weight, deadline=deadline, max_plies=context.max_plies)
        for row, moves in zip(rows, first_moves):
            row["first_moves"] = moves
        if best is None:
            # Partial new comparisons are not evidence for choosing a new goal.
            return previous, "retained_without_complete_sample" if previous else "planning_incomplete", rows, 0
        if rows[best]["robust_value"] < 0:
            return None, "negative_objective_values", rows, samples
        if previous is not None:
            for i, goal in enumerate(goals):
                if (goal == previous and rows[i]["robust_value"] >= 0
                        and rows[i]["robust_value"] >= rows[best]["robust_value"] - .02):
                    best = i
        selected = goals[best]
        return selected, "retained" if selected == previous else "selected", rows, samples

    def choose_moves(self, position, context):
        started = time.perf_counter()
        self._active = None
        goal, status, rows, samples = None, "disabled", [], 0
        planning_seconds = 0.0
        if self.goals:
            # config.time_limit is a whole-decision limit here, including planning.
            deadline = context.deadline
            if self.config.time_limit is not None:
                limit = started + self.config.time_limit
                deadline = limit if deadline is None else min(deadline, limit)
            if deadline is not None:
                context = replace(context, deadline=deadline)
            reserve = self.goal_time if deadline is None else min(
                self.goal_time, max(0, deadline - started) * self.goal_fraction)
            try:
                goal, status, rows, samples = self._plan(
                    position, context, None if deadline is None else started + reserve)
            except TimeoutError:
                status = "planning_deadline"
            planning_seconds = time.perf_counter() - started
            self._goal = goal
            self._active = (position, goal) if goal is not None else None
        try:
            moves = super().choose_moves(position, context)
        finally:
            self._active = None
        self.info.update(version="v7", goals=self.goals, goal_status=status,
                         objective=None if goal is None else goal.to_dict(),
                         goal_planning_seconds=planning_seconds, goal_samples_completed=samples,
                         goal_comparisons=rows, goal_weight=self.goal_weight)
        if goal is not None:
            self.info["leaf_evaluation"] = "v6-with-bounded-objective-progress-v1"
        return moves
