"""Compare choices on identical saved positions, untimed at fixed depth.

Includes a common-parameter comparison and the historical selected profiles.
Never starts a server or changes a bot. Chance/quiescence remain explicit.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import TurnContext, make_agent, parse_spec, safe_choose
from game import Cell
from mapgen import random_map
from simulator import load_map


def spec(name, params):
    return name + ':' + ','.join(f'{k}={v!r}' for k, v in params.items())


def saved_positions(game, runtime):
    manifest = json.loads((game/'result.json').read_text(encoding='utf8'))
    initial = load_map(runtime/manifest['map'])
    cells, turn, player = dict(initial.cells), 0, 0
    species = [manifest['bots'][name]['species'] for name in manifest['order']]
    result = []
    for trace in sorted(game.glob('trace*')):
        for line in trace.read_text(encoding='utf8', errors='replace').splitlines():
            m = re.search(r'Coup n.(\d+)', line)
            if m:
                turn = int(m[1])
            m = re.search(r'Tour du joueur #(\d+)', line)
            if m:
                player = int(m[1])
            if 'Trame de UPD:' not in line:
                continue
            frame = bytes.fromhex(line.split('Trame de UPD:')[1].strip().replace('-', ''))
            if frame[:3] != b'UPD' or len(frame) != 4+5*frame[3]:
                raise ValueError('Invalid UPD frame')
            for i in range(frame[3]):
                x, y, h, v, w = frame[4+5*i:9+5*i]
                if h or v or w:
                    cells[x, y] = Cell(h, v, w)
                else:
                    cells.pop((x, y), None)
            if turn in (1, 9, 17, 29):
                result.append((f'{manifest["map"]}-before-{turn}', replace(
                    initial, cells=dict(cells), ply=turn-1, to_play=species[player])))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--ab7', type=Path, required=True)
    p.add_argument('--original-runs', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Use a new directory; previous comparisons will not be replaced')
    selection = json.loads(args.selection.read_text(encoding='utf8'))
    tuned = json.loads(args.ab7.read_text(encoding='utf8'))['spec']
    positions = []
    for folder in ('006-ab2-thetrap-40-1', '026-ab5-testmap2-40-1'):
        positions += saved_positions(args.original_runs/folder, args.runtime)
    positions += [(f'generated-{seed}', random_map(random.Random(seed), 'small'))
                  for seed in range(44001, 44005)]
    if len(positions) != 12:
        raise ValueError('Expected twelve identical-position probes')
    selected = {name: item['selected'] for name, item in selection['architectures'].items()}
    selected |= dict(ab7_new=tuned, legacy='alphabeta')
    _, common = parse_spec(selected['ab3'])
    rows = []
    args.output.mkdir(parents=True)
    for regime in ('common', 'selected'):
        for label, position in positions:
            choices = {}
            for name, original_spec in selected.items():
                agent_name, params = parse_spec(original_spec)
                if regime == 'common' and name != 'legacy':
                    params = common | ({'weights': params['weights']} if 'weights' in params else {})
                current_spec = spec(agent_name, params | dict(depth=2, max_depth=2))
                agent = make_agent(current_spec)
                agent.new_game(position, position.to_play, 42)
                started = time.perf_counter()
                moves, fault = safe_choose(agent, position, TurnContext(None, 40, []))
                info = agent.info or {}
                choices[name] = dict(spec=current_spec, moves=sorted(map(list, moves)), fault=fault,
                                     seconds=time.perf_counter()-started,
                                     depth=info.get('depth'), value=info.get('value'),
                                     nodes=info.get('nodes'), features=info.get('features'))
            record = dict(regime=regime, position=label, rows=position.rows, columns=position.columns,
                          ply=position.ply, to_play=position.to_play,
                          cells=[[x,y,c.humans,c.vampires,c.werewolves]
                                 for (x,y),c in sorted(position.cells.items())], choices=choices)
            rows.append(record)
            (args.output/'decisions.json').write_text(json.dumps(rows, indent=2), encoding='utf8')
            print('PROBED', regime, label, flush=True)
    summary = {}
    for regime in ('common', 'selected'):
        subset = [r for r in rows if r['regime'] == regime]
        summary[regime] = {name: dict(different_from_ab3=sum(
            r['choices'][name]['moves'] != r['choices']['ab3']['moves'] for r in subset),
            faults=sum(bool(r['choices'][name]['fault']) for r in subset)) for name in selected}
    report = dict(depth=2, max_plies=40, deadline=None, source_sha=subprocess.check_output(
        ['git','-c','safe.directory=*','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), summary=summary,
        note='Fixed depth is not equal time. Quiescence extends AB5 and chance changes AB6 semantics. '
             'Equal moves are expected for search optimizations on the same tree; tie choices can differ. '
             'Values from the legacy agent use a different scale and are not compared numerically.')
    (args.output/'summary.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
