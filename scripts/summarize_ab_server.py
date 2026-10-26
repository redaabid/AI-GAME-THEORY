"""Summarize only completed real-server records with explicit UI evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def ui_result(path):
    if not path.exists():
        return dict(winner=None, confirmed=False, populations={}, reason='UI missing')
    evidence = json.loads(path.read_text(encoding='utf8'))
    if evidence.get('manual'):
        result = dict(evidence['manual'])
        result['confirmed'] = result.get('winner') is not None
        return result
    tree = '\n'.join(x.get('tree', '') for x in evidence.get('captures', []))
    if not tree:
        return dict(winner=None, confirmed=False, populations={}, reason='Empty UI capture')
    head = tree.split('ID: Board', 1)[0]
    names = []
    for name in re.findall(r'\btexte (AB\d+)\b', head):
        if name.lower() not in names:
            names.append(name.lower())
    counts = [int(float(x.replace(',', '.'))) for x in
              re.findall(r'barre de progression Value: ([\d.,]+)', tree)]
    populations = dict(zip(names, counts)) if len(names) == len(counts) == 2 else {}
    ending = tree.split('ID: messVw', 1)[-1]
    tokens = re.findall(r'\btexte (AB\d+|wins|loses|draw|Draw|tie|Tie)\b', ending)
    compressed = [x for i, x in enumerate(tokens) if not i or x != tokens[i-1]]
    winners = [compressed[i-1].lower() for i, x in enumerate(compressed)
               if x == 'wins' and i and re.fullmatch(r'AB\d+', compressed[i-1])]
    if len(winners) == 1:
        return dict(winner=winners[0], confirmed=True, populations=populations, observed_order=names,
                    reason='WPF names winner explicitly')
    if (any(x.lower() in ('draw', 'tie') for x in compressed) or
            ('texte No winner' in ending and 'texte No looser' in ending)):
        return dict(winner='draw', confirmed=True, populations=populations, observed_order=names,
                    reason='WPF displays draw')
    return dict(winner=None, confirmed=False, populations=populations, observed_order=names,
                reason='No explicit winner/draw found in captured UI')


def summarize(root):
    rows = []
    for path in sorted(root.glob('**/result.json')):
        r = json.loads(path.read_text(encoding='utf8'))
        r['ui'] = ui_result(path.parent/'ui-evidence.json')
        if r['ui']['confirmed'] and r['ui'].get('observed_order', r['order']) != r['order']:
            r['ui'].update(winner=None, confirmed=False,
                           reason='WPF header order differs from the game manifest')
        r['directory'] = path.parent.relative_to(root).as_posix()
        r['server_trace_files'] = [p.name for p in path.parent.glob('trace*')]
        for name, stat in r['bots'].items():
            log = (path.parent/f'{name}.stderr.log').read_text(encoding='utf8', errors='replace')
            stat['fallback_occurrences'] = len(re.findall(r'\bfallback\b', log, re.I))
        rows.append(r)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--max-plies', type=int, help='Restrict comparison to one server ply cap')
    args = p.parse_args()
    attempts = summarize(args.root)
    if args.max_plies is not None:
        attempts = [r for r in attempts if r['max_plies'] == args.max_plies]
    selected = {}
    # Keep every attempt; count each condition once, preferring explicit WPF evidence.
    for row in sorted(attempts, key=lambda r: (r['ui']['confirmed'], r['started'])):
        selected[row['id']] = row
    rows = [selected[key] for key in sorted(selected)]
    text = ['# AB0–AB8 — parties sur le vrai serveur WPF\n',
            'Rapport généré depuis les logs des bots et les captures textuelles de l’interface du serveur. '
            'Les gagnants non lisibles sont laissés non confirmés.\n',
            f'Conditions terminées : **{len(rows)}** ; tentatives conservées : **{len(attempts)}**. '
            f'Résultats explicitement confirmés par WPF : **{sum(r["ui"]["confirmed"] for r in rows)}**.\n',
            '| Partie | Carte | MaxPlays | Ordre (espèces) | Vainqueur WPF | Effectifs (ordre) | Max / moyenne A (s) | Max / moyenne B (s) | >1,8 s A/B | >2 s A/B | Faults A/B | Fallback A/B | Secours internes A/B |',
            '|---|---|---:|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        a, b = r['order']
        aa, bb = r['bots'][a], r['bots'][b]
        def timing(stat):
            return '?' if stat['max_seconds'] is None else f'{stat["max_seconds"]:.3f} / {stat["mean_seconds"]:.3f}'
        pops = r['ui']['populations']
        text.append(f'| [{r["id"]}]({r["directory"]}/result.json) | {r["map"]} | {r["max_plies"]} | {a} ({aa["species"]}) puis {b} ({bb["species"]}) | '
                    f'{r["ui"]["winner"] or "non confirmé"} | {pops.get(a,"?")} / {pops.get(b,"?")} | '
                    f'{timing(aa)} | {timing(bb)} | {aa["alerts_1_8"]}/{bb["alerts_1_8"]} | '
                    f'{aa["violations_2"]}/{bb["violations_2"]} | {aa["faults"]}/{bb["faults"]} | '
                    f'{aa["fallback_occurrences"]}/{bb["fallback_occurrences"]} | '
                    f'{aa["bootstraps"]}/{bb["bootstraps"]} |')
    aggregate = {}
    for r in rows:
        for name, stat in r['bots'].items():
            x = aggregate.setdefault(name, dict(games=0, confirmed=0, wins=0, losses=0, draws=0,
                                                max_seconds=0, faults=0, alerts_1_8=0, violations_2=0,
                                                bootstraps=0, fallback_occurrences=0, turns=0,
                                                total_seconds=0, abnormal_sessions=0, errors=[]))
            x['games'] += 1
            if r['ui']['confirmed']:
                x['confirmed'] += 1
                x['draws' if r['ui']['winner']=='draw' else 'wins' if r['ui']['winner']==name else 'losses'] += 1
            x['max_seconds'] = max(x['max_seconds'], stat['max_seconds'] or 0)
            x['turns'] += stat['turns']
            x['total_seconds'] += (stat['mean_seconds'] or 0) * stat['turns']
            x['abnormal_sessions'] += int(not stat['ended'] or not stat['bye'] or
                                         stat['new_game_failures'] > 0 or any(r['exit_codes']))
            for key in ('faults','alerts_1_8','violations_2','bootstraps','fallback_occurrences'):
                x[key] += stat[key]
            x['errors'].extend(stat['errors'])
    for stat in aggregate.values():
        stat['mean_seconds'] = stat['total_seconds'] / stat['turns'] if stat['turns'] else None
    repeated = [r for r in attempts if r is not selected[r['id']]]
    if repeated:
        text.append('\n## Tentatives conservées hors classement')
        text.extend(f'- Condition {r["id"]} : [{r["directory"]}]({r["directory"]}/result.json), '
                    f'{r["ui"]["reason"]}.' for r in repeated)
    text.extend(['\n## Limites',
                 'Chaque variante est comparée à AB3, pas dans un tournoi complet. '
                 'Les versions réglées peuvent avoir des largeurs différentes : cette campagne '
                 'ne constitue pas une ablation isolant chaque optimisation. Le hasard du serveur '
                 'n’est pas contrôlé par --seed. Les temps imprimés sont arrondis à trois décimales '
                 'et ne remplacent pas une mesure de l’horloge interne du serveur.'])
    suffix = f'-{args.max_plies}' if args.max_plies is not None else ''
    rendered = '\n\n'.join(text)+'\n'
    rendered = re.sub(r'(?m)(^\|[^\n]*\|)\n\n(?=\|)', r'\1\n', rendered)
    (args.root/f'SUMMARY{suffix}.md').write_text(rendered, encoding='utf8')
    (args.root/f'aggregate{suffix}.json').write_text(json.dumps(dict(
        generated=datetime.now(timezone.utc).isoformat(), games=rows, attempts=attempts,
        architectures=aggregate), indent=2), encoding='utf8')
    print(json.dumps(dict(completed=len(rows), confirmed=sum(r['ui']['confirmed'] for r in rows),
                         architectures=aggregate), ensure_ascii=False))


if __name__ == '__main__':
    main()
