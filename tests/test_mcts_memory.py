"""Memory must use game context without corrupting rewards or baseline MCTS."""

from dataclasses import replace
from hashlib import sha256
import json
from math import tanh
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from agents.mcts_memory import MemoryMCTSAgent, position_key, quiet_plan
from candidates import supported_turn
from game import Cell
from search import SearchConfig, action_key, evaluate, search
from simulator import Position, get_outcome, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]


def board(*, to_play="vampires", ply=20):
    return Position(5, 9, {(1, 2): Cell(vampires=6), (7, 2): Cell(werewolves=8),
                           (4, 2): Cell(humans=4)}, to_play=to_play, ply=ply)


class ClockTests(unittest.TestCase):
    def test_distant_humans_have_no_value_with_one_ply_left(self):
        position = board()
        value = evaluate(position, "vampires", max_plies=21)
        self.assertAlmostEqual(value, 0.95 * tanh(-2 / (0.6 * 14)))
        self.assertAlmostEqual(value, -evaluate(position, "werewolves", max_plies=21))

    def test_last_ply_recruitment_belongs_to_current_actor_only(self):
        position = Position(1, 3, {(0, 0): Cell(vampires=6), (1, 0): Cell(humans=4),
                                  (2, 0): Cell(werewolves=6)}, ply=20)
        self.assertGreater(evaluate(position, "vampires", max_plies=21), 0)
        self.assertLess(evaluate(replace(position, to_play="werewolves"),
                                 "vampires", max_plies=21), 0)

    def test_cap_and_elimination_are_exact_rewards(self):
        position = board()
        self.assertEqual(evaluate(position, "vampires", max_plies=20), -1)
        self.assertEqual(evaluate(position, "werewolves", max_plies=20), 1)
        empty = replace(position, cells={(0, 0): Cell(vampires=8)})
        self.assertEqual(evaluate(empty, "vampires", max_plies=40), 1)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.position = board()
        self.move = [(1, 2, 6, 2, 2)]
        self.history = [(replace(self.position, ply=12), self.move),
                        (replace(self.position, ply=16), self.move)]

    def test_key_ignores_ply_and_serialization_order_but_keeps_rules_and_actor(self):
        position = self.position
        restored = Position.from_dict(json.loads(json.dumps(position.to_dict())))
        self.assertEqual(position_key(position), position_key(restored))
        self.assertEqual(position_key(position), position_key(replace(
            position, ply=2, cells=dict(reversed(list(position.cells.items()))))))
        for kwargs in ({"to_play": "werewolves"}, {"rules_profile": "brief"},
                       {"columns": 10}, {"cells": {(0, 0): Cell(vampires=7)}}):
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(position_key(position), position_key(replace(position, **kwargs)))
        plan = [(0, 0, 1, 1, 0), (0, 2, 1, 1, 2)]
        self.assertEqual(action_key(plan), action_key(list(reversed(plan))))

    def test_only_repeated_quiet_actions_are_penalized(self):
        agent = MemoryMCTSAgent(iterations=8)
        penalties, count = agent.repetition_penalties(self.position, self.history)
        self.assertEqual(count, 2)
        self.assertEqual(penalties, {action_key(self.move): 0.3})
        self.assertEqual(agent.repetition_penalties(self.position, self.history[:1])[0], {})
        self.assertFalse(quiet_plan(self.position, []))
        near = Position(2, 3, {(0, 0): Cell(vampires=6), (1, 0): Cell(humans=4),
                               (1, 1): Cell(werewolves=8)})
        self.assertFalse(quiet_plan(near, [(0, 0, 6, 1, 0)]))
        self.assertFalse(quiet_plan(near, [(0, 0, 6, 1, 1)]))

    def test_recorded_server_loop_activates_memory(self):
        fixture = json.loads((ROOT / "examples" / "mcts_losing_loop.json").read_text())
        position = Position.from_dict(fixture["state"])
        history = [(Position.from_dict(t["state"]), t["action"]) for t in fixture["history"]]
        agent = MemoryMCTSAgent(iterations=8)
        moves, fault = safe_choose(agent, position, TurnContext(None, fixture["max_plies"], history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["population_margin"], -2)
        self.assertEqual(agent.info["repetitions"], 2)
        self.assertEqual(agent.info["penalized_actions"], 1)

    def test_wrong_actor_rules_future_timeout_and_old_history_are_ignored(self):
        agent = MemoryMCTSAgent(iterations=8, history_window=2)
        for previous in (replace(self.position, ply=30),
                         replace(self.position, ply=10, to_play="werewolves"),
                         replace(self.position, ply=10, rules_profile="brief")):
            with self.subTest(previous=previous):
                self.assertEqual(agent.repetition_penalties(self.position, [(previous, self.move)] * 2), ({}, 0))
        self.assertEqual(agent.repetition_penalties(self.position,
                         self.history + [(replace(self.position, ply=18), [])] * 2)[0], {})

    def test_leading_and_tied_players_keep_repeated_actions(self):
        for enemy in (5, 6, 8):
            cells = dict(self.position.cells)
            cells[(7, 2)] = Cell(werewolves=enemy)
            position = replace(self.position, cells=cells)
            history = [(replace(position, ply=ply), self.move) for ply in (12, 16)]
            agent = MemoryMCTSAgent(iterations=8, clock=False)
            agent.choose_moves(position, TurnContext(None, 40, history))
            with self.subTest(enemy=enemy):
                self.assertEqual(agent.info["penalized_actions"], int(enemy > 6))

    def test_memory_also_works_when_assigned_werewolves(self):
        position = replace(self.position, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in self.position.cells.items()})
        history = [(replace(position, ply=ply), self.move) for ply in (12, 16)]
        agent = MemoryMCTSAgent(iterations=8)
        moves, fault = safe_choose(agent, position, TurnContext(None, 40, history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["penalized_actions"], 1)
        self.assertEqual(agent.info["population_margin"], -2)

    def test_disabled_features_reproduce_original_for_both_players(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        for species in ("vampires", "werewolves"):
            position = replace(initial, to_play=species)
            baseline = make_agent("mcts:iterations=48")
            variant = make_agent("mcts-memory:iterations=48,memory=False,clock=False")
            for agent in (baseline, variant):
                agent.new_game(position, species, 81)
            context = TurnContext(None, 40)
            with self.subTest(species=species):
                self.assertEqual(baseline.choose_moves(position, context), variant.choose_moves(position, context))
                self.assertEqual(baseline.info["iterations"], variant.info["iterations"])
                self.assertEqual(baseline.rng.getstate(), variant.rng.getstate())

    def test_expired_deadline_and_reset_remain_safe(self):
        agent = MemoryMCTSAgent(iterations=100000)
        moves, fault = safe_choose(agent, self.position,
                                   TurnContext(time.perf_counter() - 1, 40, self.history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(self.position.to_game_state(), moves))
        self.assertEqual(agent.info["iterations"], 0)
        self.assertTrue(agent.info["fallback"])
        agent.new_game(self.position, "vampires", 42)
        self.assertIsNone(agent.info)
        agent.config = SearchConfig(iterations=8)
        agent.choose_moves(self.position, TurnContext(None, 40))
        self.assertEqual(agent.info["penalized_actions"], 0)

    def test_invalid_parameters_fail_early(self):
        for kwargs in ({"memory": "False"}, {"clock": 1}, {"penalty": float("nan")},
                       {"penalty": -1}, {"repetition_visits": 0}, {"history_window": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MemoryMCTSAgent(**kwargs)


class SearchHookTests(unittest.TestCase):
    def test_original_search_matches_reference_revision(self):
        # Captured from untouched main 352ebf4, then compared with this branch:
        # four maps, both species, seeds 0/42, 64 iterations, cap 40.
        # Round values to avoid insignificant libm differences across platforms.
        records = []
        for name in ("demo", "endgame", "recruitment", "tactics"):
            path = ROOT / "maps" / f"{name}.xml"
            for species in ("vampires", "werewolves"):
                for seed in (0, 42):
                    result = search(replace(load_map(path), to_play=species),
                                    config=SearchConfig(iterations=64),
                                    rng=random.Random(seed), max_plies=40)
                    metadata = result.training_metadata()
                    metadata["action_values"] = [None if value is None else round(value, 12)
                                                 for value in result.action_values]
                    records.append([result.moves, result.candidate_actions, metadata])
        self.assertEqual(sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
                         "5743ae940fbc61f3fbd7d65e253f9907813ad867503b5703c7f160f4084dc8b6")

    def test_selection_penalties_do_not_change_terminal_or_chance_rewards(self):
        position = Position(1, 2, {(0, 0): Cell(vampires=1), (1, 0): Cell(werewolves=1)})
        config = SearchConfig(iterations=1200, rollout_depth=0)
        kwargs = dict(config=config, max_plies=20)
        baseline = search(position, rng=random.Random(2), **kwargs)
        biased = search(position, rng=random.Random(2), root_penalties={action_key(baseline.moves): 0.3},
                        leaf_evaluator=evaluate, **kwargs)
        self.assertEqual(baseline.training_metadata(), biased.training_metadata())
        self.assertAlmostEqual(biased.action_values[0], 0, delta=0.07)

    def test_repetition_bias_can_change_choice_without_altering_leaf_values(self):
        # All leaves tie: a root preference should break the tie, not fake a reward.
        position = board()
        config = SearchConfig(iterations=96, tree_depth=1, rollout_depth=0)
        zero = lambda *args, **kwargs: 0.0
        baseline = search(position, config=config, rng=random.Random(4), leaf_evaluator=zero)
        biased = search(position, config=config, rng=random.Random(4), leaf_evaluator=zero,
                        root_penalties={action_key(baseline.moves): 0.3})
        self.assertNotEqual(baseline.moves, biased.moves)
        self.assertEqual(sum(biased.visits), biased.iterations)
        self.assertTrue(all(v is None or v == 0 for v in biased.action_values))

    def test_winning_joint_attack_is_preserved(self):
        position = Position(3, 3, {(0, 0): Cell(vampires=3), (0, 2): Cell(vampires=3),
                                  (1, 1): Cell(werewolves=4)}, ply=20)
        agent = MemoryMCTSAgent(iterations=100, rollout_depth=2)
        agent.new_game(position, "vampires", 0)
        moves = agent.choose_moves(position, TurnContext(None, 40))
        self.assertEqual(get_outcome(simulate_turn(position, moves, random.Random(1))).winner, "vampires")

    def test_interrupted_custom_evaluation_adds_no_visits(self):
        with patch("search.evaluate", side_effect=TimeoutError) as leaf:
            result = search(board(), config=SearchConfig(iterations=8, rollout_depth=0),
                            leaf_evaluator=leaf)
        self.assertEqual(result.iterations, 0)

    def test_penalties_are_validated(self):
        for value in (-1, float("nan"), float("inf"), "0.3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                search(board(), root_penalties={(): value})


if __name__ == "__main__":
    unittest.main()
