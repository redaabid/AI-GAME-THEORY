"""Macro-actions, race evaluation, scripts, playouts, and Portfolio Greedy Search."""

import random
import time
import unittest

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from combat import expected_battle
from evaluation import WIN, evaluate, race_owners
from game import Cell, distance
from macro import Order, needed, orders_to_moves, step
from mapgen import random_map
from playbook import SCRIPTS, View, play_turn, playout
from simulator import Position, simulate_turn


def board(records, *, rows=5, columns=7, **kwargs):
    return Position(rows, columns, {(x, y): Cell(h, v, w) for x, y, h, v, w in records}, **kwargs)


class MacroTests(unittest.TestCase):
    def test_orders_never_step_onto_another_source(self):
        position = board([(0, 0, 0, 5, 0), (1, 0, 0, 5, 0), (6, 4, 0, 0, 3)])
        moves, steps = orders_to_moves(position, [Order((0, 0), 5, (4, 0)), Order((1, 0), 5, (4, 0))])
        self.assertTrue(supported_turn(position.to_game_state(), moves))
        self.assertNotIn((1, 0), steps)
        self.assertEqual(steps[1], (2, 0))

    def test_orders_are_trimmed_to_available_creatures(self):
        position = board([(0, 0, 0, 5, 0), (6, 4, 0, 0, 3)])
        moves, _ = orders_to_moves(position, [Order((0, 0), 4, (3, 0)), Order((0, 0), 4, (0, 3))])
        self.assertEqual(sum(m[2] for m in moves), 5)
        self.assertTrue(supported_turn(position.to_game_state(), moves))

    def test_steps_toward_and_away(self):
        self.assertEqual(step(Order((2, 2), 1, (6, 2)), 5, 7), (3, 2))
        away = step(Order((2, 2), 1, (3, 2), away=True), 5, 7)
        self.assertEqual(distance(away, (3, 2)), 2)

    def test_needed_creatures(self):
        position = board([(0, 0, 0, 5, 0), (1, 1, 4, 0, 0), (3, 3, 0, 0, 5)])
        self.assertEqual(needed(position, (1, 1), "vampires"), 4)
        self.assertEqual(needed(position, (3, 3), "vampires"), 8)


class CombatTests(unittest.TestCase):
    def test_expected_battles(self):
        self.assertEqual(expected_battle(6, 6, humans=True).survivors, 12)
        self.assertEqual(expected_battle(15, 10).survivors, 15)
        win = expected_battle(12, 10)  # p = 0.7
        self.assertEqual((win.attacker_won, win.survivors), (True, 8))
        loss = expected_battle(10, 14)  # p = 10/28
        self.assertEqual((loss.attacker_won, loss.survivors), (False, 9))

    def test_rng_none_is_deterministic(self):
        position = board([(0, 0, 0, 12, 0), (1, 0, 0, 0, 10)])
        results = [simulate_turn(position, [(0, 0, 12, 1, 0)], None).to_dict() for _ in range(3)]
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[0]["cells"], [[1, 0, 0, 8, 0]])


class EvaluationTests(unittest.TestCase):
    def test_terminal_values(self):
        self.assertGreater(evaluate(board([(0, 0, 0, 5, 0)]), "vampires"), WIN)
        self.assertLess(evaluate(board([(0, 0, 0, 0, 5)]), "vampires"), -WIN)

    def test_race_goes_to_the_closer_group_and_ties_to_the_mover(self):
        position = board([(0, 0, 0, 5, 0), (6, 0, 0, 0, 5), (2, 0, 3, 0, 0), (3, 4, 3, 0, 0)])
        owners = race_owners(position, "vampires")
        self.assertEqual(owners[(2, 0)], ("vampires", 2))
        self.assertEqual(owners[(3, 4)][0], "vampires")  # 4 turns each: we move first.
        self.assertGreater(evaluate(position, "vampires"), 0)
        self.assertLess(evaluate(position, "werewolves"), 0)

    def test_humans_too_large_for_everyone_are_ignored(self):
        position = board([(0, 0, 0, 5, 0), (6, 0, 0, 0, 5), (3, 2, 9, 0, 0)])
        self.assertEqual(race_owners(position, "vampires")[(3, 2)], (None, None))

    def test_immediate_threat_counts_for_the_side_to_move(self):
        position = board([(0, 0, 0, 9, 0), (1, 0, 0, 0, 6), (6, 4, 0, 0, 3)])
        self.assertGreater(evaluate(position, "vampires"), 0)


class ScriptTests(unittest.TestCase):
    def test_split_sends_exactly_enough(self):
        position = board([(3, 2, 0, 9, 0), (0, 0, 4, 0, 0), (6, 4, 5, 0, 0), (6, 0, 0, 0, 2)])
        orders = SCRIPTS["split"](View(position), (3, 2), 9)
        self.assertEqual(sorted(o.count for o in orders), [4, 5])
        self.assertEqual({o.goal for o in orders}, {(0, 0), (6, 4)})

    def test_flee_moves_away_from_a_predator(self):
        position = board([(3, 2, 0, 4, 0), (5, 2, 0, 0, 9)])
        (order,) = SCRIPTS["flee"](View(position), (3, 2), 4)
        moves, _ = orders_to_moves(position, [order])
        self.assertEqual(distance(moves[0][3:], (5, 2)), 3)

    def test_eat_skips_humans_the_enemy_reaches_first(self):
        position = board([(0, 2, 0, 5, 0), (6, 2, 0, 0, 5), (5, 2, 3, 0, 0), (1, 0, 2, 0, 0)])
        (order,) = SCRIPTS["eat"](View(position), (0, 2), 5)
        self.assertEqual(order.goal, (1, 0))

    def test_every_script_gives_legal_turns_on_random_maps(self):
        for seed in range(15):
            position = random_map(random.Random(seed), ("small", "medium", "large")[seed % 3])
            for script in SCRIPTS:
                for side in ("vampires", "werewolves"):
                    turn = Position(position.rows, position.columns, position.cells, to_play=side)
                    moves, _ = play_turn(turn, {}, script)
                    with self.subTest(seed=seed, script=script, side=side):
                        self.assertTrue(supported_turn(turn.to_game_state(), moves))

    def test_playouts_reach_the_horizon(self):
        position = random_map(random.Random(4), "medium")
        final = playout(position, {}, horizon=12, default="eat")
        self.assertEqual(final.ply, 12)


class PortfolioTests(unittest.TestCase):
    def test_legal_turns_and_deadline(self):
        agent = make_agent("portfolio")
        for seed in range(6):
            position = random_map(random.Random(seed), "large")
            started = time.perf_counter()
            moves, fault = safe_choose(agent, position, TurnContext(started + 0.05, 200))
            with self.subTest(seed=seed):
                self.assertIsNone(fault)
                self.assertLess(time.perf_counter() - started, 0.5)

    def test_takes_free_humans_and_kills_a_weak_enemy(self):
        agent = make_agent("portfolio")
        humans = board([(0, 0, 0, 5, 0), (1, 1, 4, 0, 0), (6, 4, 0, 0, 5)])
        self.assertEqual(safe_choose(agent, humans, TurnContext(None, 200))[0], [(0, 0, 5, 1, 1)])
        kill = board([(0, 0, 0, 9, 0), (1, 0, 0, 0, 5)])
        self.assertEqual(safe_choose(agent, kill, TurnContext(None, 200))[0], [(0, 0, 9, 1, 0)])

    def test_bad_scripts_are_rejected(self):
        with self.assertRaises(ValueError):
            make_agent("portfolio:default='dance'")


if __name__ == "__main__":
    unittest.main()
