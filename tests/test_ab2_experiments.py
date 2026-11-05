"""AB2 ablations, history-safe caching, legal distant moves and bounded tactics."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import json
import time
import unittest

from agents import TurnContext, make_agent, safe_choose
from agents.ab2_experiments import repetition_key
from agents.ab_variants import PROFILES
from candidates import supported_turn
from game import Cell
from simulator import Position


def board():
    return Position(4, 6, {(0, 1): Cell(vampires=6),
                         (5, 2): Cell(werewolves=4), (2, 1): Cell(humans=2)})


class AB2ExperimentTests(unittest.TestCase):
    def test_disabled_changes_preserve_ab2_decisions_and_values(self):
        for depth in (1, 2, 3):
            ref = make_agent(f'ab2:depth={depth},width=6,extra=0')
            exp = make_agent(f'ab2exp:depth={depth},width=6,extra=0')
            context = TurnContext(None, 40)
            a, af = safe_choose(ref, board(), context)
            b, bf = safe_choose(exp, board(), context)
            self.assertIsNone(af)
            self.assertIsNone(bf)
            self.assertEqual(a, b)
            self.assertEqual(ref.info['value'], exp.info['value'])
            self.assertEqual(ref.info['nodes'], exp.info['nodes'])
        self.assertFalse(PROFILES['ab2'].quiescence)

    def test_repetition_ignores_ply_but_keeps_actor_and_all_populations(self):
        node = board()
        self.assertEqual(repetition_key(node), repetition_key(replace(node, ply=22)))
        self.assertNotEqual(repetition_key(node), repetition_key(replace(node, to_play='werewolves')))
        self.assertNotEqual(repetition_key(node), repetition_key(
            replace(node, cells=dict(node.cells) | {(5, 2): Cell(werewolves=3)})))

    def test_observed_repetition_penalty_and_terminal_verdict(self):
        node = board()
        ref = make_agent('ab2')
        exp = make_agent('ab2exp:repeat_penalty=5000')
        ref.max_plies = exp.max_plies = 40
        exp.root_species = 'vampires'
        exp.observed = Counter({repetition_key(node): 1})
        self.assertEqual(exp.leaf(node), ref.leaf(node) - 5000)
        exp.observed = Counter({repetition_key(node): 50})
        self.assertEqual(exp.leaf(node), ref.leaf(node) - 15000)
        terminal = replace(node, cells={(0, 1): Cell(vampires=6)})
        exp.observed[repetition_key(terminal)] = 10
        self.assertEqual(exp.leaf(terminal), ref.leaf(terminal))

    def test_history_changes_do_not_reuse_old_evaluation_cache(self):
        exp = make_agent('ab2exp:depth=2,repeat_penalty=5000')
        node = board()
        safe_choose(exp, node, TurnContext(None, 40))
        exp.table[('poison-previous-decision',)] = object()
        context = TurnContext(None, 40, [(node, [])] * 3)
        moves, fault = safe_choose(exp, node, context)
        fresh = make_agent('ab2exp:depth=2,repeat_penalty=5000')
        expected, other_fault = safe_choose(fresh, node, context)
        self.assertIsNone(fault)
        self.assertIsNone(other_fault)
        self.assertNotIn(('poison-previous-decision',), exp.table)
        self.assertEqual(moves, expected)
        self.assertEqual(exp.info['value'], fresh.info['value'])

    def test_long_range_goal_has_gradient_and_is_not_a_teleport(self):
        node = Position(3, 25, {(0, 1): Cell(vampires=12), (24, 1): Cell(werewolves=8)})
        agent = make_agent('ab2exp:depth=2,progress_weight=2000')
        agent.root_species, agent.max_plies = 'vampires', 200
        agent.goal = agent.select_goal(node)
        nearer = replace(node, cells={(1, 1): Cell(vampires=12), (24, 1): Cell(werewolves=8)})
        # On an otherwise featureless board, progress alone breaks the flat score.
        self.assertEqual(agent.leaf(nearer) - agent.leaf(node), 2000)
        moves, fault = safe_choose(agent, node, TurnContext(None, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(node.to_game_state(), moves))
        self.assertTrue(all(abs(tx-x) <= 1 and abs(ty-y) <= 1 for x, y, _, tx, ty in moves))
        agent.root_species = 'werewolves'
        self.assertIsNone(agent.select_goal(replace(node, to_play='werewolves')))

    def test_tactical_search_is_bounded_and_actually_extends(self):
        node = Position(3, 4, {(0, 0): Cell(vampires=4), (1, 1): Cell(humans=2),
                                (3, 2): Cell(werewolves=4)})
        agent = make_agent('ab2exp:depth=1,tactical=True,qdepth=2,qwidth=2')
        moves, fault = safe_choose(agent, node, TurnContext(None, 40))
        self.assertIsNone(fault)
        self.assertGreater(agent.info['qnodes'], 0)
        self.assertTrue(supported_turn(node.to_game_state(), moves))

    def test_all_profiles_are_legal_under_deadline_and_expose_metrics(self):
        manifest = Path(__file__).resolve().parents[1] / 'scripts' / 'ab2_experiment_profiles.json'
        for name, spec in json.loads(manifest.read_text())['profiles'].items():
            with self.subTest(name=name):
                agent = make_agent(spec)
                started = time.perf_counter()
                moves, fault = safe_choose(agent, board(), TurnContext(started + .02, 200))
                self.assertIsNone(fault)
                self.assertTrue(supported_turn(board().to_game_state(), moves))
                self.assertLess(time.perf_counter() - started, .3)
                self.assertGreaterEqual(agent.info['depth'], 1)

    def test_invalid_history_and_progress_settings_rejected(self):
        for params in ('repeat_after=1', 'repeat_penalty=-1', 'progress_weight=-1', 'tactical=1'):
            with self.subTest(params=params), self.assertRaises(ValueError):
                make_agent('ab2exp:' + params)


if __name__ == '__main__':
    unittest.main()
