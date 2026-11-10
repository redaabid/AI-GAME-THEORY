"""Full V5 traces preserve play and correctly distinguish partial diagnostics."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from campaign import make_plan, run_campaign
from game import Cell
from scripts.compare_mcts_v5 import source_hashes
import scripts.diagnose_mcts_recruitment as tracing
from scripts.diagnose_mcts_v5 import (capture_v5_root, contacts, select_games,
                                      summarize, trace_game)
import scripts.mcts_v5.agent as v5_module
from scripts.render_mcts_trace import render
from simulator import Position, load_map, simulate_turn
from tournament import play_match

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(5, 9, {(0, 0): Cell(vampires=6), (8, 4): Cell(werewolves=8),
                        (4, 2): Cell(humans=4)})


def job_for(position, *, cap=8):
    return make_plan(['mcts-v5:iterations=8,rollout_depth=2', 'baseline'],
                     [('fixture', position)], max_plies=cap, move_time=0)['jobs'][0]


class V5DiagnosticTests(unittest.TestCase):
    def test_v5_observer_preserves_every_untimed_move_and_original_match_outcome(self):
        position = load_map(ROOT / 'maps/demo.xml')
        job = job_for(position)
        specs = {'vampires': job['a'], 'werewolves': job['b']}
        args = dict(seed=job['seed'], stop_after_plies=8, max_plies=8, move_time=0)
        original_search, original_capture = v5_module.search, tracing.capture_root
        control = tracing.trace_opening(position, specs, **args)
        result = trace_game(position, specs, **args)
        self.assertIs(v5_module.search, original_search)
        self.assertIs(tracing.capture_root, original_capture)
        for recorded, unchanged in zip(result['records'], control['records']):
            for key in ('before', 'after', 'executed_moves', 'suggested_moves'):
                self.assertEqual(recorded[key], unchanged[key])
        reference = play_match(position, specs, seed=job['seed'], max_plies=8, move_time=0)
        row = summarize(result['records'], position, job)
        self.assertEqual(row['outcome'], {'winner': reference['winner'], 'reason': reference['termination']})
        for record in result['records']:
            if record['actor'] == 'vampires':
                self.assertIsNotNone(record['mcts_root'])
                self.assertEqual(record['mcts_root']['iterations'], 8)
                self.assertEqual(record['agent_info']['leaf_evaluation'], 'recruitment-feasibility-v1')

    def test_recording_a_prefix_keeps_the_real_clock_and_does_not_invent_a_result(self):
        job = job_for(BOARD, cap=200)
        result = trace_game(BOARD, {'vampires': job['a'], 'werewolves': job['b']},
                            seed=job['seed'], max_plies=200, stop_after_plies=4, move_time=0)
        row = summarize(result['records'], BOARD, job)
        self.assertEqual(row['status'], 'truncated')
        self.assertIsNone(row['outcome'])
        self.assertIsNone(row['a_score'])
        self.assertEqual(row['plies_recorded'], 4)
        changed = deepcopy(result['records'])
        changed[0]['mcts_root'] = None
        with self.assertRaises(ValueError):
            summarize(changed, BOARD, job)

    def test_observers_restore_even_after_exceptions(self):
        original_search, original_capture = v5_module.search, tracing.capture_root
        with self.assertRaises(RuntimeError):
            with capture_v5_root():
                raise RuntimeError('fixture')
        self.assertIs(v5_module.search, original_search)
        with patch.object(tracing, 'trace_opening', side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):
                trace_game(BOARD, {})
        self.assertIs(tracing.capture_root, original_capture)

    def test_reference_selection_is_declared_before_new_play_and_ignores_faults_and_timeouts(self):
        plan = make_plan(['mcts-v5:iterations=4', 'baseline'],
                         [('testmap2', BOARD), ('val-large-1290000', BOARD)])
        records = {index: {'map_name': job['map_name'], 'a_score': .5 if index < 4 else 0,
                           'final_populations': {'vampires': 6, 'werewolves': 8},
                           'termination': 'ply_limit',
                           'a_stats': {'faults': [], 'timeouts': int(index in (0, 4))},
                           'b_stats': {'faults': [], 'timeouts': 0}}
                   for index, job in enumerate(plan['jobs'])}
        jobs, references = select_games(plan, records)
        self.assertEqual([r['game_number'] for r in references], [2, 6])
        self.assertEqual([j['map_name'] for j in jobs], ['testmap2', 'val-large-1290000'])
        for numbers in ([1, 1], [99], []):
            with self.assertRaises(ValueError):
                select_games(plan, records, numbers)
        records[5]['a_stats']['faults'] = ['fixture']
        self.assertEqual(select_games(plan, records)[1][1]['game_number'], 7)

    def test_contacts_describe_actual_recruitment_without_using_the_expected_battle_surrogate(self):
        before = Position(3, 5, {(0, 1): Cell(vampires=6), (1, 1): Cell(humans=4),
                                 (4, 1): Cell(werewolves=8)})
        moves = [(0, 1, 6, 1, 1)]
        after = simulate_turn(before, moves, random.Random(2))
        row = contacts({'before': before.to_dict(), 'after': after.to_dict(), 'executed_moves': moves})[0]
        self.assertEqual(row['kind'], 'humans')
        self.assertEqual(row['win_probability'], 1)
        self.assertEqual(row['after']['vampires'], 10)

    def test_repeated_boards_distinguish_ties_and_losing_positions(self):
        for enemy in (2, 3):
            initial = Position(3, 5, {(0, 0): Cell(vampires=2), (4, 2): Cell(werewolves=enemy)})
            job = job_for(initial, cap=8)
            current, records = initial, []
            for ply in range(8):
                actor = current.to_play
                source = next(p for p, c in current.cells.items() if getattr(c, actor))
                target = (0, 1 - source[1]) if actor == 'vampires' else (4, 3 - source[1])
                move = [(source[0], source[1], getattr(current.cells[source], actor), *target)]
                after = simulate_turn(current, move, random.Random(0))
                records.append({'ply': ply, 'actor': actor,
                                'agent': job['a'] if actor == 'vampires' else job['b'],
                                'before': current.to_dict(), 'after': after.to_dict(),
                                'timeout': False, 'fault': None,
                                'suggested_moves': move, 'executed_moves': move,
                                'populations_before': tracing.populations(current),
                                'populations_after': tracing.populations(after),
                                'agent_info': {'iterations': 1},
                                'mcts_root': {'visits': [1], 'iterations': 1, 'chosen_moves': move}
                                if actor == 'vampires' else None})
                current = after
            row = summarize(records, initial, job)
            repeated = [r for r in row['repetitions'] if r['actor'] == 'vampires']
            self.assertEqual([r['ply'] for r in repeated], [4, 6])
            self.assertEqual([r['margin'] for r in repeated], [2 - enemy] * 2)
            self.assertEqual(row['a_score'], .5 if enemy == 2 else 0)

    def test_cli_spawn_saves_full_games_reanalyses_and_preserves_reference_and_traces(self):
        with TemporaryDirectory() as temporary:
            reference, output = Path(temporary) / 'reference', Path(temporary) / 'diagnostic'
            plan = make_plan(['mcts-v5:iterations=4,rollout_depth=1', 'baseline'],
                             [('testmap2', BOARD), ('val-large-1290000', BOARD)],
                             workers=1, max_plies=4, move_time=0)
            plan['v5_source_sha256'] = source_hashes()
            run_campaign(plan, reference)
            original = (reference / 'report.json').read_bytes()
            args = [sys.executable, 'scripts/diagnose_mcts_v5.py', '--campaign', str(reference),
                    '--games', '1', '5', '--workers', '2', '--output', str(output)]
            preview = subprocess.run([*args, '--dry-run'], cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(output.exists())
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((output / 'analysis.json').read_text())
            self.assertEqual(data['recorded_games'], 2)
            self.assertTrue(all(row['status'] == 'terminal' for row in data['games']))
            self.assertTrue(all(row['plies_recorded'] == 4 for row in data['games']))
            trace = output / 'game-01.jsonl'
            raw = trace.read_bytes()
            rows = [json.loads(line) for line in raw.decode().splitlines()]
            self.assertTrue(all(r['mcts_root'] and r['static_root_evaluation']
                                for r in rows if r['actor'] == 'vampires'))
            again = subprocess.run([sys.executable, 'scripts/diagnose_mcts_v5.py', '--analyse', str(output)],
                                   cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(trace.read_bytes(), raw)
            html = render(output).read_text(encoding='utf-8')
            payload = html.split('<script id="data" type="application/json">', 1)[1].split('</script>', 1)[0]
            replay = json.loads(payload)
            self.assertEqual(len(replay), 2)
            self.assertEqual(replay[0]['records'], rows)
            self.assertEqual(trace.read_bytes(), raw)
            refused = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(trace.read_bytes(), raw)
            self.assertEqual((reference / 'report.json').read_bytes(), original)
            with trace.open('a', encoding='utf-8') as stream:
                stream.write('{}\n')
            bad = subprocess.run([sys.executable, 'scripts/diagnose_mcts_v5.py', '--analyse', str(output)],
                                 cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn('fingerprint mismatch', bad.stderr)


if __name__ == '__main__':
    unittest.main()
