"""Tactical rollout, chance, cutoff, deadline and v1-control regressions."""

from dataclasses import replace
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import Agent, TurnContext, make_agent, safe_choose
from agents.mcts_memory import MemoryMCTSAgent
from agents.mcts_v2 import MCTSV1Agent, MCTSV2Agent
from candidates import supported_turn
from game import Cell
from playbook import play_turn
from rollouts import CoordinatedRollout, coordinated_moves
from search import SearchConfig, accumulate_diagnostics, evaluate, search
from simulator import Position, get_outcome, load_map, simulate_turn
from tournament import play_match

ROOT = Path(__file__).resolve().parents[1]


def swap(position):
    return replace(position, to_play="werewolves", cells={
        p: Cell(c.humans, c.werewolves, c.vampires) for p, c in position.cells.items()})


class CoordinatedPlanTests(unittest.TestCase):
    def test_two_groups_recruit_at_different_locations_in_one_turn_for_both_sides(self):
        initial = Position(5, 7, {(0, 0): Cell(vampires=3), (0, 3): Cell(vampires=4),
                                  (1, 0): Cell(humans=2), (1, 3): Cell(humans=3),
                                  (6, 2): Cell(werewolves=8)})
        for position in (initial, swap(initial)):
            moves = coordinated_moves(position, random.Random(0), variation=0)
            self.assertEqual(len({move[:2] for move in moves}), 2)
            final = simulate_turn(position, moves, random.Random(0))
            self.assertEqual(sum(getattr(c, position.to_play) for c in final.cells.values()), 12)

    def test_joint_attack_wins_when_neither_group_could_win_alone(self):
        initial = Position(3, 3, {(0, 0): Cell(vampires=3), (0, 2): Cell(vampires=3),
                                  (1, 1): Cell(werewolves=4)})
        for position in (initial, swap(initial)):
            moves = coordinated_moves(position, random.Random(0), variation=0)
            self.assertEqual(len(moves), 2)
            self.assertEqual(get_outcome(simulate_turn(position, moves, random.Random(0))).winner,
                             position.to_play)

    def test_groups_can_jointly_recruit_a_village_too_large_for_either_group(self):
        position = Position(5, 7, {(0, 0): Cell(vampires=4), (0, 2): Cell(vampires=4),
                                   (1, 1): Cell(humans=6), (6, 4): Cell(werewolves=10)})
        moves = coordinated_moves(position, random.Random(0), variation=0)
        final = simulate_turn(position, moves, random.Random(0))
        self.assertEqual(final.cells[(1, 1)].vampires, 14)

    def test_split_recruits_two_villages_simultaneously(self):
        position = Position(3, 7, {(0, 1): Cell(vampires=7), (1, 0): Cell(humans=3),
                                   (1, 2): Cell(humans=4), (6, 1): Cell(werewolves=5)})
        moves = coordinated_moves(position, random.Random(0), variation=0)
        final = simulate_turn(position, moves, random.Random(0))
        self.assertEqual(len(moves), 2)
        self.assertEqual(sum(c.vampires for c in final.cells.values()), 14)

    def test_overflow_proposals_are_rejected_and_a_legal_move_survives(self):
        position = Position(5, 7, {(0, 0): Cell(vampires=200), (0, 2): Cell(vampires=100),
                                   (1, 1): Cell(humans=200), (6, 4): Cell(werewolves=10)})
        moves = coordinated_moves(position, random.Random(0), variation=0)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        simulate_turn(position, moves, random.Random(0))

    def test_script_planning_checks_deadlines_inside_its_loops(self):
        position = load_map(ROOT / "maps/demo.xml")
        with patch("playbook.check_deadline", side_effect=[None] * 5 + [TimeoutError]):
            with self.assertRaises(TimeoutError):
                play_turn(position, {}, deadline=time.perf_counter() + 10)


class RolloutTests(unittest.TestCase):
    def test_tactical_extension_includes_the_enemy_response_after_recruitment(self):
        # Our 8 just converted 5 humans. The opponent's 20 surely kill our 13.
        position = Position(1, 3, {(1, 0): Cell(vampires=13), (2, 0): Cell(werewolves=20)},
                            to_play="werewolves")
        config = SearchConfig(rollout_depth=0)
        short = CoordinatedRollout(extension_depth=0)(position, "vampires", random.Random(0),
                                                      config, None, 200, evaluate)
        extended = CoordinatedRollout(extension_depth=1)(position, "vampires", random.Random(0),
                                                         config, None, 200, evaluate)
        self.assertEqual(short.plies, 0)
        self.assertGreater(short.value, -1)
        self.assertEqual((extended.value, extended.plies, extended.extension_plies), (-1, 1, 1))

    def test_a_quiet_position_does_not_get_extra_tactical_plies(self):
        position = Position(1, 20, {(0, 0): Cell(vampires=6), (19, 0): Cell(werewolves=8)})
        result = CoordinatedRollout(extension_depth=4)(position, "vampires", random.Random(0),
                                                       SearchConfig(rollout_depth=2), None, 200, evaluate)
        self.assertEqual((result.plies, result.extension_plies), (2, 0))

    def test_extension_depth_is_a_hard_cap_even_if_contact_continues(self):
        position = Position(2, 2, {(0, 0): Cell(vampires=6), (1, 1): Cell(werewolves=8)})
        # Isolate the extension controller from battle luck with a legal shuttle.
        def shuttle(current, moves, rng):
            return replace(current, to_play=("werewolves" if current.to_play == "vampires"
                                              else "vampires"), ply=current.ply + 1)
        with patch("rollouts.simulate_turn", side_effect=shuttle):
            result = CoordinatedRollout(extension_depth=3, detect_loops=False)(
                position, "vampires", random.Random(0), SearchConfig(rollout_depth=2), None, 200, evaluate)
        self.assertEqual((result.plies, result.extension_plies), (5, 3))

    def test_game_cap_and_terminal_rewards_override_heuristics(self):
        position = Position(1, 20, {(0, 0): Cell(vampires=6), (19, 0): Cell(werewolves=8)}, ply=99)
        result = CoordinatedRollout()(position, "vampires", random.Random(0),
                                       SearchConfig(rollout_depth=12), None, 100, evaluate)
        self.assertEqual((result.value, result.plies), (-1, 1))
        draw = replace(position, cells={(0, 0): Cell(vampires=8), (19, 0): Cell(werewolves=8)}, ply=100)
        self.assertEqual(CoordinatedRollout()(draw, "vampires", random.Random(0),
                                              SearchConfig(), None, 100, evaluate).value, 0)

    def test_random_battle_outcomes_are_sampled_instead_of_expected_battles(self):
        position = Position(1, 2, {(0, 0): Cell(vampires=1), (1, 0): Cell(werewolves=1)})
        config = SearchConfig(rollout_depth=1)
        policy = CoordinatedRollout(extension_depth=0, variation=0)
        values = [policy(position, "vampires", random.Random(seed), config, None, 20).value
                  for seed in range(800)]
        self.assertEqual(set(values), {-1, 0, 1})
        self.assertAlmostEqual(sum(values) / len(values), 0, delta=0.09)

    def test_rollout_loop_stops_with_a_heuristic_and_does_not_invent_a_draw(self):
        position = Position(1, 5, {(0, 0): Cell(vampires=6), (4, 0): Cell(werewolves=8)})
        def shuttle(current, rng, **kwargs):
            (x, y), count = current.to_game_state().groups()[0]
            return [(x, y, count, {0: 1, 1: 0, 3: 4, 4: 3}[x], y)]
        with patch("rollouts.coordinated_moves", side_effect=shuttle):
            result = CoordinatedRollout()(position, "vampires", random.Random(0),
                                           SearchConfig(rollout_depth=20), None, 100, evaluate)
        self.assertEqual((result.plies, result.loop_cutoffs), (4, 1))
        self.assertEqual(result.value, evaluate(position, "vampires", max_plies=100))
        self.assertLess(result.value, 0)


class SearchIntegrationTests(unittest.TestCase):
    def test_v1_matches_the_current_memory_agent_on_all_bundled_maps(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                position = replace(load_map(path), to_play=species)
                for seed in (0, 42):
                    agents = [MemoryMCTSAgent(iterations=24), MCTSV1Agent(iterations=24)]
                    for agent in agents:
                        agent.new_game(position, species, seed)
                    moves = [agent.choose_moves(position, TurnContext(None, 200)) for agent in agents]
                    with self.subTest(map=path.name, species=species, seed=seed):
                        self.assertEqual(moves[0], moves[1])
                        self.assertEqual(agents[0].config, agents[1].config)

    def test_all_rollout_upgrades_can_be_disabled_for_a_controlled_ablation(self):
        position = load_map(ROOT / "maps/demo.xml")
        config = SearchConfig(iterations=64)
        original = search(position, config=config, rng=random.Random(9), max_plies=200,
                          leaf_evaluator=evaluate, collect_diagnostics=True)
        disabled = search(position, config=config, rng=random.Random(9), max_plies=200,
                          leaf_evaluator=evaluate, collect_diagnostics=True,
                          rollout_policy=CoordinatedRollout(extension_depth=0, coordinated=False,
                                                            variation=0, detect_loops=False))
        self.assertEqual(original.moves, disabled.moves)
        self.assertEqual(original.training_metadata(), disabled.training_metadata())

    def test_v2_is_reproducible_and_preserves_the_input_board(self):
        position = load_map(ROOT / "maps/demo.xml")
        before = position.to_dict()
        agents = [make_agent("mcts-v2:iterations=32") for _ in range(2)]
        for agent in agents:
            agent.new_game(position, "vampires", 9)
        moves = [agent.choose_moves(position, TurnContext(None, 200)) for agent in agents]
        self.assertEqual(moves[0], moves[1])
        self.assertEqual(position.to_dict(), before)
        for key in ("iterations", "rollouts", "rollout_plies", "tree_depth_total", "extension_plies"):
            self.assertEqual(agents[0].info["search"][key], agents[1].info["search"][key])
        self.assertEqual(agents[0].config.rollout_depth, 12)

    def test_an_expired_deadline_returns_a_legal_fallback_without_fault(self):
        position = load_map(ROOT / "maps/demo.xml")
        agent = MCTSV2Agent(iterations=100000)
        moves, fault = safe_choose(agent, position, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["iterations"], 0)
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["search"]["deadline_stops"], 1)

    def test_interrupted_v2_rollout_does_not_back_up_an_unfinished_iteration(self):
        position = load_map(ROOT / "maps/demo.xml")
        with patch("rollouts.simulate_turn", side_effect=TimeoutError):
            result = search(position, config=SearchConfig(iterations=8),
                            rollout_policy=CoordinatedRollout(), collect_diagnostics=True)
        self.assertEqual(result.iterations, 0)
        self.assertEqual(sum(result.visits), 0)
        self.assertEqual(result.diagnostics["rollouts"], 0)
        self.assertEqual(result.diagnostics["deadline_stops"], 1)

    def test_live_budget_interrupts_v2_on_generated_maps_without_faults(self):
        from mapgen import random_map
        for family in ("medium", "large"):
            for seed in (0, 1):
                position = random_map(random.Random(seed), family)
                agent = MCTSV2Agent(iterations=100000)
                agent.new_game(position, position.to_play, seed)
                started = time.perf_counter()
                moves, fault = safe_choose(agent, position, TurnContext(started + 0.03, 200))
                with self.subTest(family=family, seed=seed):
                    self.assertIsNone(fault)
                    self.assertTrue(supported_turn(position.to_game_state(), moves))
                    self.assertLess(agent.info["iterations"], 100000)
                    self.assertLess(time.perf_counter() - started, 0.5)

    def test_diagnostics_do_not_change_seeded_search_results_or_training_labels(self):
        position = load_map(ROOT / "maps/demo.xml")
        kwargs = dict(config=SearchConfig(iterations=32), rollout_policy=CoordinatedRollout())
        plain = search(position, rng=random.Random(42), **kwargs)
        measured = search(position, rng=random.Random(42), collect_diagnostics=True, **kwargs)
        self.assertEqual(plain.moves, measured.moves)
        self.assertEqual(plain.training_metadata(), measured.training_metadata())
        d = measured.diagnostics
        self.assertEqual(d["iterations"], measured.iterations)
        self.assertLessEqual(d["tree_depth_max"], 12)
        self.assertLessEqual(d["rollout_depth_max"], 10)  # This test uses the base depth 6, plus 4.
        self.assertGreater(d["rollouts"], 0)
        self.assertGreater(d["search_cpu_seconds"], 0)

    def test_aggregates_use_weighted_depth_totals_and_maxima(self):
        aggregate = {}
        accumulate_diagnostics(aggregate, {"iterations": 2, "tree_depth_total": 6, "tree_depth_max": 4})
        accumulate_diagnostics(aggregate, {"decisions": 3, "iterations": 10,
                                           "tree_depth_total": 20, "tree_depth_max": 3})
        self.assertEqual(aggregate["decisions"], 4)
        self.assertEqual(aggregate["iterations"], 12)
        self.assertEqual(aggregate["tree_depth_total"], 26)
        self.assertEqual(aggregate["tree_depth_max"], 4)

    def test_bad_rollout_parameters_are_rejected(self):
        for kwargs in ({"extension_depth": -1}, {"extension_depth": True}, {"rollout_width": 0},
                       {"variation": float("nan")}, {"variation": 1.1}, {"coordinated": "yes"},
                       {"detect_loops": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MCTSV2Agent(**kwargs)

    def test_runner_preserves_slow_turn_state_rng_and_wall_cpu_diagnostics(self):
        class MeasuredAgent(Agent):
            def __init__(self):
                self.rng = random.Random(42)
                self.info = {"search": {"iterations": 2, "tree_depth_total": 4,
                                         "tree_depth_max": 2, "rollouts": 2, "rollout_plies": 12}}

            def choose_moves(self, position, context):
                (x, y), count = position.to_game_state().groups()[0]
                return [(x, y, count, x + (1 if x == 0 else -1), y)]

        position = Position(1, 5, {(0, 0): Cell(vampires=6), (4, 0): Cell(werewolves=8)})
        with patch("tournament.make_agent", side_effect=[MeasuredAgent(), MeasuredAgent()]), \
                patch("tournament.time.perf_counter", side_effect=[0, 3, 4, 4.1]), \
                patch("tournament.time.process_time", side_effect=[0, 0.1, 0.2, 0.3]):
            result = play_match(position, {"vampires": "fixture", "werewolves": "fixture"},
                                seed=0, max_plies=2, move_time=2, margin=0.5)
        record = result["stats"]["vampires"]
        self.assertEqual(record["timeouts"], 1)
        self.assertEqual(record["search"]["decisions"], 1)
        self.assertEqual(record["search"]["tree_depth_total"], 4)
        trace = record["slow_decisions"][0]
        self.assertEqual(trace["wall_seconds"], 3)
        self.assertAlmostEqual(trace["cpu_seconds"], 0.1)
        self.assertEqual(trace["state"], position.to_dict())
        self.assertEqual(trace["rng_before"], random.Random(42).getstate())


if __name__ == "__main__":
    unittest.main()
