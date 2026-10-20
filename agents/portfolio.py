"""Portfolio Greedy Search (Churchill & Buro 2013), adapted to Vampires vs Werewolves.

Each group gets a script from playbook.SCRIPTS. Starting from the default script
everywhere, we greedily improve the enemy's assignment against ours, then ours
against theirs, one group and one script at a time. An assignment is scored by
a deterministic playout of `horizon` plies followed by the human-race evaluation.
Only the first turn of our best assignment is played.
"""

import time

from agents import Agent, fallback_moves, register
from evaluation import WEIGHTS, evaluate
from macro import groups
from playbook import SCRIPTS, play_turn, playout
from simulator import opponent


@register("portfolio")
class PortfolioGreedySearch(Agent):
    def __init__(self, horizon=10, passes=3, default="eat", scripts=tuple(SCRIPTS), weights=None):
        if default not in SCRIPTS or any(s not in SCRIPTS for s in scripts):
            raise ValueError(f"Scripts must be among {sorted(SCRIPTS)}.")
        self.horizon, self.passes, self.default = horizon, passes, default
        self.scripts = tuple(scripts)
        self.weights = WEIGHTS | (weights or {})

    def choose_moves(self, position, context):
        me = position.to_play
        them = opponent(me)
        deadline = context.deadline

        def check():
            if deadline is not None and time.perf_counter() >= deadline:
                raise TimeoutError

        def value(ours, theirs):
            final = playout(position, {me: ours, them: theirs}, horizon=self.horizon, default=self.default,
                            max_plies=context.max_plies, deadline_check=check)
            return evaluate(final, me, self.weights, context.max_plies)

        def improve(assignment, other, side_is_me, current):
            for cell in sorted(assignment):
                for script in self.scripts:
                    if script == assignment[cell]:
                        continue
                    trial = assignment | {cell: script}
                    score = value(trial, other) if side_is_me else value(other, trial)
                    if (score > current) if side_is_me else (score < current):
                        assignment, current = trial, score
            return assignment, current

        ours = {cell: self.default for cell, _ in groups(position, me)}
        theirs = {cell: self.default for cell, _ in groups(position, them)}
        best, passes_done = dict(ours), 0
        try:
            current = value(ours, theirs)
            for _ in range(self.passes):
                theirs, current = improve(theirs, ours, False, current)
                ours, current = improve(ours, theirs, True, current)
                best = dict(ours)
                passes_done += 1
        except TimeoutError:
            pass
        self.info = {"passes": passes_done, "assignment": sorted(best.items())}
        moves, _ = play_turn(position, best, self.default)
        return moves or fallback_moves(position)
