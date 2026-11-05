"""Autonomous five-agent simulator screening, then independent finalist check.

80 screening games: ten pairs, two symmetric maps, four species/first roles.
16 confirmation games: two provisional finalists, two fresh maps, four roles,
two battle seeds. Budget 1.5 s, cap 200. Every game is saved; --resume skips
finished games and checks protocol/code fingerprints. No LLM calls or WPF.
"""
import argparse
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_ab2_experiments import diagnostic_maps, duel
from mapgen import random_map, write_map


def dump(path, obj):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    temporary.replace(path)


def ranking(games, names):
    stats = {n: dict(name=n, games=0, wins=0, draws=0, losses=0, points=0.,
                     seconds=0., decisions=0, max_seconds=0., faults=0,
                     repeated_states=0) for n in names}
    for game in games:
        for key, species in (('a', game['candidate_species']),
                             ('b', 'werewolves' if game['candidate_species']=='vampires' else 'vampires')):
            row = stats[game[key]]
            score = game['score'] if key == 'a' else 1-game['score']
            times = game['timings'][species]
            row['games'] += 1
            row['wins'] += score == 1
            row['draws'] += score == .5
            row['losses'] += score == 0
            row['points'] += score
            row['seconds'] += sum(times)
            row['decisions'] += len(times)
            row['max_seconds'] = max([row['max_seconds'], *times])
            row['faults'] += sum(f['species']==species for f in game['faults'])
            row['repeated_states'] += game['repetitions']
    for row in stats.values():
        row['score_rate'] = row['points']/max(1,row['games'])
        row['mean_seconds'] = row['seconds']/max(1,row['decisions'])
    # Repetition is a declared secondary screening criterion only. It does
    # not prove superiority, and ties by primary score are explicitly retained.
    return sorted(stats.values(), key=lambda r: (-r['score_rate'], r['faults'],
                                                r['repeated_states'], r['name']))


def write_report(out, games, final_games, names, finalists=None):
    lines = ['# AB2 paired simulator tournament', '',
             '**Exploratory simulator evidence; real-server confirmation remains required.**',
             '', 'Budget: 1.5 s/decision; cap: 200 plies; all species and first-player roles.',
             'Primary criterion: win=1, draw=0.5. Secondary screening tie-break: fewer repeated states.',
             'Equal scores remain inconclusive; a tie-break is not a statistical result.', '']
    for title, records, participants in [('Screening', games, names),
                                           ('Fresh-map confirmation', final_games, finalists or [])]:
        if not records:
            continue
        lines += [f'## {title}', '',
                  '| Agent | Games | W/D/L | Score | Mean/max s | Faults |',
                  '|---|---:|---|---:|---|---:|']
        for row in ranking(records, participants):
            lines.append(f'| {row["name"]} | {row["games"]} | '
                         f'{row["wins"]}/{row["draws"]}/{row["losses"]} | '
                         f'{row["score_rate"]:.3f} | {row["mean_seconds"]:.3f} / '
                         f'{row["max_seconds"]:.3f} | {row["faults"]} |')
        lines.append('')
    if finalists:
        lines += [f'Provisional finalists: {", ".join(finalists)}.',
                  'Selected after screening only; no weights are adjusted on confirmation maps.', '']
    dump(out/'ranking.json', dict(screening=ranking(games,names),
                                  confirmation=ranking(final_games,finalists) if finalists else []))
    (out/'SUMMARY.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--smoke', action='store_true', help='Functional checks only, .02 s and 8 plies')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'scripts/ab2_distant_profiles.json').read_text())
    specs=manifest['profiles']
    if len(specs)!=5:
        parser.error('Exactly five frozen configurations required')
    budget, cap=(.02,8) if args.smoke else (1.5,200)
    fixtures=diagnostic_maps()
    maps={'contact':fixtures['tactical-contact'], 'distant':fixtures['distant-recruitment']}
    holdouts={f'fresh-{seed}':random_map(random.Random(seed),'medium')
              for seed in (20054231,20054232)}
    code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for folder in [ROOT, ROOT/'agents',ROOT/'scripts'] for p in folder.glob('*.py')}
    protocol=dict(manifest=manifest,budget=budget,cap=cap,smoke=args.smoke,
                  maps={k:v.to_dict() for k,v in maps.items()},
                  holdouts={k:v.to_dict() for k,v in holdouts.items()},
                  seeds_screen=[5422901], seeds_confirm=[5422911,5422912], code=code)
    if args.resume:
        old=json.loads((args.output/'protocol.json').read_text())
        if old['protocol']!=protocol:
            parser.error('Resume refused: changed source, configuration or maps')
    else:
        args.output.mkdir(parents=True,exist_ok=False)
        dump(args.output/'protocol.json',dict(protocol=protocol,python=sys.version,
             machine=platform.platform(),created=datetime.now(timezone.utc).isoformat()))
        for name,node in dict(maps,**holdouts).items():
            write_map(node,args.output/'maps'/f'{name}.xml')
    out=args.output
    def run(stage, pairs, mapset, seeds):
        records=[]
        for a,b in pairs:
            for map_name,initial in mapset.items():
                for seed in seeds:
                    for first in ('vampires','werewolves'):
                        for species in ('vampires','werewolves'):
                            filename=f'{stage}-{a}-{b}-{map_name}-{seed}-{first}-{species}.json'
                            target=out/filename
                            if target.exists():
                                record=json.loads(target.read_text())
                            else:
                                def progress(turn):
                                    dump(out/'progress.json',dict(stage=stage,a=a,b=b,
                                         map=map_name,first=first,species=species,
                                         stage_completed=len(records),
                                         updated=datetime.now(timezone.utc).isoformat(),**turn))
                                record=duel(replace(initial,to_play=first),specs[a],specs[b],
                                            species,budget,cap,seed,progress)
                                record.update(a=a,b=b,map=map_name,first=first,stage=stage)
                                dump(target,record)
                            records.append(record)
                            if record['faults'] or record['alerts_over_1_8']:
                                dump(out/'STOPPED_INVALID.json',dict(game=filename,
                                     reason='Fault or elapsed time >1.8s; investigate before ranking'))
                                raise RuntimeError('Stopped on invalid game; raw result saved')
                            print(f'{stage}: {len(records)} games saved',flush=True)
                            if stage=='screen':
                                write_report(out,records,[],list(specs))
                            else:
                                write_report(out,screened,records,list(specs),finalists)
        return records
    screened=run('screen',list(combinations(specs,2)),maps,[5422901])
    rows=ranking(screened,list(specs))
    finalists=[r['name'] for r in rows[:2]]
    tied=[r['name'] for r in rows if r['score_rate']==rows[1]['score_rate']]
    dump(out/'finalists.json',dict(names=finalists,primary_score_ties_at_cutoff=tied,
                                  note='Secondary tie-break is exploratory, not evidence of superiority'))
    confirmed=run('confirm',[tuple(finalists)],holdouts,[5422911,5422912])
    write_report(out,screened,confirmed,list(specs),finalists)
    dump(out/'completed.json',dict(screening_games=len(screened),confirmation_games=len(confirmed),
                                  completed=datetime.now(timezone.utc).isoformat()))


if __name__=='__main__':
    if os.name=='nt':
        import ctypes
        wake=ctypes.windll.kernel32.SetThreadExecutionState
        if not wake(0x80000001):
            raise RuntimeError('Unable to request Windows remain awake')
        try:
            main()
        finally:
            wake(0x80000000)
    else:
        main()
