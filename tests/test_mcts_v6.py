"""Clock calibration, V5 control parity and two recorded tactical regressions."""

from dataclasses import replace
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from combat import win_probability
from game import Cell
from scripts.mcts_v5.value import feasible_evaluate
from scripts.mcts_v6 import EndgameMCTSAgent
from scripts.mcts_v6.value import endgame_evaluate, endgame_weight
from search import search
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "examples/mcts_v6_endgame.json").read_text())


def recorded(label):
    return Position.from_dict(FIXTURE["cases"][label]["state"])


class EndgameValueTests(unittest.TestCase):
    def test_clock_weight_and_leaf_value_follow_the_documented_linear_blend(self):
        position = recorded("late_attack")
        base = feasible_evaluate(position, "vampires", max_plies=200)
        self.assertAlmostEqual(base, -0.058567605632631636)
        for ply, expected in ((159, 0), (160, 0), (161, .025), (167, .175),
                              (180, .5), (199, .975), (200, 1), (210, 1)):
            current = replace(position, ply=ply)
            with self.subTest(ply=ply):
                weight = endgame_weight(current, max_plies=200)
                self.assertAlmostEqual(weight, expected)
                value = endgame_evaluate(current, "vampires", max_plies=200)
                self.assertAlmostEqual(value, (1 - weight) * base - weight)
                self.assertLessEqual(abs(value), 1)

    def test_no_cap_early_positions_and_any_remaining_humans_keep_v5_values(self):
        late = recorded("late_attack")
        for position, cap in ((late, None), (replace(late, ply=100), 200),
                              (recorded("early_trap"), 200),
                              (replace(late, cells={**late.cells, (0, 0): Cell(humans=255)}), 200)):
            for species in ("vampires", "werewolves"):
                self.assertEqual(endgame_evaluate(position, species, max_plies=cap),
                                 feasible_evaluate(position, species, max_plies=cap))
                self.assertEqual(endgame_weight(position, max_plies=cap), 0)

    def test_species_symmetry_opposite_perspectives_and_ties(self):
        position = recorded("late_attack")
        swapped = replace(position, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in position.cells.items()})
        value = endgame_evaluate(position, "vampires", max_plies=200)
        self.assertEqual(value, endgame_evaluate(swapped, "werewolves", max_plies=200))
        self.assertEqual(value, -endgame_evaluate(position, "werewolves", max_plies=200))
        tied = Position(3, 5, {(0, 1): Cell(vampires=12), (4, 1): Cell(werewolves=12)}, ply=195)
        self.assertEqual(endgame_evaluate(tied, "vampires", max_plies=200), 0)
        self.assertEqual(endgame_evaluate(tied, "werewolves", max_plies=200), 0)

    def test_terminal_elimination_and_cap_rewards_are_exact(self):
        position = recorded("late_attack")
        for cells, expected in (({(0, 0): Cell(vampires=2)}, 1),
                                ({(0, 0): Cell(werewolves=2)}, -1), ({}, 0)):
            for ply in (0, 195, 200):
                self.assertEqual(endgame_evaluate(replace(position, cells=cells, ply=ply),
                                                 "vampires", max_plies=200), expected)
        for species, expected in (("vampires", -1), ("werewolves", 1)):
            self.assertEqual(endgame_evaluate(replace(position, ply=200), species, max_plies=200), expected)

    def test_window_validation_and_deadlines(self):
        for value in (0, -1, True, 2.5, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                endgame_evaluate(recorded("late_attack"), "vampires", endgame_window=value)
        with self.assertRaises(TimeoutError):
            endgame_evaluate(recorded("late_attack"), "vampires", deadline=time.perf_counter() - 1)
        with patch("scripts.mcts_v6.value.check_deadline", side_effect=[None, TimeoutError]):
            with self.assertRaises(TimeoutError):
                endgame_evaluate(recorded("late_attack"), "vampires", max_plies=200)


class V6AgentTests(unittest.TestCase):
    def test_defaults_keep_v5_budgets_and_invalid_options_fail(self):
        v5, v6 = make_agent("mcts-v5"), make_agent("mcts-v6")
        self.assertIsInstance(v6, EndgameMCTSAgent)
        self.assertEqual(v5.config, v6.config)
        for key in ("memory", "clock", "feasibility", "repetition_visits", "history_window", "penalty"):
            self.assertEqual(getattr(v5, key), getattr(v6, key))
        self.assertEqual(v6.endgame_window, 40)
        for kwargs in ({"endgame": 1}, {"endgame": "False"}, {"endgame_window": 0},
                       {"endgame_window": True}, {"endgame_window": 2.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                EndgameMCTSAgent(**kwargs)

    def test_disabled_feature_exactly_matches_v5_on_four_maps_both_species_and_clocks(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                for clock in (True, False):
                    position = replace(load_map(path), to_play=species)
                    v5 = make_agent(f"mcts-v5:iterations=24,clock={clock}")
                    v6 = make_agent(f"mcts-v6:iterations=24,clock={clock},endgame=False")
                    for agent in (v5, v6):
                        agent.new_game(position, species, 9)
                    captured = []

                    def observe(*args, **kwargs):
                        result = search(*args, **kwargs)
                        captured.append(result)
                        return result

                    with self.subTest(map=path.name, species=species, clock=clock):
                        with patch("scripts.mcts_v5.agent.search", side_effect=observe):
                            original = v5.choose_moves(position, TurnContext(None, 40))
                            control = v6.choose_moves(position, TurnContext(None, 40))
                        self.assertEqual(original, control)
                        self.assertEqual(captured[0].candidate_actions, captured[1].candidate_actions)
                        self.assertEqual(captured[0].training_metadata(), captured[1].training_metadata())
                        self.assertEqual(v5.rng.getstate(), v6.rng.getstate())

    def test_clock_and_feasibility_switches_disable_calibration_without_removing_game_cap(self):
        position = recorded("late_attack")
        agent = EndgameMCTSAgent(clock=False, iterations=8)
        self.assertEqual(agent.leaf_value(position, "vampires", max_plies=200),
                         feasible_evaluate(position, "vampires"))
        for config in ({"clock": False}, {"feasibility": False}, {"endgame": False}):
            agent = EndgameMCTSAgent(iterations=8, **config)
            with patch("scripts.mcts_v5.agent.search", wraps=search) as call:
                _, fault = safe_choose(agent, position, TurnContext(None, 200))
            self.assertIsNone(fault)
            self.assertFalse(agent.info["endgame_effective"])
            self.assertEqual(agent.info["endgame_root_weight"], 0)
            self.assertEqual(call.call_args.kwargs["max_plies"], 200)

    def test_expired_search_keeps_legal_fallback_and_reset_clears_info(self):
        position = recorded("late_attack")
        agent = EndgameMCTSAgent(iterations=100000)
        moves, fault = safe_choose(agent, position, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["iterations"], 0)
        self.assertEqual(agent.info["version"], "v6")
        agent.new_game(position, "vampires", 42)
        self.assertIsNone(agent.info)

    def test_recorded_late_attack_remains_stochastic_and_is_selected_for_four_seeds(self):
        # Local behavioral regression, not a claim that this wins the match.
        position = recorded("late_attack")
        before = position.to_dict()
        expected = [tuple(m) for m in FIXTURE["cases"]["late_attack"]["attack"]]
        self.assertAlmostEqual(win_probability(52, 46, humans=False), .6304347826086956)
        outcomes = {json.dumps(simulate_turn(position, expected, random.Random(seed)).to_dict(), sort_keys=True)
                    for seed in range(16)}
        self.assertGreater(len(outcomes), 1)
        for seed in range(4):
            agent = EndgameMCTSAgent(iterations=1024)
            agent.new_game(position, position.to_play, seed)
            with patch("search.simulate_turn", wraps=simulate_turn) as call:
                moves, fault = safe_choose(agent, position, TurnContext(None, 200))
            with self.subTest(seed=seed):
                self.assertIsNone(fault)
                self.assertEqual(moves, expected)
                self.assertEqual(agent.info["iterations"], 1024)
                self.assertAlmostEqual(agent.info["endgame_root_weight"], .175)
                self.assertTrue(all(isinstance(c.args[2], random.Random) for c in call.call_args_list))
        self.assertEqual(position.to_dict(), before)

    def test_recorded_early_kill_invites_a_certain_counterattack_and_is_still_avoided(self):
        position = recorded("early_trap")
        attack = FIXTURE["cases"]["early_trap"]["attack"]
        attacked = simulate_turn(position, attack, random.Random(0))
        self.assertEqual(attacked.cells[14, 11].vampires, 9)
        replied = simulate_turn(attacked, [(13, 12, 19, 14, 11)], random.Random(0))
        self.assertEqual(replied.cells[14, 11].vampires, 0)
        self.assertEqual(replied.cells[14, 11].werewolves, 19)
        for seed in (0, 3):
            agents = [make_agent(f"{name}:iterations=512") for name in ("mcts-v5", "mcts-v6")]
            moves = []
            for agent in agents:
                agent.new_game(position, position.to_play, seed)
                chosen, fault = safe_choose(agent, position, TurnContext(None, 200))
                self.assertIsNone(fault)
                moves.append(chosen)
            self.assertEqual(moves[0], moves[1])
            self.assertTrue(all(tuple(m[3:]) != (14, 11) for m in moves[1]))
            self.assertEqual(agents[0].rng.getstate(), agents[1].rng.getstate())


if __name__ == "__main__":
    unittest.main()
