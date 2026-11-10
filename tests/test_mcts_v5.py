"""Recruitment value ablation, V1 parity, recorded stall and deadline safety."""

from dataclasses import replace
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from game import Cell, distance
from scripts.mcts_v5 import FeasibleMCTSAgent
from scripts.mcts_v5.value import feasible_evaluate
from search import SearchConfig, evaluate, search
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]


def board():
    return Position(5, 9, {(0, 2): Cell(vampires=6), (8, 2): Cell(werewolves=8),
                           (1, 2): Cell(humans=20), (4, 2): Cell(humans=4)}, ply=20)


class FeasibilityValueTests(unittest.TestCase):
    def test_oversized_village_is_removed_from_potential_and_normalization_only(self):
        position = board()
        before = position.to_dict()
        without_large = replace(position, cells={p: c for p, c in position.cells.items() if c.humans != 20})
        for species in ("vampires", "werewolves"):
            self.assertEqual(feasible_evaluate(position, species, max_plies=200),
                             evaluate(without_large, species, max_plies=200))
            self.assertNotEqual(feasible_evaluate(position, species), evaluate(position, species))
        self.assertEqual(position.to_dict(), before)

    def test_village_is_kept_if_either_total_can_recruit_including_equality_and_merging(self):
        # Neither individual vampire group can recruit six, but their total can.
        split = Position(4, 8, {(0, 0): Cell(vampires=3), (0, 3): Cell(vampires=3),
                                (7, 0): Cell(werewolves=2), (1, 1): Cell(humans=6)})
        for position in (split, replace(split, cells={**split.cells, (1, 1): Cell(humans=5)}),
                         replace(board(), cells={**board().cells, (8, 2): Cell(werewolves=20)})):
            for species in ("vampires", "werewolves"):
                self.assertEqual(feasible_evaluate(position, species, max_plies=200),
                                 evaluate(position, species, max_plies=200))

    def test_feasibility_is_recomputed_after_population_growth(self):
        position = board()
        grown = replace(position, cells={**position.cells, (0, 2): Cell(vampires=20)})
        self.assertNotEqual(feasible_evaluate(position, "vampires"), evaluate(position, "vampires"))
        self.assertEqual(feasible_evaluate(grown, "vampires"), evaluate(grown, "vampires"))

    def test_species_symmetry_and_opposite_perspective(self):
        position = board()
        swapped = replace(position, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in position.cells.items()})
        self.assertEqual(feasible_evaluate(position, "vampires", max_plies=80),
                         feasible_evaluate(swapped, "werewolves", max_plies=80))
        self.assertAlmostEqual(feasible_evaluate(position, "vampires", max_plies=80),
                               -feasible_evaluate(position, "werewolves", max_plies=80))

    def test_terminal_elimination_and_turn_cap_keep_exact_rewards(self):
        position = board()
        for cells, expected in (({(0, 0): Cell(vampires=6), (1, 0): Cell(humans=20)}, 1),
                                ({(0, 0): Cell(werewolves=6), (1, 0): Cell(humans=20)}, -1),
                                ({(1, 0): Cell(humans=20)}, 0)):
            self.assertEqual(feasible_evaluate(replace(position, cells=cells), "vampires"), expected)
        self.assertEqual(feasible_evaluate(position, "vampires", max_plies=20), -1)
        self.assertEqual(feasible_evaluate(position, "werewolves", max_plies=20), 1)
        tied = replace(position, cells={**position.cells, (0, 2): Cell(vampires=8)})
        self.assertEqual(feasible_evaluate(tied, "vampires", max_plies=20), 0)

    def test_existing_reachability_clock_still_excludes_distant_small_villages(self):
        position = replace(board(), cells={(0, 0): Cell(vampires=6), (8, 4): Cell(werewolves=8),
                                           (4, 2): Cell(humans=4), (1, 1): Cell(humans=20)})
        bare = replace(position, cells={p: c for p, c in position.cells.items() if not c.humans})
        self.assertEqual(feasible_evaluate(position, "vampires", max_plies=21),
                         evaluate(bare, "vampires", max_plies=21))

    def test_deadlines_are_checked_before_and_during_filtering(self):
        with self.assertRaises(TimeoutError):
            feasible_evaluate(board(), "vampires", deadline=time.perf_counter() - 1)
        with patch("scripts.mcts_v5.value.check_deadline", side_effect=[None, None, TimeoutError]):
            with self.assertRaises(TimeoutError):
                feasible_evaluate(board(), "vampires")


class V5AgentTests(unittest.TestCase):
    def test_defaults_match_v1_and_bad_options_fail_early(self):
        v1, v5 = make_agent("mcts-v1"), make_agent("mcts-v5")
        self.assertIsInstance(v5, FeasibleMCTSAgent)
        self.assertEqual(v5.config, v1.config)
        for attr in ("memory", "clock", "repetition_visits", "history_window", "penalty"):
            self.assertEqual(getattr(v5, attr), getattr(v1, attr))
        for value in (1, "False", None):
            with self.assertRaises(ValueError):
                FeasibleMCTSAgent(feasibility=value)

    def test_disabled_feature_exactly_reproduces_v1_on_development_maps_both_species_and_clocks(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                for clock in (True, False):
                    position = replace(load_map(path), to_play=species)
                    v1 = make_agent(f"mcts-v1:iterations=24,clock={clock}")
                    v5 = make_agent(f"mcts-v5:iterations=24,clock={clock},feasibility=False")
                    for agent in (v1, v5):
                        agent.new_game(position, species, 9)
                    captured = []

                    def observe(*args, **kwargs):
                        result = search(*args, **kwargs)
                        captured.append(result)
                        return result

                    with self.subTest(map=path.name, species=species, clock=clock):
                        with patch("agents.mcts_memory.search", side_effect=observe):
                            original = v1.choose_moves(position, TurnContext(None, 40))
                        with patch("scripts.mcts_v5.agent.search", side_effect=observe):
                            control = v5.choose_moves(position, TurnContext(None, 40))
                        self.assertEqual(control, original)
                        self.assertEqual(captured[0].candidate_actions, captured[1].candidate_actions)
                        self.assertEqual(captured[0].training_metadata(), captured[1].training_metadata())
                        self.assertEqual(v1.rng.getstate(), v5.rng.getstate())

    def test_clock_option_only_controls_leaf_clock_and_preserves_game_cap(self):
        position = board()
        timed, unclocked = FeasibleMCTSAgent(), FeasibleMCTSAgent(clock=False)
        self.assertEqual(timed.leaf_value(position, "vampires", max_plies=20), -1)
        self.assertEqual(unclocked.leaf_value(position, "vampires", max_plies=20),
                         feasible_evaluate(position, "vampires"))
        with patch("scripts.mcts_v5.agent.search", wraps=search) as call:
            unclocked.choose_moves(position, TurnContext(None, 21))
        self.assertEqual(call.call_args.kwargs["max_plies"], 21)

    def test_recorded_losing_history_still_activates_memory_and_reset_clears_info(self):
        fixture = json.loads((ROOT / "examples/mcts_losing_loop.json").read_text())
        position = Position.from_dict(fixture["state"])
        history = [(Position.from_dict(t["state"]), t["action"]) for t in fixture["history"]]
        agent = FeasibleMCTSAgent(iterations=8)
        moves, fault = safe_choose(agent, position, TurnContext(None, fixture["max_plies"], history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["population_margin"], -2)
        self.assertEqual(agent.info["repetitions"], 2)
        self.assertEqual(agent.info["penalized_actions"], 1)
        agent.new_game(position, "vampires", 42)
        self.assertIsNone(agent.info)

    def test_expired_search_returns_legal_fallback_without_a_fault(self):
        agent = FeasibleMCTSAgent(iterations=100000)
        moves, fault = safe_choose(agent, board(), TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(board().to_game_state(), moves))
        self.assertEqual(agent.info["iterations"], 0)
        self.assertTrue(agent.info["fallback"])

    def test_search_keeps_real_board_and_samples_risky_human_battles(self):
        position = Position(3, 5, {(0, 1): Cell(vampires=3), (1, 1): Cell(humans=7),
                                  (4, 1): Cell(werewolves=4)})
        before = position.to_dict()
        self.assertTrue(supported_turn(position.to_game_state(), [(0, 1, 3, 1, 1)]))
        agent = FeasibleMCTSAgent(iterations=64)
        agent.new_game(position, "vampires", 3)
        with patch("search.simulate_turn", wraps=simulate_turn) as call:
            moves, fault = safe_choose(agent, position, TurnContext(None, 40))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        battles = [args.args for args in call.call_args_list if args.args[0] == position
                   and any(tuple(move[3:]) == (1, 1) for move in args.args[1])]
        self.assertTrue(battles, "The oversized village must remain a possible search action")
        self.assertTrue(all(isinstance(args[2], random.Random) for args in battles))
        self.assertEqual(position.to_dict(), before)

    def test_recorded_stall_matches_the_controlled_probe_for_four_fixed_seeds(self):
        # A regression for one recorded board, not a strength or optimality claim.
        fixture = json.loads((ROOT / "examples/mcts_recruitment_stall.json").read_text())
        position = Position.from_dict(fixture["state"])
        config = SearchConfig(**fixture["probe"]["search_config"])
        target = tuple(fixture["target"]["coordinate"])
        expected = {(row["seed"], row["evaluation"]): [tuple(m) for m in row["moves"]]
                    for row in fixture["probe"]["results"]}
        before = position.to_dict()
        for seed in range(4):
            for spec, evaluation in (("mcts-v1", "original"), ("mcts-v5", "feasibility_ablation")):
                agent = make_agent(spec)
                agent.config = config
                agent.new_game(position, position.to_play, seed)
                moves, fault = safe_choose(agent, position, TurnContext(None, 200))
                with self.subTest(seed=seed, agent=spec):
                    self.assertIsNone(fault)
                    self.assertEqual(moves, expected[seed, evaluation])
                    self.assertEqual(agent.info["iterations"], 512)
                    self.assertEqual(distance(tuple(moves[0][3:]), target),
                                     3 if spec == "mcts-v1" else 1)
        self.assertEqual(position.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
