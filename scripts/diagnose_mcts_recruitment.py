"""Record new opening diagnostics; this is not a replay or a strength tournament.

    python scripts/diagnose_mcts_recruitment.py --dry-run
    python scripts/diagnose_mcts_recruitment.py
    python scripts/diagnose_mcts_recruitment.py --analyse .local/diagnostics/RECRUITMENT-RUN

Stops after 48 plies while agents retain the normal 200-ply match clock.
Records boards, actual moves, root candidates and AB's actual completed depths.
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
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents import TurnContext, fallback_moves, make_agent, parse_spec, safe_choose
import agents.mcts_memory as memory_module
from campaign import atomic_json, ignore_interrupt, make_plan
from game import distance
from simulator import Position, SPECIES, get_outcome, load_map, opponent, simulate_turn

PROFILE_FILE = ROOT / 'scripts/ab2_retained_profiles.json'


def populations(position):
    return {species: sum(getattr(c, species) for c in position.cells.values())
            for species in (*SPECIES, 'humans')}


def village_races(position):
    """Single-group distance lower bounds, not safe paths or full route plans."""
    groups = {s: [(p, getattr(c, s)) for p, c in position.cells.items() if getattr(c, s)] for s in SPECIES}
    result = []
    for target, cell in sorted(position.cells.items()):
        if cell.humans:
            steps = {s: min((distance(p, target) for p, n in groups[s] if n >= cell.humans), default=None)
                     for s in SPECIES}
            result.append({'target': list(target), 'humans': cell.humans, 'single_group_steps': steps})
    return result


@contextmanager
def capture_root():
    """Observe the existing V1 search in this process; store references only.

    Serialization and extra board analysis happen after the decision timer.
    No search parameters, RNG calls or rewards are changed.
    """
    original, captured = memory_module.search, {}

    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        captured['result'] = result
        return result

    memory_module.search = observe
    try:
        yield captured
    finally:
        memory_module.search = original


def trace_opening(initial, specs, *, seed, stop_after_plies=48, max_plies=200,
                  move_time=2.0, margin=0.5, on_record=None):
    """Mirror tournament.play_match's seeding, history, cap and timeout rules."""
    # Reuse the campaign validator without generating or writing any games.
    make_plan(list(specs.values()), [('trace', initial)], max_plies=max_plies,
              move_time=move_time, margin=margin, workers=1)
    if type(stop_after_plies) is not int or stop_after_plies < 1:
        raise ValueError('stop_after_plies must be a positive integer.')
    agents = {species: make_agent(spec) for species, spec in specs.items()}
    for index, species in enumerate(SPECIES):
        agents[species].new_game(initial, species, seed * 2 + index)
    battle_rng = random.Random(seed)
    position, history, records = initial, {s: [] for s in SPECIES}, []
    with capture_root() as captured:
        while (get_outcome(position, max_plies=max_plies) is None
               and position.ply - initial.ply < stop_after_plies):
            actor, before = position.to_play, position
            captured.clear()
            started, cpu_started = time.perf_counter(), time.process_time()
            deadline = started + move_time - margin if move_time else None
            moves, fault = safe_choose(agents[actor], position, TurnContext(deadline, max_plies, history[actor]))
            elapsed, cpu = time.perf_counter() - started, time.process_time() - cpu_started
            timed_out = bool(move_time and elapsed > move_time)
            if timed_out:
                played = []
                position = replace(position, to_play=opponent(actor), ply=position.ply + 1)
            else:
                played = moves
                try:
                    position = simulate_turn(position, played, battle_rng)
                except ValueError as error:
                    fault = f'{fault or ""} simulator rejection: {error}'.strip()
                    played = fallback_moves(before)
                    position = simulate_turn(before, played, battle_rng)
            history[actor].append((before, played))
            root = captured.get('result')
            record = {'ply': before.ply, 'actor': actor, 'agent': specs[actor],
                      'before': before.to_dict(), 'after': position.to_dict(),
                      'suggested_moves': moves, 'executed_moves': played,
                      'timeout': timed_out, 'fault': fault, 'wall_seconds': elapsed, 'cpu_seconds': cpu,
                      'populations_before': populations(before), 'populations_after': populations(position),
                      'villages_before': village_races(before), 'villages_after': village_races(position),
                      'agent_info': agents[actor].info if fault is None else None,
                      'mcts_root': ({**root.training_metadata(), 'candidate_actions': root.candidate_actions,
                                     'chosen_moves': root.moves} if root is not None else None)}
            # Freeze mutable agent info and tuple moves outside the thinking timer.
            record = json.loads(json.dumps(record, allow_nan=False))
            records.append(record)
            if on_record:
                on_record(record)
    outcome = get_outcome(position, max_plies=max_plies)
    return {'status': 'terminal' if outcome else 'truncated', 'initial': initial.to_dict(),
            'final': position.to_dict(), 'records': records,
            'outcome': {'winner': outcome.winner, 'reason': outcome.reason} if outcome else None}


def verify_trace(records, initial, *, seed):
    """Replay recorded actions and stochastic battles, not timed AI decisions."""
    current, rng = initial, random.Random(seed)
    for record in records:
        if current.to_dict() != record['before']:
            raise ValueError('Trace has a discontinuous before-state.')
        if record['actor'] != current.to_play or record['ply'] != current.ply:
            raise ValueError('Trace actor/ply mismatch.')
        if record['timeout']:
            if record['executed_moves']:
                raise ValueError('A timed-out turn must be skipped.')
            current = replace(current, to_play=opponent(current.to_play), ply=current.ply + 1)
        else:
            current = simulate_turn(current, record['executed_moves'], rng)
        if current.to_dict() != record['after'] or populations(current) != record['populations_after']:
            raise ValueError('Recorded moves/battle seed do not reproduce the after-state.')
        root = record.get('mcts_root')
        if root is not None and sum(root['visits']) != root['iterations']:
            raise ValueError('Recorded MCTS visits do not match its completed iterations.')
    return current


def opening_summary(result, mcts_species):
    other, records = opponent(mcts_species), result['records']
    initial_pop = populations(Position.from_dict(result['initial']))
    events, timeline, depths = [], [], []
    first_growth = {s: None for s in SPECIES}
    for record in records:
        after = record['populations_after']
        point = {'after_ply': record['ply'] + 1, 'mcts': after[mcts_species], 'ab': after[other],
                 'humans': after['humans'], 'margin': after[mcts_species] - after[other]}
        timeline.append(point)
        if after != record['populations_before']:
            events.append({**point, 'actor': record['actor'], 'moves': record['executed_moves']})
        for s in SPECIES:
            if first_growth[s] is None and after[s] > initial_pop[s]:
                first_growth[s] = point['after_ply']
        if record['actor'] == other and record['agent_info'] is not None:
            depth = record['agent_info'].get('depth')
            if depth is not None:
                depths.append(depth)
    return {'status': result['status'], 'outcome': result['outcome'], 'plies_recorded': len(records),
            'final_populations': populations(Position.from_dict(result['final'])),
            'mcts_species': mcts_species, 'first_growth_after_ply': first_growth,
            'population_events': events, 'population_timeline': timeline,
            'ab_completed_depths': depths,
            'timeouts': sum(r['timeout'] for r in records),
            'faults': [r['fault'] for r in records if r['fault']],
            'mcts_iterations': sum(r['mcts_root']['iterations'] for r in records
                                   if r['actor'] == mcts_species and r['mcts_root'])}


def run_job(job):
    directory = Path(job['directory'])
    initial = replace(Position.from_dict(job['map']), to_play=job['first'])
    specs = {job['a_species']: job['a'], opponent(job['a_species']): job['b']}
    trace_path = directory / f'game-{job["index"] + 1:02d}.jsonl'
    with trace_path.open('x', encoding='utf-8') as stream:
        def save(record):
            stream.write(json.dumps(record, allow_nan=False) + '\n')
            stream.flush()
        result = trace_opening(initial, specs, seed=job['seed'], stop_after_plies=job['stop_after_plies'],
                               on_record=save, **{k: v for k, v in job['settings'].items() if k != 'on_timeout'})
    verified = verify_trace(result['records'], initial, seed=job['seed'])
    if verified.to_dict() != result['final']:
        raise ValueError('Verified trace ended at a different board.')
    summary = opening_summary(result, job['a_species']) | {
        'index': job['index'], 'first': job['first'], 'seed': job['seed'],
        'trace_file': trace_path.name, 'trace_sha256': sha256(trace_path.read_bytes()).hexdigest()}
    atomic_json(directory / f'game-{job["index"] + 1:02d}.summary.json', summary)
    return summary


def write_analysis(directory, manifest, results):
    ordered = sorted(results, key=lambda r: r['index'])
    data = {'purpose': 'opening_diagnostic_not_strength_comparison',
            'completed_openings': len(ordered), 'planned_openings': len(manifest['plan']['jobs']),
            'openings': ordered}
    atomic_json(directory / 'analysis.json', data)
    text = ['# Recruitment opening diagnostic', '',
            'This is a new run. Truncated openings are not wins, losses or draws.', '',
            f"Completed openings: {len(ordered)}/{data['planned_openings']}. "
            f"Agents retain the {manifest['max_plies']}-ply game clock; recording stops after "
            f"{manifest['stop_after_plies']} plies.", '',
            '| Role | MCTS species | First player | Recorded plies | MCTS / AB population | First growth MCTS / AB (after ply) |',
            '|---|---|---|---|---|---|']
    for row in ordered:
        s, p, growth = row['mcts_species'], row['final_populations'], row['first_growth_after_ply']
        text.append(f"| {row['index'] + 1} | {s} | {row['first']} | {row['plies_recorded']} | "
                    f"{p[s]} / {p[opponent(s)]} | {growth[s]} / {growth[opponent(s)]} |")
    for row in ordered:
        text += ['', f"## Role {row['index'] + 1}", '',
                 f"Timeouts: {row['timeouts']}; faults: {len(row['faults'])}. "
                 f"AB completed depths: {dict(Counter(row['ab_completed_depths']))}.", '',
                 '| After ply | Actor | MCTS population | AB population | Humans left | Moves |',
                 '|---|---|---|---|---|---|']
        for event in row['population_events']:
            text.append(f"| {event['after_ply']} | {event['actor']} | {event['mcts']} | {event['ab']} | "
                        f"{event['humans']} | `{event['moves']}` |")
    (directory / 'analysis.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    return data


def analyse(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    summaries = []
    for path in sorted(directory.glob('game-*.summary.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        if type(row['index']) is not int or not 0 <= row['index'] < len(manifest['plan']['jobs']):
            raise ValueError('Invalid opening index.')
        job = manifest['plan']['jobs'][row['index']]
        trace = directory / f'game-{row["index"] + 1:02d}.jsonl'
        if row['trace_file'] != trace.name or sha256(trace.read_bytes()).hexdigest() != row['trace_sha256']:
            raise ValueError('Trace fingerprint mismatch.')
        records = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
        initial = replace(Position.from_dict(job['map']), to_play=job['first'])
        final = verify_trace(records, initial, seed=job['seed'])
        result = {'initial': initial.to_dict(), 'final': final.to_dict(), 'records': records,
                  'status': row['status'], 'outcome': row['outcome']}
        recomputed = opening_summary(result, job['a_species'])
        if any(row[k] != v for k, v in recomputed.items()):
            raise ValueError('Stored opening summary does not match its trace.')
        summaries.append(row)
    return write_analysis(directory, manifest, summaries)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--analyse', type=Path, help='Verify and analyse an existing trace directory')
    parser.add_argument('--map', type=Path, default=ROOT / '.local/maps/mcts-vs-best-ab/testmap2.xml')
    parser.add_argument('--agent', default='mcts-v1:iterations=100000')
    parser.add_argument('--opponent', help='Default: Julian retained AB2 width7 verbatim')
    parser.add_argument('--stop-after-plies', type=int, default=48)
    parser.add_argument('--max-plies', type=int, default=200)
    parser.add_argument('--move-time', type=float, default=2.0)
    parser.add_argument('--margin', type=float, default=0.5)
    parser.add_argument('--seed', type=int, default=20261028)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--roles', type=int, choices=(1, 2, 4), default=4)
    parser.add_argument('--output', type=Path, help='Fresh directory; existing outputs are preserved')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.analyse:
            data = analyse(args.analyse)
            print(f"Verified {data['completed_openings']} recorded openings. {args.analyse / 'analysis.md'}")
            return 0
        if args.stop_after_plies < 1:
            raise ValueError('stop-after-plies must be positive.')
        if parse_spec(args.agent)[0] not in ('mcts-v1', 'mcts-memory'):
            raise ValueError('This diagnostic currently captures the V1/mcts-memory search.')
        opponent_spec = args.opponent or json.loads(PROFILE_FILE.read_text(encoding='utf-8'))['profiles']['ab2_width7']
        for spec in (args.agent, opponent_spec):
            make_agent(spec)
        plan = make_plan([args.agent, opponent_spec], [(args.map.stem, load_map(args.map))],
                         workers=args.workers, seed=args.seed, max_plies=args.max_plies,
                         move_time=args.move_time, margin=args.margin)
        if args.roles == 2:
            plan['jobs'] = [plan['jobs'][0], plan['jobs'][1]]  # Both species, same first player.
        elif args.roles == 1:
            plan['jobs'] = plan['jobs'][:1]
        manifest = {'purpose': 'new_opening_diagnostic_not_replay', 'plan': plan,
                    'stop_after_plies': args.stop_after_plies, 'max_plies': args.max_plies,
                    'script_sha256': sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                    'profiles_sha256': sha256(PROFILE_FILE.read_bytes().replace(b'\r\n', b'\n')).hexdigest()}
        directory = args.output or ROOT / '.local/diagnostics' / (
            'recruitment-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        print(f'Output: {directory.resolve()}', flush=True)
        print(f"Agents: {args.agent} vs {opponent_spec}", flush=True)
        print(f'Opening limit {args.stop_after_plies} plies; real game cap {args.max_plies}; '
              f'{len(plan["jobs"])} roles; {args.workers} workers.', flush=True)
        if args.dry_run:
            print('Plan validated. No opening started and no files written.')
            return 0
        directory.mkdir(parents=True, exist_ok=False)
        atomic_json(directory / 'manifest.json', manifest)
        jobs = [job | {'directory': str(directory), 'index': i, 'stop_after_plies': args.stop_after_plies}
                for i, job in enumerate(plan['jobs'])]
        results = []
        write_analysis(directory, manifest, results)

        def accept(row):
            results.append(row)
            write_analysis(directory, manifest, results)
            print(f"Saved opening {len(results)}/{len(jobs)} | MCTS {row['mcts_species']} | "
                  f"populations {row['final_populations']}", flush=True)

        if args.workers == 1:
            for job in jobs:
                accept(run_job(job))
        else:
            with multiprocessing.get_context('spawn').Pool(args.workers, initializer=ignore_interrupt) as pool:
                iterator = pool.imap_unordered(run_job, jobs)
                while len(results) < len(jobs):
                    try:
                        accept(iterator.next(timeout=15))
                    except multiprocessing.TimeoutError:
                        saved_plies = sum(len(p.read_text(encoding='utf-8').splitlines()) for p in directory.glob('game-*.jsonl'))
                        print(f'Recording: {saved_plies} plies saved; {len(results)}/{len(jobs)} openings complete...', flush=True)
        analyse(directory)
        print(f'Complete. Verified move/battle replay. Analysis: {directory / "analysis.md"}', flush=True)
        return 0
    except KeyboardInterrupt:
        print('Interrupted. Saved trace lines and completed openings are preserved; use --analyse on the output directory.')
        return 130
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
