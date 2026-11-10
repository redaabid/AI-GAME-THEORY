"""Adaptive controller, fixed-V1 parity, stochastic combat and safety checks."""

from dataclasses import replace
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import generate_candidates, supported_turn
from game import Cell
from scripts.mcts_v4.engine import adaptive_search
from scripts.mcts_v4.tuning import NTupleTuner, board_context, parameter_configs
from search import RolloutResult, SearchConfig, _rollout, _select, evaluate, search
from simulator import Position, get_outcome, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]


def distant():
    return Position(20, 20, {(0, 0): Cell(vampires=6), (19, 19): Cell(werewolves=8),
                             (10, 10): Cell(humans=4)})


class ContextTests(unittest.TestCase):
    def test_same_area_can_require_different_settings_and_species_are_symmetric(self):
        travel = distant()
        contact = replace(travel, cells={(0, 0): Cell(vampires=6), (1, 1): Cell(werewolves=8)})
        swapped = replace(travel, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in travel.cells.items()})
        self.assertEqual(board_context(travel)["area"], board_context(contact)["area"])
        self.assertEqual(board_context(travel)["regime"], "travel")
        self.assertEqual(board_context(contact)["regime"], "contact")
        self.assertEqual(board_context(travel), board_context(swapped))

    def test_unaffordable_nearby_village_does_not_hide_long_travel(self):
        position = replace(distant(), cells=distant().cells | {(1, 1): Cell(humans=7)})
        context = board_context(position)
        self.assertEqual(context["nearest_affordable_humans"], 10)
        self.assertEqual(context["regime"], "travel")

    def test_group_count_and_remaining_clock_change_the_domain(self):
        busy = replace(distant(), cells={
            (0, 0): Cell(vampires=2), (0, 3): Cell(vampires=2), (0, 6): Cell(vampires=2),
            (19, 0): Cell(werewolves=3), (19, 3): Cell(werewolves=3), (19, 6): Cell(werewolves=3)})
        self.assertEqual(board_context(busy)["regime"], "busy")
        late = board_context(replace(busy, ply=199), max_plies=200)
        self.assertEqual(late["regime"], "late")
        domains = {parameter: parameter_configs(SearchConfig(), {**late, "regime": parameter})
                   for parameter in ("travel", "contact", "busy", "late")}
        for configs in domains.values():
            self.assertEqual({depth for _, depth in configs}, {0})

    def test_domains_keep_baseline_and_expose_only_small_contextual_alternatives(self):
        config = SearchConfig()
        for regime, expected in (("travel", {2, 6, 10}), ("contact", {2, 4, 6}),
                                 ("balanced", {2, 4, 6}), ("busy", {0, 2, 6}), ("late", {0, 2, 6})):
            configs = parameter_configs(config, {"regime": regime, "remaining_plies": None})
            self.assertEqual({d for _, d in configs}, expected)
            self.assertIn((1.4, 6), configs)
            self.assertLessEqual(len(configs), 9)
            for (c, d), settings in configs.items():
                self.assertEqual(settings, replace(config, exploration=c, rollout_depth=d))
        zero = parameter_configs(replace(config, rollout_depth=0), board_context(distant()))
        self.assertEqual({d for _, d in zero}, {0})

    def test_exploration_only_preserves_configured_horizon_in_every_context_and_clock(self):
        config = SearchConfig()
        for regime in ("travel", "contact", "balanced", "busy", "late"):
            for remaining in (None, 20, 3, 1):
                context = {"regime": regime, "remaining_plies": remaining}
                configs = parameter_configs(config, context, tune_rollout=False)
                self.assertEqual(len(configs), 3)
                self.assertEqual({depth for _, depth in configs}, {6})
                self.assertEqual({c for c, _ in configs}, {0.7, 1.4, 1.5 * 1.4})
                for (c, _), settings in configs.items():
                    self.assertEqual(settings, replace(config, exploration=c))
        custom = parameter_configs(replace(config, rollout_depth=3), board_context(distant()), tune_rollout=False)
        self.assertEqual({depth for _, depth in custom}, {3})


class TunerTests(unittest.TestCase):
    def test_coverage_shared_statistics_and_normalized_rewards(self):
        arms = [(0.7, 2), (0.7, 6), (1.4, 2), (1.4, 6)]
        tuner = NTupleTuner(arms, random.Random(3), first=(1.4, 6))
        self.assertEqual(tuner.choose(), (1.4, 6))
        covered = []
        for _ in arms:
            arm = tuner.choose()
            covered.append(arm)
            tuner.observe(arm, 1 if arm == (1.4, 6) else -1)
        self.assertEqual(set(covered), set(arms))
        self.assertEqual(tuner.tables[0][1.4], (1.0, 2))
        self.assertEqual(tuner.tables[1][6], (1.0, 2))
        self.assertEqual(sum(row["samples"] for row in tuner.summary()), tuner.samples)
        tuner.exploration = 0
        self.assertEqual(tuner.choose(), (1.4, 6))

    def test_bad_observations_and_agent_options_are_rejected(self):
        tuner = NTupleTuner([(1.4, 6)], random.Random(0))
        for value in (-1.01, 1.01, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                tuner.observe((1.4, 6), value)
        self.assertEqual(tuner.samples, 0)
        for spec in ("mcts-v4:adaptive=1", "mcts-v4:tuning_batch=0", "mcts-v4:tuner_exploration=-1",
                     "mcts-v4:tune_rollout=1"):
            with self.assertRaises(ValueError):
                make_agent(spec)


class AdaptiveSearchTests(unittest.TestCase):
    def test_disabling_tuning_exactly_reproduces_v1_on_all_development_maps_and_sides(self):
        config = SearchConfig(iterations=16, tree_depth=4, rollout_depth=2)
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                position = replace(load_map(path), to_play=species)
                before = position.to_dict()
                args = dict(config=config, max_plies=200, leaf_evaluator=evaluate)
                original = search(position, rng=random.Random(9), **args)
                fixed = adaptive_search(position, rng=random.Random(9), adaptive=False, **args)
                with self.subTest(map=path.name, species=species):
                    self.assertEqual(fixed.moves, original.moves)
                    self.assertEqual(fixed.candidate_actions, original.candidate_actions)
                    self.assertEqual(fixed.training_metadata(), original.training_metadata())
                    self.assertEqual(position.to_dict(), before)

    def test_seeded_search_is_reproducible_and_tuner_records_only_completed_iterations(self):
        position = distant()
        config = SearchConfig(iterations=80, tree_depth=3, rollout_depth=2)
        results = [adaptive_search(position, config=config, rng=random.Random(7),
                                   parameter_rng=random.Random(2), max_plies=200) for _ in range(2)]
        self.assertEqual(results[0].training_metadata(), results[1].training_metadata())
        self.assertEqual(results[0].moves, results[1].moves)
        tuning = results[0].diagnostics["adaptive"]
        self.assertEqual(tuning["samples"], results[0].iterations)
        self.assertEqual(sum(a["samples"] for a in tuning["arms"]), sum(results[0].visits))
        self.assertGreater(sum(a["samples"] > 0 for a in tuning["arms"]), 1)
        self.assertEqual(results[0].training_metadata()["algorithm"], "contextual_sa_uct_v4")

    def test_aborted_simulation_updates_neither_tree_visits_nor_tuner(self):
        with patch("scripts.mcts_v4.engine._rollout", side_effect=TimeoutError):
            result = adaptive_search(distant(), config=SearchConfig(iterations=16))
        self.assertEqual(result.iterations, 0)
        self.assertEqual(sum(result.visits), 0)
        self.assertEqual(result.diagnostics["adaptive"]["samples"], 0)
        self.assertEqual(result.diagnostics["deadline_stops"], 1)

    def test_batch_changes_every_eight_completed_simulations_and_keeps_v1_first(self):
        depths = []

        def leaf(position, species, rng, config, *args):
            depths.append(config.rollout_depth)
            return RolloutResult(0.0, 0)

        with patch("scripts.mcts_v4.engine._rollout", side_effect=leaf):
            result = adaptive_search(distant(), config=SearchConfig(iterations=16, tree_depth=1),
                                     rng=random.Random(0))
        self.assertEqual(depths[:8], [6] * 8)
        self.assertEqual(len(set(depths[8:])), 1)
        self.assertEqual(sorted(a["samples"] for a in result.diagnostics["adaptive"]["arms"] if a["samples"]), [8, 8])

    def test_exploration_only_uses_real_six_ply_rollouts_with_both_players_and_reproducible_stats(self):
        position = distant()
        before = position.to_dict()
        agents = [make_agent("mcts-v4:tune_rollout=False,iterations=32") for _ in range(2)]
        results = []
        for agent in agents:
            agent.new_game(position, position.to_play, 42)
            with patch("scripts.mcts_v4.engine._rollout", wraps=_rollout) as rollout:
                results.append(agent.choose_moves(position, TurnContext(None, 200)))
            self.assertTrue(rollout.call_args_list)
            self.assertEqual({call.args[3].rollout_depth for call in rollout.call_args_list}, {6})
            self.assertTrue(all(call.args[5] == 200 for call in rollout.call_args_list))
            self.assertEqual(agent.info["adaptive"]["tuned_parameters"], ["exploration"])
            self.assertEqual({a["rollout_depth"] for a in agent.info["adaptive"]["arms"]}, {6})
            self.assertEqual(sum(a["samples"] > 0 for a in agent.info["adaptive"]["arms"]), 3)
            self.assertGreater(agent.info["search"]["rollout_plies"], 0)
            self.assertLessEqual(agent.info["search"]["rollout_depth_max"], 6)
        self.assertEqual(results[0], results[1])
        self.assertEqual(agents[0].info["adaptive"]["arms"], agents[1].info["adaptive"]["arms"])
        self.assertEqual(position.to_dict(), before)

    def test_exploration_only_cap_deadline_and_fixed_control_match_v1(self):
        config = SearchConfig(iterations=16)
        last = replace(distant(), ply=199)
        result = adaptive_search(last, config=config, rng=random.Random(2), tune_rollout=False,
                                 max_plies=200, leaf_evaluator=evaluate)
        tuning = result.diagnostics["adaptive"]
        self.assertEqual({a["rollout_depth"] for a in tuning["arms"]}, {6})
        self.assertEqual({v for v in result.action_values if v is not None}, {-1})
        self.assertEqual(result.diagnostics["rollout_plies"], 0)
        self.assertEqual(result.training_metadata()["algorithm"], "exploration_sa_uct_v4")
        fixed = adaptive_search(last, config=config, rng=random.Random(2), adaptive=False, tune_rollout=False,
                                max_plies=200, leaf_evaluator=evaluate)
        original = search(last, config=config, rng=random.Random(2), max_plies=200, leaf_evaluator=evaluate)
        self.assertEqual(fixed.training_metadata(), original.training_metadata())
        agent = make_agent("mcts-v4:tune_rollout=False")
        moves, fault = safe_choose(agent, distant(), TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(distant().to_game_state(), moves))
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["adaptive"]["tuned_parameters"], ["exploration"])

    def test_chance_is_resampled_and_terminal_scores_stay_exact(self):
        position = Position(1, 2, {(0, 0): Cell(vampires=1), (1, 0): Cell(werewolves=1)})
        result = adaptive_search(position, config=SearchConfig(iterations=600, rollout_depth=0), rng=random.Random(2))
        self.assertEqual(result.visits, [600])
        self.assertAlmostEqual(result.action_values[0], 0.0, delta=0.1)
        last = replace(distant(), ply=199)
        capped = adaptive_search(last, config=SearchConfig(iterations=16), rng=random.Random(2),
                                 max_plies=200, leaf_evaluator=evaluate)
        self.assertEqual({v for v in capped.action_values if v is not None}, {-1})

    def test_finds_a_guaranteed_joint_elimination(self):
        position = Position(3, 3, {(0, 0): Cell(vampires=3), (0, 2): Cell(vampires=3),
                                  (1, 1): Cell(werewolves=4)})
        result = adaptive_search(position, config=SearchConfig(iterations=100, rollout_depth=2), rng=random.Random(0))
        self.assertEqual(get_outcome(simulate_turn(position, result.moves, random.Random(1))).winner, "vampires")
        self.assertEqual(len(result.moves), 2)

    def test_exploration_tuning_keeps_the_simulated_opponent_at_the_base_setting(self):
        seen = []

        def select(node, root_species, exploration, penalties=None):
            seen.append((node.position.to_play == root_species, exploration))
            return _select(node, root_species, exploration, penalties)

        for tune_rollout in (True, False):
            seen.clear()
            with patch("scripts.mcts_v4.engine._select", side_effect=select):
                adaptive_search(distant(), config=SearchConfig(iterations=32, rollout_depth=0),
                                rng=random.Random(0), tuning_batch=1, tune_rollout=tune_rollout)
            self.assertEqual({c for own, c in seen if not own}, {1.4})
            self.assertGreater(len({c for own, c in seen if own}), 1)

    def test_avoids_recruitment_that_allows_a_forced_enemy_kill(self):
        position = Position(3, 3, {(0, 1): Cell(vampires=10), (1, 1): Cell(humans=3),
                                  (2, 1): Cell(werewolves=20)}, rules_profile="brief")
        result = adaptive_search(position, config=SearchConfig(iterations=256, tree_depth=3, rollout_depth=0),
                                 rng=random.Random(7))
        self.assertNotIn((0, 1, 10, 1, 1), result.moves)
        after = simulate_turn(position, result.moves, random.Random(0))
        for reply in generate_candidates(after):
            outcome = get_outcome(simulate_turn(after, reply, random.Random(0)))
            self.assertTrue(outcome is None or outcome.winner != "werewolves")

    def test_memory_deadline_fallback_and_new_game_reset(self):
        position = Position(5, 9, {(1, 2): Cell(vampires=6), (7, 2): Cell(werewolves=8),
                                   (4, 2): Cell(humans=4)}, ply=20)
        history = [(replace(position, ply=p), [(1, 2, 6, 2, 2)]) for p in (12, 16)]
        agent = make_agent("mcts-v4:iterations=8,rollout_depth=2")
        agent.new_game(position, position.to_play, 42)
        initial_rng = agent.parameter_rng.getstate()
        moves, fault = safe_choose(agent, position, TurnContext(None, 200, history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["penalized_actions"], 1)
        self.assertNotEqual(agent.parameter_rng.getstate(), initial_rng)
        agent.new_game(position, position.to_play, 42)
        self.assertIsNone(agent.info)
        self.assertEqual(agent.parameter_rng.getstate(), initial_rng)
        moves, fault = safe_choose(agent, position, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["adaptive"]["samples"], 0)


if __name__ == "__main__":
    unittest.main()
