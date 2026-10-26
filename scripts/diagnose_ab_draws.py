"""Read-only state-repetition diagnostics from course-server UPD traces."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def analyze(game, root, runtime):
    directory = root/game['directory']
    mapsrc = runtime/game['map']
    if hashlib.sha256(mapsrc.read_bytes()).hexdigest() != game['map_sha256']:
        raise ValueError('Map fingerprint differs from tested manifest')
    cells = {}
    for element in ET.fromstring(mapsrc.read_text(encoding='utf-8-sig')):
        values = [0, 0, 0]
        values[{'Humans': 0, 'Vampires': 1, 'Werewolves': 2}[element.tag]] = int(element.get('Count'))
        cells[int(element.get('X')), int(element.get('Y'))] = tuple(values)
    traces = sorted(directory.glob('trace*'))
    if not traces:
        return dict(id=game['id'], trace_missing=True)
    seen, observations, repeats = {}, [], []
    ply = 0
    for trace in traces:
        for line in trace.read_text(encoding='utf8', errors='replace').splitlines():
            match = re.search(r'Coup n.([0-9]+)', line)
            if match:
                ply = int(match[1])
            if 'Trame de UPD:' not in line:
                continue
            frame = bytes.fromhex(line.split('Trame de UPD:', 1)[1].strip().replace('-', ''))
            if frame[:3] != b'UPD' or len(frame) != 4+5*frame[3]:
                raise ValueError('Malformed UPD frame')
            for i in range(frame[3]):
                x, y, h, v, w = frame[4+5*i:9+5*i]
                if h or v or w:
                    cells[x, y] = (h, v, w)
                else:
                    cells.pop((x, y), None)
            key = (ply % 2, tuple(sorted(cells.items())))
            if key in seen:
                repeats.append(dict(ply=ply, repeated_ply=seen[key]))
            seen.setdefault(key, ply)
            vg = [p for p, c in cells.items() if c[1]]
            wg = [p for p, c in cells.items() if c[2]]
            distances = [max(abs(a[0]-b[0]), abs(a[1]-b[1])) for a in vg for b in wg]
            observations.append(dict(pre_move_ply=ply,
                                     populations=[sum(c[i] for c in cells.values()) for i in range(3)],
                                     nearest_enemy_distance=min(distances, default=None)))
    return dict(id=game['id'], map=game['map'], max_plies=game['max_plies'],
                ui_winner=game['ui']['winner'], ui_confirmed=game['ui']['confirmed'],
                observed_server_plies=max((x['pre_move_ply'] for x in observations), default=0),
                reached_cap=any(x['pre_move_ply'] == game['max_plies'] for x in observations),
                state_observations=len(observations), unique_states=len(seen),
                repeated_states=len(repeats), first_repeats=repeats[:10],
                first=observations[0] if observations else None,
                last=observations[-1] if observations else None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('runtime', type=Path)
    args = p.parse_args()
    aggregate = json.loads((args.root/'aggregate.json').read_text(encoding='utf8'))
    records = [analyze(game, args.root, args.runtime) for game in aggregate['games']]
    output = dict(note='States are reconstructed before each MOV from server UPDs. '
                  'The last observation precedes the final move and is not a substitute for the WPF final result. '
                  'A repeated state includes the player to move. No winner is inferred.', games=records)
    (args.root/'draw-diagnostics.json').write_text(json.dumps(output, indent=2), encoding='utf8')
    print(json.dumps([dict(id=r['id'], cap=r.get('max_plies'), reached_cap=r.get('reached_cap'),
                           repeats=r.get('repeated_states'), winner=r.get('ui_winner')) for r in records]))


if __name__ == '__main__':
    main()
