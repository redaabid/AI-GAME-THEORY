"""Context features and a small n-tuple UCB parameter tuner.

Inspired by SA-MCTS and NTBEA; this enumerates a tiny parameter grid rather
than implementing NTBEA's evolutionary neighborhood search. Domain thresholds
and parameter ranges are engineering starting points, not learned optima.
"""

from dataclasses import replace
from itertools import product
from math import isfinite, log, sqrt

from candidates import check_deadline
from game import distance
from simulator import opponent


def board_context(position, *, deadline=None, max_plies=None):
    own, enemy, humans = [], [], []
    other = opponent(position.to_play)
    for point, cell in sorted(position.cells.items()):
        check_deadline(deadline)
        if getattr(cell, position.to_play):
            own.append((point, getattr(cell, position.to_play)))
        elif getattr(cell, other):
            enemy.append((point, getattr(cell, other)))
        elif cell.humans:
            humans.append((point, cell.humans))
    enemy_distance = target_distance = None
    for point, count in own:
        for target, _ in enemy:
            check_deadline(deadline)
            gap = distance(point, target)
            enemy_distance = gap if enemy_distance is None else min(enemy_distance, gap)
        for target, population in humans:
            check_deadline(deadline)
            if count >= population:
                gap = distance(point, target)
                target_distance = gap if target_distance is None else min(target_distance, gap)
    remaining = None if max_plies is None else max(0, max_plies - position.ply)
    span = max(position.rows, position.columns)
    next_event = min((d for d in (enemy_distance, target_distance) if d is not None), default=0)
    if remaining is not None and remaining <= 12:
        regime = "late"
    elif enemy_distance is not None and enemy_distance <= 2:
        regime = "contact"
    elif len(own) + len(enemy) >= 6:
        regime = "busy"
    elif next_event >= max(4, (span + 2) // 3):
        regime = "travel"
    else:
        regime = "balanced"
    return {"regime": regime, "rows": position.rows, "columns": position.columns,
            "area": position.rows * position.columns, "span": span,
            "own_groups": len(own), "enemy_groups": len(enemy), "human_groups": len(humans),
            "nearest_enemy": enemy_distance, "nearest_affordable_humans": target_distance,
            "remaining_plies": remaining}


def parameter_configs(config, context, *, tune_rollout=True):
    """Keep V1's setting among a small context-dependent set of alternatives."""
    if type(tune_rollout) is not bool:
        raise ValueError("tune_rollout must be True or False.")
    base = config.rollout_depth
    if not tune_rollout:
        # Preserve V1's configured horizon even near the match cap. The
        # rollout itself stops at terminal states or the clock, as in V1.
        depths = (base,)
    elif context["regime"] == "travel" and base:
        depths = (min(2, base), base, min(12, base + 4))
    elif context["regime"] in ("busy", "late"):
        depths = (0, min(2, base), base)
    else:
        depths = (min(2, base), min(4, base), base)
    remaining = context["remaining_plies"]
    if tune_rollout and remaining is not None:
        depths = tuple(min(d, max(0, remaining - 1)) for d in depths)
    depths = tuple(sorted(set(depths)))
    exploration = (0.5 * config.exploration, config.exploration, 1.5 * config.exploration)
    return {(c, d): replace(config, exploration=c, rollout_depth=d)
            for c, d in product(exploration, depths)}


class NTupleTuner:
    """Share observations across each parameter value and complete parameter pairs.

    Returns are root-perspective simulation rewards, not observed match wins.
    The model is fresh for each decision, avoiding stale position-dependent
    returns and cross-game leakage. An aborted simulation is never observed.
    """

    def __init__(self, arms, rng, *, exploration=0.35, first=None):
        self.arms = tuple(arms)
        if not self.arms or len(set(self.arms)) != len(self.arms):
            raise ValueError("The tuner needs distinct parameter pairs.")
        if type(exploration) not in (int, float) or not isfinite(exploration) or exploration < 0:
            raise ValueError("Tuner exploration must be finite and nonnegative.")
        self.exploration = exploration
        self.order = list(self.arms)
        rng.shuffle(self.order)
        if first in self.order:
            self.order.remove(first)
            self.order.insert(0, first)
        self.tables = ({}, {}, {})
        self.samples = 0

    @staticmethod
    def keys(arm):
        return (arm[0], arm[1], arm)

    def choose(self):
        for arm in self.order:
            if arm not in self.tables[2]:
                return arm
        log_total = log(self.samples + 1)

        def ucb(arm):
            values = []
            for table, key in zip(self.tables, self.keys(arm)):
                reward_sum, count = table[key]
                values.append(reward_sum / count + self.exploration * sqrt(log_total / count))
            return sum(values) / len(values)

        return max(self.order, key=ucb)

    def observe(self, arm, value):
        if arm not in self.arms:
            raise ValueError("Observation refers to an unknown parameter pair.")
        if not isfinite(value) or not -1 <= value <= 1:
            raise ValueError("Simulation values must be finite and in [-1, 1].")
        reward = (value + 1) / 2
        for table, key in zip(self.tables, self.keys(arm)):
            total, count = table.get(key, (0.0, 0))
            table[key] = (total + reward, count + 1)
        self.samples += 1

    def summary(self):
        return [{"exploration": c, "rollout_depth": d,
                 "samples": self.tables[2].get((c, d), (0, 0))[1],
                 "mean_simulation_value": (2 * self.tables[2][(c, d)][0] /
                                           self.tables[2][(c, d)][1] - 1)
                 if (c, d) in self.tables[2] else None}
                for c, d in self.arms]
