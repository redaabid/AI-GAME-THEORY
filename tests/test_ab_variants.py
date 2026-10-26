"""Independent small-tree oracles and protocol-level checks for AB variants."""
from dataclasses import replace
import math
import random
import time
import unittest

from agents import TurnContext, available_agents, make_agent, safe_choose
from agents.ab_variants import PROFILES, SCORE, battle_distribution, exact_successors
from candidates import supported_turn
from game import Cell
from mapgen import random_map
from simulator import Position, get_outcome, simulate_turn


def tiny():
    return Position(3, 3, {(0, 0): Cell(vampires=1), (2, 2): Cell(werewolves=1)})


def exhaustive(node, depth, leaf):
    if not depth or get_outcome(node, max_plies=20) is not None:
        return leaf(node)
    # Independent enumeration: one creature/group in this fixture. No script,
    # heuristic ordering, TT, or production candidate generator is used.
    state = node.to_game_state()
    values = []
    for (x, y), n in state.groups():
        for tx, ty in state.neighbors((x, y)):
            child = simulate_turn(node, [(x, y, n, tx, ty)], None)
            values.append(-exhaustive(child, depth - 1, leaf))
    return max(values) if values else leaf(node)


class VariantTests(unittest.TestCase):
    def test_all_architectures_registered_and_distinct(self):
        self.assertTrue(set(PROFILES) <= set(available_agents()))
        self.assertEqual(len(set(PROFILES.values())), 9)
        with self.assertRaisesRegex(ValueError, 'explicit weights'):
            make_agent('ab7')

    def test_minimax_equivalence_full_windows_tt_pvs_and_mtd(self):
        position = tiny()
        for name in ('ab0', 'ab1', 'ab2', 'ab3', 'ab4', 'ab8'):
            agent = make_agent(f'{name}:depth=3,width=64,extra=0')
            moves, fault = safe_choose(agent, position, TurnContext(None, 20))
            with self.subTest(name=name):
                self.assertIsNone(fault)
                expected = exhaustive(position, 3, agent.leaf)
                self.assertEqual(agent.info['value'], expected)
                self.assertEqual(-exhaustive(simulate_turn(position, moves, None), 2, agent.leaf), expected)

    def test_deadlines_legality_and_feature_manifest(self):
        for name in PROFILES:
            spec = name + (":weights={'humans':0.8}" if name == 'ab7' else '')
            agent = make_agent(spec)
            node = random_map(random.Random(314), 'medium')
            started = time.perf_counter()
            moves, fault = safe_choose(agent, node, TurnContext(started + 0.03, 40))
            with self.subTest(name=name):
                self.assertIsNone(fault)
                self.assertTrue(supported_turn(node.to_game_state(), moves))
                self.assertLess(time.perf_counter() - started, 0.3)
                self.assertEqual(agent.info['profile'], name)

    def test_empty_budget_is_observable_bootstrap_not_agent_fault(self):
        agent = make_agent('ab3')
        moves, fault = safe_choose(agent, tiny(), TurnContext(time.perf_counter() - 1, 40))
        self.assertIsNone(fault)
        self.assertTrue(agent.info['bootstrap'])
        self.assertTrue(moves)

    def test_quiescence_is_bounded_and_actually_runs(self):
        agent = make_agent('ab5:depth=1,width=12,qdepth=1')
        node = Position(3, 4, {(0, 0): Cell(vampires=4), (1, 1): Cell(humans=2),
                                (3, 2): Cell(werewolves=4)})
        moves, fault = safe_choose(agent, node, TurnContext(None, 20))
        self.assertIsNone(fault)
        self.assertGreater(agent.info['qnodes'], 0)
        self.assertTrue(supported_turn(node.to_game_state(), moves))

    def test_values_do_not_leak_between_game_caps(self):
        a = make_agent('ab2:depth=2,width=64')
        node = tiny()
        for cap in (2, 20):
            safe_choose(a, node, TurnContext(None, cap))
            b = make_agent('ab1:depth=2,width=64')
            safe_choose(b, node, TurnContext(None, cap))
            self.assertEqual(a.info['value'], b.info['value'])


class ExactChanceTests(unittest.TestCase):
    def test_distribution_mass_means_and_extinction_atom(self):
        distribution = battle_distribution(2, 2, False, 'vampires', 'server-v3.2.1')
        self.assertAlmostEqual(math.fsum(q for q, _ in distribution), 1)
        self.assertAlmostEqual(sum(q * c.vampires for q, c in distribution), .5)
        self.assertAlmostEqual(sum(q * c.werewolves for q, c in distribution), .5)
        self.assertAlmostEqual(sum(q for q, c in distribution if c == Cell()), .25)

    def test_human_conversion_and_certain_branches(self):
        dist = battle_distribution(2, 4, True, 'werewolves', 'server-v3.2.1')
        self.assertAlmostEqual(sum(q * c.werewolves for q, c in dist), 6 * .25**2)
        self.assertEqual(battle_distribution(4, 4, True, 'vampires', 'brief'),
                         [(1, Cell(vampires=8))])
        self.assertEqual(battle_distribution(2, 4, False, 'vampires', 'brief'),
                         [(1, Cell(werewolves=4))])

    def test_joint_arrivals_resolved_once_and_turn_changes_once(self):
        node = Position(3, 3, {(0, 0): Cell(vampires=1), (0, 2): Cell(vampires=1),
                                (1, 1): Cell(werewolves=2)})
        moves = [(0, 0, 1, 1, 1), (0, 2, 1, 1, 1)]
        dist = list(exact_successors(node, moves))
        self.assertAlmostEqual(sum(q for q, _ in dist), 1)
        self.assertAlmostEqual(sum(q * p.cells.get((1, 1), Cell()).vampires for q, p in dist), .5)
        self.assertTrue(all(p.ply == 1 and p.to_play == 'werewolves' for _, p in dist))

    def test_ab6_value_matches_exact_chance_oracle_at_depth_one(self):
        node = Position(2, 2, {(0, 0): Cell(vampires=2), (1, 1): Cell(werewolves=2)})
        a = make_agent('ab6:depth=1,width=64')
        _, fault = safe_choose(a, node, TurnContext(None, 20))
        self.assertIsNone(fault)
        state = node.to_game_state()
        expected = max(sum(q * -a.leaf(p) for q, p in exact_successors(
            node, [(0, 0, 2, *target)])) for target in state.neighbors((0, 0)))
        self.assertAlmostEqual(a.info['value'], expected, places=5)


if __name__ == '__main__':
    unittest.main()
