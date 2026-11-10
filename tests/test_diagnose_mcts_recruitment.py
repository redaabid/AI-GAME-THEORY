"""Opening traces must preserve the game clock, policies and stochastic replay."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from agents import Agent, fallback_moves, register
import agents.mcts_memory as memory_module
from game import Cell
from scripts.diagnose_mcts_recruitment import opening_summary, trace_opening, verify_trace, village_races
from simulator import Position, load_map
from tournament import play_match

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(5, 20, {(0, 0): Cell(vampires=6), (19, 4): Cell(werewolves=8),
                          (10, 2): Cell(humans=4)})


@register('trace-test-clock')
class ClockAgent(Agent):
    contexts = []

    def choose_moves(self, position, context):
        self.contexts.append((context.max_plies, len(context.history)))
        return fallback_moves(position)


@register('trace-test-slow')
class SlowAgent(Agent):
    def choose_moves(self, position, context):
        time.sleep(0.02)
        return fallback_moves(position)


@register('trace-test-crash')
class CrashAgent(Agent):
    def choose_moves(self, position, context):
        raise RuntimeError('diagnostic fault fixture')


class RecruitmentTraceTests(unittest.TestCase):
    def test_recording_limit_does_not_replace_the_real_game_clock(self):
        ClockAgent.contexts.clear()
        result = trace_opening(BOARD, {'vampires': 'trace-test-clock', 'werewolves': 'baseline'},
                               seed=42, stop_after_plies=4, max_plies=200, move_time=0)
        self.assertEqual(result['status'], 'truncated')
        self.assertIsNone(result['outcome'])
        self.assertEqual(result['final']['ply'], 4)
        self.assertEqual(ClockAgent.contexts, [(200, 0), (200, 1)])
        summary = opening_summary(result, 'vampires')
        self.assertIsNone(summary['outcome'])

    def test_untimed_decisions_and_final_result_match_the_original_match_runner(self):
        initial = load_map(ROOT / 'maps/demo.xml')
        specs = {'vampires': 'mcts-v1:iterations=8,rollout_depth=2', 'werewolves': 'baseline'}
        original = memory_module.search
        traced = trace_opening(initial, specs, seed=13, stop_after_plies=8, max_plies=8, move_time=0)
        reference = play_match(initial, specs, seed=13, max_plies=8, move_time=0)
        self.assertEqual(traced['outcome'], {'winner': reference['winner'], 'reason': reference['termination']})
        self.assertEqual(traced['final']['ply'], reference['plies'])
        summary = opening_summary(traced, 'vampires')
        self.assertEqual({s: summary['final_populations'][s] for s in specs}, reference['final_populations'])
        self.assertIs(memory_module.search, original)
        roots = [r['mcts_root'] for r in traced['records'] if r['mcts_root']]
        self.assertTrue(roots)
        for root in roots:
            self.assertEqual(sum(root['visits']), 8)
            self.assertIn(root['chosen_moves'], root['candidate_actions'])
        verified = verify_trace(traced['records'], initial, seed=13)
        self.assertEqual(verified.to_dict(), traced['final'])

    def test_stochastic_battles_replay_exactly_with_recorded_moves_and_seed(self):
        duel = Position(1, 2, {(0, 0): Cell(vampires=1), (1, 0): Cell(werewolves=1)})
        outcomes = set()
        for seed in range(16):
            result = trace_opening(duel, {'vampires': 'random', 'werewolves': 'baseline'},
                                   seed=seed, stop_after_plies=2, move_time=0)
            self.assertEqual(verify_trace(result['records'], duel, seed=seed).to_dict(), result['final'])
            self.assertEqual(result['status'], 'terminal')
            outcomes.add(result['outcome']['winner'])
        self.assertEqual(outcomes, {'vampires', 'werewolves', None})

    def test_timeout_is_a_skipped_turn_and_does_not_consume_battle_randomness(self):
        result = trace_opening(BOARD, {'vampires': 'trace-test-slow', 'werewolves': 'baseline'},
                               seed=42, stop_after_plies=1, move_time=0.005, margin=0.001)
        record = result['records'][0]
        self.assertTrue(record['timeout'])
        self.assertEqual(record['executed_moves'], [])
        self.assertEqual(record['before']['cells'], record['after']['cells'])
        self.assertEqual(verify_trace(result['records'], BOARD, seed=42).ply, 1)

    def test_fault_is_recorded_and_legal_fallback_replays(self):
        result = trace_opening(BOARD, {'vampires': 'trace-test-crash', 'werewolves': 'baseline'},
                               seed=42, stop_after_plies=1, move_time=0)
        self.assertIn('diagnostic fault fixture', result['records'][0]['fault'])
        self.assertIsNone(result['records'][0]['agent_info'])
        self.assertEqual(verify_trace(result['records'], BOARD, seed=42).to_dict(), result['final'])

    def test_trace_verifier_rejects_changed_after_state(self):
        result = trace_opening(BOARD, {'vampires': 'random', 'werewolves': 'baseline'},
                               seed=42, stop_after_plies=2, move_time=0)
        corrupted = deepcopy(result['records'])
        corrupted[0]['after']['ply'] += 2
        with self.assertRaises(ValueError):
            verify_trace(corrupted, BOARD, seed=42)

    def test_village_distances_exclude_unaffordable_single_group_recruitment(self):
        initial = replace(BOARD, cells=BOARD.cells | {(1, 0): Cell(humans=7)})
        races = {tuple(row['target']): row for row in village_races(initial)}
        self.assertIsNone(races[(1, 0)]['single_group_steps']['vampires'])
        self.assertEqual(races[(10, 2)]['single_group_steps']['vampires'], 10)
        self.assertEqual(races[(1, 0)]['single_group_steps']['werewolves'], 18)

    def test_cli_dry_run_does_not_write_output(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'trace'
            result = subprocess.run([sys.executable, 'scripts/diagnose_mcts_recruitment.py', '--dry-run',
                                     '--map', 'maps/demo.xml', '--output', str(directory)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Opening limit 48 plies; real game cap 200; 4 roles; 2 workers', result.stdout)
            self.assertFalse(directory.exists())

    def test_cli_spawn_replay_analysis_and_existing_output_preservation(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'trace'
            args = [sys.executable, 'scripts/diagnose_mcts_recruitment.py', '--map', 'maps/demo.xml',
                    '--agent', 'mcts-v1:iterations=4', '--opponent', 'baseline', '--move-time', '0',
                    '--stop-after-plies', '4', '--roles', '2', '--output', str(directory)]
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((directory / 'analysis.json').read_text())
            self.assertEqual(data['completed_openings'], 2)
            self.assertTrue(all(row['status'] == 'truncated' for row in data['openings']))
            self.assertTrue(all(row['outcome'] is None for row in data['openings']))
            trace = directory / 'game-01.jsonl'
            before = trace.read_bytes()
            analysed = subprocess.run([sys.executable, 'scripts/diagnose_mcts_recruitment.py', '--analyse', str(directory)],
                                      cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(analysed.returncode, 0, analysed.stderr)
            self.assertEqual(trace.read_bytes(), before)
            refused = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(trace.read_bytes(), before)
            with trace.open('a', encoding='utf-8') as stream:
                stream.write('{}\n')
            corrupted = subprocess.run([sys.executable, 'scripts/diagnose_mcts_recruitment.py', '--analyse', str(directory)],
                                       cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(corrupted.returncode, 0)
            self.assertIn('fingerprint mismatch', corrupted.stderr)


if __name__ == '__main__':
    unittest.main()
