"""Alpha-beta, OEP, risky-battle branches, the clock in the evaluation, and tuning helpers."""

import random
import time
import unittest

from agents import TurnContext, make_agent, parse_spec, safe_choose
from candidates import supported_turn
from evaluation import evaluate, race_owners
from game import Cell
from lookahead import candidate_turns, outcomes
from mapgen import random_map
from simulator import Position
from tune import build_spec


def board(records, *, rows=5, columns=7, **kwargs):
    return Position(rows, columns, {(x, y): Cell(h, v, w) for x, y, h, v, w in records}, **kwargs)


class LookaheadTests(unittest.TestCase):
    def test_risky_battle_has_two_weighted_branches(self):
        position = board([(0, 0, 0, 12, 0), (1, 0, 0, 0, 10), (6, 4, 0, 0, 2)])
        branches = outcomes(position, [(0, 0, 12, 1, 0)])
        self.assertEqual(len(branches), 2)
        self.assertAlmostEqual(sum(q for q, _ in branches), 1.0)
        (win_q, win), (loss_q, loss) = branches
        self.assertAlmostEqual(win_q, 0.7)
        self.assertEqual(win.cells[(1, 0)], Cell(vampires=8))
        self.assertEqual(loss.cells[(1, 0)], Cell(werewolves=3))

    def test_sure_battles_do_not_branch(self):
        position = board([(0, 0, 0, 15, 0), (1, 0, 0, 0, 10)])
        self.assertEqual(len(outcomes(position, [(0, 0, 15, 1, 0)])), 1)

    def test_candidate_turns_are_legal_and_distinct(self):
        for seed in range(6):
            position = random_map(random.Random(seed), ("medium", "large")[seed % 2])
            turns = candidate_turns(position, extra=6)
            self.assertEqual(len(turns), len({tuple(sorted(t)) for t in turns}))
            for moves in turns:
                self.assertTrue(supported_turn(position.to_game_state(), moves))


class ClockTests(unittest.TestCase):
    def test_humans_out_of_reach_before_the_last_ply_are_ignored(self):
        # Vampires need 3 turns, werewolves 4; at ply 196 each side has 2 turns left.
        position = board([(0, 0, 0, 5, 0), (6, 4, 0, 0, 5), (3, 0, 3, 0, 0)], ply=196)
        self.assertEqual(race_owners(position, "vampires")[(3, 0)][0], "vampires")
        self.assertEqual(race_owners(position, "vampires", max_plies=200)[(3, 0)], (None, None))
        self.assertEqual(race_owners(position, "vampires", max_plies=201)[(3, 0)][0], "vampires")

    def test_last_ply_is_scored_like_the_server(self):
        position = board([(0, 0, 0, 6, 0), (6, 4, 0, 0, 5)], ply=200)
        self.assertGreater(evaluate(position, "vampires", max_plies=200), 9_000)


class EngineTests(unittest.TestCase):
    SPECS = ("alphabeta", "alphabeta:depth=2,extra=4", "oep", "oep:generations=3,opponents=('eat',)")

    def test_legal_turns_and_deadlines_on_random_maps(self):
        for spec in self.SPECS:
            agent = make_agent(spec)
            for seed in range(4):
                position = random_map(random.Random(seed), ("medium", "large")[seed % 2])
                agent.new_game(position, position.to_play, seed)
                started = time.perf_counter()
                moves, fault = safe_choose(agent, position, TurnContext(started + 0.1, 200))
                with self.subTest(spec=spec, seed=seed):
                    self.assertIsNone(fault)
                    self.assertLess(time.perf_counter() - started, 0.6)

    def test_takes_free_humans_and_kills_a_weak_enemy(self):
        humans = board([(0, 0, 0, 5, 0), (1, 1, 4, 0, 0), (6, 4, 0, 0, 5)])
        kill = board([(0, 0, 0, 9, 0), (1, 0, 0, 0, 5)])
        for spec in ("alphabeta", "oep"):
            agent = make_agent(spec)
            agent.new_game(humans, "vampires", 0)
            with self.subTest(spec=spec):
                self.assertEqual(safe_choose(agent, humans, TurnContext(None, 200))[0], [(0, 0, 5, 1, 1)])
                self.assertEqual(safe_choose(agent, kill, TurnContext(None, 200))[0], [(0, 0, 9, 1, 0)])

    def test_alphabeta_avoids_a_coin_flip_it_does_not_need(self):
        # 6 v 6: attacking is a 50% gamble; a safe group of humans is available instead.
        position = board([(0, 0, 0, 6, 0), (1, 0, 0, 0, 6), (0, 2, 2, 0, 0)], ply=20)
        moves, _ = safe_choose(make_agent("alphabeta"), position, TurnContext(None, 200))
        self.assertNotIn((0, 0, 6, 1, 0), moves)

    def test_deep_alphabeta_takes_a_likely_win_over_a_sure_deficit(self):
        # Course server, thetrap, ply 12: at depth 12 it used to flee and lose instead of eating.
        position = board([(9, 0, 0, 4, 0), (9, 1, 0, 2, 0), (6, 1, 0, 0, 8), (9, 2, 1, 0, 0), (9, 4, 2, 0, 0)],
                         rows=5, columns=10, ply=12)
        moves, _ = safe_choose(make_agent("alphabeta:depth=12"), position, TurnContext(None, 40))
        self.assertIn((9, 1, 2, 9, 2), moves)

    def test_alphabeta_with_a_lead_keeps_out_of_a_coin_flip(self):
        # Course server, thetrap, ply 24: 9 v 8, it stepped next to the 8 and lost the battle.
        position = board([(8, 2, 0, 9, 0), (6, 1, 0, 0, 8)], rows=5, columns=10, ply=24)
        moves, _ = safe_choose(make_agent("alphabeta:depth=12"), position, TurnContext(None, 40))
        self.assertTrue(all(max(abs(m[3] - 6), abs(m[4] - 1)) > 1 for m in moves), moves)

    def test_oep_coordinates_several_groups(self):
        position = board([(0, 0, 0, 4, 0), (6, 0, 0, 4, 0), (1, 1, 3, 0, 0), (5, 1, 3, 0, 0), (3, 4, 0, 0, 6)])
        agent = make_agent("oep")
        agent.new_game(position, "vampires", 0)
        moves, fault = safe_choose(agent, position, TurnContext(None, 200))
        self.assertIsNone(fault)
        self.assertEqual(sorted(m[3:] for m in moves), [(1, 1), (5, 1)])


class SpecTests(unittest.TestCase):
    def test_nested_values_in_specs(self):
        name, params = parse_spec("alphabeta:depth=2,weights={'humans': 0.9, 'threat': 0.5}")
        self.assertEqual((name, params), ("alphabeta", {"depth": 2, "weights": {"humans": 0.9, "threat": 0.5}}))

    def test_tuned_spec_round_trips(self):
        spec = build_spec("portfolio:passes=2", {"humans": 0.91234, "horizon": 7.6}, {"humans": 0.8, "horizon": 10})
        self.assertEqual(parse_spec(spec)[1], {"passes": 2, "horizon": 8, "weights": {"humans": 0.9123}})
        make_agent(spec)


if __name__ == "__main__":
    unittest.main()
