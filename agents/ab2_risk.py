"""Experimental AB2: exact stochastic branches only for uncertain combats.

Same candidates, evaluation, width and iterative deepening as AB2Experiment.
Quiet and guaranteed transitions keep ordinary alpha-beta windows. At uncertain
combats, reuse AB6's exact distributions and chance bounds. No tuning claim.
"""
from dataclasses import replace
from agents import register
from agents.ab2_experiments import AB2Experiment
from agents.ab_variants import Variant
from combat import win_probability
from game import Cell
from simulator import opponent

def uncertain_combat(node, moves):
    arrivals = {}
    for _, _, count, x, y in moves:
        arrivals[(x, y)] = arrivals.get((x, y), 0) + count
    for target, count in arrivals.items():
        cell = node.cells.get(target, Cell())
        defenders = cell.humans or getattr(cell, opponent(node.to_play))
        if defenders and 0 < win_probability(count, defenders, humans=bool(cell.humans),
                                             rules_profile=node.rules_profile) < 1:
            return True
    return False

@register("ab2risk")
class AB2Risk(AB2Experiment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.features = replace(self.features, chance=True)

    def action_value(self, node, moves, child, depth, alpha, beta, qleft):
        if not uncertain_combat(node, moves):
            return -self.search(child, depth - 1, -beta, -alpha, qleft)[0]
        return Variant.action_value(self, node, moves, child, depth, alpha, beta, qleft)
