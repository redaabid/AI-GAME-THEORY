"""Checks for alternating legal travel rollouts, not a strength ranking."""
import time
import unittest

from agents import make_agent, safe_choose, TurnContext
from candidates import supported_turn
from game import Cell
from simulator import Position, simulate_turn


class RouteTests(unittest.TestCase):
    def distant(self):
        return Position(5, 25, {(0, 2): Cell(vampires=8), (24, 2): Cell(werewolves=8),
                              (6, 1): Cell(humans=4), (18, 3): Cell(humans=4)})

    def test_rollout_uses_legal_alternating_turns_and_respects_bound(self):
        node = self.distant()
        agent = make_agent('ab2route:route_plies=8')
        agent.deadline, agent.max_plies = None, 200
        expected = node
        for _ in range(8):
            moves = agent.route_move(expected)
            self.assertTrue(supported_turn(expected.to_game_state(), moves))
            following = simulate_turn(expected, moves, None)
            self.assertNotEqual(following.to_play, expected.to_play)
            expected = following
        actual = agent.travel(node)
        self.assertEqual(actual.to_dict(), expected.to_dict())
        self.assertEqual(actual.ply, 8)
        self.assertEqual(agent.route_max, 8)

    def test_no_scripted_travel_when_enemy_is_near(self):
        node = Position(3, 4, {(0, 1): Cell(vampires=6), (2, 1): Cell(werewolves=4)})
        agent = make_agent('ab2route')
        agent.deadline, agent.max_plies = None, 200
        self.assertEqual(agent.travel(node).to_dict(), node.to_dict())
        self.assertEqual(agent.route_steps, 0)

    def test_zero_route_matches_unmodified_ab2(self):
        context = TurnContext(None, 200)
        ref = make_agent('ab2:depth=2,width=6,extra=0')
        route = make_agent('ab2route:depth=2,width=6,extra=0,route_plies=0')
        a, af = safe_choose(ref, self.distant(), context)
        b, bf = safe_choose(route, self.distant(), context)
        self.assertIsNone(af)
        self.assertIsNone(bf)
        self.assertEqual(a, b)
        self.assertEqual(ref.info['value'], route.info['value'])

    def test_rollout_score_has_original_leaf_perspective(self):
        agent = make_agent('ab2route:route_plies=1')
        agent.deadline, agent.max_plies, agent.stats = None, 200, dict(nodes=0)
        node = self.distant()
        following = simulate_turn(node, agent.route_move(node), None)
        expected = -agent.leaf(following)
        self.assertEqual(agent.search(node, 0, -1000001, 1000001)[0], expected)

    def test_deadline_returns_a_legal_root_move(self):
        agent = make_agent('ab2route:depth=1,max_depth=24,width=6,extra=0')
        node = self.distant()
        start = time.perf_counter()
        moves, fault = safe_choose(agent, node, TurnContext(start+.05, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(node.to_game_state(), moves))
        self.assertLess(time.perf_counter()-start, .3)
        self.assertGreater(agent.info['route_steps'], 0)


if __name__ == '__main__':
    unittest.main()
