"""Isolated SA-UCT experiment sharing V1's nodes, rollout and combat code.

The search loop mirrors V1 so the adaptive=False control can be regression
checked. Only per-iteration exploration and rollout depth are changed. No
module in the running V1/V3 experiment is patched or modified.
"""

from math import isfinite
import random
import time

from candidates import check_deadline, first_supported_move, generate_candidates, supported_turn
from search import (SearchConfig, SearchResult, _Edge, _Node, _key, _rollout, _select,
                    empty_diagnostics)
from simulator import get_outcome, simulate_turn
from strategy import choose_moves
from scripts.mcts_v4.tuning import NTupleTuner, board_context, parameter_configs


class AdaptiveSearchResult(SearchResult):
    def training_metadata(self):
        metadata = super().training_metadata()
        tuning = self.diagnostics.get("adaptive", {})
        if tuning.get("enabled"):
            algorithm = ("contextual_sa_uct_v4" if tuning["tune_rollout"]
                         else "exploration_sa_uct_v4")
            metadata = metadata | {"algorithm": algorithm,
                                   "context": tuning["context"], "parameter_arms": tuning["arms"]}
        return metadata


def adaptive_search(position, *, config=None, rng=None, max_plies=None, deadline=None,
                    leaf_evaluator=None, root_penalties=None, adaptive=True,
                    parameter_rng=None, tuner_exploration=0.35, tuning_batch=8,
                    tune_rollout=True):
    started, cpu_started = time.perf_counter(), time.process_time()
    diagnostics = empty_diagnostics()
    config = config or SearchConfig()
    rng = rng if rng is not None else random.Random()
    parameter_rng = parameter_rng if parameter_rng is not None else random.Random(0)
    if type(adaptive) is not bool or type(tuning_batch) is not int or tuning_batch < 1:
        raise ValueError("adaptive must be boolean and tuning_batch a positive integer.")
    if type(tune_rollout) is not bool:
        raise ValueError("tune_rollout must be True or False.")
    root_penalties = dict(root_penalties or {})
    if any(not isinstance(v, (int, float)) or not isfinite(v) or v < 0 for v in root_penalties.values()):
        raise ValueError("Root penalties must be nonnegative and finite.")
    if config.time_limit is not None:
        limit = started + config.time_limit
        deadline = limit if deadline is None else min(deadline, limit)
    if get_outcome(position, max_plies=max_plies) is not None:
        raise ValueError("Cannot search a terminal position.")
    view = position.to_game_state()
    fallback = first_supported_move(view)
    root = _Node(position, [_Edge(fallback)])
    tuner, configs, arm, context = None, {}, None, {}
    tuning_wall = tuning_cpu = 0.0

    def candidates(current, **kwargs):
        wall, cpu = time.perf_counter(), time.process_time()
        diagnostics["candidate_calls"] += 1
        try:
            return generate_candidates(current, limit=config.max_candidates, deadline=deadline, **kwargs)
        finally:
            diagnostics["candidate_wall_seconds"] += time.perf_counter() - wall
            diagnostics["candidate_cpu_seconds"] += time.process_time() - cpu

    def rollout(current, iteration_config):
        wall, cpu = time.perf_counter(), time.process_time()
        try:
            result = _rollout(current, position.to_play, rng, iteration_config,
                              deadline, max_plies, leaf_evaluator)
        finally:
            diagnostics["rollout_wall_seconds"] += time.perf_counter() - wall
            diagnostics["rollout_cpu_seconds"] += time.process_time() - cpu
        diagnostics["rollouts"] += 1
        diagnostics["rollout_plies"] += result.plies
        diagnostics["rollout_depth_max"] = max(diagnostics["rollout_depth_max"], result.plies)
        for name in ("extension_plies", "coordinated_turns", "loop_cutoffs"):
            diagnostics[name] += getattr(result, name)
        return result.value

    try:
        benchmark = choose_moves(view, deadline=deadline)
        if supported_turn(view, benchmark):
            fallback = benchmark
        root.edges = [_Edge(fallback)]
        root.edges = [_Edge(moves) for moves in candidates(position, fallback=fallback)]
        if adaptive:
            wall, cpu = time.perf_counter(), time.process_time()
            try:
                context = board_context(position, deadline=deadline, max_plies=max_plies)
                configs = parameter_configs(config, context, tune_rollout=tune_rollout)
                remaining = context["remaining_plies"]
                first_depth = config.rollout_depth
                if tune_rollout and remaining is not None:
                    first_depth = min(first_depth, max(0, remaining - 1))
                tuner = NTupleTuner(configs, parameter_rng, exploration=tuner_exploration,
                                    first=(config.exploration, first_depth))
            finally:
                tuning_wall += time.perf_counter() - wall
                tuning_cpu += time.process_time() - cpu
    except TimeoutError:
        diagnostics["deadline_stops"] = 1

    for _ in range(config.iterations):
        node, path, nodes = root, [], [root]
        iteration_config = config
        try:
            check_deadline(deadline)
            if tuner is not None:
                wall, cpu = time.perf_counter(), time.process_time()
                if arm is None or tuner.samples % tuning_batch == 0:
                    arm = tuner.choose()
                iteration_config = configs[arm]
                tuning_wall += time.perf_counter() - wall
                tuning_cpu += time.process_time() - cpu
            for _ in range(config.tree_depth):
                check_deadline(deadline)
                outcome = get_outcome(node.position, max_plies=max_plies)
                if outcome is not None:
                    value = outcome.value_for(position.to_play)
                    break
                if not node.edges:
                    node.edges = [_Edge(moves) for moves in candidates(node.position)]
                # Adapt our role only. Rewarding root returns for changing the
                # opponent's exploration could favor an artificially weak foe.
                exploration = (iteration_config.exploration
                               if node.position.to_play == position.to_play else config.exploration)
                edge = _select(node, position.to_play, exploration,
                               root_penalties if node is root else None)
                next_position = simulate_turn(node.position, edge.moves, rng)
                path.append(edge)
                key = _key(next_position)
                child = edge.outcomes.get(key)
                if child is None:
                    child = _Node(next_position)
                    edge.outcomes[key] = child
                    nodes.append(child)
                    value = rollout(next_position, iteration_config)
                    break
                node = child
                nodes.append(node)
            else:
                value = rollout(node.position, iteration_config)
        except TimeoutError:
            diagnostics["deadline_stops"] = 1
            break
        diagnostics["iterations"] += 1
        diagnostics["tree_depth_total"] += len(path)
        diagnostics["tree_depth_max"] = max(diagnostics["tree_depth_max"], len(path))
        for visited in nodes:
            visited.visits += 1
        for edge in path:
            edge.visits += 1
            edge.total_value += value
        if tuner is not None:
            wall, cpu = time.perf_counter(), time.process_time()
            tuner.observe(arm, value)
            tuning_wall += time.perf_counter() - wall
            tuning_cpu += time.process_time() - cpu

    if root.visits:
        best = max(root.edges, key=lambda edge: (edge.visits,
                   edge.total_value / edge.visits if edge.visits else -float("inf")))
        moves = best.moves
    else:
        moves = fallback
    view.validate_moves(moves)
    diagnostics["adaptive"] = {
        "enabled": adaptive, "context": context, "samples": tuner.samples if tuner else 0,
        "tune_rollout": tune_rollout, "rollout_depth": config.rollout_depth,
        "tuned_parameters": (["exploration", "rollout_depth"] if tune_rollout else ["exploration"])
                            if adaptive else [],
        "arms": tuner.summary() if tuner else [], "batch_size": tuning_batch,
        "tuner_wall_seconds": tuning_wall, "tuner_cpu_seconds": tuning_cpu,
        "fitness": "root_simulation_value_not_match_win_rate",
    }
    diagnostics["search_wall_seconds"] = time.perf_counter() - started
    diagnostics["search_cpu_seconds"] = time.process_time() - cpu_started
    return AdaptiveSearchResult(moves, [edge.moves for edge in root.edges],
                                [edge.visits for edge in root.edges],
                                [edge.total_value / edge.visits if edge.visits else None for edge in root.edges],
                                root.visits, time.perf_counter() - started, root.visits == 0, diagnostics)
