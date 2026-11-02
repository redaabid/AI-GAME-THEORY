"""Sequential simulator screening of AB2 experiments, never WPF certification.

Default: active profiles only, 1.5 s/decision, 200 plies, three diagnostic maps, both roles,
two seeds. --smoke uses .02 s/decision and 12 plies: functional checks only.
Each game is saved immediately; output must be a new directory. Do not compare
smoke win rates as evidence of playing strength. No simultaneous CPU matches.
"""
import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import TurnContext, make_agent, safe_choose
from agents.ab2_experiments import repetition_key
from game import Cell, distance
from mapgen import write_map
from simulator import Position, get_outcome, load_map, opponent, simulate_turn


def diagnostic_maps():
    return {
        'distant-recruitment': Position(5, 25, {
            (0, 2): Cell(vampires=8), (24, 2): Cell(werewolves=8),
            (6, 1): Cell(humans=4), (18, 3): Cell(humans=4),
            (12, 2): Cell(humans=6)}),
        'distant-pursuit': Position(5, 25, {
            (0, 2): Cell(vampires=12), (24, 2): Cell(werewolves=8)}),
        'tactical-contact': Position(5, 7, {
            (1, 2): Cell(vampires=8), (5, 2): Cell(werewolves=8),
            (3, 1): Cell(humans=3), (3, 3): Cell(humans=3)}),
    }


def duel(initial, candidate, reference, species, budget, cap, seed, on_turn=None):
    agents = {species: make_agent(candidate), opponent(species): make_agent(reference)}
    for actor, agent in agents.items():
        agent.new_game(initial, actor, seed)
    histories = {s: [] for s in agents}
    seen, trace, faults, timings = Counter(), [], [], {s: [] for s in agents}
    rng, node, repeats = random.Random(seed), initial, 0
    while (outcome := get_outcome(node, max_plies=cap)) is None:
        actor = node.to_play
        key = repetition_key(node)
        repeats += seen[key] > 0
        seen[key] += 1
        started = time.perf_counter()
        moves, fault = safe_choose(agents[actor], node,
            TurnContext(started + budget, cap, histories[actor]))
        elapsed = time.perf_counter() - started
        timings[actor].append(elapsed)
        if fault:
            faults.append({'ply': node.ply, 'species': actor, 'fault': fault})
        trace.append({'ply': node.ply, 'species': actor, 'seconds': elapsed,
                      'moves': moves, 'metrics': agents[actor].info,
                      'position': node.to_dict()})
        histories[actor].append((node, moves))
        node = simulate_turn(node, moves, rng)
        if on_turn is not None:
            on_turn(dict(ply=node.ply, last_seconds=elapsed, faults=len(faults)))
    trace.append({'ply': node.ply, 'position': node.to_dict()})
    first_contact = None
    for row in trace:
        p = Position.from_dict(row['position'])
        ours = [q for q, c in p.cells.items() if c.vampires]
        theirs = [q for q, c in p.cells.items() if c.werewolves]
        if ours and theirs and min(distance(a, b) for a in ours for b in theirs) <= 1:
            first_contact = p.ply
            break
    return dict(candidate_species=species, seed=seed, winner=outcome.winner,
                termination=outcome.reason, plies=node.ply, repetitions=repeats,
                first_adjacent_ply=first_contact,
                final_populations={s: sum(getattr(c, s) for c in node.cells.values()) for s in agents},
                faults=faults, timings=timings, trace=trace,
                alerts_over_1_8=sum(t > 1.8 for times in timings.values() for t in times),
                bootstraps=sum(bool((r.get('metrics') or {}).get('bootstrap')) for r in trace),
                score=.5 if outcome.winner is None else int(outcome.winner == species))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'scripts' / 'ab2_experiment_profiles.json')
    parser.add_argument('--diagnostic-maps', nargs='+', choices=list(diagnostic_maps()))
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Skip saved games in an existing identical protocol')
    parser.add_argument('--map', type=Path, action='append', default=[])
    parser.add_argument('--profiles', nargs='+', help='Optional names from the profile manifest')
    parser.add_argument('--only-supplied-maps', action='store_true')
    parser.add_argument('--seeds', type=int, nargs='+', default=[5422001, 5422002])
    parser.add_argument('--first-player', choices=['vampires','werewolves','both'], default='vampires')
    parser.add_argument('--stop-on-invalid', action='store_true', help='Save and stop on faults or elapsed times >1.8s')
    args = parser.parse_args()
    manifest_path = args.manifest
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    profiles = {n: s for n, s in manifest['profiles'].items()
                if n != 'control' and (args.profiles is None or n in args.profiles)}
    if not profiles or (args.profiles and set(args.profiles) - profiles.keys()):
        parser.error('Select known experimental profile names (control is the reference)')
    for spec in [manifest['reference'], *profiles.values()]:
        make_agent(spec)  # Fail before creating output if the manifest is invalid.
    if args.only_supplied_maps and not args.map:
        parser.error('--only-supplied-maps requires --map')
    if len(manifest['profiles']) > 5:
        parser.error('At most five configurations including the control are permitted')
    maps = {} if args.only_supplied_maps else diagnostic_maps()
    if args.diagnostic_maps:
        maps = {name: node for name, node in maps.items() if name in args.diagnostic_maps}
    for index, path in enumerate(args.map):
        maps[f'external-{index}-{path.stem}'] = load_map(path)
    if args.first_player == 'both':
        maps = {f'{name}-first-{first}': replace(node,to_play=first)
                for name,node in maps.items() for first in ('vampires','werewolves')}
    elif args.first_player == 'werewolves':
        maps = {name:replace(node,to_play='werewolves') for name,node in maps.items()}
    budget, cap = (.02, 12) if args.smoke else (manifest['budget_seconds'], manifest['max_plies'])
    seeds = args.seeds[:1] if args.smoke else args.seeds
    code = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in [ROOT, ROOT / 'agents', ROOT / 'scripts'] for p in folder.glob('*.py')}
    protocol = dict(created=datetime.now(timezone.utc).isoformat(), simulator_only=True,
                    smoke=args.smoke, budget=budget, max_plies=cap, seeds=seeds,
                    python=sys.version, platform=platform.platform(), profiles=profiles,
                    reference=manifest['reference'], manifest=manifest, code_sha256=code,
                    first_player=args.first_player, stop_on_invalid=args.stop_on_invalid)
    if args.resume:
        old = json.loads((args.output / 'protocol.json').read_text(encoding='utf-8'))
        for field in ('smoke', 'budget', 'max_plies', 'seeds', 'profiles', 'reference', 'manifest', 'first_player'):
            if old.get(field, 'vampires') != protocol[field]:
                parser.error(f'Resume refused: changed {field}')
        for path, digest in old['code_sha256'].items():
            if Path(path).name != Path(__file__).name and code.get(path) != digest:
                parser.error(f'Resume refused: changed source {path}')
        saved_maps = {p.stem for p in (args.output / 'maps').glob('*.xml')}
        if saved_maps != set(maps):
            parser.error('Resume refused: changed map selection')
        for name, node in maps.items():
            if load_map(args.output / 'maps' / f'{name}.xml',to_play=node.to_play).to_dict() != node.to_dict():
                parser.error(f'Resume refused: changed map {name}')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (args.output / f'resume-{stamp}.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
        for name, node in maps.items():
            write_map(node, args.output / 'maps' / f'{name}.xml')
    records = []
    for name, spec in profiles.items():
        reference_name = manifest.get('comparison_reference', {}).get(name, 'control')
        reference = manifest['profiles'][reference_name]
        for map_name, node in maps.items():
            for seed in seeds:
                for species in ('vampires', 'werewolves'):
                    filename = f'{len(records)+1:03}-{name}-{map_name}-{species}.json'
                    saved = args.output / filename
                    if args.resume and saved.exists():
                        record = json.loads(saved.read_text(encoding='utf-8'))
                        expected = dict(profile=name, map=map_name, seed=seed,
                                        candidate_species=species, candidate=spec, reference=reference)
                        if any(record.get(k) != v for k, v in expected.items()):
                            parser.error(f'Resume refused: mismatched game {filename}')
                        records.append({k: v for k, v in record.items() if k not in ('trace', 'timings')})
                        print(f'Skipping saved game {filename}', flush=True)
                        continue
                    # Candidate has each species; --first-player both also swaps
                    # which species starts, giving all four role assignments.
                    def progress(turn):
                        state = dict(profile=name, reference=reference_name, map=map_name,
                                     species=species, seed=seed, completed_games=len(records),
                                     updated=datetime.now(timezone.utc).isoformat(), **turn)
                        (args.output / 'progress.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
                    record = duel(node, spec, reference, species, budget, cap, seed, progress)
                    record.update(profile=name, reference_name=reference_name,
                                  reference=reference, map=map_name, candidate=spec)
                    times = record['timings'][species]
                    metrics = [r['metrics'] for r in record['trace'] if r.get('species') == species]
                    record.update(mean_seconds=sum(times)/max(1,len(times)),
                                  max_seconds=max(times,default=0),
                                  mean_depth=sum(m.get('depth',0) for m in metrics)/max(1,len(metrics)))
                    (args.output / filename).write_text(json.dumps(record, indent=2), encoding='utf-8')
                    records.append({k: v for k, v in record.items() if k not in ('trace', 'timings')})
                    (args.output / 'summary.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
                    if args.stop_on_invalid and (record['faults'] or record['alerts_over_1_8']):
                        (args.output / 'STOPPED_INVALID.json').write_text(json.dumps(dict(
                            game=filename, reason='Agent fault or elapsed time >1.8s; inspect before ranking'),indent=2),encoding='utf-8')
                        raise RuntimeError('Invalid game saved; comparison stopped')
                    print(f'{len(records)} {name} {map_name} {species}: '
                          f'faults={len(record["faults"])} bootstraps={record["bootstraps"]}', flush=True)
    lines = ['# AB2 simulator screening', '',
             '**Functional smoke check only; do not rank playing strength.**' if args.smoke
             else '**Simulator results only; real Windows server verification still required.**',
             '', f'Budget: {budget} s/decision. Cap: {cap} plies.', '',
             '| Profile | Reference | W/D/L | Mean/max seconds | Mean depth | Repeated states | Faults |',
             '|---|---|---|---|---:|---:|---:|']
    for name in profiles:
        group = [r for r in records if r['profile'] == name]
        wins = sum(r['score'] == 1 for r in group)
        draws = sum(r['score'] == .5 for r in group)
        losses = sum(r['score'] == 0 for r in group)
        lines.append(f'| {name} | {group[0]["reference_name"]} | {wins}/{draws}/{losses} | '
                     f'{sum(r["mean_seconds"] for r in group)/len(group):.3f} / '
                     f'{max(r["max_seconds"] for r in group):.3f} | '
                     f'{sum(r["mean_depth"] for r in group)/len(group):.1f} | '
                     f'{sum(r["repetitions"] for r in group)} | '
                     f'{sum(len(r["faults"]) for r in group)} |')
    lines += ['', 'Exploratory small sample; repetitions are full boards with actor.',
              'Reference specifications and exploratory limitations are recorded in protocol.json.',
              f'Alerts >1.8 s: {sum(r["alerts_over_1_8"] for r in records)}.',
              f'Bootstrap decisions: {sum(r["bootstraps"] for r in records)}.']
    (args.output / 'SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (args.output / 'completed.json').write_text(json.dumps(dict(
        completed=datetime.now(timezone.utc).isoformat(), games=len(records)), indent=2), encoding='utf-8')
    return int(any(r['faults'] or r['alerts_over_1_8'] for r in records))


if __name__ == '__main__':
    # Keep Windows awake during an unattended benchmark without changing global
    # power settings or keeping the screen on. Closing the lid/manual sleep can
    # still suspend the machine; the process-scoped request ends on exit.
    import os
    if os.name == 'nt':
        import ctypes
        keep_awake = ctypes.windll.kernel32.SetThreadExecutionState
        if not keep_awake(0x80000001):
            raise RuntimeError('Unable to request Windows to remain awake')
        try:
            raise SystemExit(main())
        finally:
            keep_awake(0x80000000)
    else:
        raise SystemExit(main())
