"""V3 must isolate coordination, preserve V1's settings and honor the deadline."""

from dataclasses import replace
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from game import Cell
import main
from search import evaluate
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]


class CoordinationOnlyTests(unittest.TestCase):
    def test_v3_keeps_every_v1_search_memory_and_clock_setting(self):
        for settings in ("", ":iterations=24,tree_depth=4,memory=False,clock=False"):
            v1, v3 = (make_agent(name + settings) for name in ("mcts-v1", "mcts-v3"))
            self.assertEqual(v3.config, v1.config)
            for name in ("memory", "clock", "repetition_visits", "history_window", "penalty"):
                self.assertEqual(getattr(v3, name), getattr(v1, name))
        v3 = make_agent("mcts-v3")
        self.assertEqual(v3.config.rollout_depth, 6)
        policy = v3.rollout_policy
        self.assertTrue(policy.coordinated)
        self.assertEqual(policy.extension_depth, 0)
        self.assertEqual(policy.variation, 0)
        self.assertFalse(policy.detect_loops)

    def test_v3_coordinates_both_players_within_the_original_six_ply_horizon(self):
        position = Position(5, 9, {
            (0, 0): Cell(vampires=3), (0, 3): Cell(vampires=4),
            (8, 0): Cell(werewolves=3), (8, 3): Cell(werewolves=4),
            (1, 0): Cell(humans=2), (1, 3): Cell(humans=3),
            (7, 0): Cell(humans=2), (7, 3): Cell(humans=3),
        })
        agent = make_agent("mcts-v3")
        with patch("rollouts.simulate_turn", wraps=simulate_turn) as transition:
            result = agent.rollout_policy(position, "vampires", random.Random(0),
                                          agent.config, None, 200, evaluate)
        self.assertEqual(result.plies, 6)
        self.assertEqual(result.extension_plies, 0)
        for call, actor in zip(transition.call_args_list[:2], ("vampires", "werewolves")):
            current, moves, _ = call.args
            self.assertEqual(current.to_play, actor)
            self.assertEqual(len({move[:2] for move in moves}), 2)

    def test_v3_does_not_cut_off_repetitions_or_add_tactical_extensions(self):
        position = Position(1, 5, {(0, 0): Cell(vampires=6), (4, 0): Cell(werewolves=8)})
        agent = make_agent("mcts-v3")

        def shuttle(current, rng, **kwargs):
            (x, y), count = current.to_game_state().groups()[0]
            return [(x, y, count, {0: 1, 1: 0, 3: 4, 4: 3}[x], y)]

        with patch("rollouts.coordinated_moves", side_effect=shuttle), \
                patch("rollouts.tactical_contact", side_effect=AssertionError("No tactical extension in V3")):
            result = agent.rollout_policy(position, "vampires", random.Random(0),
                                          agent.config, None, 200, evaluate)
        self.assertEqual((result.plies, result.loop_cutoffs, result.extension_plies), (6, 0, 0))

    def test_zero_horizon_v3_returns_the_leaf_without_continuing_a_battle(self):
        position = Position(1, 3, {(1, 0): Cell(vampires=13), (2, 0): Cell(werewolves=20)},
                            to_play="werewolves")
        agent = make_agent("mcts-v3:rollout_depth=0")
        result = agent.rollout_policy(position, "vampires", random.Random(0),
                                      agent.config, None, 200, evaluate)
        self.assertEqual((result.plies, result.extension_plies), (0, 0))
        self.assertEqual(result.value, evaluate(position, "vampires", max_plies=200))

    def test_seeded_v3_decisions_are_reproducible_and_keep_the_board_immutable(self):
        position = load_map(ROOT / "maps/demo.xml")
        before = position.to_dict()
        agents = [make_agent("mcts-v3:iterations=24") for _ in range(2)]
        for agent in agents:
            agent.new_game(position, position.to_play, 42)
        moves = [agent.choose_moves(position, TurnContext(None, 200)) for agent in agents]
        self.assertEqual(moves[0], moves[1])
        self.assertEqual(position.to_dict(), before)
        for key in ("iterations", "rollouts", "rollout_plies", "coordinated_turns"):
            self.assertEqual(agents[0].info["search"][key], agents[1].info["search"][key])
        self.assertLessEqual(agents[0].info["search"]["rollout_depth_max"], 6)

    def test_v3_preserves_repeated_position_memory(self):
        position = Position(5, 9, {(1, 2): Cell(vampires=6), (7, 2): Cell(werewolves=8),
                                   (4, 2): Cell(humans=4)}, ply=20)
        move = [(1, 2, 6, 2, 2)]
        history = [(replace(position, ply=ply), move) for ply in (12, 16)]
        agent = make_agent("mcts-v3:iterations=8")
        moves, fault = safe_choose(agent, position, TurnContext(None, 200, history))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["penalized_actions"], 1)
        self.assertEqual(agent.info["repetitions"], 2)

    def test_v3_returns_a_legal_fallback_when_the_deadline_has_expired(self):
        position = load_map(ROOT / "maps/demo.xml")
        agent = make_agent("mcts-v3:iterations=100000")
        moves, fault = safe_choose(agent, position, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertEqual(agent.info["iterations"], 0)
        self.assertTrue(agent.info["fallback"])

    def test_live_cli_applies_iteration_flags_to_v3_and_respects_explicit_specs(self):
        for spec, expected in (("mcts-v3", "mcts-v3:iterations=123"),
                               ("mcts-v3:iterations=8", "mcts-v3:iterations=8")):
            with self.subTest(spec=spec), patch("main.play_game") as run, patch("main.logging.basicConfig"):
                self.assertEqual(main.main(["--agent", spec, "--iterations", "123"]), 0)
                self.assertEqual(run.call_args.args[0].agent, expected)


if __name__ == "__main__":
    unittest.main()
