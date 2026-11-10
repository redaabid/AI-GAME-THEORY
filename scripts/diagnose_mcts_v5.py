"""Record two new full V5/AB games selected from the completed campaign.

    python scripts/diagnose_mcts_v5.py --dry-run
    python scripts/diagnose_mcts_v5.py
    python scripts/diagnose_mcts_v5.py --analyse .local/diagnostics/V5-RUN

Defaults select the first clean testmap2 draw and first clean large-map loss.
Their settings/seeds are retained; timed searches need not reproduce outcomes.
All new outcomes are kept. This diagnostic is not a new strength tournament.
"""

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import multiprocessing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.mcts_v5.agent as v5_module
import scripts.diagnose_mcts_recruitment as tracing
from agents import parse_spec
from campaign import atomic_json, ignore_interrupt, read_games, runtime_hashes
from combat import win_probability
from scripts.mcts_v5.value import feasible_evaluate
from search import evaluate
from simulator import Position, get_outcome, opponent

DEFAULT_CAMPAIGN = ROOT / '.local/campaigns/mcts-v5-vs-julian-ab2-width7'


def fingerprint(path):
    return sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def select_games(plan, records, game_numbers=None):
    """Choose diagnostics by existing labels, never by a new run's outcome."""
    if game_numbers is None:
        indices = []
        for name, score in (('testmap2', 0.5), ('val-large-1290000', 0)):
            candidates = [i for i, result in sorted(records.items())
                          if result['map_name'] == name and result['a_score'] == score
                          and not any(result[key]['timeouts'] or result[key]['faults']
                                      for key in ('a_stats', 'b_stats'))]
            if not candidates:
                raise ValueError(f'No clean reference game for {name} with score {score}.')
            indices.append(candidates[0])
    else:
        if not game_numbers or len(set(game_numbers)) != len(game_numbers):
            raise ValueError('Reference game numbers must be nonempty and unique.')
        indices = [number - 1 for number in game_numbers]
    if any(index not in records for index in indices):
        raise ValueError('A requested reference game has no saved checkpoint.')
    jobs, references = [], []
    for index in indices:
        job = plan['jobs'][index]
        if parse_spec(job['a'])[0] != 'mcts-v5':
            raise ValueError('This recorder requires V5 as the reference challenger.')
        jobs.append(job)
        result = records[index]
        references.append({'game_number': index + 1, 'a_score': result['a_score'],
                           'final_populations': result['final_populations'],
                           'termination': result['termination']})
    return jobs, references


def diagnostic_manifest(directory, *, game_numbers=None, workers=2):
    if type(workers) is not int or workers < 1:
        raise ValueError('workers must be positive.')
    path = Path(directory) / 'manifest.json'
    original = json.loads(path.read_text(encoding='utf-8'))['plan']
    if original['source_sha256'] != runtime_hashes():
        raise ValueError('Core code differs from the reference campaign; preserve it and use matching source.')
    for relative, expected in original.get('v5_source_sha256', {}).items():
        if fingerprint(ROOT / relative) != expected:
            raise ValueError(f'V5 source differs from the reference campaign: {relative}')
    jobs, references = select_games(original, read_games(Path(directory), original), game_numbers)
    return {'purpose': 'new_v5_full_game_diagnostic_not_replay',
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'reference_campaign': str(Path(directory).resolve()),
            'reference_manifest_sha256': sha256(path.read_bytes()).hexdigest(),
            'references': references, 'plan': original | {'jobs': jobs, 'workers': workers},
            'diagnostic_source_sha256': {
                path.relative_to(ROOT).as_posix(): fingerprint(path)
                for path in (Path(__file__), Path(tracing.__file__))}}


@contextmanager
def capture_v5_root():
    """Process-local observer; retain results without adding RNG calls or I/O."""
    original, captured = v5_module.search, {}

    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        captured['result'] = result
        return result

    v5_module.search = observe
    try:
        yield captured
    finally:
        v5_module.search = original


def trace_game(initial, specs, **kwargs):
    # Reuse the already-tested match clock, history, battle RNG and move recorder.
    # Redirect its observer in this worker only; no source/engine files change.
    original = tracing.capture_root
    tracing.capture_root = capture_v5_root
    try:
        return tracing.trace_opening(initial, specs, **kwargs)
    finally:
        tracing.capture_root = original


def contacts(record):
    """Actual attacks/recruitments, with pre-battle probabilities and outcomes."""
    before, after = Position.from_dict(record['before']), Position.from_dict(record['after'])
    arrivals = Counter()
    for _, _, count, x, y in record['executed_moves']:
        arrivals[x, y] += count
    result = []
    for target, count in sorted(arrivals.items()):
        cell = before.cells.get(target)
        if cell is None:
            continue
        defenders = cell.humans or getattr(cell, opponent(before.to_play))
        if defenders:
            survivor = after.cells.get(target)
            result.append({'target': list(target), 'kind': 'humans' if cell.humans else 'monsters',
                           'attackers': count, 'defenders': defenders,
                           'win_probability': win_probability(count, defenders, humans=bool(cell.humans),
                                                               rules_profile=before.rules_profile),
                           'after': None if survivor is None else {
                               s: getattr(survivor, s) for s in ('humans', 'vampires', 'werewolves')}})
    return result


def summarize(records, initial, job):
    """Replay saved moves, derive terminal status, and explain population/loops."""
    final = tracing.verify_trace(records, initial, seed=job['seed'])
    cap, v5_species = job['settings']['max_plies'], job['a_species']
    ab_species = opponent(v5_species)
    if len(records) > cap - initial.ply:
        raise ValueError('Trace exceeds the game clock.')
    outcome = get_outcome(final, max_plies=cap)
    result = {'initial': initial.to_dict(), 'final': final.to_dict(), 'records': records,
              'status': 'terminal' if outcome else 'truncated',
              'outcome': None if outcome is None else {'winner': outcome.winner, 'reason': outcome.reason}}
    summary = tracing.opening_summary(result, v5_species)
    seen = {s: {} for s in (v5_species, ab_species)}
    repetitions, events, first_deficit = [], [], None
    for record in records:
        actor, before = record['actor'], record['populations_before']
        expected = job['a'] if actor == v5_species else job['b']
        if record['agent'] != expected:
            raise ValueError('Trace agent differs from the planned game.')
        root, info = record['mcts_root'], record['agent_info'] or {}
        if actor == v5_species and record['fault'] is None:
            if root is None or root['iterations'] != info.get('iterations'):
                raise ValueError('Missing or inconsistent V5 root diagnostics.')
            if root['chosen_moves'] != record['suggested_moves']:
                raise ValueError('Root choice differs from the suggested move.')
        key = tuple(tuple(cell) for cell in record['before']['cells'])
        if key in seen[actor]:
            repetitions.append({'ply': record['ply'], 'actor': actor,
                                'previous_ply': seen[actor][key],
                                'margin': before[actor] - before[opponent(actor)],
                                'penalized_actions': info.get('penalized_actions', 0)})
        seen[actor][key] = record['ply']
        after = record['populations_after']
        if first_deficit is None and after[v5_species] < after[ab_species]:
            first_deficit = record['ply'] + 1
        interaction = contacts(record)
        if interaction or before != after:
            events.append({'after_ply': record['ply'] + 1, 'actor': actor,
                           'v5': after[v5_species], 'ab': after[ab_species], 'humans': after['humans'],
                           'v5_delta': after[v5_species] - before[v5_species],
                           'ab_delta': after[ab_species] - before[ab_species], 'contacts': interaction,
                           'moves': record['executed_moves']})
    summary.update(map_name=job['map_name'], first=job['first'], seed=job['seed'],
                   first_deficit_after_ply=first_deficit, interactions=events,
                   repetitions=repetitions, a_score=None if outcome is None else (
                       0.5 if outcome.winner is None else float(outcome.winner == v5_species)))
    return summary


def run_job(job):
    directory, index = Path(job['directory']), job['index']
    trace_path = directory / f'game-{index + 1:02d}.jsonl'
    initial = replace(Position.from_dict(job['map']), to_play=job['first'])
    specs = {job['a_species']: job['a'], opponent(job['a_species']): job['b']}
    _, params = parse_spec(job['a'])
    with trace_path.open('x', encoding='utf-8') as stream:
        def save(record):
            # Extra comparisons happen AFTER the decision timer and never guide play.
            if record['actor'] == job['a_species']:
                before = Position.from_dict(record['before'])
                cap = job['settings']['max_plies'] if params.get('clock', True) else None
                record['static_root_evaluation'] = {
                    'v1': evaluate(before, before.to_play, max_plies=cap),
                    'v5': feasible_evaluate(before, before.to_play, max_plies=cap)}
            stream.write(json.dumps(record, allow_nan=False) + '\n')
            stream.flush()
        result = trace_game(initial, specs, seed=job['seed'],
                            stop_after_plies=job['settings']['max_plies'],
                            on_record=save, **{k: v for k, v in job['settings'].items() if k != 'on_timeout'})
    row = summarize(result['records'], initial, job) | {
        'index': index, 'trace_file': trace_path.name,
        'trace_sha256': sha256(trace_path.read_bytes()).hexdigest()}
    atomic_json(directory / f'game-{index + 1:02d}.summary.json', row)
    return row


def write_analysis(directory, manifest, rows):
    rows = sorted(rows, key=lambda row: row['index'])
    data = {'purpose': manifest['purpose'], 'planned_games': len(manifest['plan']['jobs']),
            'recorded_games': len(rows), 'games': rows}
    atomic_json(directory / 'analysis.json', data)
    text = ['# V5 full-game diagnostic', '',
            'New timed games using reference settings. Every observed outcome is kept;',
            'these are not replays of earlier decisions or a strength comparison.', '',
            '| Map | Reference game/result | New result | Final V5 / AB | Plies | Timeouts / faults |',
            '|---|---|---|---|---|---|']
    for row in rows:
        ref = manifest['references'][row['index']]
        populations = row['final_populations']
        species = row['mcts_species']
        label = 'unfinished' if row['outcome'] is None else {0: 'loss', .5: 'draw', 1: 'win'}[row['a_score']]
        text.append(f"| {row['map_name']} | {ref['game_number']} / {ref['a_score']} | {label} | "
                    f"{populations[species]} / {populations[opponent(species)]} | "
                    f"{row['plies_recorded']} | {row['timeouts']} / {len(row['faults'])} |")
    for row in rows:
        species = row['mcts_species']
        repeats = [r for r in row['repetitions'] if r['actor'] == species]
        text += ['', f"## {row['map_name']}", '',
                 f"V5 species: {species}; first player: {row['first']}; seed: {row['seed']}.", '',
                 f"AB completed depths: {dict(sorted(Counter(row['ab_completed_depths']).items()))}.", '',
                 f"First V5 population deficit after ply: {row['first_deficit_after_ply']}. "
                 f"Repeated V5 boards: {len(repeats)} "
                 f"({sum(r['margin'] == 0 for r in repeats)} tied; "
                 f"{sum(r['margin'] < 0 for r in repeats)} behind).", '',
                 f"First repeated V5 board: {repeats[0] if repeats else None}.", '',
                 '| After ply | Actor | V5 | AB | Humans left | Interaction | Moves |',
                 '|---|---|---|---|---|---|---|']
        for event in row['interactions']:
            descriptions = '; '.join(f"{c['attackers']} vs {c['defenders']} {c['kind']} at "
                                     f"{c['target']}, p={c['win_probability']:.3f}"
                                     for c in event['contacts'])
            text.append(f"| {event['after_ply']} | {event['actor']} | {event['v5']} | {event['ab']} | "
                        f"{event['humans']} | {descriptions} | `{event['moves']}` |")
    (directory / 'analysis.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    return data


def analyse(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    rows = []
    for index, job in enumerate(manifest['plan']['jobs']):
        path = directory / f'game-{index + 1:02d}.jsonl'
        if not path.exists():
            continue
        stored_path = directory / f'game-{index + 1:02d}.summary.json'
        digest = sha256(path.read_bytes()).hexdigest()
        stored = json.loads(stored_path.read_text(encoding='utf-8')) if stored_path.exists() else None
        if stored is not None and stored['trace_sha256'] != digest:
            raise ValueError('Trace fingerprint mismatch; preserving recorded data.')
        records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        initial = replace(Position.from_dict(job['map']), to_play=job['first'])
        row = summarize(records, initial, job) | {'index': index, 'trace_file': path.name,
                                                 'trace_sha256': digest}
        if stored is not None and row != stored:
            raise ValueError('Summary does not match verified trace.')
        rows.append(row)
    return write_analysis(directory, manifest, rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--campaign', type=Path, default=DEFAULT_CAMPAIGN)
    parser.add_argument('--games', nargs='+', type=int, help='Explicit 1-based reference game numbers')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--output', type=Path, help='Fresh output directory')
    parser.add_argument('--analyse', type=Path, help='Verify recorded moves without rerunning agents')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.analyse:
            data = analyse(args.analyse)
            print(f"Verified {data['recorded_games']} recorded games. {args.analyse / 'analysis.md'}")
            return 0
        manifest = diagnostic_manifest(args.campaign, game_numbers=args.games, workers=args.workers)
        directory = args.output or ROOT / '.local/diagnostics' / (
            'v5-full-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        jobs = [job | {'directory': str(directory.resolve()), 'index': index}
                for index, job in enumerate(manifest['plan']['jobs'])]
        print(f'Output: {directory.resolve()}', flush=True)
        for job, reference in zip(jobs, manifest['references']):
            print(f"{job['map_name']}: reference game {reference['game_number']}, "
                  f"score {reference['a_score']}; {job['a_species']}, first {job['first']}, "
                  f"seed {job['seed']}; {job['settings']}", flush=True)
        if args.dry_run:
            print('Plan validated. No games started or files written.')
            return 0
        directory.mkdir(parents=True, exist_ok=False)
        atomic_json(directory / 'manifest.json', manifest)
        rows = []
        write_analysis(directory, manifest, rows)
        with multiprocessing.get_context('spawn').Pool(args.workers, initializer=ignore_interrupt) as pool:
            iterator = pool.imap_unordered(run_job, jobs)
            while len(rows) < len(jobs):
                try:
                    row = iterator.next(timeout=15)
                    rows.append(row)
                    write_analysis(directory, manifest, rows)
                    print(f"Saved {len(rows)}/{len(jobs)} | {row['map_name']} | "
                          f"score {row['a_score']} | populations {row['final_populations']}", flush=True)
                except multiprocessing.TimeoutError:
                    counts = {path.name: len(path.read_text(encoding='utf-8').splitlines())
                              for path in directory.glob('game-*.jsonl')}
                    print(f'Recording: {counts}; {len(rows)}/{len(jobs)} games complete...', flush=True)
        analyse(directory)
        print(f'Complete. Move/battle replay verified. {directory / "analysis.md"}', flush=True)
        return 0
    except KeyboardInterrupt:
        print('Interrupted. Recorded plies are preserved. Use --analyse on the output directory.')
        return 130
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
