"""Geometric witnesses, conservative contact models and unchanged V6 controls."""

from dataclasses import replace
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from game import Cell
from scripts.mcts_v8 import InterceptionMCTSAgent
from scripts.mcts_v8.interception import Budget, PairContact, analyse, merge_escape
from search import search
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Position.from_dict(json.loads((ROOT / "examples/mcts_v7_controlled_snapshot.json").read_text())["state"])
CORRIDOR = Position(1, 7, {(2, 0): Cell(vampires=6), (6, 0): Cell(werewolves=2)})


class ContactTests(unittest.TestCase):
    def test_recorded_merge_witness_is_legal_fast_and_outside_our_reachable_sets(self):
        witness = merge_escape(SNAPSHOT, (11, 2), budget=Budget(None, 4000))
        self.assertEqual(witness["enemy_turns"], 6)
        self.assertEqual(witness["merged_count"], 16)
        position = SNAPSHOT
        rng = random.Random(0)
        for turn, enemy_moves in enumerate(witness["enemy_moves"], 1):
            position = simulate_turn(position, [(29 - turn, 0, 16, 28 - turn, 0)], rng)
            position = simulate_turn(position, enemy_moves, rng)
        self.assertEqual(position.cells[tuple(witness["meeting"])].werewolves, 16)
        scores, details = analyse(SNAPSHOT, max_plies=200)
        self.assertFalse(scores)
        self.assertEqual(details["status"], "no_verified_contact")
        self.assertTrue(all(r["status"] == "merge_escape_witness" for r in details["pairs"]))

    def test_witness_cannot_ignore_a_nearer_own_army_blocking_village_or_clock(self):
        near = replace(SNAPSHOT, cells={**SNAPSHOT.cells, (5, 5): Cell(vampires=1)})
        blocked = replace(SNAPSHOT, cells={**SNAPSHOT.cells,
                          **{(x, y): Cell(humans=1) for x in (5, 6) for y in (1, 2)}})
        for position, cap in ((near, 200), (blocked, 200), (SNAPSHOT, 60)):
            with self.subTest(position=position, cap=cap):
                self.assertIsNone(merge_escape(position, (11, 2), budget=Budget(None, 4000), max_plies=cap))

    def test_contact_model_distinguishes_cornering_from_escaping_within_the_horizon(self):
        solver = PairContact(CORRIDOR, (2, 0), (6, 0), budget=Budget(None, 4000), depth=8)
        self.assertEqual(solver.solve((3, 0), (6, 0))[0], "contact")
        self.assertEqual(solver.solve((1, 0), (6, 0))[0], "avoid")
        scores, details = analyse(CORRIDOR)
        self.assertEqual(details["status"], "guided")
        self.assertIn(((2, 0, 6, 3, 0),), scores)
        self.assertNotIn(((2, 0, 6, 1, 0),), scores)

    def test_recruitment_and_moving_third_party_are_unresolved_not_proven_catches(self):
        village = Position(1, 6, {(0, 0): Cell(vampires=6), (4, 0): Cell(werewolves=2),
                                  (5, 0): Cell(humans=1)})
        solver = PairContact(village, (0, 0), (4, 0), budget=Budget(None, 4000), depth=8)
        self.assertEqual(solver.solve((1, 0), (4, 0))[0], "unknown")
        third = Position(3, 7, {(0, 1): Cell(vampires=6), (4, 1): Cell(werewolves=2),
                                (5, 1): Cell(werewolves=6)})
        solver = PairContact(third, (0, 1), (4, 1), budget=Budget(None, 4000), depth=8)
        self.assertEqual(solver.solve((1, 1), (4, 1))[0], "unknown")

    def test_partial_comparisons_discard_guidance_and_cap_limits_contact_horizon(self):
        scores, info = analyse(CORRIDOR, nodes=1)
        self.assertFalse(scores)
        self.assertEqual(info["status"], "node_limit")
        scores, _ = analyse(CORRIDOR, deadline=time.perf_counter() - 1)
        self.assertFalse(scores)
        scores, _ = analyse(CORRIDOR, max_plies=2)
        self.assertFalse(scores)

    def test_species_swap_preserves_contact_analysis_and_input_is_immutable(self):
        before = CORRIDOR.to_dict()
        swapped = replace(CORRIDOR, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in CORRIDOR.cells.items()})
        self.assertEqual(analyse(CORRIDOR), analyse(swapped))
        self.assertEqual(CORRIDOR.to_dict(), before)


class AgentTests(unittest.TestCase):
    def test_disabled_feature_has_exact_v6_moves_targets_and_rng_on_both_species(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                position = replace(load_map(path), to_play=species)
                original = make_agent("mcts-v6:iterations=24")
                control = make_agent("mcts-v8:interceptions=False,iterations=24")
                captured = []

                def observe(*args, **kwargs):
                    result = search(*args, **kwargs)
                    captured.append(result)
                    return result

                for agent in (original, control):
                    agent.new_game(position, species, 42)
                with self.subTest(map=path.name, species=species):
                    with patch("scripts.mcts_v5.agent.search", side_effect=observe):
                        a = original.choose_moves(position, TurnContext(None, 200))
                        b = control.choose_moves(position, TurnContext(None, 200))
                    self.assertEqual(a, b)
                    self.assertEqual(captured[0].training_metadata(), captured[1].training_metadata())
                    self.assertEqual(original.rng.getstate(), control.rng.getstate())

    def test_merge_escape_falls_back_to_exact_v6_at_fixed_iterations(self):
        original, candidate = make_agent("mcts-v6:iterations=32"), make_agent("mcts-v8:iterations=32")
        for agent in (original, candidate):
            agent.new_game(SNAPSHOT, SNAPSHOT.to_play, 7)
        a = original.choose_moves(SNAPSHOT, TurnContext(None, 200))
        b = candidate.choose_moves(SNAPSHOT, TurnContext(None, 200))
        self.assertEqual(a, b)
        self.assertEqual(original.rng.getstate(), candidate.rng.getstate())
        self.assertFalse(candidate.info["interception_guided"])

    def test_guided_search_keeps_stochastic_simulation_v6_values_and_all_actions(self):
        agent = InterceptionMCTSAgent(iterations=32)
        agent.new_game(CORRIDOR, CORRIDOR.to_play, 3)
        captured = []

        def observe(*args, **kwargs):
            result = search(*args, **kwargs)
            captured.append((result, kwargs))
            return result

        with patch("scripts.mcts_v5.agent.search", side_effect=observe):
            moves, fault = safe_choose(agent, CORRIDOR, TurnContext(None, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(CORRIDOR.to_game_state(), moves))
        self.assertTrue(agent.info["interception_guided"])
        self.assertEqual(agent.info["penalized_actions"], 0)
        self.assertEqual(captured[0][0].iterations, 32)
        self.assertIn([(2, 0, 6, 1, 0)], captured[0][0].candidate_actions)
        self.assertGreater(captured[0][1]["root_penalties"][((2, 0, 6, 1, 0),)], 0)
        self.assertEqual(agent.leaf_value(CORRIDOR, "vampires", max_plies=200),
                         make_agent("mcts-v6").leaf_value(CORRIDOR, "vampires", max_plies=200))

    def test_expired_deadline_and_configuration_validation(self):
        agent = InterceptionMCTSAgent(iterations=100000)
        moves, fault = safe_choose(agent, CORRIDOR, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(CORRIDOR.to_game_state(), moves))
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["iterations"], 0)
        for config in ({"interceptions": 1}, {"intercept_nodes": 0}, {"intercept_depth": 17},
                       {"intercept_depth": True}, {"intercept_weight": float("nan")},
                       {"intercept_time": 0}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                InterceptionMCTSAgent(**config)


if __name__ == "__main__":
    unittest.main()
